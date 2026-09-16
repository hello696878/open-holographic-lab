r"""Regenerate the three deterministic Milestone 3 handoff figures.

    .\.venv\Scripts\python.exe -B scripts\make_m3_figures.py

All displayed targets pass through the strict PNG decoder. The twelve
predeclared fixture/seed combinations are retained; no seed is selected for
appearance. Every reconstruction is the shipped solver's unmodified forward
field. Plotting and temporary PNG I/O stay outside the numerical core.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from probe_m3_evidence import (  # noqa: E402
    DISTANCE_M, ITERATIONS, SEEDS, WAVELENGTH_M,
    Fixture, decode_fixture_png, planning_fixture, solve_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "handoffs" / "milestone_3" / "figures"
DPI = 150


def _extent(fixture: Fixture) -> tuple[float, float, float, float]:
    grid = fixture.grid
    return (
        (grid.x[0] - grid.dx / 2) * 1e6, (grid.x[-1] + grid.dx / 2) * 1e6,
        (grid.y[-1] + grid.dy / 2) * 1e6, (grid.y[0] - grid.dy / 2) * 1e6,
    )


def _image(
    figure: plt.Figure, axis: plt.Axes, data: np.ndarray, fixture: Fixture,
    title: str, *, low: float, high: float, cmap: str, color_label: str,
) -> None:
    artist = axis.imshow(
        data, extent=_extent(fixture), origin="upper", interpolation="nearest",
        vmin=low, vmax=high, cmap=cmap,
    )
    axis.set(title=title, xlabel="x [µm], +x right", ylabel="y [µm], +y downward")
    colorbar = figure.colorbar(artist, ax=axis, fraction=0.046, pad=0.035, label=color_label)
    if cmap == "twilight":
        colorbar.set_ticks((-np.pi, 0.0, np.pi), labels=("−π", "0", "+π"))


def _save(figure: plt.Figure, filename: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    figure.savefig(
        path, dpi=DPI, facecolor="white",
        metadata={"Software": "Open Holographic Lab - Milestone 3"},
    )
    plt.close(figure)
    print(f"wrote {path.relative_to(ROOT).as_posix()}")


def fig01_single_plane_gs() -> None:
    """Show the default smooth-spot PNG and actual seed-zero reconstruction."""
    fixture = planning_fixture(0)
    intensity, target = decode_fixture_png(fixture)
    # The demo explicitly computes illumination from the decoded amplitude.
    source_value = float(np.sqrt(np.sum(target**2) / target.size))
    source = np.full(fixture.grid.shape, source_value, dtype=np.float64)
    result = solve_fixture(fixture, SEEDS[0], target=target, source=source)
    reconstruction = result.reconstruction.intensity
    maximum = float(max(intensity.max(), reconstruction.max()))
    figure, axes = plt.subplots(2, 2, figsize=(12.2, 9.7), layout="constrained")
    _image(
        figure, axes[0, 0], intensity, fixture, "Decoded PNG target intensity",
        low=0.0, high=maximum, cmap="gray", color_label="intensity [a.u.], shared scale",
    )
    _image(
        figure, axes[0, 1], result.phase, fixture, "Ideal numerical source phase\nNot a calibrated SLM drive image",
        low=-np.pi, high=np.pi, cmap="twilight", color_label="phase [rad]",
    )
    _image(
        figure, axes[1, 0], reconstruction, fixture, "Actual forward reconstruction intensity",
        low=0.0, high=maximum, cmap="gray", color_label="intensity [a.u.], shared scale",
    )
    axes[1, 1].plot(np.arange(ITERATIONS + 1), result.residual_history, color="#1261a0", linewidth=2)
    axes[1, 1].set(
        title="Raw normalized squared amplitude residual",
        xlabel="complete target/source projection cycles k", ylabel="rho(k), full grid",
        xlim=(0, ITERATIONS), ylim=(0, None),
    )
    axes[1, 1].grid(alpha=0.25)
    axes[1, 1].text(
        0.96, 0.87,
        f"rho(0) = {result.residual_history[0]:.6f}\n"
        f"rho(50) = {result.residual_history[-1]:.6f}\n\n"
        "Measured before target replacement\nNo independent image normalization",
        transform=axes[1, 1].transAxes, va="top", ha="right", fontsize=10.5,
    )
    figure.suptitle(
        "Single-plane Gerchberg–Saxton on a complete periodic grid\n"
        f"64 × 64 | λ = {WAVELENGTH_M*1e9:g} nm | dx = dy = 8 µm | z = {DISTANCE_M*1e3:g} mm | seed 0 | 50 cycles\n"
        f"Shared intensity limits [0, {maximum:.6f}]; separately configured source amplitude {source_value:.6f}",
        fontsize=13,
    )
    _save(figure, "fig01_single_plane_gs.png")
    print(f"fig01 final residual={result.residual_history[-1]:.17e}; shared vmax={maximum:.17e}")


def fig02_seed_histories() -> None:
    """Show all twelve raw histories on labelled logarithmic vertical scales."""
    figure, axes = plt.subplots(1, 3, figsize=(15.0, 5.5), layout="constrained")
    history_minimum, history_maximum = float("inf"), 0.0
    for index, axis in enumerate(axes):
        fixture = planning_fixture(index)
        intensity, target = decode_fixture_png(fixture)
        np.testing.assert_array_equal(intensity, fixture.intensity)
        finals = []
        for seed in SEEDS:
            result = solve_fixture(fixture, seed, target=target)
            history = result.residual_history
            assert history[-1] < 0.05 and history[-1] < 0.1 * history[0]
            axis.semilogy(np.arange(history.size), history, label=f"seed {seed}", linewidth=1.6)
            finals.append(float(history[-1]))
            history_minimum = min(history_minimum, float(history.min()))
            history_maximum = max(history_maximum, float(history.max()))
        axis.axhline(0.05, color="#666666", linestyle="--", linewidth=1, label="fixture limit 0.05")
        axis.set(
            title=f"{fixture.name}\nFinal range {min(finals):.6f}–{max(finals):.6f}",
            xlabel="complete projection cycles k", ylabel="rho(k), full grid (log scale)",
            xlim=(0, ITERATIONS),
        )
        axis.grid(which="both", alpha=0.17)
        axis.legend(fontsize=9, loc="upper right")
    for axis in axes:
        axis.set_ylim(history_minimum * 0.75, history_maximum * 1.2)
    figure.suptitle(
        "All predeclared seeds: 0, 1, 2, 3 | all three unchanged planning fixtures\n"
        "Decoded 8-bit targets; raw residual values, no smoothing or history clipping\n"
        "Each case passes rho(50) < 0.05 and rho(50) < 0.1 × rho(0); these are fixture-specific criteria",
        fontsize=13,
    )
    _save(figure, "fig02_seed_histories.png")
    print("fig02 verified all 12 declared fixture/seed criteria")


def fig03_rectangular_case() -> None:
    """Show anisotropic-grid orientation and the actual signed amplitude mismatch."""
    fixture = planning_fixture(2)
    intensity, target = decode_fixture_png(fixture)
    result = solve_fixture(fixture, SEEDS[0], target=target)
    reconstruction = result.reconstruction.intensity
    maximum = float(max(intensity.max(), reconstruction.max()))
    amplitude_error = result.reconstruction.amplitude - target
    error_limit = float(np.max(np.abs(amplitude_error)))
    figure, axes = plt.subplots(2, 2, figsize=(12.2, 9.5), layout="constrained")
    _image(
        figure, axes[0, 0], intensity, fixture, "Decoded two-feature target intensity",
        low=0.0, high=maximum, cmap="gray", color_label="intensity [a.u.], shared scale",
    )
    _image(
        figure, axes[0, 1], result.phase, fixture, "Ideal numerical source phase\nNot a calibrated SLM drive image",
        low=-np.pi, high=np.pi, cmap="twilight", color_label="phase [rad]",
    )
    _image(
        figure, axes[1, 0], reconstruction, fixture, "Actual forward reconstruction intensity",
        low=0.0, high=maximum, cmap="gray", color_label="intensity [a.u.], shared scale",
    )
    _image(
        figure, axes[1, 1], amplitude_error, fixture, "Signed amplitude mismatch: |V| − A_target",
        low=-error_limit, high=error_limit, cmap="RdBu_r", color_label="amplitude error [a.u.]",
    )
    figure.suptitle(
        "Rectangular periodic case | (ny, nx) = (48, 64) | dx = 8 µm, dy = 10 µm\n"
        f"λ = 633 nm | z = 5 mm | seed 0 | 50 cycles | final rho = {result.residual_history[-1]:.6f}\n"
        f"Target/reconstruction share [0, {maximum:.6f}]; physical pixel aspect and +y-down orientation preserved",
        fontsize=13,
    )
    _save(figure, "fig03_rectangular_case.png")
    print(f"fig03 final residual={result.residual_history[-1]:.17e}; shared vmax={maximum:.17e}")


def main() -> None:
    """Regenerate exactly the three approved figures using deterministic inputs."""
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10}):
        fig01_single_plane_gs()
        fig02_seed_histories()
        fig03_rectangular_case()


if __name__ == "__main__":
    main()
