"""Version-one run bundles: exact bytes, explicit provenance, measured replay.

This I/O boundary orchestrates the unchanged M2/M3/M4 public functions. It
does not implement optics, initialize a second RNG, or invoke Git. SHA-256
checks integrity relative to a manifest, not authorship or authenticity.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import importlib.metadata
import io
import math
import os
from pathlib import Path
import platform
import re
import stat
import struct
import sys
import tempfile
import time
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray
import scipy

from .. import __version__
from ..algorithms import GerchbergSaxtonResult, gerchberg_saxton
from ..field import ComplexField
from ..grid import SamplingGrid
from ..metrics import (
    intensity_mse, intensity_nmse, intensity_psnr,
    regional_intensity_cv, signal_region_power_fraction,
)
from ..targets import intensity_to_amplitude
from .config import RunConfig, _json_bytes, _parse_json
from .images import load_target_intensity

__all__ = [
    "run_and_save_bundle", "verify_run_bundle", "load_run_bundle",
    "replay_run_bundle",
]

_PARTIAL = ".ohlab-partial-"
_SPEC_KEYS = {"schema_version", "grid", "optics", "solver", "metrics"}
_DTYPES = {
    "target_intensity": "f8", "target_amplitude": "f8",
    "source_amplitude": "f8", "source_field": "c16", "phase": "f8",
    "reconstruction_field": "c16", "reconstruction_intensity": "f8",
    "residual_history": "f8", "initial_phase": "f8",
    "signal_mask": "b1", "cv_mask": "b1",
}
_OPTIONAL_ARRAYS = {"initial_phase", "signal_mask", "cv_mask"}
_BASE_ARRAYS = set(_DTYPES) - _OPTIONAL_ARRAYS
_ALLOWED_FILES = {f"{role}.npy": role for role in _DTYPES} | {
    "config.json": "config", "metrics.json": "metrics",
    "input_target.png": "input_target",
}
_ENV_STRINGS = {
    "python_implementation", "python_version", "numpy_version", "scipy_version",
    "platform", "machine", "processor", "byteorder", "fft",
}


def _object(value: object, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name}: expected an object, got {type(value).__name__}")
    actual = set(value)
    if actual != keys:
        raise ValueError(f"{name}: expected keys {sorted(keys)}, got {sorted(map(str, actual))}")
    return dict(value)


def _version(value: object, name: str) -> None:
    if type(value) is not int or value != 1:
        raise ValueError(f"{name}: expected schema_version 1, got {value!r}")


def _source_record(value: Mapping[str, object] | None) -> dict[str, Any]:
    if value is None:
        return {"revision": None, "state": "unavailable", "method": "caller"}
    record = _object(value, {"revision", "state", "method"}, "source provenance")
    if record["state"] not in ("clean", "dirty", "unavailable"):
        raise ValueError("source provenance state: expected clean, dirty or unavailable")
    if record["method"] not in ("caller", "git"):
        raise ValueError("source provenance method: expected caller or git")
    revision = record["revision"]
    if record["state"] == "unavailable":
        if revision is not None:
            raise ValueError("unavailable source provenance must have null revision")
    elif not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("source revision: expected an exact 40-character lowercase Git SHA")
    return record


def _environment(include_png: bool) -> dict[str, Any]:
    pillow = None
    if include_png:
        try:
            pillow = importlib.metadata.version("Pillow")
        except importlib.metadata.PackageNotFoundError:
            pass  # An unavailable decoder makes qualification fail, never installs it.
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": sys.version, "numpy_version": np.__version__,
        "scipy_version": scipy.__version__, "pillow_version": pillow,
        "platform": platform.platform(), "machine": platform.machine(),
        "processor": platform.processor(), "byteorder": sys.byteorder,
        "pointer_bits": struct.calcsize("P") * 8, "fft": "numpy.fft",
    }


def _software(source: Mapping[str, object] | None, include_png: bool) -> dict[str, Any]:
    return {
        "ohlab_version": __version__, "source": _source_record(source),
        "required_environment": _environment(include_png),
        "informational_environment": {
            "python_executable": sys.executable, "cpu_count": os.cpu_count(),
        },
    }


def _validate_software(value: object, include_png: bool) -> dict[str, Any]:
    software = _object(value, {
        "ohlab_version", "source", "required_environment", "informational_environment",
    }, "software")
    if not isinstance(software["ohlab_version"], str) or not software["ohlab_version"]:
        raise ValueError("software.ohlab_version: expected nonempty string")
    software["source"] = _source_record(software["source"])
    env = _object(software["required_environment"],
                  _ENV_STRINGS | {"pillow_version", "pointer_bits"}, "required_environment")
    if any(not isinstance(env[key], str) for key in _ENV_STRINGS):
        raise TypeError("required_environment: expected string-valued version/platform fields")
    if env["byteorder"] not in ("little", "big") or env["fft"] != "numpy.fft":
        raise ValueError("required_environment: unsupported byte order or FFT identifier")
    if type(env["pointer_bits"]) is not int or env["pointer_bits"] not in (32, 64):
        raise ValueError("required_environment.pointer_bits: expected 32 or 64")
    if include_png:
        if not isinstance(env["pillow_version"], str) or not env["pillow_version"]:
            raise ValueError("PNG provenance requires a recorded Pillow version")
    elif env["pillow_version"] is not None:
        raise ValueError("array-only capture requires null pillow_version")
    info = _object(software["informational_environment"],
                   {"python_executable", "cpu_count"}, "informational_environment")
    if not isinstance(info["python_executable"], str):
        raise TypeError("python_executable: expected string")
    if info["cpu_count"] is not None and (type(info["cpu_count"]) is not int or info["cpu_count"] < 1):
        raise ValueError("cpu_count: expected positive integer or null")
    return software


def _grid(spec: dict[str, Any]) -> SamplingGrid:
    settings = spec["grid"]
    return SamplingGrid(ny=settings["ny"], nx=settings["nx"],
                        dy=settings["dy_m"], dx=settings["dx_m"])


def _roles(spec: dict[str, Any]) -> set[str]:
    roles = _BASE_ARRAYS.copy()
    if spec["solver"]["initialization"]["mode"] == "explicit_phase":
        roles.add("initial_phase")
    if "signal_region_power_fraction" in spec["metrics"]:
        roles.add("signal_mask")
    if "regional_intensity_cv" in spec["metrics"]:
        roles.add("cv_mask")
    return roles


def _document(config: RunConfig, software: dict[str, Any], include_png: bool) -> dict[str, Any]:
    return config.to_dict() | {
        "target": {
            "representation": "normalized_m2_intensity", "mapping": "sqrt_intensity",
            "intensity": "target_intensity.npy", "amplitude": "target_amplitude.npy",
            "input_png": "input_target.png" if include_png else None,
        },
        "source": {"amplitude": "source_amplitude.npy"},
        "replay": {"criterion": "bitwise_v1", "array_order": "C"},
        "software": software,
    }


def _read_document(value: object) -> tuple[RunConfig, dict[str, Any], bool]:
    doc = _object(value, _SPEC_KEYS | {"target", "source", "replay", "software"}, "config.json")
    config = RunConfig({key: doc[key] for key in _SPEC_KEYS})
    target = _object(doc["target"],
                     {"representation", "mapping", "intensity", "amplitude", "input_png"}, "target")
    if target["input_png"] not in (None, "input_target.png"):
        raise ValueError("target.input_png: expected null or input_target.png")
    include_png = target["input_png"] is not None
    software = _validate_software(doc["software"], include_png)
    expected = _document(config, software, include_png)
    for section in ("target", "source", "replay"):
        if doc[section] != expected[section]:
            raise ValueError(f"config.{section}: expected schema-v1 fixed contract {expected[section]!r}")
    return config, software, include_png


def _array_snapshot(value: object, role: str, shape: tuple[int, ...]) -> np.ndarray:
    if type(value) is not np.ndarray:
        raise TypeError(f"{role}: expected plain numpy.ndarray, got {type(value).__name__}")
    dtype = np.dtype(_DTYPES[role])
    if value.dtype != dtype or not value.dtype.isnative:
        raise TypeError(f"{role}: expected native {dtype}, got {value.dtype}")
    if value.shape != shape:
        raise ValueError(f"{role}: expected shape {shape}, got {value.shape}")
    if dtype.kind != "b" and not bool(np.all(np.isfinite(value))):
        raise ValueError(f"{role}: expected finite values")
    if role in {"target_intensity", "target_amplitude", "source_amplitude", "reconstruction_intensity", "residual_history"}:
        if bool(np.any(value < 0)):
            raise ValueError(f"{role}: expected nonnegative values")
    if role in {"target_intensity", "target_amplitude"} and bool(np.any(value > 1)):
        raise ValueError(f"{role}: expected normalized M2 values in [0, 1]")
    return np.array(value, order="C", copy=True)


def _same_array(a: np.ndarray, b: np.ndarray) -> bool:
    return a.dtype.str == b.dtype.str and a.shape == b.shape and a.tobytes(order="C") == b.tobytes(order="C")


def _metrics(spec: dict[str, Any], arrays: Mapping[str, np.ndarray], intensity: np.ndarray) -> dict[str, float]:
    values = {}
    for name, parameters in spec["metrics"].items():
        pair = {"target_intensity": arrays["target_intensity"], "reconstruction_intensity": intensity}
        if name == "intensity_mse":
            value = intensity_mse(**pair)
        elif name == "intensity_nmse":
            value = intensity_nmse(**pair)
        elif name == "intensity_psnr":
            value = intensity_psnr(**pair, data_range=parameters["data_range"])
        elif name == "signal_region_power_fraction":
            value = signal_region_power_fraction(reconstruction_intensity=intensity, signal_mask=arrays["signal_mask"])
        else:
            value = regional_intensity_cv(intensity=intensity, mask=arrays["cv_mask"])
        values[name] = value
    return values


def _metric_document(values: Mapping[str, float]) -> dict[str, Any]:
    return {"schema_version": 1, "values": {
        key: "+inf" if key == "intensity_psnr" and value == math.inf else value
        for key, value in values.items()
    }}


def _read_metrics(value: object, names: set[str]) -> dict[str, float]:
    doc = _object(value, {"schema_version", "values"}, "metrics.json")
    _version(doc["schema_version"], "metrics.json")
    raw = _object(doc["values"], names, "metrics.values")
    values = {}
    for name, item in raw.items():
        if name == "intensity_psnr" and item == "+inf":
            values[name] = math.inf
            continue
        if type(item) not in (float, int):
            raise TypeError(f"metrics.{name}: expected finite number or PSNR '+inf', got {item!r}")
        try:
            number = float(item)
        except OverflowError as exc:
            raise ValueError(f"metrics.{name}: value is outside binary64") from exc
        if not math.isfinite(number) or (name != "intensity_psnr" and number < 0):
            raise ValueError(f"metrics.{name}: invalid numerical value {item!r}")
        # Retain M4's actual finite result. Differing selected/full reduction
        # orders can round a mathematical fraction of one slightly above one;
        # the artifact boundary must not clamp or tighten the numerical API.
        values[name] = number
    return values


def _outputs(result: GerchbergSaxtonResult) -> dict[str, np.ndarray]:
    return {role: np.array(array, order="C", copy=True) for role, array in {
        "source_field": result.source_field.data, "phase": result.phase,
        "reconstruction_field": result.reconstruction.data,
        "reconstruction_intensity": result.reconstruction.intensity,
        "residual_history": result.residual_history,
    }.items()}


def _solve(spec: dict[str, Any], arrays: Mapping[str, np.ndarray]) -> GerchbergSaxtonResult:
    initialization = spec["solver"]["initialization"]
    init = {"seed": initialization["seed"]} if initialization["mode"] == "seed" else {"initial_phase": arrays["initial_phase"]}
    return gerchberg_saxton(
        target_amplitude=arrays["target_amplitude"], source_amplitude=arrays["source_amplitude"],
        grid=_grid(spec), wavelength_m=spec["optics"]["wavelength_m"],
        distance_m=spec["optics"]["distance_m"], iterations=spec["solver"]["iterations"], **init,
    )


def _npy_bytes(array: np.ndarray) -> bytes:
    stream = io.BytesIO()
    np.lib.format.write_array(stream, array, version=(1, 0), allow_pickle=False)
    return stream.getvalue()


def _load_npy(data: bytes, entry: dict[str, Any], role: str, shape: tuple[int, ...], byteorder: str) -> np.ndarray:
    stream = io.BytesIO(data)
    try:
        version = np.lib.format.read_magic(stream)
        if version != (1, 0):
            raise ValueError(f"expected NPY 1.0, got {version}")
        stored_shape, fortran_order, dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=10000)
        kind = _DTYPES[role]
        expected_dtype = np.dtype(kind if kind == "b1" else ("<" if byteorder == "little" else ">") + kind)
        if dtype != expected_dtype or dtype.hasobject or dtype.fields is not None:
            raise ValueError(f"expected dtype {expected_dtype.str}, got {dtype!r}")
        if stored_shape != shape or fortran_order:
            raise ValueError(f"expected C-order shape {shape}, got {stored_shape}, fortran_order={fortran_order}")
        if entry["dtype"] != dtype.str or entry["shape"] != list(shape) or entry["order"] != "C":
            raise ValueError("manifest array metadata disagrees with role/config/header")
        required_size = stream.tell() + math.prod(shape) * dtype.itemsize
        if len(data) != required_size:
            raise ValueError(f"expected exactly {required_size} bytes, got {len(data)} (truncation/trailing bytes)")
        stream.seek(0)
        array = np.load(stream, allow_pickle=False, mmap_mode=None, max_header_size=10000)
        if stream.tell() != len(data):
            raise ValueError("unexpected trailing bytes")
    except (ValueError, TypeError, EOFError, OSError) as exc:
        raise ValueError(f"{role}.npy: invalid NPY artifact: {exc}") from exc
    # Header and exact payload size were checked before NumPy could allocate.
    if dtype.kind != "b" and not bool(np.all(np.isfinite(array))):
        raise ValueError(f"{role}: expected finite array values")
    if role in {"target_intensity", "target_amplitude", "source_amplitude", "reconstruction_intensity", "residual_history"}:
        if bool(np.any(array < 0)):
            raise ValueError(f"{role}: expected nonnegative values")
    if role in {"target_intensity", "target_amplitude"} and bool(np.any(array > 1)):
        raise ValueError(f"{role}: expected normalized M2 values in [0, 1]")
    # Retain stored byte order on load; qualification decides native replay.
    array = np.array(array, order="C", copy=True)
    array.flags.writeable = False
    return array


def _path(value: str | os.PathLike[str]) -> Path:
    if not isinstance(value, (str, os.PathLike)) or not isinstance(os.fspath(value), str):
        raise TypeError("bundle path: expected str or PathLike[str]")
    return Path(value).absolute()


def _no_link(path: Path, *, directory: bool) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError(f"{path}: symlinks and reparse points are unsupported")
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError(f"{path}: expected {'directory' if directory else 'regular file'}")


def _public_path(value: str | os.PathLike[str]) -> Path:
    path = _path(value)
    if path.name.lower().startswith(_PARTIAL):
        raise ValueError(f"{path}: partial staging directories are not completed bundles")
    return path


@dataclass(frozen=True)
class _IntegrityReport:
    status: str
    files: tuple[str, ...]


@dataclass(frozen=True, eq=False)
class _RunBundle:
    path: Path
    config: RunConfig
    arrays: Mapping[str, np.ndarray]
    metrics: Mapping[str, float]
    _software_bytes: bytes

    @property
    def software(self) -> dict[str, Any]:
        """Fresh metadata copy; changing it cannot alter the loaded bundle."""
        return _parse_json(self._software_bytes, "software")


@dataclass(frozen=True)
class _ReplayReport:
    integrity: str
    qualification: str
    comparison: str
    qualification_reasons: tuple[str, ...]
    checks: Mapping[str, bool]
    recorded_source: Mapping[str, object]
    current_source: Mapping[str, object]


def _verified_snapshots(path: Path) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    _no_link(path, directory=True)
    actual = {entry.name for entry in path.iterdir()}
    if "manifest.json" not in actual:
        raise ValueError("manifest.json: missing required file")
    for name in actual:
        if name != "manifest.json" and name not in _ALLOWED_FILES:
            raise ValueError(f"bundle inventory: extra/unsupported file {name!r}")
        _no_link(path / name, directory=False)
    manifest = _object(_parse_json((path / "manifest.json").read_bytes(), "manifest.json"),
                       {"schema_version", "hash_algorithm", "artifacts"}, "manifest.json")
    _version(manifest["schema_version"], "manifest.json")
    if manifest["hash_algorithm"] != "sha256" or type(manifest["artifacts"]) is not list:
        raise ValueError("manifest: expected sha256 and an artifacts list")
    entries = {}
    names = []
    for record in manifest["artifacts"]:
        if not isinstance(record, dict):
            raise TypeError("manifest artifact: expected an object")
        name = record.get("path")
        if not isinstance(name, str) or name not in _ALLOWED_FILES:
            raise ValueError(f"manifest path {name!r}: expected a schema-defined flat filename")
        if name in entries:
            raise ValueError(f"manifest: duplicate artifact path {name!r}")
        role = _ALLOWED_FILES[name]
        keys = {"logical_name", "path", "size_bytes", "sha256"}
        if role in _DTYPES:
            keys |= {"dtype", "shape", "order"}
        entry = _object(record, keys, f"manifest {name}")
        if entry["logical_name"] != role:
            raise ValueError(f"manifest {name}: expected logical name {role!r}")
        if type(entry["size_bytes"]) is not int or entry["size_bytes"] < 0:
            raise ValueError(f"manifest {name}: invalid size_bytes")
        if not isinstance(entry["sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is None:
            raise ValueError(f"manifest {name}: expected lowercase SHA-256 digest")
        if role in _DTYPES:
            if (not isinstance(entry["dtype"], str) or type(entry["shape"]) is not list
                    or not entry["shape"] or any(type(n) is not int or n < 1 for n in entry["shape"])
                    or entry["order"] != "C"):
                raise ValueError(f"manifest {name}: invalid dtype/shape/C-order metadata")
        names.append(name)
        entries[name] = entry
    if names != sorted(names):
        raise ValueError("manifest artifacts: expected deterministic path ordering")
    if actual != set(entries) | {"manifest.json"}:
        raise ValueError(f"bundle inventory mismatch: missing {sorted(set(entries)-actual)}, extra {sorted(actual-set(entries)-{'manifest.json'})}")
    if not {"config.json", "metrics.json"}.issubset(entries):
        raise ValueError("manifest: missing config.json or metrics.json")
    snapshots = {}
    # No config/metric/NPY interpretation occurs until EVERY digest passes.
    for name, entry in entries.items():
        data = (path / name).read_bytes()
        if len(data) != entry["size_bytes"]:
            raise ValueError(f"{name}: byte length mismatch, expected {entry['size_bytes']}, got {len(data)}")
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"{name}: SHA-256 digest mismatch")
        snapshots[name] = data
    return snapshots, entries


def _validated_contents(path: Path) -> tuple[_RunBundle, _IntegrityReport]:
    snapshots, entries = _verified_snapshots(path)
    config, software, include_png = _read_document(_parse_json(snapshots["config.json"], "config.json"))
    spec = config.to_dict()
    expected_roles = _roles(spec)
    expected_files = {f"{role}.npy" for role in expected_roles} | {"config.json", "metrics.json"}
    if include_png:
        expected_files.add("input_target.png")
    if set(snapshots) != expected_files:
        raise ValueError(f"conditional inventory: expected {sorted(expected_files)}, got {sorted(snapshots)}")
    shape = (spec["grid"]["ny"], spec["grid"]["nx"])
    arrays = {}
    for role in sorted(expected_roles):
        array_shape = (spec["solver"]["iterations"] + 1,) if role == "residual_history" else shape
        arrays[role] = _load_npy(snapshots[f"{role}.npy"], entries[f"{role}.npy"], role, array_shape,
                                 software["required_environment"]["byteorder"])
    values = _read_metrics(_parse_json(snapshots["metrics.json"], "metrics.json"), set(spec["metrics"]))
    bundle = _RunBundle(path, config, MappingProxyType(arrays), MappingProxyType(values), _json_bytes(software))
    return bundle, _IntegrityReport("passed", tuple(sorted(entries)))


def _write_file(path: Path, data: bytes, owned: list[Path]) -> None:
    with path.open("xb") as stream:
        # Register only after exclusive creation succeeded. A conflicting
        # foreign file must never become eligible for this call's cleanup.
        owned.append(path)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _publish(stage: Path, destination: Path) -> None:
    # Windows can transiently deny a directory rename after all of our file
    # handles have closed. Never retry an existing destination or a different
    # error. Four attempts / at most 140 ms of explicit waits are bounded;
    # exhaustion preserves the FIRST OS error and ordinary owned cleanup.
    delays = (0.01, 0.03, 0.10)
    first_error = None
    for attempt in range(len(delays) + 1):
        try:
            os.rename(stage, destination)
            return
        except PermissionError as exc:
            if os.name != "nt" or getattr(exc, "winerror", None) != 5:
                raise
            if first_error is None:
                first_error = exc
            if os.path.lexists(destination) or attempt == len(delays):
                raise first_error
            time.sleep(delays[attempt])
            if os.path.lexists(destination):
                raise first_error


def run_and_save_bundle(
    path: str | os.PathLike[str], *, config: RunConfig,
    target_intensity: NDArray[np.float64], source_amplitude: NDArray[np.float64],
    source_revision: Mapping[str, object] | None = None,
    initial_phase: NDArray[np.float64] | None = None,
    signal_mask: NDArray[np.bool_] | None = None,
    cv_mask: NDArray[np.bool_] | None = None,
    input_png: str | os.PathLike[str] | None = None,
) -> _RunBundle:
    """Compute and exclusively publish a schema-v1 M2/M3/M4 bundle.

    Config pitches/wavelength/distance are metres; phase is radians; target
    intensity is normalized design intensity in [0,1]. Source amplitude is
    explicitly supplied in a.u.; the unchanged solver checks power. Plain
    native arrays are copied to owned C storage without casting or scaling.
    Optional PNG bytes must decode to exactly the captured target. Masks and
    initial_phase are required exactly when specified by config.

    Parent directory must exist. Existing destinations are never intentionally
    replaced. Publication uses a temporary sibling, file fsync, validation and
    rename. Windows no-clobber behavior is tested; concurrent POSIX writers and
    power-loss durability are not guaranteed. Git is never invoked here.

    Return a verified loaded bundle (owned read-only arrays, immutable config,
    read-only metrics, defensive software copy). TypeError denotes wrong input
    types/dtypes; ValueError denotes invalid schema/data/integrity. Filesystem
    OSError subclasses remain intact; cleanup failures are added as notes.
    """
    destination = _public_path(path)
    if os.path.lexists(destination):
        raise FileExistsError(f"bundle destination already exists: {destination}")
    _no_link(destination.parent, directory=True)
    if not isinstance(config, RunConfig):
        raise TypeError("config: expected RunConfig")
    spec = config.to_dict()
    grid = _grid(spec)
    arrays = {
        "target_intensity": _array_snapshot(target_intensity, "target_intensity", grid.shape),
        "source_amplitude": _array_snapshot(source_amplitude, "source_amplitude", grid.shape),
    }
    supplied = {"initial_phase": initial_phase, "signal_mask": signal_mask, "cv_mask": cv_mask}
    required = _roles(spec)
    for role, value in supplied.items():
        if (value is not None) != (role in required):
            raise ValueError(f"{role}: must be supplied exactly when required by configuration")
        if value is not None:
            arrays[role] = _array_snapshot(value, role, grid.shape)
    arrays["target_amplitude"] = intensity_to_amplitude(arrays["target_intensity"], grid=grid)
    software = _software(source_revision, input_png is not None)
    document = _document(config, software, input_png is not None)
    _read_document(document)
    stage = Path(tempfile.mkdtemp(prefix=_PARTIAL, dir=destination.parent))
    owned: list[Path] = []
    published = False
    try:
        files = {}
        if input_png is not None:
            encoded = _path(input_png).read_bytes()
            png_path = stage / "input_target.png"
            _write_file(png_path, encoded, owned)
            decoded = load_target_intensity(png_path, grid=grid)
            if not _same_array(decoded, arrays["target_intensity"]):
                raise ValueError("input_target.png: decoded intensity differs from captured target bits")
            files["input_target.png"] = encoded
        arrays.update(_outputs(_solve(spec, arrays)))
        values = _metrics(spec, arrays, arrays["reconstruction_intensity"])
        files.update({f"{role}.npy": _npy_bytes(array) for role, array in arrays.items()})
        files["config.json"] = _json_bytes(document)
        files["metrics.json"] = _json_bytes(_metric_document(values))
        entries = []
        for name, data in sorted(files.items()):
            target_path = stage / name
            if name != "input_target.png":
                _write_file(target_path, data, owned)
            entry = {"logical_name": _ALLOWED_FILES[name], "path": name,
                     "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            if name.endswith(".npy"):
                array = arrays[_ALLOWED_FILES[name]]
                entry.update(dtype=array.dtype.str, shape=list(array.shape), order="C")
            entries.append(entry)
        manifest_path = stage / "manifest.json"
        _write_file(manifest_path, _json_bytes({"schema_version": 1, "hash_algorithm": "sha256", "artifacts": entries}), owned)
        _validated_contents(stage)
        # Preflight helps ordinary callers on every OS. Windows rename also
        # atomically refuses a destination introduced after this check.
        if os.path.lexists(destination):
            raise FileExistsError(f"bundle destination appeared during save: {destination}")
        _publish(stage, destination)
        published = True
    except BaseException as exc:
        if not published:
            cleanup_errors = []
            for owned_path in reversed(owned):
                try:
                    if os.path.lexists(owned_path):
                        _no_link(owned_path, directory=False)
                        owned_path.unlink()
                except OSError as cleanup_exc:
                    cleanup_errors.append(str(cleanup_exc))
                except ValueError as cleanup_exc:
                    cleanup_errors.append(str(cleanup_exc))
            try:
                stage.rmdir()
            except OSError as cleanup_exc:
                cleanup_errors.append(str(cleanup_exc))
            if cleanup_errors:
                exc.add_note(f"cleanup failed; staging remains at {stage}: {'; '.join(cleanup_errors)}")
        raise
    return load_run_bundle(destination)


def verify_run_bundle(path: str | os.PathLike[str]) -> _IntegrityReport:
    """Validate inventory, file hashes and schema without running optics.

    Return status='passed' and the tuple of hashed filenames on success.
    Integrity is relative to the unsigned manifest. Public partial directories
    are rejected; no public skip-validation option exists. Invalid artifacts
    raise contextual errors, never a success report.
    """
    return _validated_contents(_public_path(path))[1]


def load_run_bundle(path: str | os.PathLike[str]) -> _RunBundle:
    """Verify then load owned read-only arrays and validated run metadata.

    Decode the same snapshots whose hashes passed; no original PNG path, live
    input arrays or original directory is needed. PNG provenance bytes are
    hashed but not decoded during loading. No pickle or arbitrary objects.
    """
    return _validated_contents(_public_path(path))[0]


def replay_run_bundle(
    path: str | os.PathLike[str], *,
    source_revision: Mapping[str, object] | None = None, diagnostic: bool = False,
) -> _ReplayReport:
    """Recompute from saved inputs and compare exact arrays/scalars.

    Runtime environment is independently collected now; current source is an
    explicit caller/detector record, NEVER copied from the bundle. Matching
    clean SHAs qualify under this metadata policy, not as code attestation.
    Unqualified default requests report comparison='not_run'. Explicit
    diagnostic=True may compute but cannot promote qualification. Foreign
    byte order blocks native-core execution and also reports 'not_run'.

    Results separate integrity, qualification and numerical comparison. Checks
    name saved derivations, saved-data metric recomputation, each replay array,
    and each replay metric. Arrays compare dtype/shape/C-order bytes; finite
    metrics compare binary64 bits, +inf PSNR compares semantically. No allclose,
    normalization, seed substitution or automatic environment repair occurs.
    """
    if type(diagnostic) is not bool:
        raise TypeError("diagnostic: expected bool")
    bundle = load_run_bundle(path)
    recorded = bundle.software
    spec = bundle.config.to_dict()
    include_png = recorded["required_environment"]["pillow_version"] is not None
    current = _software(source_revision, include_png)
    reasons = []
    for label, record in (("recorded", recorded["source"]), ("current", current["source"])):
        if record["state"] != "clean":
            reasons.append(f"{label} source state is {record['state']}, expected clean")
    if recorded["source"]["revision"] != current["source"]["revision"]:
        reasons.append("source revision mismatch")
    if recorded["ohlab_version"] != current["ohlab_version"]:
        reasons.append("ohlab_version mismatch")
    for key, value in recorded["required_environment"].items():
        if current["required_environment"][key] != value:
            reasons.append(f"required_environment.{key} mismatch")
    qualification = "unqualified" if reasons else "qualified"
    checks: dict[str, bool] = {}
    comparison = "not_run"
    if not reasons or diagnostic:
        arrays = bundle.arrays
        # A foreign endian format remains inspectable but cannot be passed to
        # the unchanged native-array core. Report the mismatch without casting.
        if any(not value.dtype.isnative for value in arrays.values()):
            checks["native_array_byteorder"] = False
        else:
            expected_amplitude = intensity_to_amplitude(arrays["target_intensity"], grid=_grid(spec))
            checks["derived:target_amplitude"] = _same_array(expected_amplitude, arrays["target_amplitude"])
            saved_result = GerchbergSaxtonResult(
                source_field=ComplexField(data=arrays["source_field"], grid=_grid(spec), wavelength_m=spec["optics"]["wavelength_m"]),
                reconstruction=ComplexField(data=arrays["reconstruction_field"], grid=_grid(spec), wavelength_m=spec["optics"]["wavelength_m"]),
                residual_history=arrays["residual_history"],
            )
            checks["derived:phase"] = _same_array(saved_result.phase, arrays["phase"])
            checks["derived:reconstruction_intensity"] = _same_array(saved_result.reconstruction.intensity, arrays["reconstruction_intensity"])
            saved_metrics = _metrics(spec, arrays, arrays["reconstruction_intensity"])
            replayed = _outputs(_solve(spec, arrays))
            for role, actual in replayed.items():
                checks[f"output:{role}"] = _same_array(actual, arrays[role])
            replay_metrics = _metrics(spec, arrays, replayed["reconstruction_intensity"])
            for name, expected in bundle.metrics.items():
                for prefix, actual in (("saved_metric", saved_metrics[name]), ("replay_metric", replay_metrics[name])):
                    checks[f"{prefix}:{name}"] = (actual == expected if math.isinf(expected)
                        else struct.pack(">d", actual) == struct.pack(">d", expected))
            comparison = "passed" if all(checks.values()) else "failed"
    return _ReplayReport("passed", qualification, comparison, tuple(reasons), MappingProxyType(checks),
                         MappingProxyType(recorded["source"]), MappingProxyType(current["source"]))
