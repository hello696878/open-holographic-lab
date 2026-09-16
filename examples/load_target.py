r"""Load a strict grayscale target and display its intensity and amplitude.

Run this file with the project's existing interpreter from PowerShell or
VS Code. The default input is a deterministic PNG created in a temporary
directory; no input or output image is left in the repository. For a user
image, give its path and the expected grid dimensions explicitly::

    .\.venv\Scripts\python.exe -B examples\load_target.py
    .\.venv\Scripts\python.exe -B examples\load_target.py --no-show
    .\.venv\Scripts\python.exe -B examples\load_target.py --input target.png --ny 480 --nx 640

Pixel pitches are in metres and retain their declared physical meaning.
This example prepares real target arrays; their phase remains unspecified.
Plotting, temporary-file creation, and image encoding stay outside the core.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from ohlab import SamplingGrid
from ohlab.io.images import load_target_intensity
from ohlab.targets import intensity_to_amplitude

# A square root followed by a square has float64 roundoff on the [0, 1]
# scale. The all-256-code sweep in M2 records the measured error. Both
# tolerances are explicit, and black pixels are also checked exactly below.
RELATION_RTOL = 1e-14
RELATION_ATOL = 1e-15


def _synthetic_codes(grid: SamplingGrid) -> np.ndarray:
    """Return deterministic uint8 code steps with distinct row/column variation."""
    rows, columns = np.indices(grid.shape)
    levels = np.array([0, 32, 64, 128, 192, 224, 255], dtype=np.uint8)
    return levels[(columns + 2 * rows) % levels.size]


def main(argv: Sequence[str] | None = None) -> int:
    """Show normalized target arrays; optional grid pitches are in metres."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="local strict grayscale PNG")
    parser.add_argument("--ny", type=int, help="expected number of image rows")
    parser.add_argument("--nx", type=int, help="expected number of image columns")
    parser.add_argument("--dy-m", type=float, default=5e-6, help="row pitch in metres")
    parser.add_argument("--dx-m", type=float, default=3.74e-6, help="column pitch in metres")
    parser.add_argument("--no-show", action="store_true", help="verify and render headlessly")
    args = parser.parse_args(argv)
    if args.input is not None and (args.ny is None or args.nx is None):
        parser.error("--input requires explicit --ny and --nx; images are never resized")

    grid = SamplingGrid(
        ny=5 if args.ny is None else args.ny,
        nx=8 if args.nx is None else args.nx,
        dy=args.dy_m,
        dx=args.dx_m,
    )
    if args.input is None:
        from PIL import Image

        with TemporaryDirectory(prefix="ohlab-m2-demo-") as directory:
            path = Path(directory) / "synthetic_target.png"
            with Image.fromarray(_synthetic_codes(grid)) as image:
                image.save(path, format="PNG")
            intensity = load_target_intensity(path, grid=grid)
        source = "deterministic synthetic 8-bit grayscale PNG"
    else:
        intensity = load_target_intensity(args.input, grid=grid)
        source = str(args.input.resolve())
    amplitude = intensity_to_amplitude(intensity, grid=grid)
    residual = float(np.max(np.abs(amplitude**2 - intensity)))
    np.testing.assert_allclose(
        amplitude**2, intensity, rtol=RELATION_RTOL, atol=RELATION_ATOL
    )
    # EXACTNESS IS THE PROPERTY UNDER TEST: sqrt(0) remains zero.
    assert np.all(amplitude[intensity == 0.0] == 0.0)

    print(f"source: {source}")
    print(f"grid: shape={grid.shape}, dx={grid.dx:g} m, dy={grid.dy:g} m")
    print(f"intensity: {intensity.dtype}, range=[{intensity.min():.17g}, {intensity.max():.17g}]")
    print(f"amplitude: {amplitude.dtype}, range=[{amplitude.min():.17g}, {amplitude.max():.17g}]")
    print(f"max |A_target**2 - I_target|: {residual:.17e}")
    print(f"relation check: passed (rtol={RELATION_RTOL:g}, atol={RELATION_ATOL:g})")
    print("Target phase remains unspecified; these outputs are intensity and amplitude.")

    import matplotlib

    if args.no_show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), layout="constrained")
    for axis, data, title in zip(
        axes,
        (intensity, amplitude),
        (r"Target intensity $I = g/255$", r"Target amplitude $A = \sqrt{I}$"),
        strict=True,
    ):
        artist = axis.imshow(
            data, cmap="gray", vmin=0.0, vmax=1.0,
            origin="upper", interpolation="nearest",
        )
        axis.set_title(title)
        axis.set_xlabel("column j (+x)")
        axis.set_ylabel("row i (+y downward)")
        figure.colorbar(artist, ax=axis, fraction=0.045, pad=0.035)
    figure.suptitle(
        f"Target preparation | shape={grid.shape} | fixed display scales [0, 1]\n"
        f"max absolute amplitude-squared residual = {residual:.3e}",
        fontsize=12,
    )
    if args.no_show:
        figure.canvas.draw()
    else:
        plt.show()
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
