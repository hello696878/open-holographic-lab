"""Generate the Milestone 1 handoff figures.

**Outside the numerical core by design.** Together with
``make_m0_figures.py`` this is one of only two files in the repository that
import matplotlib; ``src/ohlab/`` imports no plotting or image library, which
is enforced by an AST scan in ``tests/test_fft_conventions.py``.

Every figure is generated from the implemented API, so it cannot drift away
from the code. Figures illustrate the tests; the tests are the evidence.

Usage
-----
    .\\.venv\\Scripts\\python.exe scripts\\make_m1_figures.py
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ohlab import (  # noqa: E402
    ComplexField,
    SamplingGrid,
    angular_spectrum_transfer_function,
    propagate_angular_spectrum,
)
from ohlab.units import MM, NM, UM  # noqa: E402

OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "handoffs"
    / "milestone_1"
    / "figures"
)

WAVELENGTH_M = 633 * NM
K = 2.0 * math.pi / WAVELENGTH_M
DPI = 130

ACCENT = "#1f77b4"
ACCENT_2 = "#d62728"
ACCENT_3 = "#2ca02c"
NEUTRAL = "#555555"


def _save(fig: plt.Figure, name: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote {path.relative_to(OUTPUT_DIR.parents[3])}")


# ---------------------------------------------------------------------------
def fig01_angular_spectrum_decomposition() -> None:
    """A field as a sum of tilted plane waves, each with its own kz."""
    grid = SamplingGrid.square(n=192, pitch=4.0 * UM)
    x_grid, y_grid = grid.meshgrid()

    components = [(6, 4, 1.0), (-11, 3, 0.6), (9, -8, 0.35)]
    fig, axes = plt.subplots(2, 4, figsize=(15.0, 6.6))

    total = np.zeros(grid.shape, dtype=np.complex128)
    for index, (dcol, drow, amplitude) in enumerate(components):
        col, row = grid.nx // 2 + dcol, grid.ny // 2 + drow
        fx0 = float(grid.fx_centered[col])
        fy0 = float(grid.fy_centered[row])
        wave = amplitude * np.exp(2j * np.pi * (fx0 * x_grid + fy0 * y_grid))
        total += wave
        kz = 2 * np.pi * math.sqrt((1 / WAVELENGTH_M) ** 2 - fx0**2 - fy0**2)

        ax = axes[0, index]
        ax.imshow(np.angle(wave), cmap="twilight", vmin=-np.pi, vmax=np.pi)
        ax.set_title(
            f"component {index + 1}   A = {amplitude}\n"
            f"$\\theta_x$={math.degrees(math.asin(fx0*WAVELENGTH_M)):+.2f}$\\degree$, "
            f"$\\theta_y$={math.degrees(math.asin(fy0*WAVELENGTH_M)):+.2f}$\\degree$\n"
            f"$k_z$ = {kz:.5e} rad/m",
            fontsize=9,
        )
        ax.set_xticks([])
        ax.set_yticks([])

    axes[0, 3].imshow(np.angle(total), cmap="twilight", vmin=-np.pi, vmax=np.pi)
    axes[0, 3].set_title("SUM: phase of $U(x,y,0)$", fontsize=10)
    axes[0, 3].set_xticks([])
    axes[0, 3].set_yticks([])

    field = ComplexField(data=total, grid=grid, wavelength_m=WAVELENGTH_M)
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(field.data)))
    axes[1, 0].imshow(spectrum, cmap="magma")
    axes[1, 0].set_title(
        "$|$FFT$(U)|$ : three isolated bins\n(the angular spectrum)", fontsize=10
    )
    axes[1, 0].set_xticks([])
    axes[1, 0].set_yticks([])

    for index, z in enumerate((5 * MM, 20 * MM, 60 * MM)):
        out = propagate_angular_spectrum(field, distance_m=z, pad_factor=1)
        ax = axes[1, index + 1]
        ax.imshow(np.angle(out.data), cmap="twilight", vmin=-np.pi, vmax=np.pi)
        ax.set_title(f"propagated  z = {z*1e3:.0f} mm", fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])

    fig.suptitle(
        "Figure 1 - The Angular Spectrum idea.  A field is a SUM of tilted "
        "plane waves.\nEach travels at its own axial rate $k_z$, so "
        "propagation is just a per-component phase $e^{ik_z z}$ - "
        "a multiplication in the frequency domain.",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    _save(fig, "fig01_angular_spectrum_decomposition.png")


# ---------------------------------------------------------------------------
def fig02_space_frequency_pipeline() -> None:
    """The four-step pipeline, annotated with shapes and orderings."""
    fig, ax = plt.subplots(figsize=(13.0, 5.4))
    ax.axis("off")

    boxes = [
        (0.02, "$U(x,y,0)$", "SPACE\n(ny, nx) complex128\nComplexField.data"),
        (0.27, "$A(f_x,f_y;0)$", "FREQUENCY\nnp.fft.fft2\nFFT ORDER: DC at [0,0]"),
        (0.52, "$A(f_x,f_y;z)$", "FREQUENCY\n$\\times\\ H = e^{ik_zz}$\nelementwise"),
        (0.77, "$U(x,y,z)$", "SPACE\nnp.fft.ifft2\nsame grid, same $\\lambda$"),
    ]
    for left, title, body in boxes:
        ax.add_patch(
            plt.Rectangle((left, 0.42), 0.19, 0.34, facecolor="#eaf2fb",
                          edgecolor=ACCENT, linewidth=1.8)
        )
        ax.text(left + 0.095, 0.70, title, ha="center", fontsize=14)
        ax.text(left + 0.095, 0.54, body, ha="center", fontsize=9, color=NEUTRAL)

    for left in (0.21, 0.46, 0.71):
        ax.annotate("", xy=(left + 0.06, 0.59), xytext=(left, 0.59),
                    arrowprops={"arrowstyle": "->", "lw": 2.2, "color": ACCENT})

    ax.text(0.5, 0.30,
            "Zero padding (pad_factor > 1) wraps the whole pipeline:\n"
            "embed $U$ in a larger zero window  ->  propagate  ->  crop back",
            ha="center", fontsize=10, color=ACCENT_2)
    ax.text(0.5, 0.16,
            "Origin alignment rule:  pad_before = $N_{pad}//2 - N//2$,  so "
            "original index $N//2$ lands on padded index $N_{pad}//2$\n"
            "and every physical coordinate is preserved BIT-EXACTLY.",
            ha="center", fontsize=10, color=NEUTRAL)
    ax.text(0.5, 0.04,
            "$H$ is built on the FFT-ORDERED frequency mesh, so no full-size "
            "array is ever fftshifted.",
            ha="center", fontsize=10, color=NEUTRAL)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 0.92)
    fig.suptitle("Figure 2 - The propagation pipeline", fontsize=13)
    _save(fig, "fig02_space_frequency_pipeline.png")


# ---------------------------------------------------------------------------
def fig03_kz_geometry() -> None:
    """The wavevector sphere: kx^2 + ky^2 + kz^2 = k^2."""
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(12.0, 5.2))

    theta = np.linspace(0, np.pi, 400)
    ax_left.plot(K * np.sin(theta), K * np.cos(theta), color=NEUTRAL, lw=1.5)
    ax_left.plot([-K * 1.15, K * 1.15], [0, 0], color=NEUTRAL, lw=0.8)
    ax_left.plot([0, 0], [-0.2 * K, K * 1.2], color=NEUTRAL, lw=0.8)

    for angle_deg, colour in ((0, ACCENT_3), (25, ACCENT), (60, ACCENT_2)):
        angle = math.radians(angle_deg)
        kt, kz = K * math.sin(angle), K * math.cos(angle)
        ax_left.annotate("", xy=(kt, kz), xytext=(0, 0),
                         arrowprops={"arrowstyle": "->", "color": colour, "lw": 2.2})
        ax_left.plot([kt, kt], [0, kz], ls=":", color=colour, lw=1.2)
        ax_left.text(kt * 1.06, kz * 1.02,
                     f"$\\theta$={angle_deg}$\\degree$\n$k_z$={kz/K:.3f}$k$",
                     color=colour, fontsize=9)

    ax_left.set_xlabel("$k_x$ (transverse)")
    ax_left.set_ylabel("$k_z$ (axial)")
    ax_left.set_aspect("equal")
    ax_left.set_title(
        "$k_x^2 + k_y^2 + k_z^2 = k^2$\n"
        "More tilt -> smaller $k_z$ -> SLOWER axial phase", fontsize=11)

    transverse = np.linspace(0, 1.6 * K, 500)
    with np.errstate(invalid="ignore"):
        kz_real = np.sqrt(np.maximum(K**2 - transverse**2, 0.0))
        kz_imag = np.sqrt(np.maximum(transverse**2 - K**2, 0.0))
    ax_right.plot(transverse / K, kz_real / K, color=ACCENT, lw=2.4,
                  label="Re$(k_z)/k$  - propagating")
    ax_right.plot(transverse / K, kz_imag / K, color=ACCENT_2, lw=2.4, ls="--",
                  label="Im$(k_z)/k$  - evanescent")
    ax_right.axvline(1.0, color=NEUTRAL, ls=":", lw=1.5)
    ax_right.text(1.03, 1.05, "cutoff\n$k_t = k$", fontsize=10, color=NEUTRAL)
    ax_right.set_xlabel("$\\sqrt{k_x^2+k_y^2}\\ /\\ k$")
    ax_right.set_ylabel("$k_z / k$")
    ax_right.legend(fontsize=9)
    ax_right.grid(alpha=0.3)
    ax_right.set_title(
        "The branch: $k_z=\\sqrt{k^2-k_x^2-k_y^2}$ with Im$(k_z)\\geq 0$\n"
        "Beyond cutoff $k_z$ is purely imaginary -> $|H|<1$, decay", fontsize=11)

    fig.suptitle("Figure 3 - Wavevector geometry and the $k_z$ branch", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    _save(fig, "fig03_kz_geometry.png")


# ---------------------------------------------------------------------------
def fig04_propagating_vs_evanescent() -> None:
    """Where the sampled mesh sits relative to the evanescent cutoff circle.

    Shows the corrected 2-D criterion: the CORNER of the Nyquist square, not
    the axis, decides whether a grid carries evanescent samples.
    """
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.0))
    cutoff = 1.0 / WAVELENGTH_M
    circle = np.linspace(0, 2 * np.pi, 400)

    cases = [
        (3.74 * UM, "Realistic SLM pitch 3.74 um", "no evanescent samples"),
        (400 * NM, "Pitch 400 nm", "CORNERS ONLY are evanescent"),
        (250 * NM, "Pitch 250 nm", "a broad evanescent region"),
    ]
    for ax, (pitch, title, note) in zip(axes, cases):
        grid = SamplingGrid.square(n=64, pitch=pitch)
        fx, fy = grid.freq_meshgrid(order="centered")
        mask = (fx**2 + fy**2) > cutoff**2

        ax.scatter(fx[~mask] / cutoff, fy[~mask] / cutoff, s=4,
                   color=ACCENT, label="propagating")
        if mask.any():
            ax.scatter(fx[mask] / cutoff, fy[mask] / cutoff, s=12,
                       color=ACCENT_2, label="evanescent")
        ax.plot(np.cos(circle), np.sin(circle), color="black", lw=2.0,
                label="cutoff  $|f| = 1/\\lambda$")

        half = grid.nyquist_fx / cutoff
        ax.add_patch(plt.Rectangle((-half, -half), 2 * half, 2 * half,
                                   fill=False, edgecolor=ACCENT_3, lw=1.8,
                                   ls="--", label="Nyquist square"))
        limit = max(1.25, half * 1.15)
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_aspect("equal")
        ax.set_xlabel("$f_x\\ \\lambda$")
        ax.set_ylabel("$f_y\\ \\lambda$")
        ax.set_title(f"{title}\n{note}  ({int(mask.sum())} of {mask.size})",
                     fontsize=10)
        ax.legend(fontsize=7, loc="upper right")

    fig.suptitle(
        "Figure 4 - Propagating vs evanescent is decided by the DISCRETE MESH, "
        "not by a pitch rule.\n"
        "The axis-only condition $d<\\lambda/2$ = 316.5 nm is WRONG: the CORNER "
        "of the Nyquist square reaches the cutoff first, at "
        "$d<\\lambda/\\sqrt{2}$ = 447.6 nm.\n"
        "Between those pitches (middle panel) only the four corners are "
        "evanescent - which is why the code tests the mesh itself.",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    _save(fig, "fig04_propagating_vs_evanescent.png")


# ---------------------------------------------------------------------------
def fig05_transfer_function_phase() -> None:
    """arg H and |H| for several distances, showing fringes tightening."""
    grid = SamplingGrid.square(n=256, pitch=3.74 * UM)
    distances = (1 * MM, 10 * MM, 100 * MM)

    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.4))
    for index, z in enumerate(distances):
        transfer = np.fft.fftshift(
            angular_spectrum_transfer_function(
                grid, wavelength_m=WAVELENGTH_M, distance_m=z
            )
        )
        axes[0, index].imshow(np.angle(transfer), cmap="twilight",
                              vmin=-np.pi, vmax=np.pi)
        axes[0, index].set_title(f"$\\arg H$,  z = {z*1e3:.0f} mm", fontsize=10)
        axes[0, index].set_xticks([])
        axes[0, index].set_yticks([])

        centre = grid.ny // 2
        axes[1, index].plot(grid.fx_centered / 1e3,
                            np.angle(transfer[centre, :]), color=ACCENT, lw=0.9)
        axes[1, index].set_xlabel("$f_x$  (cycles/mm)")
        axes[1, index].set_ylabel("$\\arg H$  (rad)")
        axes[1, index].set_title(
            f"central cut - {'well sampled' if z <= 1 * MM else 'fringes tightening'}",
            fontsize=9,
        )
        axes[1, index].grid(alpha=0.3)

    fig.suptitle(
        "Figure 5 - The transfer function $H=e^{ik_zz}$ on the frequency plane.\n"
        "$|H|=1$ everywhere here (this grid has no evanescent samples). As $z$ "
        "grows the phase fringes tighten;\n"
        "once they approach one cycle per sample the transfer function itself "
        "is undersampled - the motivation for band-limited ASM (deferred).",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.87))
    _save(fig, "fig05_transfer_function_phase.png")


# ---------------------------------------------------------------------------
def fig06_propagation_before_after() -> None:
    """Gaussian beam: numeric vs analytic, and their difference."""
    waist = 100.0 * UM
    grid = SamplingGrid.square(n=512, pitch=4.0 * UM)
    rayleigh = math.pi * waist**2 / WAVELENGTH_M
    x_grid, y_grid = grid.meshgrid()
    r_sq = x_grid**2 + y_grid**2

    def analytic(z: float) -> np.ndarray:
        w_z = waist * math.sqrt(1 + (z / rayleigh) ** 2)
        gouy = math.atan2(z, rayleigh)
        curv = 0.0 if z == 0 else K * r_sq / (2 * z * (1 + (rayleigh / z) ** 2))
        return ((waist / w_z) * np.exp(-r_sq / w_z**2)
                * np.exp(1j * (K * z + curv - gouy)))

    source = ComplexField(data=analytic(0.0), grid=grid,
                          wavelength_m=WAVELENGTH_M)
    extent = [1e3 * grid.x[0], 1e3 * grid.x[-1],
              1e3 * grid.y[-1], 1e3 * grid.y[0]]

    fig, axes = plt.subplots(3, 3, figsize=(12.5, 11.0))
    for row, factor in enumerate((0.0, 1.0, 2.0)):
        z = factor * rayleigh
        out = propagate_angular_spectrum(source, distance_m=z, pad_factor=2)
        reference = analytic(z)
        scale = float(np.max(np.abs(reference)))
        error = float(np.max(np.abs(out.data - reference))) / scale
        w_z = waist * math.sqrt(1 + (z / rayleigh) ** 2)

        im0 = axes[row, 0].imshow(out.intensity, extent=extent, cmap="inferno")
        axes[row, 0].set_title(
            f"z = {factor:.0f} $z_R$ = {z*1e3:.1f} mm\n"
            f"numeric intensity,  w(z) = {w_z*1e6:.1f} um", fontsize=9)
        fig.colorbar(im0, ax=axes[row, 0], fraction=0.046)

        im1 = axes[row, 1].imshow(np.abs(reference) ** 2, extent=extent,
                                  cmap="inferno")
        axes[row, 1].set_title("analytic Gaussian (paraxial)", fontsize=9)
        fig.colorbar(im1, ax=axes[row, 1], fraction=0.046)

        im2 = axes[row, 2].imshow(np.abs(out.data - reference) / scale,
                                  extent=extent, cmap="viridis")
        axes[row, 2].set_title(
            f"|difference| / max|analytic|\nmax = {error:.2e}", fontsize=9)
        fig.colorbar(im2, ax=axes[row, 2], fraction=0.046)

        for ax in axes[row]:
            ax.set_xlabel("x (mm)")
            ax.set_ylabel("y (mm)")

    fig.suptitle(
        "Figure 6 - Gaussian beam vs an INDEPENDENT analytic solution.\n"
        "Agreement is ~1e-6, and that floor is the PARAXIAL APPROXIMATION of "
        "the reference, not float64 error:\n"
        "$(\\lambda/\\pi w_0)^2 \\approx 4\\times10^{-6}$ here. The plane-wave "
        "tests, which have no such model error, agree to ~2e-14.",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    _save(fig, "fig06_propagation_before_after.png")


# ---------------------------------------------------------------------------
def fig07_wraparound_padding() -> None:
    """Circular wrap-around, and what zero padding does about it."""
    waist = 40.0 * UM
    grid = SamplingGrid.square(n=256, pitch=3.74 * UM)
    rayleigh = math.pi * waist**2 / WAVELENGTH_M
    x_grid, y_grid = grid.meshgrid()
    r_sq = x_grid**2 + y_grid**2
    field = ComplexField(data=np.exp(-r_sq / waist**2).astype(np.complex128),
                         grid=grid, wavelength_m=WAVELENGTH_M)

    z = 100.0 * MM
    w_z = waist * math.sqrt(1 + (z / rayleigh) ** 2)
    gouy = math.atan2(z, rayleigh)
    curv = K * r_sq / (2 * z * (1 + (rayleigh / z) ** 2))
    reference = ((waist / w_z) * np.exp(-r_sq / w_z**2)
                 * np.exp(1j * (K * z + curv - gouy)))
    scale = float(np.max(np.abs(reference)))

    unpadded = propagate_angular_spectrum(field, distance_m=z, pad_factor=1)
    padded = propagate_angular_spectrum(field, distance_m=z, pad_factor=2)
    err_unpadded = float(np.max(np.abs(unpadded.data - reference))) / scale
    err_padded = float(np.max(np.abs(padded.data - reference))) / scale

    extent = [1e3 * grid.x[0], 1e3 * grid.x[-1],
              1e3 * grid.y[-1], 1e3 * grid.y[0]]
    fig, axes = plt.subplots(1, 4, figsize=(16.0, 4.3))

    for ax, data, title in (
        (axes[0], np.abs(reference) ** 2, "analytic reference"),
        (axes[1], unpadded.intensity,
         f"pad_factor = 1\nrel err {err_unpadded:.2e}"),
        (axes[2], padded.intensity,
         f"pad_factor = 2\nrel err {err_padded:.2e}"),
    ):
        im = ax.imshow(data, extent=extent, cmap="inferno")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
        fig.colorbar(im, ax=ax, fraction=0.046)

    centre = grid.ny // 2
    axes[3].semilogy(1e3 * grid.x, np.abs(reference[centre, :]) ** 2,
                     color="black", lw=2.0, label="analytic")
    axes[3].semilogy(1e3 * grid.x, unpadded.intensity[centre, :],
                     color=ACCENT_2, lw=1.3, label="pad_factor=1")
    axes[3].semilogy(1e3 * grid.x, padded.intensity[centre, :],
                     color=ACCENT, lw=1.3, ls="--", label="pad_factor=2")
    axes[3].set_xlabel("x (mm)")
    axes[3].set_ylabel("intensity (a.u., log)")
    axes[3].set_title("central cut\nedges reveal the wrap-around", fontsize=10)
    axes[3].legend(fontsize=8)
    axes[3].grid(alpha=0.3)

    fig.suptitle(
        "Figure 7 - Circular wrap-around.  The DFT treats the window as "
        f"periodic, so at z = {z*1e3:.0f} mm light leaving one edge re-enters "
        "from the opposite one.\n"
        f"Zero padding reduces the error by {err_unpadded/err_padded:.0f}x here. "
        "It changes the boundary condition from periodic to zero-embedded - "
        "it is NOT a guarantee of physical correctness,\n"
        "and once light reaches the padded edge it wraps again.",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.85))
    _save(fig, "fig07_wraparound_padding.png")


# ---------------------------------------------------------------------------
def main() -> None:
    print("Generating Milestone 1 figures...")
    fig01_angular_spectrum_decomposition()
    fig02_space_frequency_pipeline()
    fig03_kz_geometry()
    fig04_propagating_vs_evanescent()
    fig05_transfer_function_phase()
    fig06_propagation_before_after()
    fig07_wraparound_padding()
    print("Done.")


if __name__ == "__main__":
    main()
