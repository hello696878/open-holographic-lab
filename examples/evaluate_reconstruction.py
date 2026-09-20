r"""Evaluate one unchanged M3 reconstruction with explicit intensity metrics.

Run with the existing project interpreter from PowerShell or VS Code::

    .\.venv\Scripts\python.exe -B examples\evaluate_reconstruction.py
    .\.venv\Scripts\python.exe -B examples\evaluate_reconstruction.py --no-show

The fixed 64x64 target, seed and signal mask are declared before synthesis.
The separate flat-region examples demonstrate CV where flat brightness is
intended. This example prints measurements and displays figures; it exports
no simulation artifacts and does not alter the GS solver or its history.
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence
import math
from typing import TYPE_CHECKING

import numpy as np

from ohlab import ComplexField, SamplingGrid
from ohlab.algorithms import GerchbergSaxtonResult, gerchberg_saxton
from ohlab.metrics import (
    intensity_mse, intensity_nmse, intensity_psnr,
    regional_intensity_cv, signal_region_power_fraction,
)
from ohlab.propagation import propagate_angular_spectrum
from ohlab.targets import grayscale8_to_intensity, intensity_to_amplitude

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

DATA_RANGE = 1.0
WAVELENGTH_M = 633e-9
DISTANCE_M = 5e-3
SEED = 0
ITERATIONS = 50
IntensityRow = tuple[float, float, float, float]
RegionRow = tuple[float, float]


def build_m3_case() -> tuple[
    SamplingGrid, np.ndarray, np.ndarray, np.ndarray, GerchbergSaxtonResult,
]:
    """Return grid, target intensity, source amplitude, fixed ROI, and M3 result.

    Pitches/wavelength/distance are metres; intensity and amplitude retain the
    existing arbitrary-unit convention. The ROI is an integer-index disk of
    radius 15 pixels (120 micrometres), fixed independently of output values.
    """
    grid = SamplingGrid(ny=64, nx=64, dy=8e-6, dx=8e-6)
    rows, columns = np.indices(grid.shape)
    signal_mask = (rows - 32)**2 + (columns - 32)**2 <= 15**2
    x, y = grid.meshgrid()
    design = np.exp(-0.5 * ((x / 60e-6)**2 + (y / 60e-6)**2))
    codes = np.rint(255.0 * design).astype(np.uint8)
    target = grayscale8_to_intensity(codes, grid=grid)
    target_amplitude = intensity_to_amplitude(target, grid=grid)
    source = np.full(
        grid.shape, np.sqrt(np.sum(target_amplitude**2) / target.size), dtype=np.float64,
    )
    result = gerchberg_saxton(
        target_amplitude=target_amplitude, source_amplitude=source, grid=grid,
        wavelength_m=WAVELENGTH_M, distance_m=DISTANCE_M,
        iterations=ITERATIONS, seed=SEED,
    )
    rebuilt = ComplexField.from_amplitude_phase(
        amplitude=source, phase=result.phase, grid=grid, wavelength_m=WAVELENGTH_M,
    )
    independent = propagate_angular_spectrum(rebuilt, distance_m=DISTANCE_M, pad_factor=1)
    np.testing.assert_allclose(
        result.reconstruction.data, independent.data, rtol=1e-12, atol=1e-14,
    )
    return grid, target, source, signal_mask, result


def build_flat_cases() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Return the fixed 4x6 Boolean ROI and three intended-flat intensity fixtures."""
    mask = np.zeros((4, 6), dtype=bool)
    mask[1:3, 1:5] = True
    uniform = mask.astype(np.float64)
    nonuniform = np.zeros((4, 6), dtype=np.float64)
    nonuniform[1:3, 1:5] = [[0.5, 1.5, 0.5, 1.5], [1.5, 0.5, 1.5, 0.5]]
    leakage = np.where(mask, 1.0, 0.25)
    return mask, {
        "uniform_region": uniform,
        "varying_region": nonuniform,
        "uniform_with_leakage": leakage,
    }


def measure_intensity_cases(
    target: np.ndarray, cases: dict[str, np.ndarray], signal_mask: np.ndarray,
) -> dict[str, IntensityRow]:
    """Measure the four displayed intensity/power columns with the public M4 API."""
    return {
        name: (
            intensity_mse(target_intensity=target, reconstruction_intensity=candidate),
            intensity_nmse(target_intensity=target, reconstruction_intensity=candidate),
            intensity_psnr(
                target_intensity=target, reconstruction_intensity=candidate, data_range=DATA_RANGE,
            ),
            signal_region_power_fraction(reconstruction_intensity=candidate, signal_mask=signal_mask),
        )
        for name, candidate in cases.items()
    }


def measure_flat_cases(
    cases: dict[str, np.ndarray], mask: np.ndarray,
) -> dict[str, RegionRow]:
    """Measure population CV and regional power fraction for the flat fixtures."""
    return {
        name: (
            regional_intensity_cv(intensity=candidate, mask=mask),
            signal_region_power_fraction(reconstruction_intensity=candidate, signal_mask=mask),
        )
        for name, candidate in cases.items()
    }


def _number(value: float, *, compact: bool = False) -> str:
    if math.isinf(value) and value > 0.0:
        return "+inf"
    return format(value, ".6g" if compact else ".17e")


def _overlay(axis: Axes, mask: np.ndarray) -> None:
    """Draw the predeclared pixel-mask boundary without deriving another ROI."""
    axis.contour(mask.astype(np.float64), levels=[0.5], colors=["#22c55e"], linewidths=1.3)


def comparison_figure(
    target: np.ndarray, cases: dict[str, np.ndarray], signal_mask: np.ndarray,
    measured: dict[str, IntensityRow], amplitude_residual: float,
) -> Figure:
    """Plot common intensity/error scales and the separately labelled M3 residual."""
    import matplotlib.pyplot as plt

    maximum = max(float(values.max()) for values in cases.values())
    error_limit = max(float(np.max(np.abs(values-target))) for values in cases.values())
    figure = plt.figure(figsize=(14.2, 10.3), layout="constrained")
    layout = figure.add_gridspec(3, 3, height_ratios=(1.0, 1.0, 0.30))
    image_axes, error_axes = [], []
    titles = ("Exact target", "Twice the target", "Actual M3 reconstruction")
    for column, ((name, candidate), title) in enumerate(zip(cases.items(), titles, strict=True)):
        axis = figure.add_subplot(layout[0, column])
        image_axes.append(axis)
        image = axis.imshow(
            candidate, origin="upper", interpolation="nearest", cmap="gray",
            vmin=0.0, vmax=maximum,
        )
        _overlay(axis, signal_mask)
        axis.set(title=title, xlabel="column j (+x)", ylabel="row i (+y downward)")
        axis = figure.add_subplot(layout[1, column])
        error_axes.append(axis)
        error = axis.imshow(
            candidate-target, origin="upper", interpolation="nearest",
            cmap="RdBu_r", vmin=-error_limit, vmax=error_limit,
        )
        _overlay(axis, signal_mask)
        axis.set(title="Signed intensity error: R − T", xlabel="column j (+x)", ylabel="row i (+y downward)")
        text_axis = figure.add_subplot(layout[2, column])
        text_axis.axis("off")
        mse, nmse, psnr, fraction = measured[name]
        text_axis.text(
            0.04, 0.98,
            f"MSE_I = {_number(mse, compact=True)} a.u.²\n"
            f"NMSE_I = {_number(nmse, compact=True)}\n"
            f"PSNR_I = {_number(psnr, compact=True)} dB (data_range = 1)\n"
            f"Signal-region power fraction = {fraction:.6f}",
            transform=text_axis.transAxes, va="top", fontsize=10.5, linespacing=1.4,
        )
    figure.colorbar(image, ax=image_axes, shrink=0.87, label="intensity [a.u.], shared")
    figure.colorbar(error, ax=error_axes, shrink=0.87, label="intensity error [a.u.], shared")
    figure.suptitle(
        "Intensity comparisons on one declared scale\n"
        f"64 × 64 | λ = 633 nm | dx = dy = 8 µm | z = 5 mm | seed 0 | 50 GS cycles\n"
        f"Green ROI: (i−32)² + (j−32)² ≤ 225; {int(signal_mask.sum())} pixels | "
        f"Display [0, {maximum:g}]; PSNR data_range = 1\n"
        f"Separate M3 squared amplitude residual = {amplitude_residual:.8f}; "
        "the exact-target ROI fraction is below 1 because the disk excludes target tails",
        fontsize=12,
    )
    return figure


def region_figure(
    cases: dict[str, np.ndarray], mask: np.ndarray, measured: dict[str, RegionRow],
) -> Figure:
    """Show why variation inside an intended-flat ROI and leakage are distinct."""
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 3, figsize=(13.2, 5.0), layout="constrained")
    titles = ("Uniform selected region", "Deliberately varying selected region", "Uniform region with outside leakage")
    for axis, (name, candidate), title in zip(axes, cases.items(), titles, strict=True):
        artist = axis.imshow(
            candidate, cmap="gray", origin="upper", interpolation="nearest",
            vmin=0.0, vmax=1.5,
        )
        _overlay(axis, mask)
        for (row, column), value in np.ndenumerate(candidate):
            axis.text(
                column, row, f"{value:g}", ha="center", va="center", fontsize=10,
                color="white" if value < 0.7 else "black",
            )
        cv, fraction = measured[name]
        axis.set(
            title=f"{title}\nCV = {cv:.6f}; power fraction = {fraction:.6f}",
            xlabel="column j", ylabel="row i",
        )
        axis.set_xticks(np.arange(6))
        axis.set_yticks(np.arange(4))
    figure.colorbar(artist, ax=axes, shrink=0.78, label="intensity [a.u.], shared [0, 1.5]")
    figure.suptitle(
        "Two diagnostics on predefined flat-region fixtures (not GS outputs)\n"
        "Green ROI: rows[1:3], columns[1:5] (8 pixels); CV uses population std, ddof = 0\n"
        "Changing only the outside intensity leaves CV unchanged and reduces the power fraction",
        fontsize=12,
    )
    return figure


def main(argv: Sequence[str] | None = None) -> int:
    """Print public metric values and render the two fixed evaluation figures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-show", action="store_true", help="verify and render headlessly")
    args = parser.parse_args(argv)
    grid, target, source, mask, result = build_m3_case()
    cases = {
        "exact_target": target,
        "twice_target": 2.0 * target,
        "actual_GS": result.reconstruction.intensity,
    }
    flat_mask, flat_cases = build_flat_cases()
    arrays = (
        target, source, mask, result.source_field.data, result.reconstruction.data,
        result.residual_history, *cases.values(), flat_mask, *flat_cases.values(),
    )
    before = [array.tobytes(order="C") for array in arrays]
    measured = measure_intensity_cases(target, cases, mask)
    flat_measured = measure_flat_cases(flat_cases, flat_mask)
    # EXACTNESS IS THE PROPERTY UNDER TEST: evaluating metrics must not mutate bytes.
    assert before == [array.tobytes(order="C") for array in arrays]

    print("M4 evaluation: actual shipped metric functions; fixed quantized smooth-spot target")
    print(f"grid={grid.shape}, dx={grid.dx:g} m, dy={grid.dy:g} m, wavelength={WAVELENGTH_M:g} m, distance={DISTANCE_M:g} m")
    print(f"seed={SEED}, GS cycles={ITERATIONS}, configured uniform source amplitude={source[0, 0]:.17e}")
    print(f"signal ROI: (row-32)^2 + (column-32)^2 <= 225; selected pixels={int(mask.sum())}")
    print("PSNR data_range=1 explicitly; it is independent of the display limits.")
    print("case | MSE_I [a.u.^2] | NMSE_I | PSNR_I [dB] | signal_region_power_fraction")
    for name, values in measured.items():
        print(name + " | " + " | ".join(_number(value) for value in values))
    print(f"M3 normalized squared amplitude residual (separate quantity): {result.residual_history[-1]:.17e}")
    print(f"actual reconstruction intensity maximum: {cases['actual_GS'].max():.17e}")
    print(f"shared intensity display range: [0, {max(float(v.max()) for v in cases.values()):g}]")
    print(f"shared signed-error display range: +/-{max(float(np.max(np.abs(v-target))) for v in cases.values()):g}")
    print("Exact-target signal fraction is below one because the fixed disk excludes target tails.")
    print("Equal regional fractions do not establish correct brightness; power fractions use full-window total intensity.")
    print("CV is evaluated separately where flat brightness is intended; population std uses ddof=0.")
    print("flat ROI: shape=(4, 6), rows[1:3], columns[1:5], selected pixels=8")
    print("case | regional_intensity_cv | signal_region_power_fraction")
    for name, values in flat_measured.items():
        print(name + " | " + " | ".join(_number(value) for value in values))
    print("verification: public-ASM reconstruction agreement and metric input/result byte nonmutation passed")

    import matplotlib

    if args.no_show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures = (
        comparison_figure(target, cases, mask, measured, float(result.residual_history[-1])),
        region_figure(flat_cases, flat_mask, flat_measured),
    )
    if args.no_show:
        for figure in figures:
            figure.canvas.draw()
    else:
        plt.show()
    for figure in figures:
        plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
