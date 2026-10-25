"""Owned W3 request identity around one public direction-only trace.

Validation constructs immutable SI records without tracing. Scientific failures
and final representation failures remain separate; neither produces a partial
successful route.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ohlab.optics.refractive_routing import (
    RefractiveScene, RefractiveTraceResult, NumericalAmbiguityError,
    UnsupportedNumericalInputError, MediumStateAmbiguityError,
    trace_routes, validate_scene,
)

from .adapter import NumericalError
from .refractive_routing_protocol import (
    encode_trace_result, encode_validation_reply, json_bytes, scene_digest,
    validate_digest, validate_request_id,
)


class RefractiveNumericalError(NumericalError):
    """Declared numerical/medium admission or tracing failure, never a miss."""

    def __init__(self, message: str, *, code: str = "numerical_failure") -> None:
        if code not in {"numerical_failure", "numerical_ambiguity",
                        "medium_state_ambiguity", "unsupported_numerical_input"}:
            raise ValueError("unsupported W3 numerical error code")
        self.code = code
        super().__init__(message)


def _owned_scene(value: object) -> RefractiveScene:
    try:
        return validate_scene(value)
    except MediumStateAmbiguityError as exc:
        raise RefractiveNumericalError(str(exc), code="medium_state_ambiguity") from exc
    except NumericalAmbiguityError as exc:
        raise RefractiveNumericalError(str(exc), code="numerical_ambiguity") from exc
    except UnsupportedNumericalInputError as exc:
        raise RefractiveNumericalError(str(exc), code="unsupported_numerical_input") from exc


@dataclass(frozen=True, kw_only=True)
class ValidatedRefractiveSubmission:
    """Complete immutable scene, canonical UUID and opaque SHA256 ownership."""

    request_id: str
    scene: RefractiveScene
    scene_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request_id(self.request_id)
        if not isinstance(self.scene, RefractiveScene):
            raise TypeError("scene: expected public RefractiveScene")
        owned = _owned_scene(self.scene)
        object.__setattr__(self, "scene", owned)
        object.__setattr__(self, "scene_sha256", scene_digest(owned.to_dict()))


def validate_submission(payload: object, *, trace: bool = False) -> ValidatedRefractiveSubmission:
    """Admit the exact W3 request without tracing; distances are metres."""
    if type(trace) is not bool:
        raise TypeError("trace: expected bool")
    if type(payload) is not dict:
        raise TypeError("submission: expected plain object")
    expected = {"request_id", "scene", "scene_sha256"} if trace else {"request_id", "scene"}
    if set(payload) != expected:
        raise ValueError("submission: incorrect closed W3 envelope")
    request_id = validate_request_id(payload["request_id"])
    digest = validate_digest(payload["scene_sha256"]) if trace else None
    submission = ValidatedRefractiveSubmission(request_id=request_id,
                                               scene=_owned_scene(payload["scene"]))
    if trace and digest != submission.scene_sha256:
        raise ValueError("scene_sha256: differs from complete submitted W3 scene")
    return submission


def validation_reply(submission: ValidatedRefractiveSubmission) -> bytes:
    """Encode authoritative validated metadata without taking the worker gate."""
    if not isinstance(submission, ValidatedRefractiveSubmission):
        raise TypeError("submission: expected ValidatedRefractiveSubmission")
    scene = submission.scene
    return encode_validation_reply(submission.request_id, scene.to_dict(),
        media=[item.to_dict() for item in scene.media],
        body_faces=[item.to_dict() for item in scene.body_faces],
        legacy_surface_frames=[item.to_dict() for item in scene.legacy_surface_frames],
        limits=scene.limits.to_dict())


def trace_submission(submission: ValidatedRefractiveSubmission) -> bytes:
    """Trace once, then validate/encode inside the same actual worker lifetime."""
    if not isinstance(submission, ValidatedRefractiveSubmission):
        raise TypeError("submission: expected ValidatedRefractiveSubmission")
    try:
        result = trace_routes(submission.scene)
    except MediumStateAmbiguityError as exc:
        raise RefractiveNumericalError(str(exc), code="medium_state_ambiguity") from exc
    except NumericalAmbiguityError as exc:
        raise RefractiveNumericalError(str(exc), code="numerical_ambiguity") from exc
    except UnsupportedNumericalInputError as exc:
        raise RefractiveNumericalError(str(exc), code="unsupported_numerical_input") from exc
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise RefractiveNumericalError(str(exc)) from exc
    if not isinstance(result, RefractiveTraceResult):
        raise TypeError("public W3 trace returned an unexpected result type")
    value = result.to_dict()
    if (type(value) is not dict or "scene" not in value
            or json_bytes(value["scene"], canonical=True) !=
            json_bytes(submission.scene.to_dict(), canonical=True)):
        raise ValueError("trace result differs from captured W3 scene identity")
    # Representation errors are not numerical outcomes or successful misses.
    return encode_trace_result(submission.request_id, submission.scene_sha256, value)
