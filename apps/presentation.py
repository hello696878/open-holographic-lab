"""Present an already verified M5 bundle without scientific or file side effects.

Callers supply saved arrays, configuration and metric values. This module never
decodes files, solves, evaluates M4 metrics, changes inputs or imports Streamlit.
Matplotlib Figure objects are independent of pyplot's global figure registry.
"""
from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import numpy as np

from ohlab.io.config import RunConfig


def format_metric_value(name: str, value: float) -> str:
    """Format a saved metric; retain positive-infinite PSNR explicitly.

    Units and parameters belong in the accompanying UI label. This operation
    does not recalculate a metric or replace infinity with a finite score.
    """
    if math.isinf(value) and value > 0 and name == "intensity_psnr":
        return "+∞"
    if not math.isfinite(value):
        raise ValueError(f"cannot display nonfinite {name}: {value!r}")
    return format(value, ".8g")


def _intensity_limits(arrays: Mapping[str, np.ndarray]) -> tuple[float, float]:
    maximum = max(
        float(np.max(arrays["target_intensity"])),
        float(np.max(arrays["reconstruction_intensity"])),
    )
    # A degenerate all-zero inspected image still needs a nonzero colour axis.
    # This changes only the axis bounds; both saved arrays remain exactly zero.
    return 0.0, maximum if maximum > 0.0 else 1.0


def _amplitude_power(amplitude: np.ndarray, dx: float, dy: float) -> float:
    """Summarize saved prescribed amplitude as power in a.u. m^2."""
    try:
        with np.errstate(all="raise"):
            area = np.float64(dx) * np.float64(dy)
            power = float(np.sum(amplitude**2) * area)
    except FloatingPointError as exc:
        raise ValueError("saved amplitude power cannot be displayed in float64") from exc
    if not math.isfinite(power):
        raise ValueError("saved amplitude power is not finite")
    return power


def summarize_bundle(
    *, arrays: Mapping[str, np.ndarray], config: RunConfig,
    metrics: Mapping[str, float],
) -> dict[str, Any]:
    """Return display metadata derived only from the supplied saved bundle.

    Lengths in the returned configuration remain metres. Amplitude is in
    arbitrary units; prescribed source and target-amplitude powers are
    ``sum(A**2) * dx * dy`` in a.u. m^2, as in the existing examples. Saved
    metrics are copied, not recomputed. A uniform loaded source is described
    as uniform without claiming how its illumination was originally chosen.
    """
    settings = config.to_dict()
    grid = settings["grid"]
    source = arrays["source_amplitude"]
    minimum = float(np.min(source))
    maximum = float(np.max(source))
    uniform = minimum == maximum
    lower, upper = _intensity_limits(arrays)
    history = arrays["residual_history"]
    metric_rows = []
    for name, parameters in settings["metrics"].items():
        role = parameters.get("mask")
        role = role.removesuffix(".npy") if role is not None else None
        metric_rows.append({
            "name": name,
            "value": metrics[name],
            "display_value": format_metric_value(name, metrics[name]),
            "parameters": parameters,
            "mask_role": role,
            "selected_pixels": int(np.count_nonzero(arrays[role])) if role else None,
        })
    return {
        "grid": grid,
        "optics": settings["optics"],
        "solver": settings["solver"],
        "illumination": {
            "kind": "uniform" if uniform else "nonuniform",
            "amplitude_min": minimum,
            "amplitude_max": maximum,
            "uniform_amplitude": minimum if uniform else None,
            "prescribed_source_power_au_m2": _amplitude_power(
                source, grid["dx_m"], grid["dy_m"],
            ),
            "target_amplitude_power_au_m2": _amplitude_power(
                arrays["target_amplitude"], grid["dx_m"], grid["dy_m"],
            ),
        },
        "display": {
            "intensity_min": lower,
            "intensity_max": upper,
            "phase_min_rad": -math.pi,
            "phase_max_rad": math.pi,
            "history_samples": int(history.size),
            "last_amplitude_residual": float(history[-1]),
        },
        "metrics": metric_rows,
    }


def build_result_figures(
    *, arrays: Mapping[str, np.ndarray],
) -> tuple[Figure, Figure]:
    """Build saved-image and complete raw-history figures without modifying data.

    Image axes are pixel columns and rows with +y downward. Target and actual
    reconstruction share one nonnegative intensity scale including overshoot.
    Ideal numerical phase uses a fixed [-pi, pi] radian display range; it is
    not a calibrated SLM drive image. Every saved residual is shown, including
    initialization at cycle zero. The caller owns the returned figures.
    """
    lower, upper = _intensity_limits(arrays)
    images = Figure(figsize=(12.0, 4.0), layout="constrained")
    axes = images.subplots(1, 3)
    for axis, role, title in zip(
        axes[:2],
        ("target_intensity", "reconstruction_intensity"),
        ("Saved target intensity", "Actual reconstruction intensity"),
        strict=True,
    ):
        intensity_image = axis.imshow(
            arrays[role], origin="upper", interpolation="nearest",
            cmap="magma", vmin=lower, vmax=upper,
        )
        axis.set_title(title, fontsize=11)
    images.colorbar(
        intensity_image, ax=list(axes[:2]), shrink=0.82,
        label="Shared intensity scale (a.u.)",
    )
    phase_image = axes[2].imshow(
        arrays["phase"], origin="upper", interpolation="nearest",
        cmap="twilight", vmin=-math.pi, vmax=math.pi,
    )
    axes[2].set_title("Ideal numerical source phase", fontsize=11)
    phase_bar = images.colorbar(
        phase_image, ax=axes[2], shrink=0.82, ticks=[-math.pi, 0.0, math.pi],
        label="Phase (rad)",
    )
    phase_bar.ax.set_yticklabels([r"$-\pi$", "0", r"$+\pi$"])
    for axis in axes:
        axis.set_xlabel("column j")
        axis.set_ylabel("row i (+y downward)")

    history_figure = Figure(figsize=(10.0, 2.9), layout="constrained")
    history_axis = history_figure.subplots()
    history = arrays["residual_history"]
    cycles = np.arange(history.size)
    history_axis.plot(cycles, history, color="#215c88", linewidth=1.5, marker=".")
    history_axis.set_title("Saved M3 squared amplitude residual (all samples)")
    history_axis.set_xlabel("cycle k (0 = initialization)")
    history_axis.set_ylabel(r"$\rho_k$ (dimensionless)")
    history_axis.set_ylim(bottom=0.0)
    history_axis.grid(alpha=0.2)
    if history.size == 1:
        history_axis.set_xlim(-0.5, 0.5)
        history_axis.set_xticks([0])
    else:
        history_axis.set_xlim(0, history.size - 1)
        history_axis.xaxis.set_major_locator(MaxNLocator(integer=True))
    return images, history_figure
