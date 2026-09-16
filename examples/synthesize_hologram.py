r"""Synthesize an ideal periodic phase-only hologram from a strict grayscale PNG.

Run with the existing project interpreter, including directly from VS Code::

    .\.venv\Scripts\python.exe -B examples\synthesize_hologram.py
    .\.venv\Scripts\python.exe -B examples\synthesize_hologram.py --no-show
    .\.venv\Scripts\python.exe -B examples\synthesize_hologram.py --input target.png --ny 64 --nx 64

The default is a deterministic 64x64 synthetic PNG in a temporary directory.
The example configures uniform illumination separately for each target.
Images are never resized. No phase image or hardware drive file is exported.
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from ohlab import ComplexField, SamplingGrid
from ohlab.algorithms import gerchberg_saxton
from ohlab.io.images import load_target_intensity
from ohlab.propagation import propagate_angular_spectrum
from ohlab.targets import intensity_to_amplitude


def main(argv: Sequence[str] | None = None) -> int:
    """Run PNG-to-GS synthesis; pitch, wavelength and distance inputs use metres."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="local static 8-bit grayscale PNG")
    parser.add_argument("--ny", type=int, help="exact expected row count")
    parser.add_argument("--nx", type=int, help="exact expected column count")
    parser.add_argument("--dy-m", type=float, default=8e-6, help="row pitch in metres")
    parser.add_argument("--dx-m", type=float, default=8e-6, help="column pitch in metres")
    parser.add_argument("--wavelength-m", type=float, default=633e-9)
    parser.add_argument("--distance-m", type=float, default=5e-3)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-show", action="store_true", help="verify and render headlessly")
    args = parser.parse_args(argv)
    if args.input is not None and (args.ny is None or args.nx is None):
        parser.error("--input requires explicit --ny and --nx; targets are never resized")
    grid = SamplingGrid(
        ny=64 if args.ny is None else args.ny, nx=64 if args.nx is None else args.nx,
        dy=args.dy_m, dx=args.dx_m,
    )
    if args.input is None:
        from PIL import Image

        x, y = grid.meshgrid()
        design = np.exp(-0.5 * ((x / 60e-6)**2 + (y / 60e-6)**2))
        codes = np.rint(255.0 * design).astype(np.uint8)
        with TemporaryDirectory(prefix="ohlab-m3-demo-") as directory:
            path = Path(directory) / "smooth_spot.png"
            with Image.fromarray(codes) as image:
                image.save(path, format="PNG")
            intensity = load_target_intensity(path, grid=grid)
        description = "deterministic synthetic 8-bit grayscale PNG (smooth spot)"
    else:
        intensity = load_target_intensity(args.input, grid=grid)
        description = str(args.input.resolve())
    target = intensity_to_amplitude(intensity, grid=grid)
    # Explicit illumination choice by the example, outside the solver.
    configured_amplitude = float(np.sqrt(np.sum(target**2) / (grid.nx * grid.ny)))
    source = np.full(grid.shape, configured_amplitude, dtype=np.float64)
    source_power = float(np.sum(source**2) * grid.pixel_area)
    target_power = float(np.sum(target**2) * grid.pixel_area)
    print(f"input: {description}")
    print(f"grid: shape={grid.shape}, dx={grid.dx:g} m, dy={grid.dy:g} m")
    print(f"wavelength={args.wavelength_m:g} m, distance={args.distance_m:g} m")
    print(f"seed={args.seed}, iterations={args.iterations}, full-grid periodic ASM")
    print(f"configured uniform source amplitude: {configured_amplitude:.17e} a.u.")
    print(f"source power: {source_power:.17e} a.u. m^2")
    print(f"target power: {target_power:.17e} a.u. m^2")
    print("Illumination is configured separately for this target; target values are unchanged.")
    result = gerchberg_saxton(
        target_amplitude=target, source_amplitude=source, grid=grid,
        wavelength_m=args.wavelength_m, distance_m=args.distance_m,
        iterations=args.iterations, seed=args.seed,
    )
    rebuilt = ComplexField.from_amplitude_phase(
        amplitude=source, phase=result.phase, grid=grid, wavelength_m=args.wavelength_m,
    )
    independently_propagated = propagate_angular_spectrum(
        rebuilt, distance_m=args.distance_m, pad_factor=1,
    )
    np.testing.assert_allclose(
        result.reconstruction.data, independently_propagated.data, rtol=1e-12, atol=1e-14,
    )
    independent_residual = float(
        np.sum((independently_propagated.amplitude - target)**2) / np.sum(target**2)
    )
    np.testing.assert_allclose(
        result.residual_history[-1], independent_residual, rtol=1e-12, atol=1e-14,
    )
    reconstruction = result.reconstruction.intensity
    display_maximum = float(max(intensity.max(), reconstruction.max()))
    print(f"initial normalized squared amplitude residual: {result.residual_history[0]:.17e}")
    print(f"final normalized squared amplitude residual: {result.residual_history[-1]:.17e}")
    print(f"independently recomputed final residual: {independent_residual:.17e}")
    print(f"actual reconstruction intensity range: [{reconstruction.min():.17e}, {reconstruction.max():.17e}]")
    print(f"shared target/reconstruction display range: [0, {display_maximum:.17e}]")
    print("verification: returned phase -> public ASM -> reconstruction/residual passed (rtol=1e-12, atol=1e-14)")
    print("Phase is an ideal numerical visualization, not a calibrated SLM drive image.")
    print("Raw residual is not percent accuracy; arbitrary targets need not be exactly achievable.")

    import matplotlib

    if args.no_show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 2, figsize=(11.5, 9.0), layout="constrained")
    for axis, data, title in (
        (axes[0, 0], intensity, "Target intensity: decoded code / 255"),
        (axes[1, 0], reconstruction, "Actual forward reconstruction intensity"),
    ):
        artist = axis.imshow(
            data, cmap="gray", vmin=0.0, vmax=display_maximum,
            origin="upper", interpolation="nearest",
        )
        axis.set(title=title, xlabel="column j (+x)", ylabel="row i (+y downward)")
        figure.colorbar(artist, ax=axis, label="intensity [a.u.], shared scale")
    phase_artist = axes[0, 1].imshow(
        result.phase, cmap="twilight", vmin=-np.pi, vmax=np.pi,
        origin="upper", interpolation="nearest",
    )
    axes[0, 1].set(
        title="Ideal numerical source phase (not SLM calibrated)",
        xlabel="column j (+x)", ylabel="row i (+y downward)",
    )
    figure.colorbar(phase_artist, ax=axes[0, 1], label="phase [rad]")
    axes[1, 1].plot(np.arange(result.residual_history.size), result.residual_history)
    axes[1, 1].set(
        title="Raw normalized squared amplitude residual",
        xlabel="complete projection cycles k", ylabel="rho(k), full grid",
        xlim=(0, max(1, args.iterations)), ylim=(0, None),
    )
    axes[1, 1].grid(alpha=0.25)
    figure.suptitle(
        f"Single-plane periodic ASM Gerchberg–Saxton | seed {args.seed} | {args.iterations} cycles\n"
        f"Shared intensity limits [0, {display_maximum:.6g}]; configured uniform amplitude {configured_amplitude:.6g}",
        fontsize=13,
    )
    if args.no_show:
        figure.canvas.draw()
    else:
        plt.show()
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
