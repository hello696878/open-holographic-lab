"""Exclusive W2/legacy browser acceptance. Importing starts no work or listener.

Each selected discovered test gets one isolated invocation, including every
custom evidence/figure root. No prior recovery launcher is a runtime dependency.
The caller starts and closes only its own verified loopback service separately.
"""
from __future__ import annotations

import argparse
import ctypes
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import runpy
import stat
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "frontend/bench"
NODE = Path(r"C:\Program Files\nodejs\node.exe")
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
PREFIXES = ("R03_", "V1_", "V2B_", "V2D_", "V2E_", "V2G_", "W1_", "W2_", "W3_", "ENGLISH_", "PLAYWRIGHT_")
LEGACY_FILES = ["tests/bench.browser.spec.ts", "tests/two_path.browser.spec.ts",
    "tests/polarization.browser.spec.ts", "tests/polarized_two_path.browser.spec.ts",
    "tests/experiment_documents.browser.spec.ts", "tests/polarized_two_path_documents.browser.spec.ts",
    "tests/r03_fig2a.browser.spec.ts", "tests/r03_fig2a_ux.browser.spec.ts"]


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def browser_version() -> str:
    """Read installed Windows file metadata without launching or changing Chrome."""
    version = ctypes.windll.version
    size = version.GetFileVersionInfoSizeW(str(CHROME), None)
    if not size:
        raise ValueError("Installed Chrome version metadata is unavailable")
    data = ctypes.create_string_buffer(size)
    if not version.GetFileVersionInfoW(str(CHROME), 0, size, data):
        raise ValueError("Could not read installed Chrome metadata")
    pointer, length = ctypes.c_void_p(), ctypes.c_uint()
    if not version.VerQueryValueW(data, "\\", ctypes.byref(pointer), ctypes.byref(length)) or length.value < 52:
        raise ValueError("Invalid installed Chrome version metadata")
    fixed = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint32 * 13)).contents
    return ".".join(str(value) for value in (fixed[2] >> 16, fixed[2] & 65535, fixed[3] >> 16, fixed[3] & 65535))


def dump(path: Path, value: object) -> None:
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def winpath(path: Path) -> str:
    return ntpath.normcase(ntpath.normpath(str(Path(path).resolve())))


def contained(path: Path, parent: Path) -> bool:
    value, owner = winpath(path), winpath(parent)
    try:
        return value != owner and ntpath.commonpath((value, owner)) == owner
    except ValueError:
        return False


def reject_links(path: Path, parent: Path) -> None:
    current = Path(path).absolute()
    while True:
        if current.exists() or current.is_symlink():
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError(f"Linked/reparse output ancestor: {current}")
        if winpath(current) == winpath(parent):
            return
        if current.parent == current:
            raise ValueError(f"Output ancestor escaped ownership: {path}")
        current = current.parent


def validate_outputs(owned_root: Path, outputs: dict[str, Path], *, workspace: Path = ROOT,
                     require_absent: bool = True) -> dict:
    """Reject case aliases, ancestor collisions, links and root escapes before work."""
    parent, owner = workspace.resolve() / "runs", owned_root.resolve()
    if not owned_root.is_absolute() or not contained(owner, parent):
        raise ValueError("Invocation must be a fresh descendant of this workspace's runs")
    reject_links(owner, workspace.resolve())
    normalized: dict[str, str] = {}
    for role, path in outputs.items():
        path = Path(path)
        if not path.is_absolute() or not contained(path, owner):
            raise ValueError(f"Output escaped invocation: {role}={path}")
        reject_links(path, workspace.resolve())
        key = winpath(path)
        for other, previous in normalized.items():
            if key == previous or ntpath.commonpath((key, previous)) in (key, previous):
                raise ValueError(f"Colliding/ancestor output roots: {role}, {other}")
        if require_absent and path.exists():
            raise ValueError(f"Preserve existing output: {role}={path}")
        normalized[role] = key
    return {"status": "PASS", "owned_root": str(owner), "windows_identities": normalized}


def exclusive_bytes(path: Path, data: bytes) -> None:
    """Never replace an earlier screenshot, report, fixture or failure."""
    with path.open("xb") as stream:
        stream.write(data)


def scan_environment(files: list[Path]) -> dict:
    names = sorted({name for file in files for name in re.findall(
        r"process\.env\.([A-Z][A-Z0-9_]+)", file.read_text(encoding="utf-8"))})
    return {"all": names, "outputs": [name for name in names if name.endswith(("_EVIDENCE_DIR", "_FIGURE_DIR"))]}


def child_environment(extra: dict[str, str]) -> dict[str, str]:
    child = os.environ.copy()
    for key in tuple(child):
        if key.startswith(PREFIXES):
            del child[key]
    child.update(extra)
    return child


def extract_cases(report: dict) -> list[dict]:
    result = []
    def visit(suite):
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                result.append({"id": spec["id"], "file": Path(spec["file"]).name,
                    "line": spec["line"], "title": spec["title"], "status": test.get("status"),
                    "attempts": [{"status": item["status"], "retry": item["retry"]}
                                 for item in test.get("results", [])]})
        for child in suite.get("suites", []):
            visit(child)
    for suite in report.get("suites", []):
        visit(suite)
    return result


def source_inventory(assets: Path, files: list[Path], inputs: dict[str, str]) -> dict:
    records = {}
    paths = {ROOT / "scripts/w2_acceptance.py", BENCH / "playwright.config.ts",
             BENCH / "package.json", BENCH / "package-lock.json", NODE, CHROME, *files}
    paths.update(ROOT / "scripts" / name for name in (
        "v2d_controlled_acceptance_server.py", "v2g_controlled_acceptance_server.py",
        "w1_controlled_acceptance_server.py", "w2_controlled_acceptance_server.py",
        "w3_controlled_acceptance_server.py", "w3_acceptance.py"))
    for directory in (ROOT / "src/ohlab", ROOT / "apps/virtual_bench", BENCH / "src", BENCH / "tests/support", assets):
        paths.update(p for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for key, value in inputs.items():
        if key.endswith(("_API_EVIDENCE", "_FIXTURES", "_PARTIAL_EVIDENCE", "_CONTENDER_FIXTURES")):
            path = Path(value).resolve()
            if not path.is_file():
                raise ValueError(f"Missing declared fixture: {key}")
            paths.add(path)
            if key.endswith("_FIXTURES"):
                paths.update(p for p in path.parent.rglob("*") if p.is_file())
    for path in sorted(paths):
        if not path.is_file():
            raise ValueError(f"Missing declared source/environment input: {path}")
        records[str(path.resolve())] = {"sha256": sha(path), "bytes": path.stat().st_size}
    return records


def execute(root: Path, files: list[str], assets: Path, *, inputs: dict[str, str],
            selected: list[dict] | None = None, expected_skips: int = 0,
            controls: dict[str, str] | None = None) -> dict:
    """Run discovery or a predeclared selection once, preserving all outputs."""
    root = root.absolute()
    if root.exists():
        raise ValueError(f"Preserve earlier invocation: {root}")
    paths = [(BENCH / file).resolve() for file in files]
    if not paths or any(not contained(path, BENCH / "tests") or not path.is_file() for path in paths):
        raise ValueError("Specify existing browser test owners under bench/tests")
    reject_links(assets.absolute(), ROOT)
    if not contained(assets, ROOT / "runs") or not (assets / "index.html").is_file():
        raise ValueError("Use verified owned production assets under runs")
    scan = scan_environment(paths)
    outputs = {name: root / ("custom_" + name.lower()) for name in scan["outputs"]}
    outputs.update(runner=root / "runner", reports=root / "reports", temporary=root / "temporary")
    proof = validate_outputs(root, outputs)
    extra = {**inputs, **(controls or {}), **{name: str(outputs[name]) for name in scan["outputs"]}}
    extra["TEMP"] = extra["TMP"] = str(outputs["temporary"])
    extra["PLAYWRIGHT_JSON_OUTPUT_FILE"] = str(outputs["reports"] / "report.json")
    argv = [str(NODE), "node_modules/@playwright/test/cli.js", "test", *files,
            "--workers=1", "--retries=0", "--reporter=list,json", "--output", str(outputs["runner"])]
    if selected is None:
        argv += ["--list"]
    else:
        if len(selected) != 1:
            raise ValueError("Each execution must select exactly one discovered test for exclusive custom outputs")
        argv += ["--grep", "|".join(re.escape(case["title"]) + "$" for case in selected)]
    frozen = source_inventory(assets, paths, {**inputs, **(controls or {})})
    root.mkdir(parents=True, exist_ok=False)
    for role, path in outputs.items():
        if role != "runner":
            path.mkdir(exist_ok=False)
    plan = {"utc": datetime.now(timezone.utc).isoformat(), "argv": argv, "cwd": str(BENCH),
        "selected": selected, "expected_skips": expected_skips, "inputs": inputs, "controls": controls or {},
        "custom_outputs": {key: str(value) for key, value in outputs.items()}, "output_preflight": proof,
        "scan": scan, "identity": frozen, "assets": str(assets), "browser": {"channel": "chrome", "installed_version": browser_version(), "executable_sha256": sha(CHROME)},
        "worker_count": 1, "retries": 0, "timeout_policy": "unchanged existing config/spec overrides",
        "parent_environment_changed": False, "service_owned_by_caller": True}
    dump(root / "plan.json", plan)
    if source_inventory(assets, paths, {**inputs, **(controls or {})}) != frozen:
        raise ValueError("Prepared source/environment identity changed")
    dump(root / "started.json", {"once_only": True})
    start = time.perf_counter()
    with (root / "stdout.txt").open("xb") as stdout, (root / "stderr.txt").open("xb") as stderr:
        process = subprocess.run(argv, cwd=BENCH, env=child_environment(extra), stdout=stdout, stderr=stderr)
    report_path = outputs["reports"] / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    cases = extract_cases(report)
    actual = {(c["id"], c["file"], c["title"]) for c in cases}
    expected = {(c["id"], c["file"], c["title"]) for c in selected or []}
    stats = report.get("stats", {})
    passed = process.returncode == 0 and bool(cases)
    if selected is not None:
        passed &= actual == expected and len(cases) == len(selected)
        passed &= stats.get("unexpected") == stats.get("flaky") == 0 and stats.get("skipped") == expected_skips
        passed &= all(attempt["retry"] == 0 for c in cases for attempt in c["attempts"])
        passed &= all(len(c["attempts"]) == 1 and c["attempts"][0]["status"] in ("passed", "skipped") for c in cases)
    unchanged = source_inventory(assets, paths, {**inputs, **(controls or {})}) == frozen
    passed &= unchanged
    result = {"classification": "DISCOVERY_ONLY" if selected is None else "CURRENT_PASS" if passed else "FAILED",
        "exit_code": process.returncode, "passed": bool(passed), "elapsed_seconds": time.perf_counter() - start,
        "cases": cases, "stats": stats, "coverage_exact": selected is None or actual == expected,
        "identity_unchanged": unchanged}
    dump(root / "result.json", result)
    return result


@contextmanager
def owned_server_lifetime(evidence: Path):
    """A disk-only graceful stop for servers instantiated by this owned child.

    No HTTP control route, process enumeration, unrelated service or parent
    setting is involved. The caller writes stop.flag only after genuine work
    has completed; normal server shutdown still owns executor cleanup.
    """
    import uvicorn
    original = uvicorn.Server
    servers = []
    stopped = threading.Event()
    class OwnedServer(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            servers.append(self)
    def monitor():
        while not stopped.wait(.025):
            if (evidence / "stop.flag").is_file():
                dump(evidence / "shutdown_requested.json", {"pid": os.getpid(), "owned_instances": len(servers),
                    "method": "should_exit on this child's registered Uvicorn instance only"})
                for instance in servers:
                    instance.should_exit = True
                return
    uvicorn.Server = OwnedServer
    watcher = threading.Thread(target=monitor, name="w2-owned-graceful-stop", daemon=True)
    watcher.start()
    try:
        yield
    finally:
        stopped.set(); watcher.join(timeout=2)
        uvicorn.Server = original


def legacy_child(script: Path, assets: Path, arguments: list[str]) -> int:
    """Inject owned built assets into an unchanged, exact tracked legacy child.

    The original scripts and their genuine computation/element counters remain
    authoritative. This helper changes only this child process's asset factory.
    """
    allowed = {ROOT / "scripts/v2d_controlled_acceptance_server.py",
               ROOT / "scripts/v2g_controlled_acceptance_server.py"}
    script = (ROOT / script).absolute() if not script.is_absolute() else script.absolute()
    if script not in allowed or not script.is_file():
        raise ValueError("Only the two unchanged tracked legacy acceptance children are allowed")
    reject_links(assets.absolute(), ROOT)
    if not contained(assets, ROOT / "runs") or not (assets / "index.html").is_file():
        raise ValueError("Legacy child requires fresh verified owned production assets")
    if "--evidence-dir" not in arguments:
        raise ValueError("Legacy child must declare an exclusive evidence destination")
    destination = Path(arguments[arguments.index("--evidence-dir") + 1])
    validate_outputs(destination, {"reserved": destination / "reserved"})
    if destination.exists():
        raise ValueError("Preserve earlier legacy service evidence")
    sys.path.insert(0, str(ROOT))
    from apps.virtual_bench import server
    original = server.create_app
    def owned_factory(*args, **kwargs):
        kwargs["assets_dir"] = assets
        return original(*args, **kwargs)
    previous_argv = sys.argv
    server.create_app = owned_factory
    sys.argv = [str(script), *arguments]
    try:
        with owned_server_lifetime(destination):
            runpy.run_path(str(script), run_name="__main__")
        return 0
    finally:
        server.create_app = original
        sys.argv = previous_argv


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "legacy-child":
        legacy_parser = argparse.ArgumentParser(description="Owned assets for an unchanged tracked legacy control child")
        legacy_parser.add_argument("--script", type=Path, required=True)
        legacy_parser.add_argument("--assets", type=Path, required=True)
        legacy_parser.add_argument("arguments", nargs=argparse.REMAINDER)
        legacy = legacy_parser.parse_args(sys.argv[2:])
        arguments = legacy.arguments[1:] if legacy.arguments[:1] == ["--"] else legacy.arguments
        return legacy_child(legacy.script, legacy.assets.absolute(), arguments)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("discover", "run"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--controls", type=Path)
    parser.add_argument("--expected-skips", type=int, default=0)
    args = parser.parse_args()
    if args.mode == "run" and args.selection is None:
        parser.error("Run requires frozen discovered IDs")
    selected = json.loads(args.selection.read_text(encoding="utf-8")) if args.selection else None
    result = execute(args.root, args.files, args.assets.absolute(),
        inputs=json.loads(args.inputs.read_text(encoding="utf-8")), selected=selected,
        expected_skips=args.expected_skips,
        controls=json.loads(args.controls.read_text(encoding="utf-8")) if args.controls else None)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
