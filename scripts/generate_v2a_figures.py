r"""Generate three V2a numerical figures from shipped computations and evidence.

Run the independent validation first, then generate::

    .\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v2a_interference.py --output runs\v2a-validation-NEW
    .\.venv\Scripts\python.exe -B -X utf8 scripts\generate_v2a_figures.py --evidence runs\v2a-validation-NEW

The default destination is the three approved V2a handoff PNG paths. For byte
regeneration, supply a fresh ``--output`` child of ignored ``runs/``. The script
uses Agg, starts no GUI, and never substitutes planning measurements. Set
MPLCONFIGDIR in the calling child-process environment to an owned runs folder.
Authoritative complex fields and scalar norms are never display-normalized.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import hashlib
import json
import math
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.two_path_interference import (
    DemoData,
    ILLUSTRATION_PHASE_RAD,
    PITCH_M,
    compute_demo,
)
from scripts.validate_v2a_interference import PHASES
from ohlab.optics import interference

OUTPUT = ROOT / "docs" / "handoffs" / "v2a" / "figures"
DPI = 145
PORT_COLORS = ("#24648c", "#bc582c")


def _load_evidence(directory: Path) -> tuple[dict[str, object], str]:
    """Require actual passed validation and every predeclared phase point."""
    path = directory.resolve() / "evidence.json"
    raw = path.read_bytes()
    report = json.loads(raw)
    if report.get("acceptance_passed") is not True:
        raise ValueError(f"figures require passed implementation evidence, got {path}")
    current_source_sha = hashlib.sha256(Path(interference.__file__).read_bytes()).hexdigest()
    if report["environment"]["source_sha256"] != current_source_sha:
        raise ValueError("figures require validation of the currently shipped interference source")
    phases = tuple(row["phase_rad"] for row in report["phase_sweep"])
    if phases != PHASES:
        raise ValueError(f"all ordered phase points required: expected {PHASES!r}, got {phases!r}")
    cases = report.get("independent_cases", [])
    if not any(case.get("case_id") == "asymmetric_3x4" for case in cases):
        raise ValueError("figures require the actual asymmetric_3x4 independent case")
    blocked = report.get("blocked_arm")
    if not isinstance(blocked, dict):
        raise ValueError("figures require actual blocked-arm accounting")
    return report, hashlib.sha256(raw).hexdigest()


def _verify_recomputed_data(data: DemoData, report: dict[str, object], directory: Path) -> None:
    """Match the plotted data to the actual validation rows and saved arrays."""
    for actual, validated in zip(data.report["phase_sweep"], report["phase_sweep"], strict=True):
        for stage in ("inputs", "split", "propagated", "combiner", "outputs"):
            np.testing.assert_array_equal(actual["norms"][stage], validated["norms"][stage],
                                          err_msg=f"plotted {stage} must match actual validation")
    # Byte identity here is a same-platform same-function provenance check,
    # separate from the independent scientific tolerance comparisons.
    def same_bytes(actual: np.ndarray, validated: np.ndarray) -> None:
        if (actual.shape != validated.shape or actual.dtype != validated.dtype
                or actual.tobytes(order="C") != validated.tobytes(order="C")):
            raise AssertionError("recomputed figure array differs from actual validation bytes")

    with np.load(directory / "demo_phi037.npz", allow_pickle=False) as validated:
        for name in ("incident", "output_0", "output_1"):
            same_bytes(data.arrays[f"demo_{name}"], validated[name])
    with np.load(directory / "asymmetric_3x4.npz", allow_pickle=False) as validated:
        for port in (0, 1):
            same_bytes(data.arrays[f"reference_output_{port}"], validated[f"output_{port}"])
            same_bytes(data.arrays[f"independent_reference_{port}"], validated[f"reference_{port}"])


def _raw_image(axis, data: np.ndarray, *, dy_m: float, dx_m: float,
               title: str, vmax: float, cmap: str = "magma"):
    """Display all sample cells in the repository's +y-down convention."""
    ny, nx = data.shape
    x0 = -(nx // 2) * dx_m
    y0 = -(ny // 2) * dy_m
    extent = (
        (x0 - dx_m / 2) * 1e6, (x0 + (nx - 0.5) * dx_m) * 1e6,
        (y0 + (ny - 0.5) * dy_m) * 1e6, (y0 - dy_m / 2) * 1e6,
    )
    image = axis.imshow(data, origin="upper", extent=extent, vmin=0.0,
                        vmax=vmax, cmap=cmap, interpolation="nearest")
    axis.set(title=title, xlabel="x (µm)", ylabel="y (µm; +y down)")
    return image


def _provenance(figure, evidence_sha: str) -> None:
    # Reserve a footer band so provenance never overlaps scientific axes.
    figure.get_layout_engine().set(rect=(0.0, 0.035, 1.0, 0.965))
    figure.text(0.01, 0.006,
                 f"Numerical V2a evidence; source JSON SHA-256 {evidence_sha}",
                 fontsize=6.5, color="#555555")


def _schematic(axis) -> None:
    """Draw declared logical topology; no geometric mirrors are implied."""
    axis.set(xlim=(0, 1), ylim=(0, 1))
    axis.axis("off")

    def box(x, y, width, height, text):
        axis.add_patch(FancyBboxPatch(
            (x, y), width, height, boxstyle="round,pad=0.012",
            facecolor="#eef2f4", edgecolor="#3f5766", linewidth=1.1,
        ))
        axis.text(x + width / 2, y + height / 2, text,
                  ha="center", va="center", fontsize=11)

    def arrow(start, end, color="#52616b"):
        axis.annotate("", xy=end, xytext=start,
                      arrowprops={"arrowstyle": "->", "lw": 1.7, "color": color})

    box(0.19, 0.35, 0.08, 0.30, "B")
    box(0.73, 0.35, 0.08, 0.30, "B†")
    arrow((0.02, 0.60), (0.18, 0.60))
    arrow((0.02, 0.40), (0.18, 0.40))
    axis.text(0.02, 0.69, "Input 0: U", fontsize=11)
    axis.text(0.02, 0.24, "Input 1: zero", fontsize=11)
    for y, color in ((0.75, PORT_COLORS[0]), (0.25, PORT_COLORS[1])):
        arrow((0.28, y), (0.72, y), color)
    axis.text(0.49, 0.84, "Arm 0: forward ASM(L₀=2 mm)",
              ha="center", fontsize=11, color=PORT_COLORS[0])
    axis.text(0.49, 0.11, "Arm 1: forward ASM(L₁=2 mm), then exp(iφ)",
              ha="center", fontsize=11, color=PORT_COLORS[1])
    axis.plot((0.27, 0.30, 0.30), (0.60, 0.60, 0.75), color=PORT_COLORS[0])
    axis.plot((0.27, 0.30, 0.30), (0.40, 0.40, 0.25), color=PORT_COLORS[1])
    axis.plot((0.70, 0.70, 0.73), (0.75, 0.60, 0.60), color=PORT_COLORS[0])
    axis.plot((0.70, 0.70, 0.73), (0.25, 0.40, 0.40), color=PORT_COLORS[1])
    arrow((0.82, 0.60), (0.98, 0.60), PORT_COLORS[0])
    arrow((0.82, 0.40), (0.98, 0.40), PORT_COLORS[1])
    axis.text(0.82, 0.69, "Output 0", fontsize=11, color=PORT_COLORS[0])
    axis.text(0.82, 0.24, "Output 1", fontsize=11, color=PORT_COLORS[1])
    axis.text(0.49, 0.48,
              "Identical transverse frames and sample correspondence\n"
              "Arm reference planes: after B → before B†",
              ha="center", va="center", fontsize=10)


def unfolded_figure(data: DemoData, evidence_sha: str):
    """Show actual uniform fields on a fixed shared raw intensity scale."""
    fig = plt.figure(figsize=(14.5, 8.4), layout="constrained")
    grid = fig.add_gridspec(2, 3, height_ratios=(0.85, 1.2))
    _schematic(fig.add_subplot(grid[0, :]))
    axes = [fig.add_subplot(grid[1, column]) for column in range(3)]
    fields = [data.arrays["demo_incident"], data.arrays["demo_output_0"], data.arrays["demo_output_1"]]
    labels = ["Incident |U|²", "Actual output 0 |U₀|²", "Actual output 1 |U₁|²"]
    for axis, field, label in zip(axes, fields, labels, strict=True):
        intensity = field.real**2 + field.imag**2
        image = _raw_image(axis, intensity, dy_m=PITCH_M, dx_m=PITCH_M,
                           title=f"{label}\nmax = {float(np.max(intensity)):.9f}", vmax=1.0)
    fig.colorbar(image, ax=axes, shrink=0.82, label="Shared raw intensity (amplitude-unit²); fixed 0…1")
    record = next(row for row in data.report["phase_sweep"] if row["phase_rad"] == ILLUSTRATION_PHASE_RAD)
    fractions = record["norms"]["output_fractions"]
    fig.suptitle(
        "V2a ideal unfolded two-path model — logical topology, not physical reflection geometry\n"
        f"64² at 4 µm; λ=633 nm; φ={ILLUSTRATION_PHASE_RAD:g} rad; "
        f"N₀/Nin={fractions[0]:.9f}, N₁/Nin={fractions[1]:.9f}\n"
        "Uniform equal modes redistribute brightness. No spatial stripes or per-output normalization.",
        fontsize=12,
    )
    _provenance(fig, evidence_sha)
    return fig


def sweep_figure(data: DemoData, evidence_sha: str):
    """Retain every prescribed point and signed stage residual."""
    rows = data.report["phase_sweep"]
    phases = np.array([row["phase_rad"] for row in rows])
    fractions = np.array([row["norms"]["output_fractions"] for row in rows])
    fig, axes = plt.subplots(2, 2, figsize=(14.5, 9.4), layout="constrained")
    dense_phase = np.linspace(-1.0, 2 * math.pi + 0.15, 500)
    for port in (0, 1):
        expected = np.cos(dense_phase / 2)**2 if port == 0 else np.sin(dense_phase / 2)**2
        axes[0, 0].plot(dense_phase, expected, color=PORT_COLORS[port],
                        label=f"analytic port {port}: {'cos²' if port == 0 else 'sin²'}(φ/2)")
        axes[0, 0].scatter(phases, fractions[:, port], marker="o" if port == 0 else "s",
                           s=45, edgecolors="white", color=PORT_COLORS[port], zorder=3,
                           label=f"actual port {port}: all 8 points")
    for index, phase in enumerate(phases):
        axes[0, 0].annotate(str(index + 1), (phase, fractions[index, 0]),
                             xytext=(5, 7), textcoords="offset points", fontsize=8)
    axes[0, 0].set(xlabel="Extra arm-1 phase φ (rad)", ylabel="Noutput / original Nin",
                    title="Lossless equal arms: primary input-normalized fractions", ylim=(-0.06, 1.1))
    axes[0, 0].legend(fontsize=8)
    chosen = next(row for row in rows if row["phase_rad"] == ILLUSTRATION_PHASE_RAD)
    stages = ("inputs", "split", "propagated", "combiner", "outputs")
    for port in (0, 1):
        values = [chosen["norms"][stage][port] / 1e-8 for stage in stages]
        axes[0, 1].plot(stages, values, "o-", color=PORT_COLORS[port], label=f"port/arm {port}")
    axes[0, 1].set(ylabel="Actual sampled norm / 10⁻⁸ (amplitude-unit²·m²)",
                    title="All ten raw stage norms at φ=0.37 rad")
    axes[0, 1].legend(fontsize=9)
    delta_names = ("split_delta", "propagation_delta", "phase_delta", "recombination_delta", "total_delta")
    markers = ("o", "s", "^", "D", "x")
    x = np.arange(1, len(rows) + 1)
    for name, marker in zip(delta_names, markers, strict=True):
        scaled = [row["norms"][name] / row["norms"]["inputs_total"] * 1e15 for row in rows]
        axes[1, 0].plot(x, scaled, marker=marker, label=name.replace("_delta", ""), alpha=0.83)
    axes[1, 0].axhline(0, color="#777777", linewidth=0.8)
    axes[1, 0].set(xlabel="Prescribed point number (table order)",
                    ylabel="Signed (after − before) / Nin × 10¹⁵",
                    title="Roundoff retained with sign; not labeled absorption", xticks=x)
    axes[1, 0].legend(fontsize=8)
    axes[1, 1].axis("off")
    cell_rows = []
    for index, row in enumerate(rows):
        norms = row["norms"]
        cell_rows.append([
            str(index + 1), f"{row['phase_rad']:.6f}",
            f"{norms['outputs'][0]:.4e}", f"{norms['outputs'][1]:.4e}",
            f"{norms['total_delta']:+.2e}",
        ])
    table = axes[1, 1].table(
        cellText=cell_rows, colLabels=("#", "φ (rad)", "Noutput 0", "Noutput 1", "Nout − Nin"),
        loc="upper center", cellLoc="center", bbox=(0, 0.38, 1, 0.6),
        colWidths=(0.055, 0.18, 0.255, 0.255, 0.255),
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.3)
    inputs_total = rows[0]["norms"]["inputs_total"]
    max_error = max(max(row["input_scaled_max_complex_errors"]) for row in rows)
    axes[1, 1].text(0.01, 0.31,
        f"All rows retained, including near-dark numerical residuals.\n"
        f"Nin={inputs_total:.12e} amplitude-unit²·m²\n"
        f"Worst input-scaled complex analytic discrepancy: {max_error:.3e}\n"
        "Fixed distances and propagating uniform spectrum: τ=1.\n"
        "General equal-arm input fractions are τ cos² and τ sin².\n"
        "No output-total denominator or phase alignment is used.",
        va="top", fontsize=9.2)
    fig.suptitle("V2a complete declared phase sweep — complex fields, budgets and signed residuals", fontsize=13)
    _provenance(fig, evidence_sha)
    return fig


def controls_figure(data: DemoData, evidence_sha: str):
    """Display real blocked-arm accounting and independent complex discrepancies."""
    blocked = data.report["blocked_arm"]
    reference = data.report["independent_reference"]
    fig, axes = plt.subplots(2, 2, figsize=(14.5, 9.0), layout="constrained")
    incident_norm = blocked["incident_norm"]
    budget = [1.0, blocked["survivor_norm"] / incident_norm,
              blocked["removed_norm"] / incident_norm, *blocked["output_fractions_original_input"]]
    labels = ("Original\nincident", "Surviving\narm 0", "Removed\narm 1", "Output 0", "Output 1")
    axes[0, 0].bar(labels, budget, color=("#657078", "#24648c", "#aaa3a0", *PORT_COLORS))
    for index, value in enumerate(budget):
        axes[0, 0].text(index, value + 0.025, f"{value:.6f}", ha="center", fontsize=9)
    axes[0, 0].set(ylim=(0, 1.18), ylabel="Norm / original incident norm",
                    title="Intentional blocking: half removed; quarter at each output")
    phase_rows = blocked["surviving_phase_rows"]
    axes[0, 1].axis("off")
    worst_intensity = max(max(row["intensity_max_abs_difference_from_zero_phase"]) for row in phase_rows)
    max_complex = max(reference["absolute_max_complex_errors"])
    max_scaled = max(reference["input_scaled_max_complex_errors"])
    axes[0, 1].text(0, 0.98,
        "Blocked-arm control is outside the runner specification.\n"
        "Set propagated arm 1 to zero at the precombiner boundary.\n"
        f"Actual incident norm: {incident_norm:.12e}\n"
        f"Actual removed arm-1 norm: {blocked['removed_norm']:.12e}\n"
        f"Combined outputs / original input: {sum(blocked['output_fractions_original_input']):.12f}\n\n"
        "A uniform phase on the sole surviving arm 0 changes its\n"
        "complex phase, while both output intensities stay invariant.\n"
        f"All 8 phases retained; worst intensity difference: {worst_intensity:.3e}\n\n"
        "Independent asymmetric 3×4 full-pipeline DFT below:\n"
        "dx=3.7 µm, dy=4.1 µm, λ=633 nm, arms 2/3 mm, φ=0.37.\n"
        f"Worst absolute complex discrepancy: {max_complex:.6e}\n"
        f"Worst input-amplitude-scaled discrepancy: {max_scaled:.6e}\n"
        "No fitted phase, scaled reference, mirror flip or resampling.",
        va="top", fontsize=9.8)
    discrepancies = [np.abs(data.arrays[f"reference_discrepancy_{port}"]) for port in (0, 1)]
    maximum = max(float(np.max(values)) for values in discrepancies)
    for port in (0, 1):
        image = _raw_image(
            axes[1, port], discrepancies[port], dy_m=4.1e-6, dx_m=3.7e-6,
            title=f"Port {port}: |Ushipped − Uindependent|\nActual maximum {reference['absolute_max_complex_errors'][port]:.6e}",
            vmax=maximum, cmap="viridis",
        )
    fig.colorbar(image, ax=axes[1, :], shrink=0.84,
                 label="Absolute complex discrepancy (amplitude units); shared linear scale")
    fig.suptitle("V2a numerical controls — actual removed norm and independent complex-array evidence", fontsize=13)
    _provenance(fig, evidence_sha)
    return fig


def _output_directory(path: Path) -> Path:
    target = path.resolve()
    approved = OUTPUT.resolve()
    if target == approved:
        target.mkdir(parents=True, exist_ok=True)
    elif target.is_relative_to((ROOT / "runs").resolve()) and target != (ROOT / "runs").resolve():
        target.mkdir(parents=True, exist_ok=False)
    else:
        raise ValueError(f"output must be approved {approved} or a fresh ignored runs child, got {target}")
    return target


def main(argv: Sequence[str] | None = None) -> int:
    """Generate only the three figures; print actual same-environment hashes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True,
                        help="directory containing actual passed validation evidence.json")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    report, evidence_sha = _load_evidence(args.evidence)
    data = compute_demo(n=64)
    _verify_recomputed_data(data, report, args.evidence.resolve())
    output = _output_directory(args.output)
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 9}):
        figures = (
            ("fig01_unfolded_interferometer.png", unfolded_figure(data, evidence_sha)),
            ("fig02_phase_sweep.png", sweep_figure(data, evidence_sha)),
            ("fig03_reference_and_controls.png", controls_figure(data, evidence_sha)),
        )
        for name, figure in figures:
            path = output / name
            figure.savefig(path, dpi=DPI, facecolor="white",
                           metadata={"Software": "Open Holographic Lab V2a numerical evidence"})
            plt.close(figure)
            print(f"{path} sha256={hashlib.sha256(path.read_bytes()).hexdigest()}")
    print(f"Source implementation evidence SHA-256: {evidence_sha}")
    print("Fixed shared raw intensity scale 0..1; signed norms retained; no output normalization.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
