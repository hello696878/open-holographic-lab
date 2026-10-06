r"""Generate three Jones evidence/teaching PNGs from a current shipped demo.

Use the existing interpreter after running the 64x64 demo::

    .\.venv\Scripts\python.exe -B -X utf8 scripts\generate_v2c_figures.py --evidence-dir runs\v2c-demo64-NEW

For regeneration, pass a fresh --output-dir under ignored runs/. Agg opens no
GUI. The caller may pass an owned MPLCONFIGDIR only to this child process.
Figures validate source hashes and exact recomputation of the saved arrays,
then plot actual unnormalized amplitudes and independently labelled references.
They are numerical teaching figures, not V2d screenshots or hardware evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples import jones_polarization
from examples.jones_polarization import compute_demo
from ohlab.optics import polarization
from scripts import validate_v2c_polarization
from scripts.validate_v2c_polarization import MALUS_DEGREES, NEAR_OFFSETS

OUTPUT = ROOT / "docs" / "handoffs" / "v2c" / "figures"
FILENAMES = ("fig01_malus_and_loss.png", "fig02_retarders_and_components.png",
             "fig03_polarization_ellipses.png")
DPI = 145
BLUE = "#24648c"
ORANGE = "#b95c28"
GREY = "#555b61"


def load_verified_demo(directory: Path) -> tuple[dict[str, object], str]:
    """Authenticate current-source provenance and byte-recompute actual arrays.

    Exactness here is repeatability of this same shipped implementation and
    environment, separate from the independent scientific tolerance checks.
    It does not certify files from another platform/library implementation.
    """
    raw = (directory / "demo.json").read_bytes()
    report = json.loads(raw)
    if report.get("acceptance_passed") is not True or report.get("shape") != [64, 64]:
        raise ValueError("figures require a passed actual 64x64 demo")
    validation = report["validation"]
    if validation.get("acceptance_passed") is not True:
        raise ValueError("figures require independent validation in the actual demo")
    sources = ((Path(polarization.__file__), validation["environment"]["source_sha256"]),
               (Path(validate_v2c_polarization.__file__), validation["environment"]["reference_source_sha256"]),
               (Path(jones_polarization.__file__), report["demo_source_sha256"]))
    for source, expected in sources:
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f"demo source provenance does not match current {source}")
    if tuple(row["degrees"] for row in validation["malus"]) != MALUS_DEGREES:
        raise ValueError("all thirteen ordered Malus points are required")
    if tuple(row["offset_rad"] for row in validation["near_extinction"]) != NEAR_OFFSETS:
        raise ValueError("all five ordered near-extinction points are required")
    array_path = directory / "demo_arrays.npz"
    if hashlib.sha256(array_path.read_bytes()).hexdigest() != report["demo_arrays_sha256"]:
        raise ValueError("actual demo-array evidence hash mismatch")
    recomputed = compute_demo(n=64, measure=False)
    with np.load(array_path, allow_pickle=False) as stored:
        if set(stored.files) != set(recomputed.arrays):
            raise ValueError("saved and recomputed demo-array inventories differ")
        for name, actual in recomputed.arrays.items():
            expected = stored[name]
            if (actual.shape != expected.shape or actual.dtype != expected.dtype
                    or actual.tobytes(order="C") != expected.tobytes(order="C")):
                raise AssertionError(f"saved/recomputed actual array bytes differ: {name}")
    for key in ("malus", "near_extinction", "literal_fixtures", "noncommuting_order"):
        if recomputed.report["validation"][key] != validation[key]:
            raise AssertionError(f"saved/recomputed diagnostic rows differ: {key}")
    if recomputed.report["ellipses"] != report["ellipses"]:
        raise AssertionError("plotted ellipses differ from actual recomputed samples")
    return report, hashlib.sha256(raw).hexdigest()


def finish_figure(figure: plt.Figure, destination: Path, evidence_sha: str) -> None:
    """Reserve a provenance footer, then write deterministic metadata."""
    # The rectangle is (left, bottom, width, height), not two corners.
    # Reserve the top for the fixed title/subtitle and the bottom for provenance.
    figure.get_layout_engine().set(rect=(0.0, 0.07, 1.0, 0.82))
    figure.text(.01, .013, f"Shipped V2c 64x64 numerical evidence; demo JSON SHA-256 {evidence_sha}",
                fontsize=6.5, color=GREY)
    figure.savefig(destination, dpi=DPI,
                   metadata={"Software": "Open Holographic Lab V2c; Matplotlib Agg"})
    plt.close(figure)


def figure_malus(report: dict[str, object], destination: Path, sha: str) -> None:
    """Actual declared operations, retained polarizer loss and weak outputs."""
    validation = report["validation"]
    figure, axes = plt.subplots(1, 3, figsize=(14, 5.1), layout="constrained")
    figure.suptitle("Classical polarized light: projection acts on amplitude", fontsize=15, y=.99)
    rows = validation["malus"]
    reference_degrees = np.linspace(-90.0, 90.0, 361)
    axes[0].plot(reference_degrees, np.cos(np.deg2rad(reference_degrees)) ** 2,
                 color=GREY, linewidth=1.6, label="Analytic cos²(theta) reference")
    axes[0].scatter([row["degrees"] for row in rows], [row["actual_ratio"] for row in rows],
                    color=BLUE, s=28, zorder=3, label="13 actual polarizer operations")
    axes[0].set(title="Malus sweep: incident x-polarized field", xlabel="Axis angle (degrees)",
                ylabel="Transmitted / incident sampled norm", xlim=(-94, 94), ylim=(-.04, 1.25))
    axes[0].set_xticks((-90, -45, 0, 45, 90))
    axes[0].grid(alpha=.2)
    axes[0].legend(fontsize=8, loc="upper center")
    fractions = (float(validation["crossed"]["ratio"]), float(validation["three_polarizers"]["ratio"]))
    axes[1].bar((0, 1), fractions, color=(BLUE, ORANGE), width=.6)
    axes[1].set_yscale("log")
    axes[1].set(title="Retain loss; do not normalize it away", ylabel="Transmitted / incident sampled norm",
                ylim=(1e-34, 2), xticks=(0, 1), xticklabels=("0° → 90°", "0° → 45° → 90°"))
    for index, value in enumerate(fractions):
        axes[1].text(index, value * 2, f"{value:.6g}", ha="center", fontsize=9)
    axes[1].text(.5, .92, "Already x-polarized input\n(not unpolarized illumination)",
                 transform=axes[1].transAxes, ha="center", va="top", fontsize=8.5)
    axes[1].grid(axis="y", alpha=.2)
    weak = validation["near_extinction"]
    axes[2].plot(range(5), [row["expected_ratio"] for row in weak], color=GREY,
                 marker="o", markerfacecolor="none", markersize=8, label="80-digit actual-angle reference")
    axes[2].scatter(range(5), [row["actual_ratio"] for row in weak], color=ORANGE,
                    s=24, zorder=3, label="Actual positive weak outputs")
    axes[2].set_yscale("log")
    axes[2].set(title="Near extinction: theta = π/2 + epsilon", ylabel="Transmitted / incident sampled norm",
                xlabel="Requested epsilon (rad)", xticks=range(5),
                xticklabels=("−1e−6", "−1e−9", "0", "+1e−9", "+1e−6"), ylim=(1e-34, 1e-8))
    axes[2].text(.5, .23, "Floating π/2 retains its residual.\nAll actual binary64 angles are recorded.",
                 transform=axes[2].transAxes, ha="center", fontsize=8.5)
    axes[2].grid(alpha=.2)
    axes[2].legend(fontsize=7.5, loc="upper center")
    finish_figure(figure, destination, sha)


def figure_retarders(report: dict[str, object], destination: Path, sha: str) -> None:
    """Actual component phase and independent complex/conservation discrepancies."""
    validation = report["validation"]
    figure, axes = plt.subplots(2, 2, figsize=(12.8, 8), layout="constrained")
    figure.suptitle("Ideal retarders preserve norm and the selected complex phase", fontsize=15, y=.99)
    fixtures = [row for row in validation["literal_fixtures"] if row["case_id"] in
                ("QWP0_linear45", "HWP_pi8_x", "QWP45_x")]
    actual = np.asarray([row["actual_components"] for row in fixtures]).reshape(6, 2)
    expected = np.asarray([row["expected_components"] for row in fixtures]).reshape(6, 2)
    positions = np.arange(6)
    labels = ("QWP 0°\nx", "QWP 0°\ny", "HWP 22.5°\nx", "HWP 22.5°\ny", "QWP 45°\nx", "QWP 45°\ny")
    for axis, part, title in ((axes[0, 0], 0, "Real component amplitudes"),
                              (axes[0, 1], 1, "Imaginary component amplitudes")):
        axis.bar(positions - .12, actual[:, part], width=.24, color=BLUE, label="Actual public operation")
        axis.scatter(positions + .12, expected[:, part], color=ORANGE, marker="o",
                     facecolors="none", s=38, label="Independent literal expectation", zorder=3)
        axis.set(title=title, ylabel="Amplitude (a.u.)", xticks=positions, xticklabels=labels,
                 ylim=(-.62, .92))
        axis.axhline(0, color=GREY, linewidth=.7)
        axis.grid(axis="y", alpha=.2)
        axis.legend(fontsize=8, loc="lower left")
    retarder_rows = validation["retarders"]
    ratios = [row["actual_ratio"] for row in retarder_rows]
    axes[1, 0].plot(range(len(ratios)), np.asarray(ratios) - 1, color=BLUE, marker=".",
                   label="35 actual retarder cases")
    axes[1, 0].axhline(0, color=ORANGE, linestyle="--", label="Norm-preservation reference")
    axes[1, 0].set(title="Asymmetric 3x4 input: tiny signed norm residual", xlabel="Declared axis/retardance case index",
                   ylabel="(Output / incident sampled norm) − 1", ylim=(-2e-15, 2e-15))
    axes[1, 0].ticklabel_format(axis="y", style="sci", scilimits=(0, 0), useOffset=False)
    axes[1, 0].grid(alpha=.2)
    axes[1, 0].legend(fontsize=8)
    # This display floor marks exactly-zero observed discrepancies without
    # changing the raw stored metrics or the numerical acceptance tests.
    display_floor = 1e-18
    axes[1, 1].semilogy(range(len(retarder_rows)),
                       [max(row["max_complex_input_scaled_error"], display_floor) for row in retarder_rows],
                       color=BLUE, marker=".", label="Complex component / input scale")
    axes[1, 1].semilogy(range(len(retarder_rows)),
                       [max(row["unitarity_entry_error"], display_floor) for row in retarder_rows],
                       color=ORANGE, marker=".", label="Public-basis unitarity entry error")
    axes[1, 1].axhline(2e-15, color=GREY, linestyle="--", linewidth=.8, label="Unitarity atol 2e−15")
    axes[1, 1].set(title="Independent discrepancies; no phase alignment", xlabel="Declared axis/retardance case index",
                   ylabel="Absolute or input-scaled discrepancy", ylim=(5e-19, 1e-14))
    axes[1, 1].text(.5, .06, "Zero discrepancies shown at 1e−18 only for display; raw zeros retained.",
                    transform=axes[1, 1].transAxes, ha="center", fontsize=7)
    axes[1, 1].grid(alpha=.2)
    axes[1, 1].legend(fontsize=7.5, loc="upper center")
    figure.text(.5, .935, "QWP45° on x gives ((1+i)/2, (1−i)/2); its common phase is retained.",
                ha="center", fontsize=10)
    finish_figure(figure, destination, sha)


def figure_ellipses(report: dict[str, object], destination: Path, sha: str) -> None:
    """Real-time component traces at the actual named nonzero sample; no fitting."""
    figure, axes = plt.subplots(2, 3, figsize=(12, 8.2), layout="constrained")
    figure.suptitle("Re([Ux, Uy] exp(−i tau)): actual sample, dimensionless optical phase", fontsize=14, y=.99)
    titles = {"linear_x": "Linear x: (1, 0)", "linear45": "Linear 45°: (1, 1)/√2",
              "QWP0_linear45": "QWP0°: (1, +i)/√2",
              "QWP45_x": "QWP45°: ((1+i)/2, (1−i)/2)",
              "HWP_pi8_x": "HWP22.5°: (1, 1)/√2"}
    for axis, row in zip(axes.ravel(), report["ellipses"], strict=False):
        points = np.asarray(row["points"], dtype=np.float64)
        axis.plot(points[:, 0], points[:, 1], color=BLUE, linewidth=1.8)
        axis.scatter(points[0, 0], points[0, 1], color=ORANGE, s=28, label="tau = 0", zorder=3)
        start, stop = points[20], points[28]
        axis.annotate("", xy=stop, xytext=start,
                      arrowprops={"arrowstyle": "->", "color": ORANGE, "lw": 1.8})
        axis.set(title=titles[row["case_id"]], xlabel="Real x component (a.u.)",
                 ylabel="Real y component (a.u.; +y down)", xlim=(-1.1, 1.1), ylim=(1.1, -1.1))
        axis.set_aspect("equal", adjustable="box")
        axis.axhline(0, color=GREY, linewidth=.5)
        axis.axvline(0, color=GREY, linewidth=.5)
        axis.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8, loc="upper left")
    axes[1, 2].axis("off")
    axes[1, 2].text(.04, .9,
                    "Named sample: row 32, column 32\n64x64 grid center, x = y = 0 m\n\n"
                    "257 points: tau from 0 to 2π\nOrange arrow: increasing tau\n\n"
                    "Equal axes; original component amplitudes\nNo fitted ellipse or amplitude normalization\n\n"
                    "Time convention: exp(−i omega t)\n+y points downward in this display\n\n"
                    "Deterministic classical polarization\nNo handedness label or physical clock\nNo 3D viewer / hardware claim",
                    transform=axes[1, 2].transAxes, va="top", fontsize=10, linespacing=1.4)
    finish_figure(figure, destination, sha)


def main() -> int:
    """Write only the three approved PNG names; print their exact content hashes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    evidence = args.evidence_dir.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if set(path.name for path in output.iterdir()) - set(FILENAMES):
        raise ValueError(f"figure destination contains unrelated files: {output}")
    report, sha = load_verified_demo(evidence)
    figure_malus(report, output / FILENAMES[0], sha)
    figure_retarders(report, output / FILENAMES[1], sha)
    figure_ellipses(report, output / FILENAMES[2], sha)
    print(json.dumps({"evidence": str(evidence), "evidence_sha256": sha,
                      "figures": {name: {"path": str(output / name),
                                          "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest()}
                                  for name in FILENAMES},
                      "saved_arrays_recomputed_byte_identically": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
