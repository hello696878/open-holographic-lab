r"""Print a current, reproducible Gaussian/ASM comparison as JSON.

This is a measurement of the shipped propagator, not a reconstruction of the
historical planning probes or a band-limited ASM implementation. No files are
written. Run from the existing environment with:
    .\.venv\Scripts\python.exe -B scripts\probe_m1_gaussian_evidence.py
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np

from ohlab import ComplexField, SamplingGrid, propagate_angular_spectrum
from ohlab.units import MM, NM, UM


ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
    ).rstrip("\r\n")


def _analytic_gaussian(
    radius_squared_m2: np.ndarray, waist_m: float, wavelength_m: float, z_m: float
) -> np.ndarray:
    """Return the paraxial complex Gaussian field, amplitude in arbitrary units.

    The waist-plane on-axis amplitude is one. Coordinates and distances are
    SI; the exp(-i omega t) convention gives carrier +k*z and Gouy lag -psi.
    """
    k = 2.0 * math.pi / wavelength_m
    z_r = math.pi * waist_m**2 / wavelength_m
    w_z = waist_m * math.sqrt(1.0 + (z_m / z_r) ** 2)
    curvature_phase = (
        np.zeros_like(radius_squared_m2)
        if z_m == 0.0
        else k * radius_squared_m2 / (2.0 * z_m * (1.0 + (z_r / z_m) ** 2))
    )
    return (
        (waist_m / w_z)
        * np.exp(-radius_squared_m2 / w_z**2)
        * np.exp(1j * (k * z_m + curvature_phase - math.atan2(z_m, z_r)))
    )


def main() -> None:
    """Print provenance, SI configuration, comparison definition, and results."""
    wavelength_m = 633 * NM
    waist_m = 40 * UM
    grid = SamplingGrid.square(n=256, pitch=3.74 * UM)
    x, y = grid.meshgrid()
    radius_squared_m2 = x**2 + y**2
    source = ComplexField(
        data=np.exp(-radius_squared_m2 / waist_m**2).astype(np.complex128),
        grid=grid,
        wavelength_m=wavelength_m,
    )
    status = _git("status", "--porcelain=v1", "--untracked-files=all")
    code_paths = sorted((ROOT / "src" / "ohlab").glob("*.py")) + [Path(__file__).resolve()]
    results = []
    for distance_mm in (5.0, 20.0, 50.0, 100.0):
        distance_m = distance_mm * MM
        reference = _analytic_gaussian(
            radius_squared_m2, waist_m, wavelength_m, distance_m
        )
        reference_peak = float(np.max(np.abs(reference)))
        for pad_factor in (1, 2):
            out = propagate_angular_spectrum(
                source, distance_m=distance_m, pad_factor=pad_factor
            )
            absolute_error = float(np.max(np.abs(out.data - reference)))
            results.append({
                "distance_m": distance_m,
                "pad_factor": pad_factor,
                "max_complex_absolute_error_au": absolute_error,
                "reference_peak_amplitude_au": reference_peak,
                "relative_complex_linf_error": absolute_error / reference_peak,
            })
    report = {
        "measurement_kind": "current shipped ASM vs analytic paraxial Gaussian",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": _git("rev-parse", "HEAD"),
        "working_tree_dirty": bool(status),
        "working_tree_status_porcelain": status.splitlines(),
        "source_sha256": {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in code_paths
        },
        "environment": {
            "python": platform.python_version(),
            "executable": sys.executable,
            "platform": platform.platform(),
            "versions": {p: version(p) for p in ("ohlab", "numpy", "scipy", "pytest")},
        },
        "configuration_si": {
            "wavelength_m": wavelength_m,
            "waist_m": waist_m,
            "grid": grid.to_dict(),
            "source": "U0=exp(-(x^2+y^2)/waist_m^2); peak amplitude 1 a.u.",
        },
        "analytic_reference": {
            "equation": "U=(w0/w(z))*exp(-r^2/w(z)^2)*exp(i*(k*z+k*r^2/(2*R(z))-psi(z)))",
            "definitions": "k=2*pi/lambda; zR=pi*w0^2/lambda; w(z)=w0*sqrt(1+(z/zR)^2); R(z)=z*(1+(zR/z)^2); psi=atan2(z,zR)",
            "model": "paraxial; same scalar, coherent, n=1 convention as ASM",
        },
        "comparison": {
            "region": "all 256x256 samples of the original source grid, after the propagator's crop",
            "error": "max(abs(U_numeric-U_reference))/max(abs(U_reference))",
            "normalization": "only division by analytic peak amplitude in the reported relative metric",
            "global_phase_alignment": "none",
            "fitted_scaling": "none",
        },
        "results": results,
    }
    print(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False))


if __name__ == "__main__":
    main()
