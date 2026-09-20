r"""Regenerate the two approved Milestone 4 figures from the standalone example.

    .\.venv\Scripts\python.exe -B scripts\make_m4_figures.py

The fixed example supplies the same target, M3 result, masks and public metric
calls as the printed demo. Only the two handoff PNGs are written; there is no
run bundle or metric-export framework. Image metadata contains no timestamp.
"""
from __future__ import annotations

from pathlib import Path
import runpy

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "handoffs" / "milestone_4" / "figures"


def main() -> None:
    """Measure the fixed cases and regenerate their two figures at 150 dpi."""
    # Reuse the standalone example without running its interactive entry point
    # or adding a helper module to the approved file inventory.
    example = runpy.run_path(str(ROOT / "examples" / "evaluate_reconstruction.py"))
    _, target, _, mask, result = example["build_m3_case"]()
    cases = {
        "exact_target": target,
        "twice_target": 2.0 * target,
        "actual_GS": result.reconstruction.intensity,
    }
    flat_mask, flat_cases = example["build_flat_cases"]()
    measured = example["measure_intensity_cases"](target, cases, mask)
    flat_measured = example["measure_flat_cases"](flat_cases, flat_mask)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10}):
        figures = (
            ("fig01_m3_intensity_comparisons.png", example["comparison_figure"](
                target, cases, mask, measured, float(result.residual_history[-1]),
            )),
            ("fig02_region_power_and_variation.png", example["region_figure"](
                flat_cases, flat_mask, flat_measured,
            )),
        )
        for filename, figure in figures:
            path = OUTPUT_DIR / filename
            figure.savefig(
                path, dpi=150, facecolor="white",
                metadata={"Software": "Open Holographic Lab - Milestone 4"},
            )
            plt.close(figure)
            print(f"wrote {path.relative_to(ROOT).as_posix()}")
    print("figure measurements use the five public M4 functions")
    print("fixed signal mask: radius 15 pixels, 709 selected; flat mask: rows[1:3], columns[1:5], 8 selected")
    print("PSNR data_range=1; shared display limits preserve brightness errors and reconstruction overshoot")


if __name__ == "__main__":
    main()
