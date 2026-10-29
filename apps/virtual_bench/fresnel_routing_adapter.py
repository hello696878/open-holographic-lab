"""Owned W4 submissions around one public Fresnel-power routing operation.

Pure validation never traces. Numerical admission, scientific failure and final
representation failure remain distinct; no partial graph is published.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ohlab.optics.fresnel_routing import (
    FresnelScene, FresnelTraceResult, NumericalAmbiguityError,
    UnsupportedNumericalInputError, MediumStateAmbiguityError,
    UnsupportedPolarizationNumericsError, validate_fresnel_scene,
    trace_fresnel_scene,
)

from .adapter import NumericalError
from .fresnel_routing_protocol import (
    encode_trace_result, encode_validation_reply, json_bytes, scene_digest,
    validate_digest, validate_request_id,
)


class FresnelNumericalError(NumericalError):
    """Declared numerical/medium failure, never an escaped or truncated ray."""

    def __init__(self, message: str, *, code: str = "numerical_failure") -> None:
        if code not in {"numerical_failure", "numerical_ambiguity",
                        "medium_state_ambiguity", "unsupported_numerical_input",
                        "unsupported_polarization_numerics"}:
            raise ValueError("unsupported W4 numerical error code")
        self.code = code
        super().__init__(message)


def _owned_scene(value: object) -> FresnelScene:
    try:
        return validate_fresnel_scene(value)
    except UnsupportedPolarizationNumericsError as exc:
        raise FresnelNumericalError(str(exc), code="unsupported_polarization_numerics") from exc
    except MediumStateAmbiguityError as exc:
        raise FresnelNumericalError(str(exc), code="medium_state_ambiguity") from exc
    except NumericalAmbiguityError as exc:
        raise FresnelNumericalError(str(exc), code="numerical_ambiguity") from exc
    except UnsupportedNumericalInputError as exc:
        raise FresnelNumericalError(str(exc), code="unsupported_numerical_input") from exc


@dataclass(frozen=True, kw_only=True)
class ValidatedFresnelSubmission:
    """Immutable owned SI scene, canonical request UUID and complete digest."""

    request_id: str
    scene: FresnelScene
    scene_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request_id(self.request_id)
        if not isinstance(self.scene, FresnelScene):
            raise TypeError("scene: expected public FresnelScene")
        owned = _owned_scene(self.scene)
        object.__setattr__(self, "scene", owned)
        object.__setattr__(self, "scene_sha256", scene_digest(owned.to_dict()))


def validate_submission(payload: object, *, trace: bool = False) -> ValidatedFresnelSubmission:
    """Admit the exact W4 request without tracing; lengths are metres."""
    if type(trace) is not bool:
        raise TypeError("trace: expected bool")
    if type(payload) is not dict:
        raise TypeError("submission: expected plain object")
    expected = {"request_id", "scene", "scene_sha256"} if trace else {"request_id", "scene"}
    if set(payload) != expected:
        raise ValueError("submission: incorrect closed W4 envelope")
    request_id = validate_request_id(payload["request_id"])
    digest = validate_digest(payload["scene_sha256"]) if trace else None
    submission = ValidatedFresnelSubmission(request_id=request_id,
                                           scene=_owned_scene(payload["scene"]))
    if trace and digest != submission.scene_sha256:
        raise ValueError("scene_sha256: differs from complete submitted W4 scene")
    return submission


def validation_reply(submission: ValidatedFresnelSubmission) -> bytes:
    """Encode authoritative admission metadata without taking the worker gate."""
    if not isinstance(submission, ValidatedFresnelSubmission):
        raise TypeError("submission: expected ValidatedFresnelSubmission")
    scene = submission.scene
    return encode_validation_reply(submission.request_id, scene.to_dict(),
        media=[item.to_dict() for item in scene.media],
        body_faces=[item.to_dict() for item in scene.body_faces],
        terminal_frames=[item.to_dict() for item in scene.terminal_frames],
        limits=scene.limits.to_dict())


def trace_submission(submission: ValidatedFresnelSubmission) -> bytes:
    """Call the public runner once and encode within that actual worker lifetime."""
    if not isinstance(submission, ValidatedFresnelSubmission):
        raise TypeError("submission: expected ValidatedFresnelSubmission")
    try:
        result = trace_fresnel_scene(submission.scene)
    except UnsupportedPolarizationNumericsError as exc:
        raise FresnelNumericalError(str(exc), code="unsupported_polarization_numerics") from exc
    except MediumStateAmbiguityError as exc:
        raise FresnelNumericalError(str(exc), code="medium_state_ambiguity") from exc
    except NumericalAmbiguityError as exc:
        raise FresnelNumericalError(str(exc), code="numerical_ambiguity") from exc
    except UnsupportedNumericalInputError as exc:
        raise FresnelNumericalError(str(exc), code="unsupported_numerical_input") from exc
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise FresnelNumericalError(str(exc)) from exc
    if not isinstance(result, FresnelTraceResult):
        raise TypeError("public W4 trace returned an unexpected result type")
    value = result.to_dict()
    if (type(value) is not dict or "scene" not in value or
            json_bytes(value["scene"], canonical=True) !=
            json_bytes(submission.scene.to_dict(), canonical=True)):
        raise ValueError("trace result differs from captured W4 scene identity")
    return encode_trace_result(submission.request_id, submission.scene_sha256, value)
