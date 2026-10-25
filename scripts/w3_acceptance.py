"""Exclusive W3 browser acceptance using the existing bounded W2 launcher.

No service/browser starts on import. Discovery precedes an explicit frozen
single-test selection; each invocation owns fresh runner/report/custom outputs.
Required W3 cases permit zero skips, retries and implicit fallback selections.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.w2_acceptance import execute as execute_existing


def validate_selection(selected: object, files: list[str]) -> list[dict]:
    """Require one actual discovered W3 ID, file and exact predeclared title."""
    if type(selected) is not list or len(selected) != 1 or type(selected[0]) is not dict:
        raise ValueError("W3 run requires exactly one frozen discovered case")
    case = selected[0]
    if any(type(case.get(key)) is not str or not case[key] for key in ("id", "file", "title")):
        raise ValueError("W3 selection requires actual discovered id/file/title")
    if Path(case["file"]).name not in {Path(file).name for file in files}:
        raise ValueError("W3 selection file differs from explicit test files")
    if re.match(r"W3-(?:B(?:0[1-9]|1[01])|C0[1-4])\b", case["title"]) is None:
        raise ValueError("W3 selection requires a frozen W3 B01-B11/C01-C04 title")
    return selected


def execute(root: Path, files: list[str], assets: Path, *, inputs: dict[str, str],
            selected: list[dict] | None = None, controls: dict[str, str] | None = None) -> dict:
    """Run one predeclared W3 case, or discover IDs without executing cases.

The caller independently owns the fixed-port listener. Shared launcher verifies
actual IDs, original installed settings, all output namespaces and source hashes.
"""
    if type(inputs) is not dict or any(type(k) is not str or type(v) is not str for k, v in inputs.items()):
        raise TypeError("W3 inputs must be string-to-string child settings")
    if selected is not None:
        validate_selection(selected, files)
    return execute_existing(root, files, assets, inputs=inputs, selected=selected,
                            expected_skips=0, controls=controls)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("discover", "run"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--controls", type=Path)
    args = parser.parse_args()
    if args.mode == "run" and args.selection is None or args.mode == "discover" and args.selection is not None:
        parser.error("Only run takes the required frozen discovered selection")
    selected = json.loads(args.selection.read_text(encoding="utf-8")) if args.selection else None
    controls = json.loads(args.controls.read_text(encoding="utf-8")) if args.controls else None
    result = execute(args.root, args.files, args.assets.absolute(),
        inputs=json.loads(args.inputs.read_text(encoding="utf-8")), selected=selected, controls=controls)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
