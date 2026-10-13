"""Generate three calculated V2f teaching/evidence PNGs from a real 64-grid demo.

Agg opens no GUI. Saved selected arrays are byte-recomputed against current
sources before plotting. Shared physical intensity scales and all 17 actual
phase markers are retained. Figures are calculated numerical evidence, not
browser screenshots, hardware measurements or a qualified replay claim.
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
from examples.polarized_two_path_interference import compute_demo
from scripts.validate_v2f_interference import PHASES

FILENAMES = ("fig01_ideal_topology_and_outputs.png", "fig02_phase_and_analyzer_fractions.png",
             "fig03_complex_overlap_and_reference.png")
OUTPUT = ROOT / "docs/handoffs/v2f/figures"
BLUE, ORANGE, GREY = "#24648c", "#b95c28", "#555b61"


def load_verified_demo(directory: Path) -> tuple[dict, dict, str]:
    """Require actual demo provenance and exact same-environment array bytes."""
    raw = (directory / "demo.json").read_bytes()
    report = json.loads(raw)
    if report.get("acceptance_passed") is not True or report.get("shape") != [64, 64]:
        raise ValueError("figures require a passed actual 64x64 demo")
    for path, digest in report["environment"]["sources"].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError(f"source changed after demo: {path}")
    example = ROOT / "examples/polarized_two_path_interference.py"
    if hashlib.sha256(example.read_bytes()).hexdigest() != report["demo_source_sha256"]:
        raise ValueError("demo source changed after demo capture")
    if tuple(report["phase_markers_rad"]) != PHASES:
        raise ValueError("all 17 declared phases, including separate endpoints, are required")
    array_file = directory / "demo_arrays.npz"
    if hashlib.sha256(array_file.read_bytes()).hexdigest() != report["demo_arrays_sha256"]:
        raise ValueError("array evidence bytes changed")
    recomputed = compute_demo(n=64, measure=False)
    with np.load(array_file, allow_pickle=False) as stored:
        if set(stored.files) != set(recomputed.arrays):
            raise AssertionError("saved/recomputed array inventory differs")
        saved = {name: stored[name].copy() for name in stored.files}
    for name, actual in recomputed.arrays.items():
        expected = saved[name]
        if actual.shape != expected.shape or actual.dtype != expected.dtype or actual.tobytes() != expected.tobytes():
            raise AssertionError(f"saved/recomputed actual array bytes differ: {name}")
    for current, old in zip(recomputed.report["sweep"], report["sweep"], strict=True):
        for key in ("phase_rad", "case", "norms", "raw_fractions_original_input", "analyzed_norms",
                    "analyzed_fractions_original_input", "removed_norms_at_analyzers", "complex_absolute_errors"):
            if json.loads(json.dumps(current[key])) != old[key]:
                raise AssertionError(f"saved/recomputed diagnostic differs: {key}")
    return report, saved, hashlib.sha256(raw).hexdigest()


def finish(figure: plt.Figure, path: Path, sha: str) -> None:
    # Reserve actual layout space for evidence and explanatory footers; a
    # figure-level text item alone does not keep constrained axes clear.
    figure.get_layout_engine().set(rect=(0., .10, 1., .90))
    figure.text(.012, .012, f"Actual shipped V2f 64x64 demo; JSON SHA-256 {sha}", color=GREY, fontsize=6.5)
    figure.savefig(path, dpi=145, metadata={"Software": "Open Holographic Lab V2f; Matplotlib Agg"})
    plt.close(figure)


def outputs_figure(report: dict, data: dict, path: Path, sha: str) -> None:
    figure = plt.figure(figsize=(15.4, 9.0), layout="constrained")
    figure.suptitle("Ideal unfolded polarized two-path experiment: raw and analyzed outputs", fontsize=16)
    grid = figure.add_gridspec(3, 4, height_ratios=(.8, 3.0, 3.0))
    top = figure.add_subplot(grid[0, :])
    top.axis("off")
    top.text(.5, .77, "Jones input + zero port  →  ideal B  →  two forward arms  →  terminal Jones actions  →  arm-1 phase  →  B†",
             ha="center", fontsize=11, transform=top.transAxes)
    top.text(.5, .25, "Raw outputs precede separate 45° analyzers.  Aligned common basis; ideal polarization-independent splitters; no reflection geometry.",
             ha="center", fontsize=9.5, color=GREY, transform=top.transAxes)
    maximum = float(data["incident_intensity"].max())
    # imshow expects pixel edges. Centers are (index-N//2)*pitch;
    # half-pixel extension preserves the actual physical sample positions.
    ny, nx = report["shape"]
    extent = ((-nx // 2 - .5) * report["grid"]["dx_m"] * 1e6,
              (nx - nx // 2 - .5) * report["grid"]["dx_m"] * 1e6,
              (ny - ny // 2 - .5) * report["grid"]["dy_m"] * 1e6,
              (-ny // 2 - .5) * report["grid"]["dy_m"] * 1e6)
    axes = []
    for row, case in enumerate(("identical", "orthogonal")):
        for col, (kind, port) in enumerate((("raw", 0), ("raw", 1), ("analyzed", 0), ("analyzed", 1))):
            axis = figure.add_subplot(grid[row + 1, col])
            axes.append(axis)
            image = axis.imshow(data[f"{case}_{kind}{port}_intensity"], extent=extent, vmin=0, vmax=maximum,
                                cmap="viridis", interpolation="nearest", origin="upper")
            axis.set(title=f"{case.title()} arms: {kind} port {port}", xlabel="x (µm)", ylabel="y (µm)")
            axis.text(.02, .02, "φ = π/4", transform=axis.transAxes, color="white", fontsize=9)
    figure.colorbar(image, ax=axes, label="Intensity (amplitude-unit²); one shared physical scale", shrink=.75)
    finish(figure, path, sha)


def phase_figure(report: dict, path: Path, sha: str) -> None:
    figure, axes = plt.subplots(2, 3, figsize=(14.4, 8.2), layout="constrained")
    figure.suptitle("All 17 independently computed phase markers; retain raw norm and analyzer loss", fontsize=15)
    for axis, case, kind, title in ((axes[0, 0], "identical", "raw", "Identical arms: raw outputs"),
                                    (axes[0, 1], "orthogonal", "raw", "Orthogonal arms: raw outputs"),
                                    (axes[0, 2], "orthogonal", "analyzed", "Orthogonal arms: 45° analyzers")):
        rows = [r for r in report["sweep"] if r["case"] == case]
        phases = [r["phase_rad"] / math.pi for r in rows]
        for port, color in ((0, BLUE), (1, ORANGE)):
            axis.plot(phases, [r[f"analytic_{kind}_fractions"][port] for r in rows], color=color, linewidth=1.2, alpha=.5)
            axis.scatter(phases, [r[f"{kind}_fractions_original_input"][port] for r in rows], color=color, s=21,
                         label=f"Port {port}: actual markers", zorder=3)
        axis.set(title=title, xlabel="Extra arm-1 phase / π", ylabel="Sampled norm / original input", ylim=(-.045, 1.08), xticks=(0, .5, 1, 1.5, 2))
        axis.grid(alpha=.2)
        axis.legend(fontsize=8)
    orthogonal = [r for r in report["sweep"] if r["case"] == "orthogonal"]
    x = [r["phase_rad"] / math.pi for r in orthogonal]
    axes[1, 0].plot(x, [sum(r["raw_fractions_original_input"]) for r in orthogonal], marker="o", color=BLUE, label="Raw total / input")
    axes[1, 0].plot(x, [sum(r["analyzed_fractions_original_input"]) for r in orthogonal], marker="s", color=ORANGE, label="Analyzed total / input")
    axes[1, 0].plot(x, [sum(r["removed_fractions_original_input"]) for r in orthogonal], marker="x", color=GREY, label="Removed at analyzers / input")
    axes[1, 0].set(title="Separate downstream measurement", xlabel="Extra phase / π", ylabel="Original-input fraction", ylim=(0, 1.12))
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].grid(alpha=.2)
    loss = report["validation"]["lossy_arm"]
    axes[1, 1].plot([r["phase_rad"] / math.pi for r in loss], [r["retained_original_input"] for r in loss], marker="o", color=BLUE, label="Terminal polarizer: retained 5/8")
    axes[1, 1].plot([r["phase_rad"] / math.pi for r in loss], [r["removed_original_input"] for r in loss], marker="s", color=ORANGE, label="Removed 3/8, not normalized away")
    axes[1, 1].set(title="Lossy terminal action retains its budget", xlabel="Extra phase / π", ylabel="Original-input fraction", ylim=(.2, .8))
    axes[1, 1].legend(fontsize=8)
    axes[1, 1].grid(alpha=.2)
    for case, color in (("identical", BLUE), ("orthogonal", ORANGE)):
        rows = [r for r in report["sweep"] if r["case"] == case]
        axes[1, 2].plot([r["phase_rad"] / math.pi for r in rows], [r["norms"]["total_delta"] / report["input_norm"] / 1e-16 for r in rows], marker=".", color=color, label=case.title())
    axes[1, 2].set(title="Signed residuals remain visible", xlabel="Extra phase / π", ylabel="(Raw output − input) / input × 10¹⁶")
    axes[1, 2].axhline(0, color=GREY, linewidth=.6)
    axes[1, 2].legend(fontsize=8)
    axes[1, 2].grid(alpha=.2)
    figure.text(.5, .055, "Lines connect independent references at sampled markers; no fitted visibility or forced bitwise endpoint closure. Residual magnification is display-only.", ha="center", fontsize=8)
    finish(figure, path, sha)


def references_figure(report: dict, path: Path, sha: str) -> None:
    validation = report["validation"]
    figure, axes = plt.subplots(2, 2, figsize=(13.4, 8.7), layout="constrained")
    figure.suptitle("Complete complex phase, independent direct sums and retained weak signals", fontsize=15)
    rows = [r for r in validation["lossless_sweep"] if r["case"] == "D_complex_first_arm" and r["phase_rad"] in PHASES]
    for port, color in ((0, BLUE), (1, ORANGE)):
        axes[0, 0].plot([r["phase_rad"] / math.pi for r in rows], [r["analytic_fractions"][port] for r in rows], color=color, alpha=.5)
        axes[0, 0].scatter([r["phase_rad"] / math.pi for r in rows], [r["actual_fractions"][port] for r in rows], color=color, s=22, label=f"Actual port {port}")
    axes[0, 0].set(title="j₀=(1,i)/√2, j₁=(1,1)/√2; γ=(1−i)/2", xlabel="Extra phase / π", ylabel="Raw norm / input", ylim=(0, 1))
    axes[0, 0].text(.02, .94, "At φ=π/2: (3/4, 1/4); conjugation is essential", transform=axes[0, 0].transAxes, fontsize=9, va="top")
    axes[0, 0].legend(fontsize=8, loc="lower left")
    anchor = validation["complex_first_arm_anchor"]
    observed = np.array(anchor["raw_sample"]).reshape(4, 2)
    expected = np.array(anchor["expected_sample"]).reshape(4, 2)
    positions = np.arange(4)
    axes[0, 1].bar(positions - .2, observed[:, 0], width=.18, color=BLUE, label="Actual real")
    axes[0, 1].bar(positions, observed[:, 1], width=.18, color=ORANGE, label="Actual imaginary")
    axes[0, 1].scatter(positions - .2, expected[:, 0], s=45, facecolors="none", edgecolors="black", zorder=3, label="Literal reference")
    axes[0, 1].scatter(positions, expected[:, 1], s=45, facecolors="none", edgecolors="black", zorder=3)
    axes[0, 1].set(title="Complex hand anchor, no phase fit", ylabel="Component amplitude (a.u.)", xticks=positions, xticklabels=("port0.x", "port0.y", "port1.x", "port1.y"))
    axes[0, 1].legend(fontsize=8)
    dense = validation["complete_direct_sums"]
    axes[1, 0].bar(np.arange(3) - .17, [r["complex"]["max_absolute_over_Ain"] / 1e-16 for r in dense], width=.34, color=BLUE, label="Max complex error / Ain")
    axes[1, 0].bar(np.arange(3) + .17, [r["norm_max_absolute_over_Nin"] / 1e-16 for r in dense], width=.34, color=ORANGE, label="Max norm error / Nin")
    axes[1, 0].set(title="Unequal arms; literal finite-sum reference", ylabel="Measured discrepancy × 10¹⁶ (display only)", xticks=range(3), xticklabels=["×".join(map(str, r["shape"])) for r in dense])
    axes[1, 0].legend(fontsize=8, loc="upper center", bbox_to_anchor=(.5, .87))
    near = validation["selected_near_dark"]
    axes[1, 1].semilogy(range(len(near)), [r["decimal_fraction_at_actual_binary64_phase"] for r in near], color=GREY, marker="o", markerfacecolor="none", markersize=7, label="80-digit actual-angle reference")
    axes[1, 1].scatter(range(len(near)), [r["actual_fraction"] for r in near], color=ORANGE, s=22, zorder=3, label="Actual nonzero dark-port fraction")
    axes[1, 1].set(title="Selected near-dark signals remain represented", xlabel="Declared phase index (actual binary64 angles recorded)", ylabel="Dark-port norm / original input", ylim=(1e-20, 1e-7))
    axes[1, 1].legend(fontsize=8)
    axes[1, 1].text(.5, .58, "Smaller real/imaginary quadrature can round to zero.\nNo universal component-relative accuracy claim.", transform=axes[1, 1].transAxes, ha="center", fontsize=8,
                         bbox={"facecolor": "white", "alpha": .9, "edgecolor": "none"})
    for axis in axes.ravel():
        axis.grid(alpha=.2)
    finish(figure, path, sha)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if set(p.name for p in output.iterdir()) - set(FILENAMES):
        raise ValueError(f"figure destination has unrelated files: {output}")
    report, data, sha = load_verified_demo(args.evidence_dir.resolve())
    outputs_figure(report, data, output / FILENAMES[0], sha)
    phase_figure(report, output / FILENAMES[1], sha)
    references_figure(report, output / FILENAMES[2], sha)
    print(json.dumps({"demo_json_sha256": sha, "selected_arrays_recomputed_byte_identically": True,
                      "figures": {name: {"path": str(output / name), "bytes": (output / name).stat().st_size,
                                         "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest()} for name in FILENAMES}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
