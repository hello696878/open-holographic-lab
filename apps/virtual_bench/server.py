r"""Loopback-only built bench and distinct bounded same-origin optics APIs.

Run from the repository root with the existing interpreter::

    .\.venv\Scripts\python.exe -B -X utf8 -m apps.virtual_bench.server

No server or executor thread starts on import. Running Python computations
continue after HTTP disconnect/abort; the gate follows their actual lifetime.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from contextlib import asynccontextmanager
import os
from pathlib import Path
import re
import socket
import stat
import sys
import threading
from typing import Callable

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import ClientDisconnect, Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from .adapter import (NumericalError, ValidatedSubmission, simulate_submission, strict_json_loads,
                      validate_submission)
from .protocol import (MAX_BODY_BYTES, MAX_RESPONSE_BYTES, PROTOCOL_VERSION,
                       validate_request_id)
from . import two_path_adapter
from .two_path_protocol import (MAX_RESPONSE_BYTES as MAX_TWO_PATH_RESPONSE_BYTES,
                                MAX_SWEEP_RESPONSE_BYTES, SweepReply)
from . import polarization_adapter, polarization_protocol
from . import experiment_documents
from . import polarized_two_path_adapter, polarized_two_path_protocol
from . import r03_fig2a_adapter, r03_fig2a_protocol
from . import wave_field_adapter, wave_field_protocol
from . import geometric_routing_adapter, geometric_routing_protocol
from . import refractive_routing_adapter, refractive_routing_protocol

Submission = (ValidatedSubmission | two_path_adapter.ValidatedTwoPathSubmission |
              two_path_adapter.ValidatedSweepSubmission |
              polarization_adapter.ValidatedPolarizationSubmission |
              polarization_adapter.ValidatedPolarizationSweepSubmission |
              polarized_two_path_adapter.ValidatedPolarizedTwoPathSubmission |
              polarized_two_path_adapter.ValidatedPolarizedTwoPathSweepSubmission |
              r03_fig2a_adapter.ValidatedIdealSubmission |
              wave_field_adapter.ValidatedWaveFieldSubmission |
              geometric_routing_adapter.ValidatedGeometricSubmission |
              refractive_routing_adapter.ValidatedRefractiveSubmission)
WorkerResult = bytes | SweepReply | polarization_protocol.SweepReply | polarized_two_path_protocol.SweepReply

HOST = "127.0.0.1"
PORT = 8510
AUTHORITY = f"{HOST}:{PORT}"
ORIGIN = f"http://{AUTHORITY}"
BODY_TIMEOUT_SECONDS = 5.0
DEFAULT_ASSETS = Path(__file__).resolve().parents[2] / "frontend" / "bench" / "dist"
_HEADER_TOKEN = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_STATIC_SUFFIXES = {".html", ".js", ".css", ".png", ".svg", ".ico", ".webp"}
_SECURITY_HEADERS = {
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "cross-origin-resource-policy": "same-origin",
    "referrer-policy": "no-referrer",
    "content-security-policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self' data:; font-src 'self'; "
        "worker-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    ),
}


def _error(status: int, code: str, message: str,
           request_id: str | None = None) -> JSONResponse:
    return JSONResponse({"protocol_version": PROTOCOL_VERSION,
                         "request_id": request_id,
                         "error": {"code": code, "message": message[:300]}},
                        status_code=status)


def _boundary_error(scope: Scope, status: int, code: str, message: str) -> Response:
    """Keep the two W3 API paths closed even before their body is trusted.

    Shared legacy HTTP errors retain their original bytes and headers. W3 has
    no trusted request UUID at this boundary and maps admission errors to its
    declared invalid_scene code while preserving the actual HTTP status.
    """
    if scope.get("path") in {"/api/w3/validate", "/api/w3/trace"}:
        return Response(refractive_routing_protocol.error_reply(None, "invalid_scene", message),
                        status_code=status, media_type="application/json", headers=_SECURITY_HEADERS)
    return _error(status, code, message)


class BusyError(RuntimeError):
    """A computation owns the sole gate; no compute queue is accepted."""


class CancelledBeforeStart(RuntimeError):
    """The executor Future was cancelled before the worker could start."""


class ComputationGate:
    """Single worker gate tied to concurrent Future completion, not HTTP lifetime.

The done callback runs after execution/encoding terminates, or after a Future
is successfully cancelled before starting. Running threads cannot be cancelled.
Submission failure releases the reservation immediately. No result history is
retained by this object. ``wait_idle`` exists for controlled synchronization.
"""

    def __init__(self, worker: Callable[[Submission], WorkerResult],
                 executor: Executor | None = None) -> None:
        self._worker = worker
        self._executor = executor if executor is not None else ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="v1-optics")
        self._lock = threading.Lock()
        self._reserved = False
        self._idle = threading.Event()
        self._idle.set()

    @property
    def busy(self) -> bool:
        """Whether an accepted computation has not reached terminal state."""
        with self._lock:
            return self._reserved

    def submit(self, submission: Submission) -> Future[WorkerResult]:
        """Reserve and submit once; reject concurrently accepted work."""
        with self._lock:
            if self._reserved:
                raise BusyError("a computation is still running")
            self._reserved = True
            self._idle.clear()
        try:
            future = self._executor.submit(self._worker, submission)
        except BaseException:
            with self._lock:
                self._reserved = False
                self._idle.set()
            raise
        future.add_done_callback(self._completed)
        return future

    def _completed(self, future: Future[WorkerResult]) -> None:
        with self._lock:
            self._reserved = False
            self._idle.set()

    def wait_idle(self, timeout_seconds: float) -> bool:
        """Wait for actual gate release, with a bounded timeout in seconds."""
        return self._idle.wait(timeout_seconds)

    def shutdown(self) -> None:
        """Finish running work and cancel only not-yet-started work on shutdown."""
        self._executor.shutdown(wait=True, cancel_futures=True)


class LocalBoundary:
    """Exact Host/Origin and duplicate-header policy without public CORS."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers: dict[bytes, bytes] = {}
        for raw_name, value in scope.get("headers", []):
            name = raw_name.lower()
            if (not _HEADER_TOKEN.fullmatch(raw_name) or name in headers or
                    any(byte < 32 and byte != 9 or byte == 127 for byte in value)):
                await _boundary_error(scope, 400, "invalid_headers", "Malformed or duplicate HTTP headers")(
                    scope, receive, send)
                return
            headers[name] = value
        if headers.get(b"host") != AUTHORITY.encode("ascii"):
            await _boundary_error(scope, 400, "invalid_host", "Expected local bench Host")(
                scope, receive, send)
            return
        origin = headers.get(b"origin")
        if (origin is not None and origin != ORIGIN.encode("ascii")) or (
                scope["method"] == "POST" and origin != ORIGIN.encode("ascii")):
            await _boundary_error(scope, 403, "invalid_origin", "Expected the same local bench Origin")(
                scope, receive, send)
            return

        async def secured_send(message: dict) -> None:
            if message["type"] == "http.response.start":
                values = list(message.get("headers", []))
                protected = {name.encode("ascii") for name in _SECURITY_HEADERS}
                values = [(name, value) for name, value in values if name.lower() not in protected]
                values.extend((name.encode("ascii"), value.encode("ascii"))
                              for name, value in _SECURITY_HEADERS.items())
                message = {**message, "headers": values}
            await send(message)

        await self.app(scope, receive, secured_send)


def _linked(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) &
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


class OwnedStaticFiles(StaticFiles):
    """Only regular owned build assets; deny links, maps, hidden and unsafe paths."""

    def __init__(self, directory: Path) -> None:
        self.root = Path(os.path.abspath(directory))
        try:
            usable = self.root.is_dir() and not any(
                _linked(path) for path in (self.root, *self.root.parents))
        except (OSError, ValueError):
            usable = False
        if not usable:
            raise RuntimeError("Build V1 frontend assets before starting the bench")
        super().__init__(directory=self.root, html=True, follow_symlink=False)
        self.config_checked = True

    def lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
        if any(character in path for character in (":", "\0")):
            return "", None
        pieces = Path(path).parts
        if any(piece in ("..", ".") or piece.startswith(".") for piece in pieces):
            return "", None
        if Path(path).is_absolute() or Path(path).suffix.lower() == ".map":
            return "", None
        try:
            candidate = self.root.joinpath(*pieces)
            if os.path.commonpath((str(candidate), str(self.root))) != str(self.root):
                return "", None
            current = self.root
            if any(_linked(path) for path in (current, *current.parents)):
                return "", None
            for piece in pieces:
                current = current / piece
                if _linked(current):
                    return "", None
            if candidate.is_file() and candidate.suffix.lower() not in _STATIC_SUFFIXES:
                return "", None
            return super().lookup_path(path)
        except (OSError, ValueError):
            return "", None

    def get_path(self, scope: Scope) -> str:
        # Check before StaticFiles normalizes dot segments. No SPA catch-all.
        path = scope.get("path", "").removeprefix(scope.get("root_path", ""))
        if any(character in path for character in ("\\", ":", "\0")):
            raise HTTPException(404)
        if any(piece in (".", "..") for piece in path.split("/")):
            raise HTTPException(404)
        return super().get_path(scope)


class BodyError(ValueError):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code = status, code


async def _read_json(request: Request, *, parser: Callable[[bytes], object] = strict_json_loads) -> object:
    content_type = request.headers.get("content-type", "").lower().strip()
    if content_type not in {"application/json", "application/json; charset=utf-8"}:
        raise BodyError(415, "invalid_content_type", "Expected application/json with UTF-8")
    content_length = request.headers.get("content-length")
    transfer = request.headers.get("transfer-encoding")
    if transfer is not None and (content_length is not None or transfer.lower() != "chunked"):
        raise BodyError(400, "invalid_framing", "Ambiguous or unsupported HTTP body framing")
    declared = None
    if content_length is not None:
        if re.fullmatch(r"[0-9]{1,10}", content_length, flags=re.ASCII) is None:
            raise BodyError(400, "invalid_length", "Invalid Content-Length")
        declared = int(content_length)
        if declared > MAX_BODY_BYTES:
            raise BodyError(413, "body_too_large", "Request body exceeds 32768 bytes")
    body = bytearray()
    try:
        async with asyncio.timeout(BODY_TIMEOUT_SECONDS):
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    raise BodyError(413, "body_too_large", "Request body exceeds 32768 bytes")
                body.extend(chunk)
    except TimeoutError as exc:
        raise BodyError(408, "body_timeout", "Request body read exceeded five seconds") from exc
    if declared is not None and declared != len(body):
        raise BodyError(400, "invalid_length", "Content-Length disagrees with received body")
    try:
        return parser(bytes(body))
    except (ValueError, TypeError, OverflowError) as exc:
        raise BodyError(400, "invalid_json", "Expected bounded strict UTF-8 JSON without duplicate keys") from exc


def _parsed_id(payload: object) -> str | None:
    if isinstance(payload, dict):
        try:
            return validate_request_id(payload.get("request_id"))
        except (ValueError, TypeError):
            pass
    return None


async def _wait_disconnect(request: Request) -> None:
    while True:
        message = await request.receive()
        if message["type"] == "http.disconnect":
            return


async def _worker_response(request: Request, future: Future[WorkerResult]) -> WorkerResult | None:
    # asyncio.wait does not cancel its inputs when the handler is cancelled.
    # Explicit shielding documents that no cancellation may reach the worker.
    wrapped = asyncio.wrap_future(future)

    def consume_late_exception(done: asyncio.Future) -> None:
        if not done.cancelled():
            done.exception()

    wrapped.add_done_callback(consume_late_exception)
    disconnected = asyncio.create_task(_wait_disconnect(request))
    protected = asyncio.shield(wrapped)
    try:
        done, _ = await asyncio.wait((protected, disconnected),
                                     return_when=asyncio.FIRST_COMPLETED)
        if disconnected in done:
            return None
        if protected.cancelled():
            raise CancelledBeforeStart("Computation was cancelled before it started")
        return protected.result()
    finally:
        disconnected.cancel()
        await asyncio.gather(disconnected, return_exceptions=True)
        # Cancelling this shield only detaches its waiter, never the Future.
        if not protected.done():
            protected.cancel()
        elif not protected.cancelled():
            # Disconnect and worker failure can become ready together. Consume
            # both the inner and shielding Future even when no response is sent.
            protected.exception()


def create_app(*, assets_dir: Path | None = None,
               worker: Callable[[ValidatedSubmission], bytes] | None = None,
               two_path_worker: Callable[[two_path_adapter.ValidatedTwoPathSubmission], bytes] | None = None,
               sweep_worker: Callable[[two_path_adapter.ValidatedSweepSubmission], SweepReply] | None = None,
               polarization_worker: Callable[[polarization_adapter.ValidatedPolarizationSubmission], bytes] | None = None,
               polarization_sweep_worker: Callable[[polarization_adapter.ValidatedPolarizationSweepSubmission], polarization_protocol.SweepReply] | None = None,
               polarized_two_path_worker: Callable[[polarized_two_path_adapter.ValidatedPolarizedTwoPathSubmission], bytes] | None = None,
               polarized_two_path_sweep_worker: Callable[[polarized_two_path_adapter.ValidatedPolarizedTwoPathSweepSubmission], polarized_two_path_protocol.SweepReply] | None = None,
               r03_ideal_worker: Callable[[r03_fig2a_adapter.ValidatedIdealSubmission], bytes] | None = None,
               wave_field_worker: Callable[[wave_field_adapter.ValidatedWaveFieldSubmission], bytes] | None = None,
               geometric_routing_worker: Callable[[geometric_routing_adapter.ValidatedGeometricSubmission], bytes] | None = None,
               refractive_routing_worker: Callable[[refractive_routing_adapter.ValidatedRefractiveSubmission], bytes] | None = None,
               executor: Executor | None = None) -> Starlette:
    """Create the local service; no numerical work or network listeners start.

Custom asset/worker/executor inputs support isolated acceptance tests. The CLI
always uses this checkout's fixed built directory and public numerical adapters.
"""
    assets = OwnedStaticFiles(assets_dir if assets_dir is not None else DEFAULT_ASSETS)
    index_path, index_stat = assets.lookup_path("index.html")
    if not index_path or index_stat is None or not stat.S_ISREG(index_stat.st_mode):
        raise RuntimeError("Build V1 frontend assets before starting the bench")
    def dispatch(submission: Submission) -> WorkerResult:
        if isinstance(submission, refractive_routing_adapter.ValidatedRefractiveSubmission):
            return (refractive_routing_worker if refractive_routing_worker is not None
                    else refractive_routing_adapter.trace_submission)(submission)
        if isinstance(submission, geometric_routing_adapter.ValidatedGeometricSubmission):
            return (geometric_routing_worker if geometric_routing_worker is not None
                    else geometric_routing_adapter.trace_submission)(submission)
        if isinstance(submission, wave_field_adapter.ValidatedWaveFieldSubmission):
            return (wave_field_worker if wave_field_worker is not None
                    else wave_field_adapter.simulate_submission)(submission)
        if isinstance(submission, r03_fig2a_adapter.ValidatedIdealSubmission):
            return (r03_ideal_worker if r03_ideal_worker is not None
                    else r03_fig2a_adapter.simulate_submission)(submission)
        if isinstance(submission, polarized_two_path_adapter.ValidatedPolarizedTwoPathSweepSubmission):
            return (polarized_two_path_sweep_worker if polarized_two_path_sweep_worker is not None
                    else polarized_two_path_adapter.sweep_submission)(submission)
        if isinstance(submission, polarized_two_path_adapter.ValidatedPolarizedTwoPathSubmission):
            return (polarized_two_path_worker if polarized_two_path_worker is not None
                    else polarized_two_path_adapter.simulate_submission)(submission)
        if isinstance(submission, ValidatedSubmission):
            return (worker if worker is not None else simulate_submission)(submission)
        if isinstance(submission, two_path_adapter.ValidatedTwoPathSubmission):
            return (two_path_worker if two_path_worker is not None else two_path_adapter.simulate_submission)(submission)
        if isinstance(submission, two_path_adapter.ValidatedSweepSubmission):
            return (sweep_worker if sweep_worker is not None else two_path_adapter.sweep_submission)(submission)
        # Sweep may specialize the single submission record: dispatch it first.
        if isinstance(submission, polarization_adapter.ValidatedPolarizationSweepSubmission):
            return (polarization_sweep_worker if polarization_sweep_worker is not None
                    else polarization_adapter.sweep_submission)(submission)
        if isinstance(submission, polarization_adapter.ValidatedPolarizationSubmission):
            return (polarization_worker if polarization_worker is not None
                    else polarization_adapter.simulate_submission)(submission)
        raise TypeError("unsupported immutable submission")

    gate = ComputationGate(dispatch, executor)

    @asynccontextmanager
    async def lifespan(app: Starlette):
        yield
        await asyncio.to_thread(gate.shutdown)

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"protocol_version": PROTOCOL_VERSION,
                             "status": "ok", "busy": gate.busy})

    async def validate(request: Request) -> Response:
        return await process(request, simulate=False)

    async def simulate(request: Request) -> Response:
        return await process(request, simulate=True)

    async def process(request: Request, *, simulate: bool) -> Response:
        request_id = None
        try:
            payload = await _read_json(request)
            request_id = _parsed_id(payload)
            submission = validate_submission(payload)
        except BodyError as exc:
            return _error(exc.status, exc.code, str(exc), request_id)
        except ClientDisconnect:
            return _error(499, "disconnected", "Client disconnected before submission", request_id)
        except (ValueError, TypeError, OverflowError) as exc:
            return _error(422, "invalid_experiment", str(exc), request_id)
        if not simulate:
            return JSONResponse({"protocol_version": PROTOCOL_VERSION,
                                 "request_id": submission.request_id,
                                 "experiment_sha256": submission.experiment_sha256,
                                 "experiment": submission.experiment.to_dict()})
        try:
            future = gate.submit(submission)
        except BusyError:
            return _error(409, "busy", "A Python computation is still running; submit again deliberately later",
                          submission.request_id)
        except Exception:
            return _error(500, "submission_failed", "Could not submit the computation", submission.request_id)
        try:
            encoded = await _worker_response(request, future)
        except asyncio.CancelledError:
            raise
        except CancelledBeforeStart:
            return _error(503, "cancelled_before_start", "Computation did not start; no result was produced",
                          submission.request_id)
        except NumericalError as exc:
            return _error(422, "numerical_failure", str(exc), submission.request_id)
        except Exception:
            return _error(500, "simulation_failed", "Numerical computation or result encoding failed",
                          submission.request_id)
        if encoded is None:
            return _error(499, "disconnected", "Client disconnected; Python work may still be running",
                          submission.request_id)
        if not isinstance(encoded, bytes) or not 16 <= len(encoded) <= MAX_RESPONSE_BYTES:
            return _error(500, "simulation_failed", "Result encoding failed", submission.request_id)
        return Response(encoded, media_type="application/octet-stream")

    async def http_error(request: Request, exception: HTTPException) -> Response:
        return _boundary_error(request.scope, exception.status_code, "http_error", "Request path or method is unavailable")

    def two_path_error(status: int, code: str, message: str,
                       request_id: str | None = None) -> JSONResponse:
        return JSONResponse({"protocol_version": 1, "message_type": "two_path_error",
                             "request_id": request_id,
                             "error": {"code": code, "message": message[:300]}}, status_code=status)

    async def two_path_validate(request: Request) -> Response:
        return await two_path_process(request, operation="validate")

    async def two_path_simulate(request: Request) -> Response:
        return await two_path_process(request, operation="simulate")

    async def two_path_sweep(request: Request) -> Response:
        return await two_path_process(request, operation="sweep")

    async def two_path_process(request: Request, *, operation: str) -> Response:
        request_id = None
        try:
            payload = await _read_json(request)
            request_id = _parsed_id(payload)
            submission = (two_path_adapter.validate_sweep_submission(payload) if operation == "sweep"
                          else two_path_adapter.validate_submission(payload))
        except BodyError as exc:
            return two_path_error(exc.status, exc.code, str(exc), request_id)
        except ClientDisconnect:
            return two_path_error(499, "disconnected", "Client disconnected before submission", request_id)
        except (ValueError, TypeError, OverflowError) as exc:
            return two_path_error(422, "invalid_experiment", str(exc), request_id)
        if operation == "validate":
            return JSONResponse({"protocol_version": 1, "message_type": "two_path_validation",
                                 "request_id": submission.request_id,
                                 "experiment_sha256": submission.experiment_sha256,
                                 "experiment": submission.experiment.to_dict()})
        try:
            future = gate.submit(submission)
        except BusyError:
            return two_path_error(409, "busy", "A Python computation is still running; submit again deliberately later",
                                  submission.request_id)
        except Exception:
            return two_path_error(500, "submission_failed", "Could not submit the computation", submission.request_id)
        try:
            encoded = await _worker_response(request, future)
        except asyncio.CancelledError:
            raise
        except CancelledBeforeStart:
            return two_path_error(503, "cancelled_before_start", "Computation did not start; no result was produced",
                                  submission.request_id)
        except NumericalError as exc:
            return two_path_error(422, "numerical_failure", str(exc), submission.request_id)
        except Exception:
            return two_path_error(500, "simulation_failed", "Numerical computation or result encoding failed",
                                  submission.request_id)
        if encoded is None:
            return two_path_error(499, "disconnected", "Client disconnected; backend completion is unknown",
                                  submission.request_id)
        if operation == "sweep":
            if (not isinstance(encoded, SweepReply) or encoded.status_code not in (200, 422, 500) or
                    not isinstance(encoded.body, bytes) or not 2 <= len(encoded.body) <= MAX_SWEEP_RESPONSE_BYTES):
                return two_path_error(500, "simulation_failed", "Sweep encoding failed", submission.request_id)
            return Response(encoded.body, status_code=encoded.status_code, media_type="application/json")
        if (not isinstance(encoded, bytes) or
                not 16 <= len(encoded) <= MAX_TWO_PATH_RESPONSE_BYTES):
            return two_path_error(500, "simulation_failed", "Result encoding failed", submission.request_id)
        return Response(encoded, media_type="application/octet-stream")

    def polarization_error(status: int, code: str, message: str,
                           request_id: str | None = None) -> JSONResponse:
        return JSONResponse({"protocol_version": 1, "message_type": "polarization_error",
                             "request_id": request_id,
                             "error": {"code": code[:64], "message": message[:300]}}, status_code=status)

    async def polarization_validate(request: Request) -> Response:
        return await polarization_process(request, operation="validate")

    async def polarization_simulate(request: Request) -> Response:
        return await polarization_process(request, operation="simulate")

    async def polarization_sweep(request: Request) -> Response:
        return await polarization_process(request, operation="sweep")

    async def polarization_process(request: Request, *, operation: str) -> Response:
        request_id = None
        try:
            payload = await _read_json(request)
            request_id = _parsed_id(payload)
            submission = (polarization_adapter.validate_sweep_submission(payload)
                          if operation == "sweep" else
                          polarization_adapter.validate_submission(payload, require_digest=operation != "validate"))
        except BodyError as exc:
            return polarization_error(exc.status, exc.code, str(exc), request_id)
        except ClientDisconnect:
            return polarization_error(499, "disconnected", "Client disconnected before submission", request_id)
        except (ValueError, TypeError, OverflowError) as exc:
            return polarization_error(422, "invalid_experiment", str(exc), request_id)
        if operation == "validate":
            return JSONResponse({"protocol_version": 1, "message_type": "polarization_validation",
                                 "request_id": submission.request_id,
                                 "experiment_sha256": submission.experiment_sha256,
                                 "experiment": submission.experiment.to_dict()})
        try:
            future = gate.submit(submission)
        except BusyError:
            return polarization_error(409, "busy", "A Python computation is still running; submit again deliberately later",
                                      submission.request_id)
        except Exception:
            return polarization_error(500, "submission_failed", "Could not submit the computation", submission.request_id)
        try:
            encoded = await _worker_response(request, future)
        except asyncio.CancelledError:
            raise
        except CancelledBeforeStart:
            return polarization_error(503, "cancelled_before_start", "Computation did not start; no result was produced",
                                      submission.request_id)
        except polarization_adapter.NumericalError as exc:
            return polarization_error(422, "numerical_failure", str(exc), submission.request_id)
        except Exception:
            return polarization_error(500, "simulation_failed", "Numerical computation or result encoding failed",
                                      submission.request_id)
        if encoded is None:
            return polarization_error(499, "disconnected", "Client disconnected; backend completion is unknown",
                                      submission.request_id)
        if operation == "sweep":
            if (not isinstance(encoded, polarization_protocol.SweepReply) or
                    encoded.status_code not in (200, 422, 500) or not isinstance(encoded.body, bytes) or
                    not 2 <= len(encoded.body) <= polarization_protocol.MAX_SWEEP_RESPONSE_BYTES):
                return polarization_error(500, "simulation_failed", "Sweep encoding failed", submission.request_id)
            return Response(encoded.body, status_code=encoded.status_code, media_type="application/json")
        if (not isinstance(encoded, bytes) or
                not 16 <= len(encoded) <= polarization_protocol.MAX_RESPONSE_BYTES):
            return polarization_error(500, "simulation_failed", "Result encoding failed", submission.request_id)
        return Response(encoded, media_type="application/octet-stream")

    def polarized_two_path_error(status: int, code: str, message: str,
                                 request_id: str | None = None) -> JSONResponse:
        return JSONResponse({"protocol_version": 1, "message_type": "polarized_two_path_error",
                             "request_id": request_id,
                             "error": {"code": code[:64], "message": message[:300]}}, status_code=status)

    async def polarized_two_path_validate(request: Request) -> Response:
        return await polarized_two_path_process(request, operation="validate")

    async def polarized_two_path_simulate(request: Request) -> Response:
        return await polarized_two_path_process(request, operation="simulate")

    async def polarized_two_path_sweep(request: Request) -> Response:
        return await polarized_two_path_process(request, operation="sweep")

    async def polarized_two_path_process(request: Request, *, operation: str) -> Response:
        request_id = None
        try:
            payload = await _read_json(request, parser=polarized_two_path_protocol.strict_json_loads)
            request_id = _parsed_id(payload)
            sweep_validation = (operation == "validate" and isinstance(payload, dict) and
                                payload.get("message_type") == "polarized_two_path_sweep_submission")
            is_sweep = operation == "sweep" or sweep_validation
            submission = (polarized_two_path_adapter.validate_sweep_submission(payload, require_digest=operation != "validate")
                          if is_sweep else polarized_two_path_adapter.validate_submission(payload, require_digest=operation != "validate"))
        except BodyError as exc:
            return polarized_two_path_error(exc.status, exc.code, str(exc), request_id)
        except ClientDisconnect:
            return polarized_two_path_error(499, "disconnected", "Client disconnected before submission", request_id)
        except (ValueError, TypeError, OverflowError) as exc:
            return polarized_two_path_error(422, "invalid_experiment", str(exc), request_id)
        if operation == "validate":
            if is_sweep:
                return JSONResponse({"protocol_version": 1, "message_type": "polarized_two_path_sweep_validation",
                    "request_id": submission.request_id, "fixed_experiment_sha256": submission.fixed_experiment_sha256,
                    "fixed_experiment": submission.fixed_dict(), "phases_rad": list(submission.phases_rad),
                    "sweep_sha256": submission.sweep_sha256})
            return JSONResponse({"protocol_version": 1, "message_type": "polarized_two_path_validation",
                "request_id": submission.request_id, "experiment_sha256": submission.experiment_sha256,
                "experiment": submission.experiment.to_dict()})
        try:
            future = gate.submit(submission)
        except BusyError:
            return polarized_two_path_error(409, "busy", "A Python computation is still running; submit again deliberately later",
                                             submission.request_id)
        except Exception:
            return polarized_two_path_error(500, "submission_failed", "Could not submit the computation", submission.request_id)
        try:
            encoded = await _worker_response(request, future)
        except asyncio.CancelledError:
            raise
        except CancelledBeforeStart:
            return polarized_two_path_error(503, "cancelled_before_start", "Computation did not start; no result was produced",
                                             submission.request_id)
        except NumericalError as exc:
            return polarized_two_path_error(422, "numerical_failure", str(exc), submission.request_id)
        except Exception:
            return polarized_two_path_error(500, "simulation_failed", "Numerical computation or result encoding failed",
                                             submission.request_id)
        if encoded is None:
            return polarized_two_path_error(499, "disconnected", "Client disconnected; backend completion is unknown",
                                             submission.request_id)
        if operation == "sweep":
            if (not isinstance(encoded, polarized_two_path_protocol.SweepReply) or encoded.status_code not in (200, 422, 500) or
                    not isinstance(encoded.body, bytes) or not 2 <= len(encoded.body) <= polarized_two_path_protocol.MAX_SWEEP_RESPONSE_BYTES):
                return polarized_two_path_error(500, "simulation_failed", "Sweep encoding failed", submission.request_id)
            return Response(encoded.body, status_code=encoded.status_code, media_type="application/json")
        if not isinstance(encoded, bytes) or not 16 <= len(encoded) <= polarized_two_path_protocol.MAX_RESPONSE_BYTES:
            return polarized_two_path_error(500, "simulation_failed", "Result encoding failed", submission.request_id)
        return Response(encoded, media_type="application/octet-stream")

    def r03_ideal_error(status: int, code: str, message: str,
                        request_id: str | None = None) -> JSONResponse:
        return JSONResponse({"protocol_version": 1, "message_type": "r03_ideal_error",
                             "request_id": request_id,
                             "error": {"code": code[:64], "message": message[:300]}}, status_code=status)

    async def r03_ideal_validate(request: Request) -> Response:
        return await r03_ideal_process(request, simulate=False)

    async def r03_ideal_simulate(request: Request) -> Response:
        return await r03_ideal_process(request, simulate=True)

    async def r03_ideal_process(request: Request, *, simulate: bool) -> Response:
        request_id = None
        try:
            payload = await _read_json(request, parser=r03_fig2a_protocol.strict_json_loads)
            request_id = _parsed_id(payload)
            submission = r03_fig2a_adapter.validate_submission(payload, require_digest=simulate)
        except BodyError as exc:
            return r03_ideal_error(exc.status, exc.code, str(exc), request_id)
        except ClientDisconnect:
            return r03_ideal_error(499, "disconnected", "Client disconnected before submission", request_id)
        except (ValueError, TypeError, OverflowError) as exc:
            return r03_ideal_error(422, "invalid_experiment", str(exc), request_id)
        if not simulate:
            return JSONResponse({"protocol_version": 1, "message_type": "r03_ideal_validation",
                "request_id": submission.request_id, "experiment_sha256": submission.experiment_sha256,
                "experiment": submission.experiment_dict()})
        try:
            future = gate.submit(submission)
        except BusyError:
            return r03_ideal_error(409, "busy", "A Python computation is still running; submit again deliberately later",
                                   submission.request_id)
        except Exception:
            return r03_ideal_error(500, "submission_failed", "Could not submit the computation", submission.request_id)
        try:
            encoded = await _worker_response(request, future)
        except CancelledBeforeStart:
            return r03_ideal_error(503, "cancelled_before_start", "Computation did not start; no result was produced",
                                   submission.request_id)
        except NumericalError as exc:
            return r03_ideal_error(422, "numerical_failure", str(exc), submission.request_id)
        except Exception:
            return r03_ideal_error(500, "simulation_failed", "Numerical computation or result encoding failed",
                                   submission.request_id)
        if encoded is None:
            return r03_ideal_error(499, "disconnected", "Client disconnected; backend completion is unknown",
                                   submission.request_id)
        if not isinstance(encoded, bytes) or not 16 <= len(encoded) <= r03_fig2a_protocol.MAX_RESPONSE_BYTES:
            return r03_ideal_error(500, "simulation_failed", "Result encoding failed", submission.request_id)
        return Response(encoded, media_type="application/json")

    def wave_field_error(status: int, code: str, message: str,
                         request_id: str | None = None) -> JSONResponse:
        return JSONResponse({"protocol_version": 1, "message_type": "w1_wave_field_error",
                             "request_id": request_id,
                             "error": {"code": code[:64], "message": message[:300]}}, status_code=status)

    async def wave_field_simulate(request: Request) -> Response:
        # The dedicated route plus exact sampling envelope discriminate W1;
        # all existing request and response formats remain unchanged.
        request_id = None
        try:
            payload = await _read_json(request, parser=wave_field_protocol.strict_json_loads)
            request_id = _parsed_id(payload)
            submission = wave_field_adapter.validate_submission(payload)
        except BodyError as exc:
            return wave_field_error(exc.status, exc.code, str(exc), request_id)
        except ClientDisconnect:
            return wave_field_error(499, "disconnected", "Client disconnected before submission", request_id)
        except (ValueError, TypeError, OverflowError) as exc:
            return wave_field_error(422, "invalid_experiment", str(exc), request_id)
        try:
            future = gate.submit(submission)
        except BusyError:
            return wave_field_error(409, "busy", "A Python computation is still running; submit again deliberately later",
                                    submission.request_id)
        except Exception:
            return wave_field_error(500, "submission_failed", "Could not submit the computation", submission.request_id)
        try:
            encoded = await _worker_response(request, future)
        except asyncio.CancelledError:
            raise
        except CancelledBeforeStart:
            return wave_field_error(503, "cancelled_before_start", "Computation did not start; no result was produced",
                                    submission.request_id)
        except NumericalError as exc:
            return wave_field_error(422, "numerical_failure", str(exc), submission.request_id)
        except Exception:
            return wave_field_error(500, "simulation_failed", "Numerical computation or result encoding failed",
                                    submission.request_id)
        if encoded is None:
            return wave_field_error(499, "disconnected", "Client disconnected; Python work may still be running",
                                    submission.request_id)
        if not isinstance(encoded, bytes) or not 16 <= len(encoded) <= wave_field_protocol.MAX_RESPONSE_BYTES:
            return wave_field_error(500, "simulation_failed", "Result encoding failed", submission.request_id)
        return Response(encoded, media_type="application/octet-stream")

    async def document_validate(request: Request) -> Response:
        try:
            payload = await _read_json(request, parser=experiment_documents.strict_document_loads)
            document = experiment_documents.validate_document(payload)
            return Response(document.canonical_bytes, media_type="application/json", headers={
                experiment_documents.EXPERIMENT_SHA256_HEADER: document.experiment_sha256})
        except BodyError as exc:
            return _error(exc.status, exc.code, str(exc))
        except ClientDisconnect:
            return _error(499, "disconnected", "Client disconnected before document receipt")
        except experiment_documents.DocumentError as exc:
            return _error(422, exc.code, str(exc))
        except Exception:
            return _error(500, "document_failed", "Could not validate or encode the document")

    def routing_error(status: int, code: str, message: str,
                      request_id: str | None = None) -> Response:
        return Response(geometric_routing_protocol.error_reply(request_id, code, message),
                        status_code=status, media_type="application/json")

    async def routing_validate(request: Request) -> Response:
        return await routing_process(request, trace=False)

    async def routing_trace(request: Request) -> Response:
        return await routing_process(request, trace=True)

    async def routing_process(request: Request, *, trace: bool) -> Response:
        request_id = None
        try:
            payload = await _read_json(request, parser=geometric_routing_protocol.strict_json_loads)
            request_id = _parsed_id(payload)
            submission = geometric_routing_adapter.validate_submission(payload, trace=trace)
        except BodyError as exc:
            code = "request_body_too_large" if exc.status == 413 else exc.code
            return routing_error(exc.status, code, str(exc), request_id)
        except ClientDisconnect:
            return routing_error(499, "disconnected", "Client disconnected before submission", request_id)
        except geometric_routing_adapter.RoutingNumericalError as exc:
            return routing_error(422, exc.code, str(exc), request_id)
        except (ValueError, TypeError, OverflowError) as exc:
            return routing_error(422, "invalid_scene", str(exc), request_id)
        if not trace:
            try:
                return Response(geometric_routing_adapter.validation_reply(submission),
                                media_type="application/json")
            except Exception:
                return routing_error(500, "encoding_failed", "Scene validation encoding failed", request_id)
        try:
            future = gate.submit(submission)
        except BusyError:
            return routing_error(409, "busy", "A Python computation is still running; submit deliberately later", request_id)
        except Exception:
            return routing_error(500, "submission_failed", "Could not submit the trace", request_id)
        try:
            encoded = await _worker_response(request, future)
        except asyncio.CancelledError:
            raise
        except CancelledBeforeStart:
            return routing_error(503, "cancelled_before_start", "Trace did not start; no result was produced", request_id)
        except geometric_routing_adapter.RoutingNumericalError as exc:
            return routing_error(422, exc.code, str(exc), request_id)
        except Exception:
            return routing_error(500, "trace_failed", "Trace computation or result encoding failed", request_id)
        if encoded is None:
            return routing_error(499, "disconnected", "Client disconnected; backend completion is unknown", request_id)
        if not isinstance(encoded, bytes) or not 2 <= len(encoded) <= geometric_routing_protocol.MAX_RESPONSE_BYTES:
            return routing_error(500, "response_too_large", "Trace response encoding failed or exceeded its bound", request_id)
        return Response(encoded, media_type="application/json")

    def refractive_error(status: int, code: str, message: str,
                      request_id: str | None = None) -> Response:
        return Response(refractive_routing_protocol.error_reply(request_id, code, message),
                        status_code=status, media_type="application/json")

    async def refractive_validate(request: Request) -> Response:
        return await refractive_process(request, trace=False)

    async def refractive_trace(request: Request) -> Response:
        return await refractive_process(request, trace=True)

    async def refractive_process(request: Request, *, trace: bool) -> Response:
        request_id = None
        try:
            payload = await _read_json(request, parser=refractive_routing_protocol.strict_json_loads)
            request_id = _parsed_id(payload)
            submission = refractive_routing_adapter.validate_submission(payload, trace=trace)
        except BodyError as exc:
            code = "request_body_too_large" if exc.status == 413 else "invalid_scene"
            return refractive_error(exc.status, code, str(exc), request_id)
        except ClientDisconnect:
            return refractive_error(499, "disconnected", "Client disconnected before submission", request_id)
        except refractive_routing_adapter.RefractiveNumericalError as exc:
            return refractive_error(422, exc.code, str(exc), request_id)
        except (ValueError, TypeError, OverflowError) as exc:
            return refractive_error(422, "invalid_scene", str(exc), request_id)
        if not trace:
            try:
                return Response(refractive_routing_adapter.validation_reply(submission),
                                media_type="application/json")
            except Exception:
                return refractive_error(500, "encoding_failed", "Scene validation encoding failed", request_id)
        try:
            future = gate.submit(submission)
        except BusyError:
            return refractive_error(409, "busy", "A Python computation is still running; submit deliberately later", request_id)
        except Exception:
            return refractive_error(500, "submission_failed", "Could not submit the trace", request_id)
        try:
            encoded = await _worker_response(request, future)
        except asyncio.CancelledError:
            raise
        except CancelledBeforeStart:
            return refractive_error(503, "cancelled_before_start", "Trace did not start; no result was produced", request_id)
        except refractive_routing_adapter.RefractiveNumericalError as exc:
            return refractive_error(422, exc.code, str(exc), request_id)
        except Exception:
            return refractive_error(500, "trace_failed", "Trace computation or result encoding failed", request_id)
        if encoded is None:
            return refractive_error(499, "disconnected", "Client disconnected; backend completion is unknown", request_id)
        if not isinstance(encoded, bytes) or not 2 <= len(encoded) <= refractive_routing_protocol.MAX_RESPONSE_BYTES:
            return refractive_error(500, "response_too_large", "Trace response encoding failed or exceeded its bound", request_id)
        return Response(encoded, media_type="application/json")

    async def unavailable_api(request: Request) -> Response:
        status = 405 if request.url.path in {
            "/api/v1/health", "/api/v1/validate", "/api/v1/simulate",
            "/api/v2b/validate", "/api/v2b/simulate", "/api/v2b/sweep",
            "/api/v2d/validate", "/api/v2d/simulate", "/api/v2d/sweep",
            "/api/v2g/validate", "/api/v2g/simulate", "/api/v2g/sweep",
            "/api/research/r03-fig2a/validate", "/api/research/r03-fig2a/simulate",
            "/api/v2e/documents/validate", "/api/w1/simulate",
            "/api/w2/validate", "/api/w2/trace",
            "/api/w3/validate", "/api/w3/trace"} else 404
        return _boundary_error(request.scope, status, "http_error", "Request path or method is unavailable")

    app = Starlette(routes=[Route("/api/v1/health", health, methods=["GET"]),
                            Route("/api/v1/validate", validate, methods=["POST"]),
                            Route("/api/v1/simulate", simulate, methods=["POST"]),
                            Route("/api/v2b/validate", two_path_validate, methods=["POST"]),
                            Route("/api/v2b/simulate", two_path_simulate, methods=["POST"]),
                            Route("/api/v2b/sweep", two_path_sweep, methods=["POST"]),
                            Route("/api/v2d/validate", polarization_validate, methods=["POST"]),
                            Route("/api/v2d/simulate", polarization_simulate, methods=["POST"]),
                            Route("/api/v2d/sweep", polarization_sweep, methods=["POST"]),
                            Route("/api/v2g/validate", polarized_two_path_validate, methods=["POST"]),
                            Route("/api/v2g/simulate", polarized_two_path_simulate, methods=["POST"]),
                            Route("/api/v2g/sweep", polarized_two_path_sweep, methods=["POST"]),
                            Route("/api/research/r03-fig2a/validate", r03_ideal_validate, methods=["POST"]),
                            Route("/api/research/r03-fig2a/simulate", r03_ideal_simulate, methods=["POST"]),
                            Route("/api/v2e/documents/validate", document_validate, methods=["POST"]),
                            Route("/api/w1/simulate", wave_field_simulate, methods=["POST"]),
                            Route("/api/w2/validate", routing_validate, methods=["POST"]),
                            Route("/api/w2/trace", routing_trace, methods=["POST"]),
                            Route("/api/w3/validate", refractive_validate, methods=["POST"]),
                            Route("/api/w3/trace", refractive_trace, methods=["POST"]),
                            Route("/api/{path:path}", unavailable_api,
                                  methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"]),
                            Mount("/", app=assets)],
                    middleware=[Middleware(LocalBoundary)], lifespan=lifespan,
                    exception_handlers={HTTPException: http_error})
    app.state.gate = gate
    app.state.assets_dir = str(assets.root)
    return app


def main() -> int:
    """Serve built bench assets only on 127.0.0.1:8510 using the existing runtime."""
    import uvicorn

    try:
        app = create_app()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind((HOST, PORT))
        listener.listen(16)
        listener.setblocking(False)
    except OSError:
        listener.close()
        app.state.gate.shutdown()
        print("Local bench port 8510 is unavailable; no existing service was changed", file=sys.stderr)
        return 2
    config = uvicorn.Config(app, host=HOST, port=PORT, workers=1, reload=False,
                            loop="asyncio", http="h11", proxy_headers=False,
                            ws="none", limit_concurrency=16,
                            timeout_keep_alive=2, server_header=False, access_log=False)
    try:
        uvicorn.Server(config).run(sockets=[listener])
    except KeyboardInterrupt:
        # Uvicorn completes its shutdown, then asyncio.Runner re-raises Ctrl+C.
        # Preserve the worker-lifetime shutdown below without an idle CLI traceback.
        pass
    finally:
        listener.close()
        app.state.gate.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
