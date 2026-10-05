# V1 implementation summary

Precommit acceptance completed 2026-10-05 (Asia/Taipei). Actual final results
are recorded below; clean-postcommit publication remains a separate later gate.

## Delivered workflow

The interactive virtual bench uses plain TypeScript, Three.js and Vite. One
WebGL2 canvas and ordinary Traditional Chinese DOM panels provide viewing,
selection, ordered component editing, numeric z editing and a constrained z-only
drag rail. A thin Starlette/Uvicorn service serves the production build and API
at `http://127.0.0.1:8510`. Node is used for development/build only.

The Python adapter validates the exact existing V0 experiment schema, then calls
the public `run_experiment` once with `record_fields=()`. There are no copied
optical formulas, JavaScript optics, phase retrieval, intermediate field replay,
new persistence formats or new optical components. The existing Streamlit
application and M0–V0 numerical code/contracts remain protected.

Optical edits perform validation only. Simulation requires an explicit click.
The submitted specification is frozen; client busy is acquired synchronously.
Camera, selection, viewport and display changes do not submit scientific work.
An optical edit immediately detaches the detector texture from the editable
bench. Earlier numerical results stay in a separately labeled panel with their
original specification. Malformed replies cannot publish partial results.
Presentation failures remain separate from numerical completion.

The service retains a computation gate until the actual worker finishes
computation and encoding. Aborting an HTTP request does not cancel the running
Python computation or release the gate. No compute queue or automatic retry is
provided. Reload restores a passive initial preset, without replay or simulation.

## Environment and build

The accepted starting main SHA is
`ce4fe39eee2213dec993e09b25492e01f9d16497`. The interpreter is
`C:\holographiclab\.venv\Scripts\python.exe` (Python 3.11.9). Existing Node
24.15.0/npm 11.17.0 are retained. Starlette 1.7.0/Uvicorn 0.54.0 are already
installed; the bench extra records those versions without reinstalling Python.

Approved exact frontend pins:

| Package | Version | Role |
|---|---|---|
| three | 0.186.1 | Runtime rendering |
| @types/three | 0.186.0 | Development types |
| typescript | 6.0.3 | Development compiler |
| vite | 8.3.2 | Production asset build |
| vitest | 5.0.3 | Unit acceptance |
| @playwright/test | 1.63.0 | Installed-Chrome browser acceptance |
| @types/node | 24.12.0 | Development types |

The reviewed lockfile v3 SHA-256 is
`d04f0937f5593e57c8e290cf812dba70db14dab4fccae4879d3e088c23cd7f91`.
All resolved tarballs come from `https://registry.npmjs.org/` with integrity
entries. The gate reviewed 74 nonroot locked packages and installed the 49
Windows-applicable packages with lifecycle scripts disabled. Optional native
bindings were retained. Script-free Rolldown import and Lightning CSS transform
passed; no native rebuild or browser download occurred.

Build and launch from ordinary Windows/VS Code terminals:

```powershell
Set-Location C:\holographiclab\frontend\bench
& 'C:\Program Files\nodejs\npm.cmd' run --ignore-scripts typecheck
& 'C:\Program Files\nodejs\npm.cmd' run --ignore-scripts test:unit
& 'C:\Program Files\nodejs\npm.cmd' run --ignore-scripts build
Set-Location C:\holographiclab
.\.venv\Scripts\python.exe -B -X utf8 -m apps.virtual_bench.server
```

Open `http://127.0.0.1:8510` in the installed browser. The service requires a
local build and stops if assets are missing or the port is occupied. It does not
install missing tools, choose another port, or manage the pre-existing 8501
service. Ordinary built-page use requires neither npm nor internet.

## Actual initial acceptance

The retained baseline suite passed: **1702 passed, 1 skipped in 160.62s**.
The existing Windows symlink skip remains. Focused state/mapping/transport unit
tests passed **51 tests in three files** after independent review; typecheck
passed. These counts are initial, separate from the final full frontend suite.

The initial production build succeeded in 347 ms: 14 modules, 0.54 kB HTML,
5.59 kB CSS and 627.37 kB JavaScript. The JS size warning is a bundle-size
observation, not a failed build or correctness evidence.

The actual loopback HTTP tool compared ten fixtures with independent direct
public V0 calls and obtained exact original float64 array/axis/stage matches.
Initial lens intensity maximum was `6.1575878701940825`; the 80 µm aperture/lens
case was `1.3783458121954204`, with retained aperture ratio
`0.7220301462596193`. These are dated V1 integration measurements; historical
V0 evidence is not replaced.

## Final precommit outcomes

- Retained full suite: **1802 passed, 1 skipped in 122.14s**; existing Windows skip retained.
- Frontend: typecheck passes; **65 unit tests** pass; final production build 267 ms.
- HTTP: all ten cases have exact complete float64/axes/stage agreement with
  separate public V0 calls and verified served asset/source ownership.
- Production Chrome/WebGL: ten cases pass; the separate actual-browser
  controlled disconnect case also passes. Its normal-production skip is
  documented and is not an unperformed acceptance gate.
- All nine deliberate isolated faults fail their intended assertions;
  production unchanged, followed by complete-suite reruns.
- Five resource cycles retain stable 8 geometries / 8 materials / 1 texture;
  intermediate GPU gray is 128, and asymmetric fixture orientation/picking passes.
- Three genuine screenshots are visually reviewed, with real V0 data.
- Exactly 44 paths; 167 protected tracked files and 52 Python distributions/metadata/
  source locations are unchanged, as is the reviewed lock hash.

The [tests/evidence](tests_and_evidence.md) contain exact outputs, commands,
preserved failures, single-run timing/resource measurements and input-sensitive
boundary explanations. The [limitations](known_limitations.md) remain visible.

One approved commit, clean-source dist rebuild/browser smoke and normal push
follow the final index review. Their outcomes stay in ignored evidence and the
completion report. Only V1 is in scope; later stages have not begun.
