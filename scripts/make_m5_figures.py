r"""Regenerate exactly the two explanatory, non-authoritative M5 diagrams.

    .\.venv\Scripts\python.exe -B scripts\make_m5_figures.py

The diagrams describe the bundle and verification contracts. They do not run
a solver, contain numerical correctness evidence, or become bundle artifacts.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "handoffs" / "milestone_5" / "figures"
INK = "#183044"
BLUE = "#e9f2fa"
GREEN = "#e9f5ed"
ORANGE = "#fff2dc"
PURPLE = "#f1ebf8"


def _canvas(title: str, subtitle: str) -> tuple[Figure, Axes]:
    figure, axis = plt.subplots(figsize=(14.4, 10.2))
    figure.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    axis.set(xlim=(0.0, 1.0), ylim=(0.0, 1.0))
    axis.axis("off")
    axis.text(0.5, 0.975, title, ha="center", va="top", fontsize=20, fontweight="bold", color=INK)
    axis.text(0.5, 0.925, subtitle, ha="center", va="top", fontsize=12, color=INK)
    return figure, axis


def _box(
    axis: Axes, x: float, y: float, width: float, height: float,
    title: str, body: str, color: str, *, font_size: float = 12.0,
) -> None:
    axis.add_patch(FancyBboxPatch(
        (x, y), width, height, boxstyle="round,pad=0.012,rounding_size=0.012",
        linewidth=1.2, edgecolor="#8093a4", facecolor=color,
    ))
    axis.text(x + 0.016, y + height - 0.018, title, ha="left", va="top",
              fontsize=13, fontweight="bold", color=INK)
    axis.text(x + 0.016, y + height - 0.063, body, ha="left", va="top",
              fontsize=font_size, linespacing=1.55, color=INK)


def _arrow(axis: Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    axis.add_patch(FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=17,
        color="#506b80", linewidth=1.7,
    ))


def bundle_anatomy() -> Figure:
    """Separate authoritative values, checked derivations, and optional provenance."""
    figure, axis = _canvas(
        "One run directory, with explicit scientific roles",
        "Schema v1 | JSON metadata + typed NPY 1.0 arrays | All references are bundle-relative",
    )
    _box(axis, 0.025, 0.495, 0.455, 0.365, "Authoritative numerical inputs", (
        "target_intensity.npy  — M2 design, float64\n"
        "target_amplitude.npy  — actual GS input, float64\n"
        "source_amplitude.npy  — prescribed illumination\n"
        "initial_phase.npy  — explicit-phase mode only\n"
        "signal_mask.npy  — when the fraction is requested\n"
        "cv_mask.npy  — when regional CV is requested\n"
        "Seed mode instead records the original seed in config."
    ), BLUE, font_size=11.5)
    _box(axis, 0.525, 0.495, 0.45, 0.365, "Authoritative numerical outputs", (
        "source_field.npy  — actual final complex128 field\n"
        "reconstruction_field.npy  — actual complex128 field\n"
        "residual_history.npy  — all N+1 float64 residuals\n\n"
        "The saved source field is not reconstructed from phase.\n"
        "The reconstruction is the actual forward result,\n"
        "before any target-amplitude replacement."
    ), GREEN, font_size=11.5)
    _box(axis, 0.025, 0.16, 0.455, 0.285, "Metadata and integrity", (
        "config.json  — grid, optics, solver, initialization,\n"
        "                         metric parameters and software\n"
        "metrics.json  — named values; PSNR +inf is a string\n"
        "manifest.json  — roles, paths, shapes/dtypes and hashes\n\n"
        "Hash every declared file except manifest.json itself."
    ), PURPLE, font_size=11.5)
    _box(axis, 0.525, 0.16, 0.45, 0.285, "Checked derivations and optional provenance", (
        "phase.npy  — canonical source phase, float64\n"
        "reconstruction_intensity.npy  — intensity, float64\n"
        "Derived arrays are saved and checked against their fields.\n\n"
        "input_target.png  — optional exact original bytes\n"
        "PNG is provenance; numerical replay uses saved arrays."
    ), ORANGE, font_size=11.5)
    axis.text(0.5, 0.09, "Only conditional files needed by this run are present; no previews are authoritative.",
              ha="center", va="center", fontsize=12, color=INK)
    axis.text(0.5, 0.05, "SHA-256 detects changed bytes relative to the manifest. It is not a signature or proof of authorship.",
              ha="center", va="center", fontsize=12, color=INK)
    axis.text(0.5, 0.015, "Explanatory diagram — independent tests and measured replay results provide the evidence.",
              ha="center", va="center", fontsize=10.5, color="#536777")
    return figure


def integrity_and_replay() -> Figure:
    """Explain independent integrity, qualification and numerical-comparison outcomes."""
    figure, axis = _canvas(
        "Integrity and numerical replay answer different questions",
        "A coherent run is computed once from captured inputs; replay invokes the existing M3 and M4 functions again",
    )
    _box(axis, 0.025, 0.60, 0.43, 0.255, "Create one coherent run", (
        "M2 target + explicit source amplitude + RunConfig\n"
        "Capture owned C-order inputs, then run M3 and M4.\n"
        "Persist actual fields, history and measured intensity.\n"
        "Optional PNG: copy and check the exact retained bytes."
    ), BLUE, font_size=11.5)
    _arrow(axis, (0.24, 0.587), (0.24, 0.553))
    _box(axis, 0.025, 0.32, 0.43, 0.215, "Publish one completed directory", (
        "Exclusive temporary sibling; write, flush/fsync, close.\n"
        "Manifest last; verify staged contents, then rename.\n"
        "Refuse an existing destination.\n"
        "Public readers reject reserved partial directories."
    ), PURPLE, font_size=11.5)
    axis.plot([0.466, 0.495, 0.495], [0.428, 0.428, 0.74], color="#506b80", linewidth=1.7)
    _arrow(axis, (0.495, 0.74), (0.525, 0.74))
    _box(axis, 0.025, 0.105, 0.43, 0.16, "What this does not claim", (
        "No universal cross-platform bitwise guarantee.\n"
        "No authorship, hardware accuracy or GS convergence\n"
        "claim follows from a valid run bundle."
    ), ORANGE, font_size=11.5)
    _box(axis, 0.54, 0.625, 0.435, 0.23, "1  Artifact integrity: passed / failed", (
        "Check inventory, bounded paths and SHA-256 first.\n"
        "Decode only the verified byte snapshots.\n"
        "Corruption blocks loading and solver invocation."
    ), GREEN, font_size=11.5)
    _arrow(axis, (0.757, 0.612), (0.757, 0.580))
    _box(axis, 0.54, 0.365, 0.435, 0.195, "2  Source/environment: qualified / unqualified", (
        "Compare recorded metadata with current code/environment.\n"
        "Clean same revision is required; dirty/unknown is visible.\n"
        "Default unqualified replay: comparison is not run."
    ), PURPLE, font_size=11.1)
    _arrow(axis, (0.757, 0.351), (0.757, 0.317))
    _box(axis, 0.54, 0.105, 0.435, 0.195, "3  Numerical comparison: passed / failed / not run", (
        "Re-run from saved inputs; recompute both sets of metrics.\n"
        "Compare fields, phase, intensity and history exactly.\n"
        "Diagnostic replay can run while remaining unqualified."
    ), BLUE, font_size=11.1)
    axis.text(0.5, 0.056, "Matching metadata is a qualification policy. Matching outputs is a separately measured result.",
              ha="center", va="center", fontsize=12, color=INK)
    axis.text(0.5, 0.016, "Explanatory diagram — a figure is not numerical evidence, and integrity does not establish semantic correctness.",
              ha="center", va="center", fontsize=10.5, color="#536777")
    return figure


def main() -> None:
    """Write exactly the two handoff illustrations with deterministic metadata."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 11}):
        figures = (
            ("fig01_run_bundle_anatomy.png", bundle_anatomy()),
            ("fig02_integrity_and_replay.png", integrity_and_replay()),
        )
        for filename, figure in figures:
            path = OUTPUT_DIR / filename
            figure.savefig(path, dpi=150, facecolor="white",
                           metadata={"Software": "Open Holographic Lab - Milestone 5"})
            plt.close(figure)
            print(f"wrote {path.relative_to(ROOT).as_posix()}")
    print("explanatory diagrams only; no solver execution or numerical evidence is implied")


if __name__ == "__main__":
    main()
