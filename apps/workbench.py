"""Session-local orchestration of the public M2--M5 APIs, without UI imports.

Only explicit accepted operations perform I/O. A rendered nonce is consumed
before expensive work; callbacks must pass the nonce captured when rendered,
not read the current one at invocation. This protects one active session from
duplicate queued events. It is not durable exactly-once execution across a
process interruption, page reload, or different sessions. Local bundle files
are assumed not to change concurrently between separate public M5 calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

import numpy as np

from ohlab.grid import SamplingGrid
from ohlab.io.artifacts import (
    load_run_bundle, replay_run_bundle, run_and_save_bundle, verify_run_bundle,
)
from ohlab.io.config import RunConfig
from ohlab.io.images import load_target_intensity
from ohlab.targets import intensity_to_amplitude

from apps.provenance import detect_source_revision

UPLOAD_LIMIT = 8 * 1024 * 1024
SIDE_LIMIT = 512
ITERATION_LIMIT = 200
WORK_LIMIT = 13_107_200
ENTRY_LIMIT = 16
FILE_LIMIT = 32 * 1024 * 1024
BUNDLE_LIMIT = 128 * 1024 * 1024


@dataclass(frozen=True, slots=True, kw_only=True)
class RunDraft:
    """New-run controls in micrometres, nanometres and millimetres as named."""

    target_kind: str = "builtin"
    ny: int = 64
    nx: int = 64
    dy_um: float = 8.0
    dx_um: float = 8.0
    wavelength_nm: float = 633.0
    distance_mm: float = 5.0
    iterations: int = 50
    seed: int = 0
    psnr_data_range: float = 1.0
    upload_bytes: bytes | None = None
    upload_name: str | None = None


@dataclass(frozen=True, slots=True)
class SubmittedRun:
    """Immutable submitted identity; its destination is allocated only once."""

    token: str
    destination: Path
    config: RunConfig
    target_kind: str
    upload_bytes: bytes | None
    upload_name: str | None
    upload_sha256: str | None
    draft_fingerprint: str


@dataclass
class WorkbenchState:
    """Small per-session state, with completed results separate from attempts."""

    offered_nonce: str = field(default_factory=lambda: uuid4().hex)
    busy: bool = False
    pending: SubmittedRun | None = None
    consumed_tokens: set[str] = field(default_factory=set)
    last_attempt: SubmittedRun | None = None
    bundle: Any | None = None
    submitted: SubmittedRun | None = None
    selected_path: Path | None = None
    saved_path: Path | None = None
    save_succeeded: bool = False
    integrity: str = "not_evaluated"
    qualification: str = "not_evaluated"
    comparison: str = "not_run"
    replay_report: Any | None = None
    error: str | None = None
    presentation_error: str | None = None
    diagnostic_enabled: bool = False
    stage: str = "idle"
    last_operation: str | None = None
    last_operation_path: Path | None = None
    last_operation_at: str | None = None


def draft_fingerprint(draft: RunDraft) -> str:
    """Identify actual draft values and uploaded bytes, not filename/size alone."""
    if not isinstance(draft, RunDraft):
        raise TypeError("draft: expected RunDraft")
    values = {item.name: getattr(draft, item.name) for item in fields(draft)}
    payload = values.pop("upload_bytes")
    if payload is not None and type(payload) is not bytes:
        raise TypeError("upload_bytes: expected immutable bytes or None")
    values["upload_sha256"] = None if payload is None else hashlib.sha256(payload).hexdigest()
    return hashlib.sha256(json.dumps(
        values, sort_keys=True, ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")).hexdigest()


def builtin_grayscale() -> np.ndarray:
    """Fresh fixed 64x64 M5 raster; its width is 7.5 pixels, never pitch-adapted."""
    grid = SamplingGrid(ny=64, nx=64, dy=8e-6, dx=8e-6)
    x, y = grid.meshgrid()
    design = np.exp(-0.5 * ((x / 60e-6) ** 2 + (y / 60e-6) ** 2))
    return np.rint(255.0 * design).astype(np.uint8)


def _count(value: object, name: str, low: int, high: int) -> int:
    if type(value) is not int:
        raise TypeError(f"{name}: expected an integer, got {type(value).__name__}")
    if not low <= value <= high:
        raise ValueError(f"{name}: app limit is {low}..{high}, got {value}")
    return value


def _real(value: object, name: str, *, positive: bool) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name}: expected a real number, excluding bool")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name}: expected a representable finite value") from exc
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"{name}: expected {'positive ' if positive else ''}finite value, got {value}")
    return result


def _draft_config(draft: RunDraft) -> RunConfig:
    if not isinstance(draft, RunDraft):
        raise TypeError("draft: expected RunDraft")
    ny = _count(draft.ny, "ny", 1, SIDE_LIMIT)
    nx = _count(draft.nx, "nx", 1, SIDE_LIMIT)
    iterations = _count(draft.iterations, "iterations", 0, ITERATION_LIMIT)
    if ny * nx * max(1, iterations) > WORK_LIMIT:
        raise ValueError(f"grid/iterations: app work limit is {WORK_LIMIT} pixel-cycles")
    seed = _count(draft.seed, "seed", 0, 2**32 - 1)
    if draft.target_kind not in ("builtin", "upload"):
        raise ValueError("target_kind: expected 'builtin' or 'upload'")
    if draft.upload_name is not None and type(draft.upload_name) is not str:
        raise TypeError("upload_name: expected str or None")
    if draft.target_kind == "builtin":
        if (ny, nx) != (64, 64):
            raise ValueError("builtin target: fixed shape is (64, 64); pitch changes only reinterpret pixels")
        if draft.upload_bytes is not None:
            raise ValueError("builtin target: unexpected upload_bytes")
    else:
        if type(draft.upload_bytes) is not bytes:
            raise TypeError("upload_bytes: expected immutable PNG bytes")
        if not 0 < len(draft.upload_bytes) <= UPLOAD_LIMIT:
            raise ValueError(f"upload_bytes: app limit is 1..{UPLOAD_LIMIT} encoded bytes")
    # This is the single UI-unit -> SI boundary. RunConfig checks the converted
    # values, including conversion underflow, without changing scientific rules.
    distance_mm = _real(draft.distance_mm, "distance_mm", positive=False)
    distance_m = distance_mm * 1e-3
    if distance_mm != 0.0 and distance_m == 0.0:
        raise ValueError("distance_mm: nonzero distance underflows to zero metres")
    return RunConfig({
        "schema_version": 1,
        "grid": {"ny": ny, "nx": nx,
                 "dy_m": _real(draft.dy_um, "dy_um", positive=True) * 1e-6,
                 "dx_m": _real(draft.dx_um, "dx_um", positive=True) * 1e-6},
        "optics": {"wavelength_m": _real(draft.wavelength_nm, "wavelength_nm", positive=True) * 1e-9,
                   "distance_m": distance_m},
        "solver": {"algorithm": "gerchberg_saxton", "contract": "m3_periodic_lossless_asm_v1",
                   "iterations": iterations, "initialization": {"mode": "seed", "seed": seed}},
        "metrics": {"intensity_mse": {}, "intensity_nmse": {},
                    "intensity_psnr": {"data_range": _real(draft.psnr_data_range, "psnr_data_range", positive=True)}},
    })


def _lexical_absolute(value: str | Path) -> Path:
    path = Path(value)
    if ".." in path.parts:
        raise ValueError("path: parent traversal '..' is not supported")
    return path.absolute()


def _reject_link_ancestors(path: Path) -> None:
    for part in (*reversed(path.parents), path):
        if not os.path.lexists(part):
            continue
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError(f"{part}: links and reparse points are outside app path policy")


def selected_bundle_path(selection: str | Path, *, runs_root: Path) -> Path:
    """Keep a selected lexical path under runs; never resolve a link away."""
    if not isinstance(selection, (str, Path)):
        raise TypeError("selection: expected str or Path")
    root = _lexical_absolute(runs_root)
    requested = Path(selection)
    path = _lexical_absolute(requested if requested.is_absolute() else root / requested)
    if path == root or not path.is_relative_to(root):
        raise ValueError(f"selection: expected a child path under {root}")
    _reject_link_ancestors(path)
    return path


def preflight_bundle(path: str | Path, *, runs_root: Path) -> None:
    """Stat-only app resource guard, before M5 reads any bundle content."""
    selected = selected_bundle_path(path, runs_root=runs_root)
    if not stat.S_ISDIR(selected.lstat().st_mode):
        raise ValueError("bundle: expected a directory")
    total = 0
    for count, entry in enumerate(selected.iterdir(), start=1):
        if count > ENTRY_LIMIT:
            raise ValueError(f"bundle: outside app limit of {ENTRY_LIMIT} direct entries")
        info = entry.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError(f"{entry}: links and reparse points are unsupported")
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"{entry}: expected a regular artifact file")
        if info.st_size > FILE_LIMIT:
            raise ValueError(f"bundle: outside app per-file limit of {FILE_LIMIT} bytes")
        total += info.st_size
        if total > BUNDLE_LIMIT:
            raise ValueError(f"bundle: outside app total limit of {BUNDLE_LIMIT} bytes")


def list_bundle_candidates(*, runs_root: Path) -> tuple[Path, ...]:
    """List direct M5/M6 completed-looking children; selection still needs M5 verification."""
    root = _lexical_absolute(runs_root)
    result: list[Path] = []
    for name in ("m5", "m6"):
        directory = root / name
        try:
            _reject_link_ancestors(directory)
            if not directory.is_dir():
                continue
            for candidate in directory.iterdir():
                if candidate.name.startswith((".", "input-", "upload-")):
                    continue
                try:
                    _reject_link_ancestors(candidate)
                    if not stat.S_ISDIR(candidate.lstat().st_mode):
                        continue
                    markers = [candidate / part for part in ("manifest.json", "config.json", "metrics.json")]
                    if all(stat.S_ISREG(part.lstat().st_mode) and not (
                        getattr(part.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                    ) for part in markers):
                        result.append(candidate)
                except (OSError, ValueError):
                    continue
        except (OSError, ValueError):
            continue
    return tuple(sorted(result, key=lambda path: str(path).casefold()))


def bundle_operating_limit(bundle: Any) -> str | None:
    """Return app-limit reason, not a claim that a verified bundle is corrupt."""
    spec = bundle.config.to_dict()
    ny, nx = spec["grid"]["ny"], spec["grid"]["nx"]
    iterations = spec["solver"]["iterations"]
    if ny > SIDE_LIMIT or nx > SIDE_LIMIT:
        return f"Verified bundle is outside app grid limit {SIDE_LIMIT} per side; plotting/replay disabled."
    if iterations > ITERATION_LIMIT or ny * nx * max(1, iterations) > WORK_LIMIT:
        return "Verified bundle is outside app iteration/work limits; plotting/replay disabled."
    return None


def _available(state: WorkbenchState, offered_nonce: str) -> bool:
    return (not state.busy and state.pending is None and offered_nonce == state.offered_nonce
            and offered_nonce not in state.consumed_tokens)


def _begin(state: WorkbenchState, nonce: str, operation: str, path: Path | None) -> None:
    state.consumed_tokens.add(nonce)
    state.offered_nonce = uuid4().hex
    state.busy = True
    state.error = state.presentation_error = None
    state.bundle = state.submitted = state.replay_report = None
    state.saved_path = None
    state.save_succeeded = False
    state.integrity = state.qualification = "not_evaluated"
    state.comparison = "not_run"
    if state.selected_path != path:
        state.diagnostic_enabled = False
    state.selected_path = path
    state.last_operation = operation
    state.last_operation_path = path
    state.last_operation_at = None
    state.stage = "validating"


def _finish(state: WorkbenchState) -> None:
    state.busy = False
    state.last_operation_at = datetime.now(timezone.utc).isoformat()
    if state.stage not in ("completed", "failed"):
        state.stage = "interrupted"


def _failure(state: WorkbenchState, exc: Exception) -> bool:
    state.error = f"{type(exc).__name__}: {exc}"
    state.stage = "failed"
    return False


def submit_generate(
    state: WorkbenchState, draft: RunDraft, *, offered_nonce: str, runs_root: Path,
) -> bool:
    """Validate/snapshot a draft and consume a rendered nonce; perform no file I/O writes."""
    if not _available(state, offered_nonce):
        return False
    # Validation failure is also a consumed explicit attempt. It must neither
    # leave a previous result looking successful for this draft nor permit a
    # queued copy of the same callback to retry later.
    _begin(state, offered_nonce, "generate", None)
    try:
        config = _draft_config(draft)
        fingerprint = draft_fingerprint(draft)
        root = _lexical_absolute(runs_root)
        _reject_link_ancestors(root / "m6")
        submitted = SubmittedRun(
            offered_nonce, root / "m6" / uuid4().hex, config, draft.target_kind,
            draft.upload_bytes, draft.upload_name,
            None if draft.upload_bytes is None else hashlib.sha256(draft.upload_bytes).hexdigest(),
            fingerprint,
        )
    except Exception as exc:
        result = _failure(state, exc)
        _finish(state)
        return result
    except BaseException:
        _finish(state)
        raise
    state.selected_path = state.last_operation_path = submitted.destination
    state.pending = state.last_attempt = submitted
    state.stage = "queued"
    return True


def execute_pending_run(state: WorkbenchState) -> bool:
    """Execute once; record completed M5 output before any caller presentation.

    Ordinary failures are visible in state. Interruption consumes the pending
    action too; a later rerun cannot retry it. If publication happened before an
    interruption, recovery is an explicit open of its fixed destination.
    """
    submitted = state.pending
    if submitted is None:
        return False
    state.pending = None  # Consume before decoding, solving, saving, or interruption.
    try:
        spec = submitted.config.to_dict()
        settings = spec["grid"]
        grid = SamplingGrid(ny=settings["ny"], nx=settings["nx"], dy=settings["dy_m"], dx=settings["dx_m"])
        parent = submitted.destination.parent
        _reject_link_ancestors(parent)
        parent.mkdir(parents=True, exist_ok=True)
        state.stage = "loading_target"
        with TemporaryDirectory(prefix=".upload-", dir=parent) as temporary:
            png_path = Path(temporary) / "target.png"
            if submitted.target_kind == "upload":
                png_path.write_bytes(submitted.upload_bytes)
            else:
                # Optional encoding dependency is loaded only for this explicit
                # action; the public M2 loader remains the sole PNG decoder.
                from PIL import Image

                with Image.fromarray(builtin_grayscale()) as image:
                    image.save(png_path, format="PNG", optimize=False, compress_level=6)
            intensity = load_target_intensity(png_path, grid=grid)
            amplitude = intensity_to_amplitude(intensity, grid=grid)
            with np.errstate(over="raise", under="raise", invalid="raise", divide="raise"):
                energy = float(np.sum(amplitude**2))
                if energy <= 0:
                    raise ValueError("target: blank intensity has zero power; choose a nonblank target")
                source_value = float(np.sqrt(energy / amplitude.size))
                source = np.full(grid.shape, source_value, dtype=np.float64)
                powers = (energy * grid.pixel_area, float(np.sum(source**2)) * grid.pixel_area)
                if not all(math.isfinite(power) and power > 0 for power in powers):
                    raise ValueError("illumination: target/source powers must be positive and finite")
            state.stage = "saving"
            bundle = run_and_save_bundle(
                submitted.destination, config=submitted.config, target_intensity=intensity,
                source_amplitude=source, input_png=png_path, source_revision=detect_source_revision(),
            )
            # Publication success is committed to session state before cleanup
            # or presentation can fail. Never erase this identity on such failure.
            state.bundle = bundle
            state.submitted = submitted
            state.saved_path = bundle.path
            state.selected_path = bundle.path
            state.save_succeeded = True
            state.integrity = "passed"
        state.stage = "completed"
        return True
    except Exception as exc:
        return _failure(state, exc)
    finally:
        _finish(state)


def record_presentation_failure(state: WorkbenchState, exc: Exception) -> None:
    """Retain published bundle and submitted identity when only rendering fails."""
    state.presentation_error = f"{type(exc).__name__}: {exc}"


def _inspect(
    state: WorkbenchState, selection: str | Path, *, runs_root: Path,
    offered_nonce: str, operation: str, diagnostic: bool = False,
) -> bool:
    if not _available(state, offered_nonce):
        return False
    # Consume before even path/preflight failures so an old callback cannot
    # become an implicit retry after a failed inspection.
    previous_path = state.selected_path
    _begin(state, offered_nonce, operation, previous_path)
    state.stage = {"open": "loading", "reverify": "verifying", "replay": "replaying"}[operation]
    try:
        path = selected_bundle_path(selection, runs_root=runs_root)
        if previous_path != path:
            state.diagnostic_enabled = False
        state.selected_path = state.last_operation_path = path
        preflight_bundle(path, runs_root=runs_root)
        if operation == "reverify":
            verify_run_bundle(path)
        bundle = load_run_bundle(path)
        state.bundle = bundle
        state.integrity = "passed"
        if operation == "replay":
            if type(diagnostic) is not bool:
                raise TypeError("diagnostic: expected bool")
            limit = bundle_operating_limit(bundle)
            if limit is not None:
                raise ValueError(limit)
            report = replay_run_bundle(path, source_revision=detect_source_revision(), diagnostic=diagnostic)
            state.replay_report = report
            state.integrity = report.integrity
            state.qualification = report.qualification
            state.comparison = report.comparison
        state.stage = "completed"
        return True
    except Exception as exc:
        # A later M5 operation can fail after the preliminary load succeeded.
        # Do not leave that earlier success badge on the failed current action.
        state.bundle = state.replay_report = None
        state.integrity = state.qualification = "not_evaluated"
        state.comparison = "not_run"
        return _failure(state, exc)
    finally:
        _finish(state)


def open_bundle(
    state: WorkbenchState, selection: str | Path, *, runs_root: Path, offered_nonce: str,
) -> bool:
    """Explicitly load once; no numerical replay or qualification is implied."""
    return _inspect(state, selection, runs_root=runs_root, offered_nonce=offered_nonce, operation="open")


def reverify_bundle(
    state: WorkbenchState, selection: str | Path, *, runs_root: Path, offered_nonce: str,
) -> bool:
    """Explicit verification followed by a fresh public load (which re-verifies)."""
    return _inspect(state, selection, runs_root=runs_root, offered_nonce=offered_nonce, operation="reverify")


def replay_bundle(
    state: WorkbenchState, selection: str | Path, *, runs_root: Path,
    offered_nonce: str, diagnostic: bool = False,
) -> bool:
    """Explicit public replay, strict by default; current provenance is re-detected."""
    return _inspect(state, selection, runs_root=runs_root, offered_nonce=offered_nonce,
                    operation="replay", diagnostic=diagnostic)
