"""Owned W2 request identity around the one public geometric trace.

No geometry formula, I/O or presentation lives here. Validation constructs
the complete immutable SI scene and frames but never invokes trace_routes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ohlab.optics.geometric_routing import (
    GeometricScene, GeometricTraceResult, NumericalAmbiguityError,
    UnsupportedNumericalInputError, trace_routes, validate_scene,
)

from .adapter import NumericalError
from .geometric_routing_protocol import (
    encode_trace_result, encode_validation_reply, json_bytes, scene_digest,
    validate_digest, validate_request_id,
)


class RoutingNumericalError(NumericalError):
    """A validated W2 trace is ambiguous or outside supported arithmetic."""

    def __init__(self, message: str, *, code: str = "numerical_failure") -> None:
        if code not in {"numerical_ambiguity", "unsupported_numerical_input", "numerical_failure"}:
            raise ValueError("unsupported W2 numerical error code")
        self.code = code
        super().__init__(message)


def _owned_scene(value: object) -> GeometricScene:
    """Preserve declared arithmetic failures during pure scene admission."""
    try:
        return validate_scene(value)
    except NumericalAmbiguityError as exc:
        raise RoutingNumericalError(str(exc), code="numerical_ambiguity") from exc
    except UnsupportedNumericalInputError as exc:
        raise RoutingNumericalError(str(exc), code="unsupported_numerical_input") from exc


@dataclass(frozen=True, kw_only=True)
class ValidatedGeometricSubmission:
    """Immutable UUID, complete owned scene and opaque canonical digest."""

    request_id: str
    scene: GeometricScene
    scene_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request_id(self.request_id)
        if not isinstance(self.scene, GeometricScene):
            raise TypeError("scene: expected public GeometricScene")
        owned = _owned_scene(self.scene)
        object.__setattr__(self, "scene", owned)
        object.__setattr__(self, "scene_sha256", scene_digest(owned.to_dict()))


def validate_submission(payload: object, *, trace: bool = False) -> ValidatedGeometricSubmission:
    """Validate exact scene submission without tracing; all positions are m.

    Trace requires the opaque SHA256 returned by validation. No cached scene,
    result or client-owned mutable JSON is retained by this stateless adapter.
    """
    if type(trace) is not bool:
        raise TypeError("trace: expected bool")
    if type(payload) is not dict:
        raise TypeError("submission: expected plain object")
    expected = {"request_id", "scene", "scene_sha256"} if trace else {"request_id", "scene"}
    if set(payload) != expected:
        raise ValueError("submission: incorrect closed W2 envelope")
    request_id = validate_request_id(payload["request_id"])
    supplied_digest = validate_digest(payload["scene_sha256"]) if trace else None
    scene = _owned_scene(payload["scene"])
    submission = ValidatedGeometricSubmission(request_id=request_id, scene=scene)
    if trace and supplied_digest != submission.scene_sha256:
        raise ValueError("scene_sha256: differs from complete submitted scene")
    return submission


def validation_reply(submission: ValidatedGeometricSubmission) -> bytes:
    """Encode owned scene/frames, with no trace or computation-gate operation."""
    if not isinstance(submission, ValidatedGeometricSubmission):
        raise TypeError("submission: expected ValidatedGeometricSubmission")
    return encode_validation_reply(submission.request_id, submission.scene.to_dict(),
                                   [frame.to_dict() for frame in submission.scene.surface_frames])


def trace_submission(submission: ValidatedGeometricSubmission) -> bytes:
    """Invoke public W2 once, then validate/encode within actual worker lifetime."""
    if not isinstance(submission, ValidatedGeometricSubmission):
        raise TypeError("submission: expected ValidatedGeometricSubmission")
    try:
        result = trace_routes(submission.scene)
    except NumericalAmbiguityError as exc:
        raise RoutingNumericalError(str(exc), code="numerical_ambiguity") from exc
    except UnsupportedNumericalInputError as exc:
        raise RoutingNumericalError(str(exc), code="unsupported_numerical_input") from exc
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise RoutingNumericalError(str(exc)) from exc
    if not isinstance(result, GeometricTraceResult):
        raise TypeError("public trace returned an unexpected result type")
    value = result.to_dict()
    if (type(value) is not dict or "scene" not in value
            or json_bytes(value["scene"], canonical=True) != json_bytes(submission.scene.to_dict(), canonical=True)):
        raise ValueError("trace result differs from captured scene identity")
    # Encoding failures deliberately remain outside the numerical-exception
    # conversion. They are not a successful partial trace or a numerical miss.
    return encode_trace_result(submission.request_id, submission.scene_sha256, value)
