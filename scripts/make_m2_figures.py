r"""Regenerate the three synthetic Milestone 2 handoff figures.

Every raster passes through the public strict PNG loader and the pure target
APIs. Synthetic input PNGs live only in temporary directories. Plots have fixed
scales, and preserve array orientation; they are illustrations of contracts,
not evidence of arbitrary optical accuracy. This module remains outside the
numerical core and never constructs or propagates a complex field.

Usage::

    .\.venv\Scripts\python.exe -B scripts\make_m2_figures.py
"""

from __future__ import annotations

import math
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from ohlab import SamplingGrid  # noqa: E402
from ohlab.io.images import load_target_intensity  # noqa: E402
from ohlab.targets import grayscale8_to_intensity, intensity_to_amplitude  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "handoffs" / "milestone_2" / "figures"
DPI = 150
RTOL = 1e-14
ATOL = 1e-15
ACCENT = "#b42318"


def _prepare(codes: np.ndarray) -> tuple[SamplingGrid, np.ndarray, np.ndarray, float]:
    """Decode synthetic uint8 codes; return metre-based grid and real targets."""
    grid = SamplingGrid(ny=codes.shape[0], nx=codes.shape[1], dy=5e-6, dx=3.74e-6)
    with TemporaryDirectory(prefix="ohlab-m2-figure-") as directory:
        path = Path(directory) / "target.png"
        with Image.fromarray(codes) as image:
            image.save(path, format="PNG")
        intensity = load_target_intensity(path, grid=grid)
    array_intensity = grayscale8_to_intensity(codes, grid=grid)
    # EXACTNESS IS THE PROPERTY UNDER TEST: lossless PNG and the array route
    # supply the same uint8 code values to the same fixed-scaling contract.
    np.testing.assert_array_equal(intensity, array_intensity)
    amplitude = intensity_to_amplitude(intensity, grid=grid)
    np.testing.assert_allclose(amplitude**2, intensity, rtol=RTOL, atol=ATOL)
    residual = float(np.max(np.abs(amplitude**2 - intensity)))
    return grid, intensity, amplitude, residual


def _save(figure: plt.Figure, filename: str) -> None:
    """Write one fixed-name PNG; metadata contains no timestamp."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    figure.savefig(
        path, dpi=DPI, facecolor="white",
        metadata={"Software": "Open Holographic Lab - Milestone 2"},
    )
    plt.close(figure)
    print(f"wrote {path.relative_to(ROOT).as_posix()}")


def _code_steps(shape: tuple[int, int] = (5, 8)) -> np.ndarray:
    """Generate a rectangular raster with fixed code values, without randomness."""
    rows, columns = np.indices(shape)
    levels = np.array([0, 32, 64, 128, 192, 224, 255], dtype=np.uint8)
    return levels[(columns + 2 * rows) % levels.size]


def fig01_code_intensity_amplitude() -> float:
    """Show fixed code scaling and its square-root amplitude; return residual."""
    codes = _code_steps()
    _, intensity, amplitude, residual = _prepare(codes)
    _, curve_intensity, curve_amplitude, curve_residual = _prepare(
        np.arange(256, dtype=np.uint8).reshape(1, 256)
    )
    figure = plt.figure(figsize=(14.4, 7.7), layout="constrained")
    layout = figure.add_gridspec(2, 3, height_ratios=(3.0, 1.5))
    for index, (data, upper, title) in enumerate(
        (
            (codes, 255.0, "8-bit grayscale code g"),
            (intensity, 1.0, r"Target intensity $I = g/255$"),
            (amplitude, 1.0, r"Target amplitude $A = \sqrt{I}$"),
        )
    ):
        axis = figure.add_subplot(layout[0, index])
        artist = axis.imshow(
            data, cmap="gray", vmin=0.0, vmax=upper,
            origin="upper", interpolation="nearest",
        )
        for (row, col), value in np.ndenumerate(data):
            label = str(int(value)) if index == 0 else f"{value:.2f}"
            axis.text(
                col, row, label, ha="center", va="center", fontsize=8.5,
                color="white" if float(value) / upper < 0.45 else "black",
            )
        axis.set_title(title, fontsize=12, pad=12)
        axis.set_xlabel("column j (+x)")
        axis.set_ylabel("row i (+y downward)")
        axis.set_xticks(range(codes.shape[1]))
        axis.set_yticks(range(codes.shape[0]))
        figure.colorbar(artist, ax=axis, orientation="horizontal", pad=0.09, fraction=0.055)

    curve = figure.add_subplot(layout[1, :2])
    curve.plot(range(256), curve_intensity[0], label="intensity: g / 255", color="#1f77b4")
    curve.plot(range(256), curve_amplitude[0], label="amplitude: sqrt(g / 255)", color="#c56b08")
    curve.set(xlim=(0, 255), ylim=(0, 1), xlabel="grayscale code g", ylabel="normalized value")
    curve.grid(alpha=0.2)
    curve.legend(loc="lower right", fontsize=10)
    note = figure.add_subplot(layout[1, 2])
    note.axis("off")
    note.text(
        0.02, 0.92,
        "Mid-gray is an intensity constraint\n\n"
        f"g = 128\nI = {curve_intensity[0, 128]:.6f}\n"
        f"A = {curve_amplitude[0, 128]:.6f}\n"
        f"A squared = {curve_amplitude[0, 128] ** 2:.6f}\n\n"
        "Target phase remains unspecified.",
        va="top", fontsize=11, linespacing=1.35,
    )
    figure.suptitle(
        "Grayscale code → target intensity → target amplitude\n"
        "Fixed scaling; normalized design values, not calibrated radiometry",
        fontsize=16,
    )
    _save(figure, "fig01_code_intensity_amplitude.png")
    return max(residual, curve_residual)


def fig02_rectangular_orientation() -> float:
    """Show physical coordinates and corner identities on both mixed parities."""
    figure, axes = plt.subplots(1, 2, figsize=(13.0, 6.9), layout="constrained")
    maximum_residual = 0.0
    for axis, shape in zip(axes, ((5, 8), (6, 7)), strict=True):
        codes = np.zeros(shape, dtype=np.uint8)
        codes[0, 0], codes[0, -1] = 32, 96
        codes[-1, 0], codes[-1, -1] = 160, 224
        codes[1, 2] = 64
        codes[shape[0] // 2, shape[1] // 2] = 255
        grid, intensity, _, residual = _prepare(codes)
        maximum_residual = max(maximum_residual, residual)
        x, y = grid.x * 1e6, grid.y * 1e6
        dx, dy = grid.dx * 1e6, grid.dy * 1e6
        artist = axis.imshow(
            intensity, cmap="gray", vmin=0.0, vmax=1.0,
            origin="upper", interpolation="nearest",
            extent=(x[0] - dx / 2, x[-1] + dx / 2, y[-1] + dy / 2, y[0] - dy / 2),
        )
        for row, col in zip(*np.nonzero(codes), strict=True):
            value = int(codes[row, col])
            axis.text(
                x[col], y[row], str(value), ha="center", va="center", fontsize=12,
                color="white" if value < 115 else "black",
            )
        axis.plot(0.0, 0.0, "o", markersize=28, markerfacecolor="none", markeredgecolor=ACCENT, markeredgewidth=2)
        axis.set_xticks(x)
        axis.set_xticklabels([f"{value:.2f}" for value in x], rotation=35, ha="right")
        axis.set_yticks(y)
        axis.set_xticks(np.r_[x - dx / 2, x[-1] + dx / 2], minor=True)
        axis.set_yticks(np.r_[y - dy / 2, y[-1] + dy / 2], minor=True)
        axis.grid(which="minor", color="#888888", alpha=0.5, linewidth=0.7)
        axis.tick_params(which="minor", length=0)
        axis.set_xlabel("x [µm] = (column j − nx//2) × dx")
        axis.set_ylabel("y [µm] = (row i − ny//2) × dy; +y downward")
        axis.set_title(
            f"shape = {shape}; origin index [{shape[0] // 2}, {shape[1] // 2}]\n"
            f"dx = {dx:g} µm; dy = {dy:g} µm", fontsize=12, pad=16,
        )
    figure.colorbar(artist, ax=axes, shrink=0.72, label="target intensity (fixed [0, 1])")
    figure.suptitle(
        "Rectangular targets preserve orientation and the caller's grid\n"
        "Labels are original code values; the red ring marks x = y = 0\n"
        "Image pixel [i, j] → target [i, j] → (x[j], y[i])",
        fontsize=15,
    )
    _save(figure, "fig02_rectangular_orientation.png")
    return maximum_residual


def fig03_cross_image_brightness() -> float:
    """Compare two images on identical scales and verify their fixed brightness ratio."""
    levels = np.array([0, 8, 16, 32, 48, 64, 32, 16], dtype=np.uint8)
    rows, columns = np.indices((5, 8))
    first = levels[(columns + rows) % levels.size]
    second = (first.astype(np.uint16) * 2).astype(np.uint8)
    _, intensity_1, amplitude_1, residual_1 = _prepare(first)
    _, intensity_2, amplitude_2, residual_2 = _prepare(second)
    np.testing.assert_allclose(intensity_2, 2 * intensity_1, rtol=RTOL, atol=ATOL)
    np.testing.assert_allclose(amplitude_2, math.sqrt(2) * amplitude_1, rtol=RTOL, atol=ATOL)

    figure, axes = plt.subplots(2, 2, figsize=(11.2, 8.5), layout="constrained")
    for row, pair in enumerate(((intensity_1, intensity_2), (amplitude_1, amplitude_2))):
        for column, data in enumerate(pair):
            axis = axes[row, column]
            quantity = "Intensity" if row == 0 else "Amplitude"
            artist = axis.imshow(
                data, cmap="gray", vmin=0.0, vmax=1.0,
                origin="upper", interpolation="nearest",
            )
            axis.set_title(
                f"Image {column + 1}: max code = {(64, 128)[column]}\n"
                f"{quantity} maximum = {data.max():.6f}", fontsize=12,
            )
            axis.set_xlabel("column j (+x)")
            axis.set_ylabel("row i (+y downward)")
        figure.colorbar(artist, ax=axes[row, :], shrink=0.8, label=f"{quantity.lower()} (fixed [0, 1])")
    figure.suptitle(
        "Fixed /255 scaling preserves brightness across images\n"
        "At corresponding nonzero pixels: intensity ratio = 2; amplitude ratio = √2\n"
        "Every panel uses the same [0, 1] display limits",
        fontsize=14,
    )
    _save(figure, "fig03_cross_image_brightness.png")
    return max(residual_1, residual_2)


def main() -> None:
    """Regenerate the three figures from deterministic PNGs and report checks."""
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10}):
        residuals = [
            fig01_code_intensity_amplitude(),
            fig02_rectangular_orientation(),
            fig03_cross_image_brightness(),
        ]
    print("verified: lossless PNG/array agreement and amplitude-squared relation")
    print("verified: fixed cross-image intensity ratio 2 and amplitude ratio sqrt(2)")
    print(f"maximum amplitude-squared residual: {max(residuals):.17e}")
    print(f"relation tolerances: rtol={RTOL:g}, atol={ATOL:g}")


if __name__ == "__main__":
    main()
