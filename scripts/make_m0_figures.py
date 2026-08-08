"""Generate the Milestone 0 handoff figures.

**This file is outside the numerical core by design.** It is the only place in
the repository that imports matplotlib. ``src/ohlab/`` must never import a
plotting or image library -- that rule is enforced by
``tests/test_fft_conventions.py::test_c06_numerical_core_imports_no_ui_or_io_library``
and by the runtime dependency set in ``pyproject.toml``.

Every figure is generated *from* the implemented API, so the figures cannot
drift away from the code. They are illustrations for the tutoring session;
they are never evidence of correctness. Correctness lives in ``tests/``.

Usage
-----
    .\\.venv\\Scripts\\python.exe scripts\\make_m0_figures.py
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: no display required, deterministic output

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ohlab import ComplexField, SamplingGrid  # noqa: E402
from ohlab.units import NM, UM  # noqa: E402

OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "handoffs"
    / "milestone_0"
    / "figures"
)

WAVELENGTH_M = 633 * NM
DPI = 130

# A neutral, colour-vision-friendly palette. Phase uses a cyclic colormap
# ('twilight') because phase wraps: a non-cyclic map would draw a false seam
# at the +pi/-pi branch cut.
ACCENT = "#1f77b4"
ACCENT_2 = "#d62728"
NEUTRAL = "#555555"


def _save(fig: plt.Figure, name: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote {path.relative_to(OUTPUT_DIR.parents[3])}")


# ---------------------------------------------------------------------------
def fig01_complex_plane() -> None:
    """A complex number as a point; amplitude, phase, and Euler's formula."""
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(10.5, 4.6))

    # --- left: one complex number -------------------------------------
    a, b = 3.0, 2.0
    modulus = math.hypot(a, b)
    argument = math.atan2(b, a)

    ax_left.axhline(0, color=NEUTRAL, lw=0.8)
    ax_left.axvline(0, color=NEUTRAL, lw=0.8)
    ax_left.annotate(
        "", xy=(a, b), xytext=(0, 0),
        arrowprops={"arrowstyle": "->", "color": ACCENT, "lw": 2.2},
    )
    ax_left.plot([a, a], [0, b], ls=":", color=NEUTRAL, lw=1.2)
    ax_left.plot([0, a], [b, b], ls=":", color=NEUTRAL, lw=1.2)
    ax_left.plot(a, b, "o", color=ACCENT, ms=8)

    arc = np.linspace(0, argument, 60)
    ax_left.plot(0.9 * np.cos(arc), 0.9 * np.sin(arc), color=ACCENT_2, lw=1.6)
    ax_left.text(1.15, 0.42, r"$\varphi$", color=ACCENT_2, fontsize=14)
    ax_left.text(
        1.35, 1.45, rf"$|U| = {modulus:.3f}$", color=ACCENT, fontsize=12,
        rotation=math.degrees(argument),
    )
    ax_left.text(a + 0.12, b, r"$U = a + ib$", fontsize=12, va="center")
    ax_left.text(a / 2, -0.35, r"$a = |U|\cos\varphi$", ha="center", fontsize=11)
    ax_left.text(-0.25, b, r"$b = |U|\sin\varphi$", ha="right", va="center",
                 fontsize=11)

    ax_left.set_xlim(-1.2, 5.0)
    ax_left.set_ylim(-1.0, 3.2)
    ax_left.set_aspect("equal")
    ax_left.set_xlabel("real part")
    ax_left.set_ylabel("imaginary part")
    ax_left.set_title(
        "A complex number carries TWO numbers:\n"
        "amplitude $|U|$ and phase $\\varphi$", fontsize=11
    )

    # --- right: the unit circle, exp(i theta) --------------------------
    theta = np.linspace(0, 2 * np.pi, 400)
    ax_right.plot(np.cos(theta), np.sin(theta), color=NEUTRAL, lw=1.2)
    ax_right.axhline(0, color=NEUTRAL, lw=0.8)
    ax_right.axvline(0, color=NEUTRAL, lw=0.8)

    marks = [0, np.pi / 4, np.pi / 2, np.pi, 3 * np.pi / 2]
    labels = ["0", r"$\pi/4$", r"$\pi/2$", r"$\pi$", r"$3\pi/2$"]
    for angle, label in zip(marks, labels):
        ax_right.plot(np.cos(angle), np.sin(angle), "o", color=ACCENT, ms=7)
        ax_right.annotate(
            label,
            xy=(np.cos(angle), np.sin(angle)),
            xytext=(1.28 * np.cos(angle), 1.28 * np.sin(angle)),
            ha="center", va="center", fontsize=11, color=ACCENT,
        )
    ax_right.set_xlim(-1.6, 1.6)
    ax_right.set_ylim(-1.6, 1.6)
    ax_right.set_aspect("equal")
    ax_right.set_title(
        r"Euler: $e^{i\theta} = \cos\theta + i\sin\theta$" "\n"
        r"$|e^{i\theta}| = 1$ always, so a phase factor never changes brightness",
        fontsize=11,
    )
    ax_right.set_xlabel("real part")

    fig.suptitle("Figure 1 - Complex numbers and Euler's formula", fontsize=13)
    _save(fig, "fig01_complex_plane.png")


# ---------------------------------------------------------------------------
def fig02_amplitude_phase_intensity() -> None:
    """Two fields with identical amplitude but different phase, and their
    identical intensities. This is why holography is hard."""
    grid = SamplingGrid.square(n=192, pitch=4 * UM)
    x_grid, y_grid = grid.meshgrid()
    radius = np.hypot(x_grid, y_grid)

    amplitude = np.exp(-((radius / (grid.extent_x / 6.0)) ** 2))

    phase_a = 2.0 * np.pi * (x_grid / (grid.extent_x / 5.0))
    phase_b = 6.0 * np.arctan2(y_grid, x_grid)

    field_a = ComplexField.from_amplitude_phase(
        amplitude=amplitude, phase=phase_a, grid=grid, wavelength_m=WAVELENGTH_M
    )
    field_b = ComplexField.from_amplitude_phase(
        amplitude=amplitude, phase=phase_b, grid=grid, wavelength_m=WAVELENGTH_M
    )

    extent_mm = [
        1e3 * grid.x[0], 1e3 * grid.x[-1], 1e3 * grid.y[-1], 1e3 * grid.y[0]
    ]

    fig, axes = plt.subplots(2, 3, figsize=(12.0, 7.4))
    rows = (
        ("Field A", field_a),
        ("Field B", field_b),
    )
    for row_index, (label, field) in enumerate(rows):
        im0 = axes[row_index, 0].imshow(
            field.amplitude, origin="upper", extent=extent_mm, cmap="viridis"
        )
        axes[row_index, 0].set_title(f"{label}: amplitude $|U|$")
        fig.colorbar(im0, ax=axes[row_index, 0], fraction=0.046)

        im1 = axes[row_index, 1].imshow(
            field.phase, origin="upper", extent=extent_mm,
            cmap="twilight", vmin=-np.pi, vmax=np.pi,
        )
        axes[row_index, 1].set_title(f"{label}: phase $\\varphi$  (cyclic map)")
        cbar = fig.colorbar(im1, ax=axes[row_index, 1], fraction=0.046,
                            ticks=[-np.pi, 0, np.pi])
        cbar.ax.set_yticklabels([r"$-\pi$", "0", r"$+\pi$"])

        im2 = axes[row_index, 2].imshow(
            field.intensity, origin="upper", extent=extent_mm, cmap="inferno"
        )
        axes[row_index, 2].set_title(f"{label}: intensity $I=|U|^2$")
        fig.colorbar(im2, ax=axes[row_index, 2], fraction=0.046)

        for ax in axes[row_index]:
            ax.set_xlabel("x (mm)")
            ax.set_ylabel("y (mm)")

    max_difference = float(np.max(np.abs(field_a.intensity - field_b.intensity)))
    fig.suptitle(
        "Figure 2 - A camera measures intensity and destroys phase\n"
        f"The two rows have completely different phase but identical intensity "
        f"(max difference {max_difference:.2e}). "
        "Recovering a phase that makes the intensity we want IS the problem.",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    _save(fig, "fig02_amplitude_phase_intensity.png")


# ---------------------------------------------------------------------------
def fig03_spatial_grid() -> None:
    """Sample positions for even and odd n, with the origin at index n//2."""
    fig, axes = plt.subplots(2, 1, figsize=(10.0, 5.0), sharex=False)

    for ax, n in zip(axes, (8, 7)):
        grid = SamplingGrid.square(n=n, pitch=1.0)  # pitch 1 m: readable axis
        x = grid.x
        centre = n // 2

        ax.axhline(0, color=NEUTRAL, lw=1.0, zorder=1)
        ax.plot(x, np.zeros_like(x), "o", color=ACCENT, ms=11, zorder=3)
        ax.plot(x[centre], 0.0, "o", color=ACCENT_2, ms=13, zorder=4)

        for index, value in enumerate(x):
            ax.annotate(
                f"j={index}", xy=(value, 0), xytext=(value, 0.32),
                ha="center", fontsize=9, color=NEUTRAL,
            )
            ax.annotate(
                f"{value:+.0f}", xy=(value, 0), xytext=(value, -0.42),
                ha="center", fontsize=9,
                color=ACCENT_2 if index == centre else "black",
            )

        parity = "even" if n % 2 == 0 else "odd"
        span = f"[{x[0]:+.0f}, {x[-1]:+.0f}]"
        ax.set_title(
            f"n = {n} ({parity}):  x[j] = (j - n//2)*dx,   n//2 = {centre},   "
            f"x[{centre}] = 0 exactly,   span {span}",
            fontsize=11,
        )
        ax.set_ylim(-0.8, 0.8)
        ax.set_yticks([])
        ax.set_xlabel("x  (units of dx)")
        for spine in ("left", "right", "top"):
            ax.spines[spine].set_visible(False)

    fig.suptitle(
        "Figure 3 - Spatial grid centring.  Even n is asymmetric by one sample "
        "(one extra on the negative side);\nthat is accepted deliberately so "
        "index n//2 is the origin in every array, in both space and frequency.",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    _save(fig, "fig03_spatial_grid.png")


# ---------------------------------------------------------------------------
def fig04_array_axes() -> None:
    """Index-to-coordinate mapping, and the downward +y convention."""
    grid = SamplingGrid(ny=6, nx=10, dy=5 * UM, dx=3.74 * UM)
    values = np.zeros(grid.shape)
    values[:] = np.arange(grid.nx)[None, :] * 0.5 + np.arange(grid.ny)[:, None]

    fig, ax = plt.subplots(figsize=(10.2, 5.6))
    ax.imshow(values, origin="upper", cmap="Blues", alpha=0.45)

    for i in range(grid.ny):
        for j in range(grid.nx):
            ax.text(j, i, f"{i},{j}", ha="center", va="center", fontsize=8,
                    color=NEUTRAL)

    centre_i, centre_j = grid.ny // 2, grid.nx // 2
    ax.plot(centre_j, centre_i, "o", color=ACCENT_2, ms=16, mfc="none", mew=2.5)
    ax.annotate(
        f"origin: data[{centre_i},{centre_j}]  ->  x = 0, y = 0\n"
        f"(row ny//2 = {centre_i}, column nx//2 = {centre_j})",
        xy=(centre_j, centre_i), xytext=(centre_j - 0.4, grid.ny + 1.1),
        fontsize=10, color=ACCENT_2, ha="center",
        arrowprops={"arrowstyle": "->", "color": ACCENT_2},
    )

    ax.annotate(
        "", xy=(9.6, -0.75), xytext=(-0.5, -0.75),
        arrowprops={"arrowstyle": "->", "color": ACCENT, "lw": 2},
    )
    ax.text(4.5, -1.05, "column index j  ->  +x", ha="center", color=ACCENT,
            fontsize=11)
    ax.annotate(
        "", xy=(-1.1, 5.6), xytext=(-1.1, -0.4),
        arrowprops={"arrowstyle": "->", "color": ACCENT, "lw": 2},
    )
    ax.text(-1.45, 2.6, "row index i  ->  +y", rotation=90, va="center",
            ha="center", color=ACCENT, fontsize=11)

    ax.set_xticks(range(grid.nx))
    ax.set_yticks(range(grid.ny))
    ax.set_xlim(-2.0, grid.nx - 0.2)
    ax.set_ylim(grid.ny + 1.8, -1.6)
    ax.set_title(
        f"Figure 4 - Array layout.  shape = (ny, nx) = {grid.shape}  "
        "-- rows FIRST.\n"
        "data[i, j] is the field at (x[j], y[i]).  With origin='upper', "
        "+y points DOWN the screen.",
        fontsize=12,
    )
    _save(fig, "fig04_array_axes.png")


# ---------------------------------------------------------------------------
def fig05_fft_ordering() -> None:
    """FFT order versus centred order, for even and odd n."""
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 6.2))

    for column, n in enumerate((8, 7)):
        grid = SamplingGrid.square(n=n, pitch=1.0)
        indices = np.arange(n)

        ax_top = axes[0, column]
        ax_top.stem(indices, grid.fx_fft, basefmt=" ", linefmt=f"C0-",
                    markerfmt="C0o")
        ax_top.axhline(0, color=NEUTRAL, lw=0.8)
        ax_top.plot(0, grid.fx_fft[0], "o", color=ACCENT_2, ms=11)
        ax_top.set_title(
            f"n = {n}:  fx_fft  (= np.fft.fftfreq)\n"
            "zero frequency at index 0", fontsize=10
        )

        ax_bottom = axes[1, column]
        ax_bottom.stem(indices, grid.fx_centered, basefmt=" ", linefmt="C2-",
                       markerfmt="C2o")
        ax_bottom.axhline(0, color=NEUTRAL, lw=0.8)
        ax_bottom.plot(n // 2, grid.fx_centered[n // 2], "o", color=ACCENT_2,
                       ms=11)
        ax_bottom.set_title(
            f"n = {n}:  fx_centered  (= fftshift(fftfreq))\n"
            f"zero frequency at index n//2 = {n // 2}", fontsize=10
        )

        for ax in (ax_top, ax_bottom):
            ax.set_xlabel("array index")
            ax.set_ylabel("f  (cycles per unit)")
            ax.set_xticks(indices)

    fig.suptitle(
        "Figure 5 - The two frequency orderings.  Same numbers, different "
        "positions.\nMixing them is the most common failure mode in this kind "
        "of code, which is why the ordering is always in the name.",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "fig05_fft_ordering.png")


# ---------------------------------------------------------------------------
def fig06_nyquist_angle() -> None:
    """Maximum diffraction angle versus pixel pitch, from the implemented API."""
    pitches_um = np.linspace(0.5, 20.0, 300)
    fig, ax = plt.subplots(figsize=(8.6, 5.0))

    for wavelength_nm, colour in ((405, "#6a3d9a"), (532, "#33a02c"),
                                  (633, "#e31a1c")):
        angles_deg = []
        for pitch_um in pitches_um:
            grid = SamplingGrid.square(n=8, pitch=pitch_um * UM)
            try:
                angle = grid.max_diffraction_angle_rad(
                    wavelength_nm * NM, axis="x"
                )
            except ValueError:
                angles_deg.append(np.nan)  # sampling too coarse: no such angle
            else:
                angles_deg.append(math.degrees(angle))
        ax.plot(pitches_um, angles_deg, color=colour, lw=2,
                label=f"$\\lambda$ = {wavelength_nm} nm")

    slm_pitch = 3.74
    slm_grid = SamplingGrid.square(n=8, pitch=slm_pitch * UM)
    slm_angle = math.degrees(
        slm_grid.max_diffraction_angle_rad(633 * NM, axis="x")
    )
    ax.plot(slm_pitch, slm_angle, "o", color="black", ms=9, zorder=5)
    ax.annotate(
        f"typical SLM: {slm_pitch} um at 633 nm\n-> {slm_angle:.2f} deg",
        xy=(slm_pitch, slm_angle), xytext=(6.5, 25),
        arrowprops={"arrowstyle": "->", "color": "black"}, fontsize=10,
    )

    ax.set_xlabel("pixel pitch d  (um)")
    ax.set_ylabel("max diffraction angle  (degrees)")
    ax.set_ylim(0, 60)
    ax.grid(alpha=0.3)
    ax.legend()
    ax.set_title(
        "Figure 6 - $\\sin(\\theta_{max}) = \\lambda / (2d)$\n"
        "The narrow field of view of an SLM hologram follows directly from "
        "the pixel pitch.",
        fontsize=12,
    )
    _save(fig, "fig06_nyquist_angle.png")


# ---------------------------------------------------------------------------
def fig07_plane_wave_fft_bin() -> None:
    """An on-grid plane wave and its single, analytically predicted FFT bin."""
    grid = SamplingGrid(ny=48, nx=64, dy=5 * UM, dx=3.74 * UM)
    col = grid.nx // 2 + 9
    row = grid.ny // 2 + 5
    theta_x = math.asin(grid.fx_centered[col] * WAVELENGTH_M)
    theta_y = math.asin(grid.fy_centered[row] * WAVELENGTH_M)

    field = ComplexField.plane_wave(
        grid=grid,
        wavelength_m=WAVELENGTH_M,
        theta_x_rad=theta_x,
        theta_y_rad=theta_y,
    )
    magnitude = np.abs(np.fft.fftshift(np.fft.fft2(field.data)))
    peak_row, peak_col = (
        int(v) for v in np.unravel_index(int(np.argmax(magnitude)), magnitude.shape)
    )

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(11.6, 4.8))

    im0 = ax_left.imshow(
        field.phase, origin="upper", cmap="twilight", vmin=-np.pi, vmax=np.pi,
        extent=[1e3 * grid.x[0], 1e3 * grid.x[-1],
                1e3 * grid.y[-1], 1e3 * grid.y[0]],
    )
    ax_left.set_title(
        f"Plane wave phase\n"
        f"$\\theta_x$ = {math.degrees(theta_x):+.3f}$\\degree$, "
        f"$\\theta_y$ = {math.degrees(theta_y):+.3f}$\\degree$",
        fontsize=11,
    )
    ax_left.set_xlabel("x (mm)")
    ax_left.set_ylabel("y (mm)")
    cbar = fig.colorbar(im0, ax=ax_left, fraction=0.046,
                        ticks=[-np.pi, 0, np.pi])
    cbar.ax.set_yticklabels([r"$-\pi$", "0", r"$+\pi$"])

    ax_right.imshow(magnitude, origin="upper", cmap="magma")
    ax_right.plot(col, row, "o", color="cyan", ms=18, mfc="none", mew=2.0)
    ax_right.annotate(
        f"predicted bin\n(row={row}, col={col})",
        xy=(col, row), xytext=(col - 30, row - 14), color="cyan", fontsize=10,
        arrowprops={"arrowstyle": "->", "color": "cyan"},
    )
    ax_right.set_title(
        "$|\\mathrm{fftshift}(\\mathrm{fft2}(U))|$\n"
        f"measured peak (row={peak_row}, col={peak_col})  -  "
        "all energy in ONE bin",
        fontsize=11,
    )
    ax_right.set_xlabel("column index (centred order)")
    ax_right.set_ylabel("row index (centred order)")

    fig.suptitle(
        "Figure 7 - Test C-01 / P-05 made visible.  The destination bin is "
        "computed in closed form BEFORE the FFT is taken.\n"
        "This picture illustrates the test; the test, not the picture, is the "
        "evidence.",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    _save(fig, "fig07_plane_wave_fft_bin.png")


# ---------------------------------------------------------------------------
def main() -> None:
    print("Generating Milestone 0 figures...")
    fig01_complex_plane()
    fig02_amplitude_phase_intensity()
    fig03_spatial_grid()
    fig04_array_axes()
    fig05_fft_ordering()
    fig06_nyquist_angle()
    fig07_plane_wave_fft_bin()
    print("Done.")


if __name__ == "__main__":
    main()
