r"""Regenerate three V0 numerical figures from shipped computations/evidence.

Required full evidence first::

    .\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v0_optics.py --full --output runs\v0_acceptance_20261001\full_optical_validation_diagnostics_final
    .\.venv\Scripts\python.exe -B -X utf8 scripts\generate_v0_figures.py --validation-report runs\v0_acceptance_20261001\full_optical_validation_diagnostics_final\validation_report.json

The aperture plot refuses incomplete evidence; it never substitutes planning
measurements. Display-only masks/crops leave optical arrays and metrics intact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from collections.abc import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.sequential_optics import compute_demo
from scripts.validate_v0_optics import second_moment_radius

OUTPUT_DIR = ROOT / "docs" / "handoffs" / "v0" / "figures"
DPI = 145


def _image(axis, data: np.ndarray, grid, *, title: str, vmax: float, phase: bool = False):
    extent = [grid.x[0] * 1e6, grid.x[-1] * 1e6, grid.y[-1] * 1e6, grid.y[0] * 1e6]
    image = axis.imshow(data, extent=extent, origin="upper", cmap="twilight" if phase else "magma",
                        vmin=-math.pi if phase else 0, vmax=math.pi if phase else vmax)
    axis.set(xlim=(-250, 250), ylim=(250, -250), xlabel="x (µm)", ylabel="y (µm)", title=title)
    return image


def _phase(data: np.ndarray) -> np.ma.MaskedArray:
    """Display phase only where intensity >= 1e-6 of this field's peak."""
    intensity = np.abs(data) ** 2
    return np.ma.masked_where(intensity < 1e-6 * intensity.max(), np.angle(data))


def _schematic(axis, spec) -> None:
    """Draw actual stored longitudinal positions; colocated actions stay named."""
    inset = axis.inset_axes([0.0, 0.79, 0.98, 0.20])
    terminal_mm = spec.observation.z_m * 1e3
    inset.plot([0, terminal_mm], [0, 0], color="#555555", linewidth=1.5)
    inset.scatter([0, terminal_mm], [0, 0], color="black", s=20)
    inset.annotate("source", (0, 0), xytext=(0, -17), textcoords="offset points", ha="center", fontsize=8)
    for index, component in enumerate(spec.components):
        position = component.z_m * 1e3
        height = 0.7 + index * 0.6
        inset.plot([position, position], [0, height], color="#477394")
        inset.text(position, height, component.id, va="bottom", ha="center", fontsize=8)
    inset.annotate(spec.observation.id, (terminal_mm, 0), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8)
    inset.set(xlim=(-max(terminal_mm * 0.11, 0.1), terminal_mm * 1.11),
              ylim=(-0.5, 2.1), xlabel="Actual longitudinal z (mm)", yticks=[])
    inset.spines[["left", "right", "top"]].set_visible(False)
    inset.tick_params(axis="x", labelsize=7)


def gaussian_free_figure(cases):
    case = next(case for case in cases if case.label == "free")
    result, spec = case.result, case.result.experiment
    source = result.field_at("source").data
    observation = result.observation.data
    grid = spec.grid
    fig, axes = plt.subplots(2, 3, figsize=(14.5, 8.5), constrained_layout=True)
    fig.suptitle(
        "V0 Gaussian free propagation: source z=0 → observation z=20 mm\n"
        "λ=633 nm; w₀=100 µm (1/e amplitude); A₀=1; φ₀=0 rad; 512² at 4 µm; periodic 2.048 mm window",
        fontsize=13,
    )
    vmax = max(float(np.abs(source).max() ** 2), float(np.abs(observation).max() ** 2))
    image = _image(axes[0, 0], np.abs(source) ** 2, grid, title="Source |U|²", vmax=vmax)
    _image(axes[0, 1], np.abs(observation) ** 2, grid, title="Actual observation |U|² (same scale)", vmax=vmax)
    fig.colorbar(image, ax=axes[0, :2], label="Intensity (amplitude-unit²)", shrink=0.82)
    phase_image = _image(axes[0, 2], _phase(observation), grid, title="Observation phase; dark support masked", vmax=math.pi, phase=True)
    fig.colorbar(phase_image, ax=axes[0, 2], label="Phase (rad)", shrink=0.82)
    row = grid.ny // 2
    axes[1, 0].plot(grid.x * 1e6, np.abs(source[row]) ** 2, label="source", color="#888888")
    axes[1, 0].plot(grid.x * 1e6, np.abs(observation[row]) ** 2, label="ASM observation")
    axes[1, 0].plot(grid.x * 1e6, np.abs(case.reference[row]) ** 2, "--", label="independent paraxial")
    axes[1, 0].set(xlim=(-250, 250), xlabel="x (µm), y=0", ylabel="|U|² (amplitude-unit²)", title="Unnormalized intensity profiles")
    axes[1, 0].legend(fontsize=8)
    axes[1, 1].plot(grid.x * 1e6, np.abs(observation[row] - case.reference[row]))
    axes[1, 1].set(xlim=(-250, 250), xlabel="x (µm), y=0", ylabel="|UASM − Uparaxial| (amplitude units)", title="Complex discrepancy, no fitted phase/scale")
    norms = [stage.norm for stage in result.stages]
    axes[1, 2].axis("off")
    _schematic(axes[1, 2], spec)
    axes[1, 2].text(0, 0.68,
        f"Actual source norm: {norms[0]:.9e}\nActual terminal norm: {norms[-1]:.9e}\n"
        f"Signed norm difference: {norms[-1]-norms[0]:+.3e}\nUnits: amplitude-unit² · m²\n\n"
        f"Complex relative L2: {case.complex_relative_l2:.6e}\n"
        f"Second-moment radius: {second_moment_radius(observation, grid)*1e6:.6f} µm\n\n"
        "View is ±250 µm, not a physical crop.\nPhase mask: I < 10⁻⁶ max(I), display only.\n"
        "Full-window norm and error use every sample.\nNo unit-power or display normalization.\n"
        "Gaussian reference is paraxial; ASM is not.", va="top", fontsize=9.3)
    return fig


def lens_waist_figure(cases):
    lens_cases = [case for case in cases if case.label.startswith("lens_")]
    waist = next(case for case in lens_cases if case.label == "lens_at_waist")
    focal_plane = next(case for case in lens_cases if case.label == "lens_at_f")
    clipped = next(case for case in cases if case.label == "aperture_lens")
    spec = waist.result.experiment
    grid = spec.grid
    fig, axes = plt.subplots(2, 3, figsize=(14.5, 8.5), constrained_layout=True)
    fig.suptitle(
        "V0 Gaussian lens experiment: source → lens f=+20 mm at z=0 → selected observations\n"
        "Same λ=633 nm, w₀=100 µm, A₀=1, φ₀=0, 512²/4 µm; optional radius-80 µm aperture before lens",
        fontsize=13,
    )
    vmax = max(float(np.abs(case.result.observation.data).max() ** 2) for case in (*lens_cases, clipped))
    image = _image(axes[0, 0], focal_plane.result.observation.intensity, grid,
                   title=f"No aperture; z={focal_plane.result.experiment.observation.z_m*1e3:.6f} mm", vmax=vmax)
    _image(axes[0, 1], clipped.result.observation.intensity, grid,
           title="Explicit aperture → lens → same z (same scale)", vmax=vmax)
    fig.colorbar(image, ax=axes[0, :2], label="Intensity (amplitude-unit²)", shrink=0.82)
    row = grid.ny // 2
    for case in lens_cases:
        z = case.result.experiment.observation.z_m
        axes[0, 2].plot(grid.x * 1e6, case.result.observation.intensity[row], label=f"z={z*1e3:.3f} mm")
    axes[0, 2].plot(grid.x * 1e6, clipped.result.observation.intensity[row], "--", color="black", label="apertured at 20 mm")
    axes[0, 2].set(xlim=(-130, 130), xlabel="x (µm), y=0", ylabel="|U|² (amplitude-unit²)", title="Actual profiles; no peak normalization")
    axes[0, 2].legend(fontsize=8)
    focal = spec.components[0].focal_length_m
    rayleigh = math.pi * spec.source.waist_radius_m**2 / spec.wavelength_m
    q_lens = 1 / (1 / complex(0, -rayleigh) - 1 / focal)
    z_values = np.linspace(min(case.result.experiment.observation.z_m for case in lens_cases) - 1e-3,
                           max(case.result.experiment.observation.z_m for case in lens_cases) + 1e-3, 160)
    radii = np.sqrt(spec.wavelength_m / (math.pi * np.imag(1 / (q_lens + z_values))))
    axes[1, 0].plot(z_values * 1e3, radii * 1e6, label="independent paraxial width")
    axes[1, 0].scatter([case.result.experiment.observation.z_m*1e3 for case in lens_cases],
                       [second_moment_radius(case.result.observation.data, grid)*1e6 for case in lens_cases],
                       label="ASM second moment", zorder=3)
    axes[1, 0].axvline(spec.observation.z_m*1e3, linestyle=":", color="black", label="analytic minimum")
    axes[1, 0].axvline(focal*1e3, linestyle="--", color="#888888", label="focal distance")
    axes[1, 0].set(xlabel="Observation z (mm)", ylabel="1/e amplitude radius (µm)", title="Finite Gaussian minimum differs from f")
    axes[1, 0].legend(fontsize=8)
    phase_image = _image(axes[1, 1], _phase(waist.result.observation.data), grid,
                         title="Waist-plane phase; dark support masked", vmax=math.pi, phase=True)
    fig.colorbar(phase_image, ax=axes[1, 1], label="Phase (rad)", shrink=0.82)
    before = next(stage for stage in clipped.result.stages if stage.selector == "before:aperture")
    after = next(stage for stage in clipped.result.stages if stage.selector == "after:aperture")
    lens_after = next(stage for stage in clipped.result.stages if stage.selector == "after:lens")
    axes[1, 2].axis("off")
    _schematic(axes[1, 2], clipped.result.experiment)
    axes[1, 2].text(0, 0.68,
        f"Source / lens / aperture: z=0\nApertured terminal: z={clipped.result.experiment.observation.z_m*1e3:.9f} mm\n"
        f"Analytic Gaussian minimum: {spec.observation.z_m*1e3:.9f} mm\n"
        f"Lens minimum-plane complex L2: {waist.complex_relative_l2:.6e}\n\n"
        f"Norm before aperture: {before.norm:.9e}\nNorm after aperture: {after.norm:.9e}\n"
        f"Aperture signed difference: {after.delta_norm:+.9e}\nLens signed difference: {lens_after.delta_norm:+.3e}\n"
        "Norm units: amplitude-unit² · m²\n\n"
        "Clipped field has no Gaussian ABCD ground truth.\nSeparate convergence evidence is required.\n"
        "Phase mask is display-only; no array crop.\nNo hidden lens aperture or renormalization.", va="top", fontsize=8.6)
    return fig


def aperture_convergence_figure(report: dict[str, object], report_sha: str):
    """Plot all five actually run approved rectangular aperture cases."""
    rows = report["aperture_convergence"]
    expected = {(512, 4e-6), (1024, 4e-6), (1024, 2e-6), (2048, 2e-6), (2048, 1e-6)}
    actual = {(row["n"], row["pitch_m"]) for row in rows}
    if actual != expected or len(rows) != 5 or report.get("acceptance_passed") is not True:
        raise ValueError("figure requires passed --full validation with all five approved convergence cases")
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.4), constrained_layout=True)
    labels = [f"{row['n']}²\n{row['pitch_m']*1e6:g} µm" for row in rows]
    errors = [row["relative_complex_l2"] for row in rows]
    axes[0].bar(labels, errors, color=["#aa5533" if error > 0.035 else "#287859" for error in errors])
    axes[0].axhline(0.035, color="black", linestyle="--", label="finest declared bound: 0.035")
    for index, error in enumerate(errors):
        axes[0].text(index, error + 0.002, f"{error:.6f}", ha="center", fontsize=8)
    axes[0].set(ylabel="Relative complex L2 within fixed ROI", title="All window / pitch cases retained", ylim=(0, max(errors)*1.19))
    axes[0].legend(fontsize=8)
    biases = [row["sampled_area_m2"] / (80e-6 * 120e-6) - 1 for row in rows]
    axes[1].bar(labels, biases, color="#477394")
    axes[1].set(ylabel="Sampled area / physical area − 1", title="Inclusive hard-edge center-sampling bias")
    for index, bias in enumerate(biases):
        axes[1].text(index, bias + 0.001, f"{bias:.6f}", ha="center", fontsize=8)
    axes[2].axis("off")
    axes[2].text(0, 0.98,
        "Uniform A=1 → explicit 80 × 120 µm aperture\n→ 5 mm free space → actual observation\n"
        "λ=633 nm; one complete periodic grid\n\n"
        "ROI: |x| ≤ 100 µm and |y| ≤ 100 µm\nIndependent continuous Fresnel field:\n"
        "original physical dimensions, amplitude 1\ncarrier and complex prefactor retained\n\n"
        "Metric = √[ΣROI|U−Uref|² / ΣROI|Uref|²]\nNo intensity-error / worst-pixel claim.\n"
        "No fitted amplitude or global phase.\nNo altered reference aperture or ROI.\n\n"
        "Larger window alone does not remove\nhard-edge center-sampling error.\n"
        "Fresnel approximation error is separate.\nThe finest case supports ~2.7% L2,\nnot sub-percent continuous accuracy.", va="top", fontsize=10)
    fig.suptitle("V0 bounded aperture diffraction: actual full validation, fixed physical experiment", fontsize=13)
    fig.text(0.01, -0.025, f"Source evidence SHA-256: {report_sha}", fontsize=7)
    return fig


def main(argv: Sequence[str] | None = None) -> int:
    """Generate only the three approved figures and print deterministic hashes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-report", type=Path, required=True)
    args = parser.parse_args(argv)
    evidence_bytes = args.validation_report.read_bytes()
    report = json.loads(evidence_bytes)
    report_sha = hashlib.sha256(evidence_bytes).hexdigest()
    # Validate the full evidence before executing even the modest demo.
    convergence = aperture_convergence_figure(report, report_sha)
    cases = compute_demo()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 9}):
        figures = [
            ("fig01_gaussian_free.png", gaussian_free_figure(cases)),
            ("fig02_lens_waist.png", lens_waist_figure(cases)),
            ("fig03_aperture_convergence.png", convergence),
        ]
        for name, figure in figures:
            path = OUTPUT_DIR / name
            figure.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white",
                           metadata={"Software": "Open Holographic Lab V0 numerical evidence"})
            plt.close(figure)
            print(f"{path.relative_to(ROOT).as_posix()} sha256={hashlib.sha256(path.read_bytes()).hexdigest()}")
    print(f"full validation evidence sha256={report_sha}")
    print("Shared intensity scales; no display normalization; phase-only mask I < 1e-6 max(I).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
