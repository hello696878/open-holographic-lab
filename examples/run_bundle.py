r"""Save, inspect and replay one deterministic M2 -> M3 -> M4 run bundle.

Run with the existing project interpreter from PowerShell or VS Code::

    .\.venv\Scripts\python.exe -B examples\run_bundle.py
    .\.venv\Scripts\python.exe -B examples\run_bundle.py --output runs\m5\example

The only argument selects a new destination; existing destinations are never
overwritten. The default creates a fresh directory under runs/m5. This example
is headless and does not export visual previews or launch an application.
Dirty/unavailable source provenance uses explicitly reported diagnostic replay;
after a clean commit the same example requires qualified replay.
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import math
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4

import numpy as np

import ohlab
from ohlab import SamplingGrid
from ohlab.io.artifacts import (
    load_run_bundle, replay_run_bundle, run_and_save_bundle, verify_run_bundle,
)
from ohlab.io.config import RunConfig
from ohlab.io.images import load_target_intensity
from ohlab.targets import intensity_to_amplitude

ROOT = Path(__file__).resolve().parents[1]


def _detect_source_revision() -> dict[str, str | None]:
    """Read Git provenance for the checkout providing imported ``ohlab``.

    This optional example-layer detection never invokes Git from the caller's
    working directory. An installed package outside a matching src/ohlab
    checkout, missing Git, or failed detection gives explicit unavailable
    provenance. A SHA describes HEAD; dirty state makes clear that HEAD alone
    does not identify candidate source bytes. No Git operation changes files.
    """
    unavailable = {"revision": None, "state": "unavailable", "method": "git"}
    if ohlab.__file__ is None:
        return unavailable
    package_directory = Path(ohlab.__file__).resolve().parent

    def git(directory: Path, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(directory), *arguments], check=True,
            capture_output=True, text=True, encoding="utf-8", timeout=10,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
        return completed.stdout.strip()

    try:
        checkout = Path(git(package_directory, "rev-parse", "--show-toplevel")).resolve()
        if package_directory != (checkout / "src" / "ohlab").resolve():
            return unavailable
        tracked = git(checkout, "ls-files", "--error-unmatch", "--", "src/ohlab/__init__.py")
        if tracked != "src/ohlab/__init__.py":
            return unavailable
        revision = git(checkout, "rev-parse", "--verify", "HEAD")
        if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
            return unavailable
        status = git(checkout, "status", "--porcelain=v1", "--untracked-files=normal")
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, UnicodeError):
        return unavailable
    return {"revision": revision, "state": "dirty" if status else "clean", "method": "git"}


def _example_config() -> RunConfig:
    """The fixed 64x64 seed-0 configuration, with all distances in metres."""
    return RunConfig({
        "schema_version": 1,
        "grid": {"ny": 64, "nx": 64, "dy_m": 8e-6, "dx_m": 8e-6},
        "optics": {"wavelength_m": 633e-9, "distance_m": 5e-3},
        "solver": {
            "algorithm": "gerchberg_saxton",
            "contract": "m3_periodic_lossless_asm_v1",
            "iterations": 50,
            "initialization": {"mode": "seed", "seed": 0},
        },
        "metrics": {
            "intensity_mse": {},
            "intensity_nmse": {},
            "intensity_psnr": {"data_range": 1.0},
            "signal_region_power_fraction": {"mask": "signal_mask.npy"},
        },
    })


def _write_fixture_png(path: Path, grid: SamplingGrid) -> None:
    """Write the deterministic quantized Gaussian design as strict grayscale PNG."""
    from PIL import Image

    x, y = grid.meshgrid()
    design = np.exp(-0.5 * ((x / 60e-6)**2 + (y / 60e-6)**2))
    codes = np.rint(255.0 * design).astype(np.uint8)
    with Image.fromarray(codes) as image:
        image.save(path, format="PNG", optimize=False, compress_level=6)


def main(argv: Sequence[str] | None = None) -> int:
    """Save and replay the fixed example, reporting all three outcomes separately."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="new run directory; never overwritten")
    arguments = parser.parse_args(argv)
    runs_directory = ROOT / "runs" / "m5"
    runs_directory.mkdir(parents=True, exist_ok=True)
    destination = (
        runs_directory / f"example-{uuid4().hex}"
        if arguments.output is None else arguments.output.resolve()
    )
    config = _example_config()
    grid = SamplingGrid(ny=64, nx=64, dy=8e-6, dx=8e-6)
    rows, columns = np.indices(grid.shape)
    signal_mask = (rows - 32)**2 + (columns - 32)**2 <= 15**2
    source_revision = _detect_source_revision()
    with TemporaryDirectory(prefix="input-", dir=runs_directory) as temporary:
        png_path = Path(temporary) / "smooth_spot.png"
        _write_fixture_png(png_path, grid)
        intensity = load_target_intensity(png_path, grid=grid)
        amplitude = intensity_to_amplitude(intensity, grid=grid)
        # Explicit per-target illumination is configured outside the solver.
        source_value = float(np.sqrt(np.sum(amplitude**2) / amplitude.size))
        source = np.full(grid.shape, source_value, dtype=np.float64)
        bundle = run_and_save_bundle(
            destination, config=config, target_intensity=intensity,
            source_amplitude=source, signal_mask=signal_mask,
            input_png=png_path, source_revision=source_revision,
        )
    # The owned external PNG has now been removed; bundle numerical replay
    # does not depend on its original location or the live caller arrays.
    integrity = verify_run_bundle(destination)
    loaded = load_run_bundle(destination)
    current_source = _detect_source_revision()
    diagnostic = source_revision["state"] != "clean" or current_source["state"] != "clean"
    replay = replay_run_bundle(
        destination, source_revision=current_source, diagnostic=diagnostic,
    )
    # EXACTNESS IS THE PROPERTY UNDER TEST: reloading preserves every role's
    # dtype, shape and C-order element bytes; this is not a numerical tolerance.
    assert set(bundle.arrays) == set(loaded.arrays)
    for role, array in bundle.arrays.items():
        restored = loaded.arrays[role]
        assert (array.dtype == restored.dtype and array.shape == restored.shape
                and array.tobytes(order="C") == restored.tobytes(order="C"))

    print(f"run directory: {destination}")
    print("schema_version: 1; deterministic numerical fixture; directory UUID is only a label")
    print("grid: ny=64, nx=64, dy_m=8e-06, dx_m=8e-06")
    print("optics: wavelength_m=6.33e-07, distance_m=0.005")
    print("solver: gerchberg_saxton; contract=m3_periodic_lossless_asm_v1; iterations=50; seed=0")
    print("target: strict 8-bit grayscale PNG; I=g/255; A=sqrt(I); Gaussian width=60e-06 m")
    print(f"configured uniform source amplitude: {source_value:.17e} a.u.")
    print(f"source power: {float(np.sum(source**2) * grid.pixel_area):.17e} a.u. m^2")
    print(f"target power: {float(np.sum(amplitude**2) * grid.pixel_area):.17e} a.u. m^2")
    print("signal mask: (row-32)^2+(column-32)^2 <= 225; 709 pixels; PSNR data_range=1")
    print("Illumination is explicitly configured for this target; no target normalization is added.")
    print("recorded software/environment: " + json.dumps(loaded.software, sort_keys=True, allow_nan=False))
    print("independently detected current source: " + json.dumps(current_source, sort_keys=True))
    print(f"artifact integrity: {integrity.status}")
    print(f"source/environment qualification: {replay.qualification}")
    print(f"explicit diagnostic mode: {diagnostic}")
    print(f"numerical comparison: {replay.comparison}")
    print("qualification reasons: " + ("; ".join(replay.qualification_reasons) or "none"))
    print("individual replay checks: " + json.dumps(dict(replay.checks), sort_keys=True))
    for name, value in sorted(loaded.metrics.items()):
        formatted = "+inf" if math.isinf(value) and value > 0.0 else f"{value:.17e}"
        print(f"{name}: {formatted}")
    print("metric parameters: " + json.dumps(config.to_dict()["metrics"], sort_keys=True))
    print(f"separate M3 squared amplitude residual: {loaded.arrays['residual_history'][-1]:.17e}")
    print("load check: dtype/shape/element bytes unchanged; original temporary PNG no longer exists")
    print("SHA-256 establishes integrity relative to the manifest, not authorship or physical accuracy.")
    if integrity.status != "passed" or replay.integrity != "passed" or replay.comparison != "passed":
        return 1
    if not diagnostic and replay.qualification != "qualified":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
