r"""Persist and reconstruct an asymmetric editable 48x64 intensity design.

From the repository root, using the existing project interpreter::

    .\.venv\Scripts\python.exe -B examples\design_target.py
    .\.venv\Scripts\python.exe -B examples\design_target.py --diagnostic

Each invocation creates a new UUID run under runs/m7 and two external design
copies under runs/designs. No existing path is overwritten. --runs-root selects
an alternate parent for this example's owned outputs. Diagnostic replay must be
requested explicitly; a dirty source remains unqualified. No UI is launched.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

import numpy as np

# The application-layer provenance detector is deliberately outside ohlab.
# Running this example as a script adds the checkout root, not a numerical API.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.provenance import detect_source_revision
from ohlab import SamplingGrid
from ohlab.io.artifacts import load_run_bundle, replay_run_bundle, run_and_save_bundle
from ohlab.io.config import RunConfig
from ohlab.io.designs import design_to_json, load_design, save_design
from ohlab.target_design import TargetDesign2D, rasterize_target_design
from ohlab.targets import intensity_to_amplitude


def example_design() -> TargetDesign2D:
    """All three primitives with asymmetric placement, overlap and exact levels."""
    return TargetDesign2D({
        "schema_version": 1, "rasterizer_version": "center_sample_overwrite_v1",
        "coordinate_system": "centered_pixels_y_down_v1",
        "canvas": {"ny": 48, "nx": 64}, "background_intensity": 0.0,
        "objects": [
            {"id": "1" * 32, "type": "disk", "intensity": 0.3,
             "parameters": {"cx_px": -9.0, "cy_px": -4.0, "radius_px": 10.0}},
            {"id": "2" * 32, "type": "rectangle", "intensity": 0.65,
             "parameters": {"cx_px": 3.0, "cy_px": 2.0, "width_px": 20.0, "height_px": 12.0}},
            {"id": "3" * 32, "type": "segment", "intensity": 0.45,
             "parameters": {"x0_px": -18.0, "y0_px": 13.0, "x1_px": 19.0, "y1_px": -10.0,
                            "width_px": 4.0}},
        ],
    })


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one explicit design -> amplitude -> matched source -> M5 run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=ROOT / "runs")
    parser.add_argument("--diagnostic", action="store_true", help="explicitly request unqualified numerical replay")
    arguments = parser.parse_args(argv)
    runs = arguments.runs_root.absolute()
    design_directory = runs / "designs"
    submissions = design_directory / "submissions"
    run_directory = runs / "m7"
    for directory in (design_directory, submissions, run_directory):
        directory.mkdir(parents=True, exist_ok=True)
    design = example_design()
    intensity = rasterize_target_design(design)
    grid = SamplingGrid(ny=48, nx=64, dy=10e-6, dx=8e-6)
    amplitude = intensity_to_amplitude(intensity, grid=grid)
    source_value = float(np.sqrt(np.sum(amplitude**2) / amplitude.size))
    source = np.full(grid.shape, source_value, dtype=np.float64)
    config = RunConfig({
        "schema_version": 1, "grid": {"ny": 48, "nx": 64, "dy_m": 10e-6, "dx_m": 8e-6},
        "optics": {"wavelength_m": 633e-9, "distance_m": 5e-3},
        "solver": {"algorithm": "gerchberg_saxton", "contract": "m3_periodic_lossless_asm_v1",
                   "iterations": 20, "initialization": {"mode": "seed", "seed": 0}},
        "metrics": {"intensity_mse": {}, "intensity_nmse": {}, "intensity_psnr": {"data_range": 1.0}},
    })
    copied_path = save_design(design_directory / f"{uuid4().hex}.json", design=design)
    restored = load_design(copied_path)
    restored_raster = rasterize_target_design(restored)
    # Exact discrete identity: no numerical tolerance and no 8-bit conversion.
    assert restored_raster.dtype == intensity.dtype and restored_raster.shape == intensity.shape
    assert restored_raster.tobytes(order="C") == intensity.tobytes(order="C")
    run_id = uuid4().hex
    snapshot = save_design(submissions / f"{run_id}.json", design=restored)
    destination = run_directory / run_id
    recorded_source = detect_source_revision()
    print(f"editable copy: {copied_path}")
    print(f"submitted design snapshot: {snapshot}", flush=True)
    # These external files remain available if the M5 call fails. Nothing is
    # appended to its schema-v1 manifest or completed numerical inventory.
    bundle = run_and_save_bundle(destination, config=config, target_intensity=restored_raster,
                                 source_amplitude=source, input_png=None, source_revision=recorded_source)
    loaded = load_run_bundle(destination)
    assert loaded.arrays["target_intensity"].tobytes(order="C") == intensity.tobytes(order="C")
    current_source = detect_source_revision()
    strict = replay_run_bundle(destination, source_revision=current_source, diagnostic=False)
    print(f"completed bundle: {destination}")
    print("design JSON SHA-256: " + hashlib.sha256(design_to_json(restored)).hexdigest())
    print("target C-order bytes SHA-256: " + hashlib.sha256(intensity.tobytes(order="C")).hexdigest())
    print("design reload raster and saved target: exact dtype/shape/C-order bytes match")
    print("config: " + json.dumps(config.to_dict(), sort_keys=True, allow_nan=False))
    values, counts = np.unique(intensity, return_counts=True)
    print("target levels/counts: " + json.dumps([[float(v), int(n)] for v, n in zip(values, counts)]))
    print(f"explicit uniform source amplitude: {source_value:.17e}")
    print("recorded source: " + json.dumps(recorded_source, sort_keys=True))
    print("current source: " + json.dumps(current_source, sort_keys=True))
    print(f"strict integrity / qualification / comparison: {strict.integrity} / {strict.qualification} / {strict.comparison}")
    print("strict reasons: " + ("; ".join(strict.qualification_reasons) or "none"))
    for name, value in sorted(bundle.metrics.items()):
        print(f"{name}: {value:.17e}")
    history = bundle.arrays["residual_history"]
    print(f"separate M3 amplitude residual: initial={history[0]:.17e}; final={history[-1]:.17e}; entries={history.size}")
    print("Hard-edged target example: no Gaussian quality threshold or general convergence claim.")
    if strict.integrity != "passed" or (strict.qualification == "qualified" and strict.comparison != "passed"):
        return 1
    if arguments.diagnostic:
        diagnostic = replay_run_bundle(destination, source_revision=detect_source_revision(), diagnostic=True)
        print(f"explicit diagnostic integrity / qualification / comparison: {diagnostic.integrity} / {diagnostic.qualification} / {diagnostic.comparison}")
        print("diagnostic checks: " + json.dumps(dict(diagnostic.checks), sort_keys=True))
        if diagnostic.integrity != "passed" or diagnostic.comparison != "passed":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
