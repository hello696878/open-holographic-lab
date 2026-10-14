"""Bounded settings-only documents around the unchanged bench validators.

All scientific lengths are SI metres and angles radians. Parsing, validation
and canonical encoding allocate no scientific fields and perform no optics or
file access. Document identity is separate from the existing scientific hash.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from types import MappingProxyType

from .adapter import strict_json_loads, validate_experiment as validate_sequential
from .two_path_adapter import validate_experiment as validate_two_path
from .polarization_adapter import PolarizationExperiment
from .polarized_two_path_adapter import PolarizedTwoPathExperiment
from .protocol import experiment_digest as sequential_digest
from .two_path_protocol import experiment_digest as two_path_digest
from .polarization_protocol import experiment_digest as polarization_digest
from .polarized_two_path_protocol import experiment_digest as polarized_two_path_digest

DOCUMENT_FORMAT = "ohlab_virtual_experiment"
DOCUMENT_VERSION = 1
POLARIZED_TWO_PATH_DOCUMENT_VERSION = 2
POLARIZED_TWO_PATH_MODEL_CONTRACT = "v2g_ideal_polarized_two_path_v1"
MAX_DOCUMENT_BYTES = 32_768
MAX_CONTAINER_DEPTH = 12
MAX_VALUE_NODES = 2048
MAX_STRING_SCALARS = 8192
MAX_TITLE_SCALARS = 120
MAX_NOTES_SCALARS = 2000
EXPERIMENT_SHA256_HEADER = "X-OHLab-Experiment-SHA256"
MODEL_CONTRACTS = MappingProxyType({
    "sequential": "v0_aligned_scalar_forward_v1",
    "two_path": "v2b_unfolded_scalar_two_path_v1",
    "polarization": "v2d_ideal_jones_same_plane_v1",
})


class DocumentError(ValueError):
    """A bounded settings/schema failure with an explicit HTTP422 code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _document_float(token: str) -> float:
    value = float(token)
    coefficient = token.lower().split("e", 1)[0]
    if not math.isfinite(value) or (value == 0.0 and any(c in "123456789" for c in coefficient)):
        raise ValueError("document JSON number is not usable finite binary64")
    return value


def _document_integer(token: str) -> int:
    value = int(token)
    try:
        finite = math.isfinite(float(value))
    except OverflowError as exc:
        raise ValueError("document JSON integer exceeds finite binary64") from exc
    if not finite:
        raise ValueError("document JSON integer exceeds finite binary64")
    return value


def strict_document_loads(data: bytes) -> object:
    """Parse original <=32768 UTF-8 bytes before any lossy reserialization.

    The unchanged bench parser rejects duplicates/constants/overflow first.
    A second stdlib decode adds the document's unusable-number policy;
    it is not a replacement JSON grammar or a change to existing route policy.
    """
    if type(data) is not bytes:
        raise TypeError("document JSON: expected bytes")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ValueError("document JSON exceeds 32768 bytes")
    parsed = strict_json_loads(data)
    try:
        json.loads(data.decode("utf-8"), parse_float=_document_float, parse_int=_document_integer)
    except RecursionError as exc:
        raise ValueError("document JSON nesting exceeds parser capacity") from exc
    return parsed


def _text(value: str, path: tuple[str, ...]) -> None:
    code = "invalid_metadata" if path[:1] == ("metadata",) else "invalid_document"
    if len(value) > MAX_STRING_SCALARS:
        raise DocumentError("document_structure_limit", "decoded string exceeds 8192 Unicode scalars")
    permitted = {9, 10} if path == ("metadata", "notes") else set()
    for character in value:
        point = ord(character)
        if 0xD800 <= point <= 0xDFFF:
            raise DocumentError(code, "text contains a lone surrogate")
        if (point < 32 or 127 <= point <= 159) and point not in permitted:
            raise DocumentError(code, "text contains a forbidden control character")


def _structure(payload: object) -> None:
    """Bound decoded containers/values/text before any mode construction."""
    if type(payload) is not dict:
        raise DocumentError("invalid_document", "document: expected JSON object")
    pending = [(payload, 0, ())]
    nodes = 0
    while pending:
        value, depth, path = pending.pop()
        nodes += 1
        if nodes > MAX_VALUE_NODES:
            raise DocumentError("document_structure_limit", "document exceeds 2048 value nodes")
        if type(value) in (dict, list):
            if depth > MAX_CONTAINER_DEPTH:
                raise DocumentError("document_structure_limit", "container depth exceeds 12")
            if type(value) is dict:
                for key, item in value.items():
                    if type(key) is not str:
                        raise DocumentError("invalid_document", "object keys must be strings")
                    _text(key, path + ("<key>",))
                    pending.append((item, depth + 1, path + (key,)))
            else:
                pending.extend((item, depth + 1, path + (str(index),)) for index, item in enumerate(value))
        elif type(value) is str:
            _text(value, path)
        elif type(value) is float:
            if not math.isfinite(value):
                raise DocumentError("invalid_document", "numbers must be finite binary64")
        elif value is not None and type(value) not in (int, bool):
            raise DocumentError("invalid_document", "document contains a non-JSON value")


def _keys(value: object, names: set[str], context: str, code: str) -> dict[str, object]:
    if type(value) is not dict:
        raise DocumentError(code, f"{context}: expected JSON object")
    if set(value) != names:
        missing, unknown = names - set(value), set(value) - names
        raise DocumentError(code, f"{context}: missing {sorted(missing)}, unknown {sorted(unknown)}; expected {sorted(names)}")
    return value


@dataclass(frozen=True, kw_only=True)
class ValidatedDocument:
    """Owned immutable canonical bytes and transient existing scientific digest."""

    canonical_bytes: bytes
    experiment_sha256: str

    def to_dict(self) -> dict[str, object]:
        """Return fresh owned JSON containers, never an alias of caller data."""
        return json.loads(self.canonical_bytes.decode("utf-8"))


def validate_document(payload: object) -> ValidatedDocument:
    """Validate one closed settings document; sample/apply/run no science."""
    _structure(payload)
    value = _keys(payload, {"document_format", "document_version", "mode", "model_contract",
                            "experiment", "metadata"}, "document", "invalid_document")
    if value["document_format"] != DOCUMENT_FORMAT:
        raise DocumentError("invalid_document", f"document_format: expected {DOCUMENT_FORMAT}")
    version = value["document_version"]
    if type(version) is not int or version not in (DOCUMENT_VERSION, POLARIZED_TWO_PATH_DOCUMENT_VERSION):
        raise DocumentError("unsupported_document_version", "document_version: expected supported integer 1 or 2")
    mode = value["mode"]
    if version == DOCUMENT_VERSION:
        if type(mode) is not str or mode not in MODEL_CONTRACTS:
            raise DocumentError("unsupported_document_mode", "version 1 mode: expected sequential, two_path or polarization")
        model = MODEL_CONTRACTS[mode]
    else:
        if type(mode) is str and mode in MODEL_CONTRACTS:
            raise DocumentError("unsupported_document_version", "old modes require document_version 1")
        if mode != "polarized_two_path":
            raise DocumentError("unsupported_document_mode", "version 2 mode: expected polarized_two_path")
        model = POLARIZED_TWO_PATH_MODEL_CONTRACT
    if value["model_contract"] != model:
        raise DocumentError("unsupported_model_contract", f"model_contract: expected {model}")
    metadata = _keys(value["metadata"], {"title", "notes"}, "metadata", "invalid_metadata")
    for name, cap in (("title", MAX_TITLE_SCALARS), ("notes", MAX_NOTES_SCALARS)):
        if type(metadata[name]) is not str or len(metadata[name]) > cap:
            raise DocumentError("invalid_metadata", f"metadata.{name}: expected string with at most {cap} Unicode scalars")
    try:
        if mode == "sequential":
            experiment = validate_sequential(value["experiment"])
            digest = sequential_digest(experiment)
        elif mode == "two_path":
            experiment = validate_two_path(value["experiment"])
            digest = two_path_digest(experiment.to_dict())
        elif mode == "polarization":
            experiment = PolarizationExperiment.from_dict(value["experiment"])
            digest = polarization_digest(experiment.to_dict())
        else:
            experiment = PolarizedTwoPathExperiment.from_dict(value["experiment"])
            digest = polarized_two_path_digest(experiment.to_dict())
    except (ValueError, TypeError, OverflowError) as exc:
        raise DocumentError("invalid_experiment", str(exc)) from exc
    owned = {"document_format": DOCUMENT_FORMAT, "document_version": version,
             "mode": mode, "model_contract": model,
             "experiment": experiment.to_dict(),
             "metadata": {"title": metadata["title"], "notes": metadata["notes"]}}
    encoded = (json.dumps(owned, sort_keys=True, indent=2, ensure_ascii=False,
                          allow_nan=False) + "\n").encode("utf-8")
    if len(encoded) > MAX_DOCUMENT_BYTES:
        raise DocumentError("canonical_document_too_large", "canonical document exceeds 32768 UTF-8 bytes")
    return ValidatedDocument(canonical_bytes=encoded, experiment_sha256=digest)


def document_from_json(data: bytes) -> ValidatedDocument:
    """Validate original document bytes and export canonical settings in SI."""
    return validate_document(strict_document_loads(data))
