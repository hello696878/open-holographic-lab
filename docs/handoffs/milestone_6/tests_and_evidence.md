# Milestone 6 — Tests and reproducible evidence

Recorded **2026-09-29** (Asia/Taipei), from accepted M5 baseline
`a2e7f999d37beb937c7ebff9f13db441cc1ed4ec`. Initial checks found clean,
synchronized `main`, its expected upstream and matching live remote. The
dependency retry rechecked that state before any implementation edits.

This document separates installation metadata, import/API probes, real
controller tests, Streamlit AppTest and actual browser acceptance. Passing
one level does not substitute for another. The bounded precommit browser
sequence and final UI limit-display recheck below passed. Clean-postcommit
UI verification remains a later,
separate publication gate.

Captured files live under ignored `runs/m6_acceptance_20260929/`. Essential
outputs, package sources and negative-control code are embedded below, so
the evidence does not depend solely on that uncommitted directory. Fenced
capture blocks preserve their decoded text and whitespace; Markdown uses LF
line endings rather than the captured Windows CRLF representation. Pytest's
own abbreviations/truncation in failure messages are retained unchanged.

## Accepted automated scope

| Level | Recorded outcome | What it establishes |
|---|---|---|
| Pre-install M5 baseline | 1291 passed, 1 skipped in 20.40s | Accepted suite before the new optional dependencies |
| Post-install unchanged baseline | 1291 passed, 1 skipped in 12.98s | The same suite after the constrained installation, before app implementation |
| Controller/API tests | 68 passed in 2.09s | Real M2–M5 integration, app/state/path policies and saved-data presentation |
| AppTest + architecture | 36 passed in 33.32s | 19 installed-framework tests and 17 import/configuration boundary tests |
| Previous full candidate suite | 1395 passed, 1 skipped in 35.93s | All 1292 baseline cases plus the then-current 104 new M6 cases |
| Focused limit-display refinement | 1 passed in 4.47s | Valid over-limit bundle retains saved metadata, disables replay, and can be replaced by an in-limit load |
| Final full suite after all source/test changes | 1396 passed, 1 skipped in 57.91s | 1292 baseline cases plus 105 M6 cases: 68 controller, 20 AppTest, 17 architecture |
| Five deliberate UI faults | Five intended assertion failures | Each selected safeguard detects its bounded injected fault |
| Actual loopback/browser workflow | Passed, bounded sequence below | Actual uploads, stale drafts, error recovery, queued events, opening and replay; final refinement recheck passed separately |
| Clean-postcommit UI generation/replay | **Deferred to publication gate** | A fresh run must qualify and compare under the final clean revision |

The existing skip remains a real Windows file-symlink test for an account
without the necessary privilege. Its reason is retained in all full-suite
outputs. The separate real-junction check does not turn that skip into a pass.

## Dependency gate and environment

The existing interpreter is `C:\holographiclab\.venv\Scripts\python.exe`.
The resolver recorded CPython 3.11.9 on Windows 10.0.26100, AMD64. Discovery
returned **21 distribution records and 20 unique distributions**; duplicate
records were collapsed only when versions and metadata hashes matched.
The full records were retained. Constraints pinned all twenty existing
versions, including NumPy, SciPy, Pillow, matplotlib, pytest, pip, setuptools
and the existing editable project. No editable rebuild was performed.

### Protected existing versions — exact constraint file

```text
colorama==0.4.6
contourpy==1.3.3
cycler==0.12.1
fonttools==4.63.0
iniconfig==2.3.0
kiwisolver==1.5.0
matplotlib==3.11.1
numpy==2.4.6
ohlab==0.1.0.dev0
packaging==26.3
pillow==12.3.0
pip==26.2.1
pluggy==1.6.0
pygments==2.20.0
pyparsing==3.3.2
pytest==9.1.1
python-dateutil==2.9.0.post0
scipy==1.17.1
setuptools==65.5.0
six==1.17.0
```

### Initial dry-run failure — preserved, no installation

The first wheel-only dry-run could not resolve Streamlit because its inherited
`PIP_NO_INDEX=1` disabled indexes. The work stopped before installing anything
or modifying tracked project files. This was not treated as a compatibility
failure of Streamlit or repaired through a global setting change.

Exact `resolver_dry_run.txt`:

```text
ERROR: Could not find a version that satisfies the requirement streamlit==1.64.0 (from versions: none)
ERROR: No matching distribution found for streamlit==1.64.0
```

Exact stopped-state record:

```json
{
  "outcome": "STOPPED: dependency dry-run failed before installation",
  "cause": "Inherited PIP_NO_INDEX=1 disables package indexes",
  "installed_new_packages": [],
  "existing_distributions_unchanged": 20,
  "tracked_files_byte_identical": 114,
  "working_tree_porcelain": "",
  "resolver_json_produced": false,
  "head": "a2e7f999d37beb937c7ebff9f13db441cc1ed4ec",
  "branch": "main",
  "next_gate": "Explicitly resume with a process-scoped index-enabled constrained dry-run; do not change global settings."
}
```

### Explicitly authorized retry and review

The retry used a child-process copy of the environment with `PIP_NO_INDEX=0`
and explicit `https://pypi.org/simple`, retaining the same wheel-only and
all-existing-version constraints. Effective package-source settings were
checked; no alternate index, find-links source or trust bypass was accepted.
The retry's captured parent value is null, distinct from the earlier failed
invocation's inherited value. The helper did not modify its parent environment.

The resolver JSON was reviewed in full: no existing distribution appeared in
its install set; every wheel matched this interpreter/platform and declared
Python compatibility; every proposed package was reachable through the active
dependencies of Streamlit/Pillow/matplotlib. The exact new set contained 32
distributions. All wheel download URLs used HTTPS at `files.pythonhosted.org`.

Exact retry command/environment record:

```json
{
  "interpreter": "C:\\holographiclab\\.venv\\Scripts\\python.exe",
  "head": "a2e7f999d37beb937c7ebff9f13db441cc1ed4ec",
  "live_remote": "a2e7f999d37beb937c7ebff9f13db441cc1ed4ec",
  "existing_distributions": 20,
  "protected_tracked_files": 114,
  "constraints_sha256": "c9257ef5b1631bdb1aa30e55750485c44de75aefc6034c6ff2d8e41da9ae374e",
  "original_failure_sha256": "bf7170743f395cb31a20f4f33f87e0e94826cc2ae1c69c1becd0b2e4e0a70f51",
  "parent_PIP_NO_INDEX": null,
  "child_PIP_NO_INDEX": "0",
  "index_url": "https://pypi.org/simple",
  "other_source_setting_keys": [],
  "command": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-m",
    "pip",
    "install",
    "--index-url",
    "https://pypi.org/simple",
    "--only-binary=:all:",
    "--dry-run",
    "--constraint",
    "C:\\holographiclab\\runs\\m6_acceptance_20260929\\constraints.txt",
    "--report",
    "C:\\holographiclab\\runs\\m6_acceptance_20260929\\resolver_retry_01.json",
    "streamlit==1.64.0",
    "pillow>=10.0",
    "matplotlib>=3.8"
  ],
  "exit_code": 0,
  "parent_environment_unchanged": true
}
```

The following are historical installation commands/records, not instructions
to rerun the already-completed environment mutation. A later environment
change requires its own scope and gate.

### Exact reviewed new wheels

The table preserves each version, full wheel URL and SHA-256 from the reviewed
resolver result. Installation used these exact version/hash pins and the
twenty constraints. Its pip report was compared against the reviewed
version/URL/hash set afterward.

| Distribution | Version | Wheel source | SHA-256 |
|---|---|---|---|
| `altair` | `6.3.0` | [altair-6.3.0-py3-none-any.whl](https://files.pythonhosted.org/packages/ca/b9/10a8bb13a0462e0bc4e02c0b7b8237dc24ab590f5bb4be94bec5e8f1d532/altair-6.3.0-py3-none-any.whl) | `7defb6ca730676dfc99a299768e2769f51585fcb3dc960ea71aacc368929d65e` |
| `anyio` | `4.15.1` | [anyio-4.15.1-py3-none-any.whl](https://files.pythonhosted.org/packages/12/b8/4bd346e22b28902df4d651910f5242c28d84e4a5c2435ca5c3f797ed7e2e/anyio-4.15.1-py3-none-any.whl) | `6152fdbbf9a77fdec97731721bebf7c4c44f7c29b424b0065826173efc7ed101` |
| `attrs` | `26.1.0` | [attrs-26.1.0-py3-none-any.whl](https://files.pythonhosted.org/packages/64/b4/17d4b0b2a2dc85a6df63d1157e028ed19f90d4cd97c36717afef2bc2f395/attrs-26.1.0-py3-none-any.whl) | `c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309` |
| `certifi` | `2026.7.22` | [certifi-2026.7.22-py3-none-any.whl](https://files.pythonhosted.org/packages/0b/a7/71ac2cff56fec219ed242bb11b8efb69fcc4bec75db06fb7bfe35de520e6/certifi-2026.7.22-py3-none-any.whl) | `62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775` |
| `charset-normalizer` | `3.5.1` | [charset_normalizer-3.5.1-cp311-cp311-win_amd64.whl](https://files.pythonhosted.org/packages/e3/57/32f0ccea59e8612057c61d6fd22ef2cb63cca93c9fe594094919696ac170/charset_normalizer-3.5.1-cp311-cp311-win_amd64.whl) | `f9b1e28d0e8dbfa858abdba91d6b547beaf2df1a59bec6da6faae7b96a4991a9` |
| `click` | `8.5.0` | [click-8.5.0-py3-none-any.whl](https://files.pythonhosted.org/packages/58/50/6c0d534c5f134586a8e1ba4e330569e32f057e33372ae556463212fb4cd3/click-8.5.0-py3-none-any.whl) | `255bc9599cf7748b4b1a446ccc735421bd08a2ae529a8b88597d3de5664ee360` |
| `h11` | `0.16.0` | [h11-0.16.0-py3-none-any.whl](https://files.pythonhosted.org/packages/04/4b/29cac41a4d98d144bf5f6d33995617b185d14b22401f75ca86f384e87ff1/h11-0.16.0-py3-none-any.whl) | `63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86` |
| `httptools` | `0.8.0` | [httptools-0.8.0-cp311-cp311-win_amd64.whl](https://files.pythonhosted.org/packages/cc/94/97b75870dea07b71e3ec535cebe525b08d723152e4c7d13fa887e51f4de2/httptools-0.8.0-cp311-cp311-win_amd64.whl) | `a1b4c8e7a489a0d750d91894e9a8cdc295838f1924c0ca903ae993456fddec07` |
| `idna` | `3.20` | [idna-3.20-py3-none-any.whl](https://files.pythonhosted.org/packages/58/a2/bb081bab032533a855d44de1d56f8e8426114ff1ba5d1f07a438a0a654f8/idna-3.20-py3-none-any.whl) | `ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c` |
| `itsdangerous` | `2.2.0` | [itsdangerous-2.2.0-py3-none-any.whl](https://files.pythonhosted.org/packages/04/96/92447566d16df59b2a776c0fb82dbc4d9e07cd95062562af01e408583fc4/itsdangerous-2.2.0-py3-none-any.whl) | `c6242fc49e35958c8b15141343aa660db5fc54d4f13a1db01a3f5891b98700ef` |
| `jinja2` | `3.1.6` | [jinja2-3.1.6-py3-none-any.whl](https://files.pythonhosted.org/packages/62/a1/3d680cbfd5f4b8f15abc1d571870c5fc3e594bb582bc3b64ea099db13e56/jinja2-3.1.6-py3-none-any.whl) | `85ece4451f492d0c13c5dd7c13a64681a86afae63a5f347908daf103ce6d2f67` |
| `jsonschema` | `4.26.0` | [jsonschema-4.26.0-py3-none-any.whl](https://files.pythonhosted.org/packages/69/90/f63fb5873511e014207a475e2bb4e8b2e570d655b00ac19a9a0ca0a385ee/jsonschema-4.26.0-py3-none-any.whl) | `d489f15263b8d200f8387e64b4c3a75f06629559fb73deb8fdfb525f2dab50ce` |
| `jsonschema-specifications` | `2025.9.1` | [jsonschema_specifications-2025.9.1-py3-none-any.whl](https://files.pythonhosted.org/packages/41/45/1a4ed80516f02155c51f51e8cedb3c1902296743db0bbc66608a0db2814f/jsonschema_specifications-2025.9.1-py3-none-any.whl) | `98802fee3a11ee76ecaca44429fda8a41bff98b00a0f2838151b113f210cc6fe` |
| `markupsafe` | `3.0.3` | [markupsafe-3.0.3-cp311-cp311-win_amd64.whl](https://files.pythonhosted.org/packages/83/8a/4414c03d3f891739326e1783338e48fb49781cc915b2e0ee052aa490d586/markupsafe-3.0.3-cp311-cp311-win_amd64.whl) | `de8a88e63464af587c950061a5e6a67d3632e36df62b986892331d4620a35c01` |
| `narwhals` | `2.26.0` | [narwhals-2.26.0-py3-none-any.whl](https://files.pythonhosted.org/packages/40/b5/1b84b2c784db76d69442334bc8b8748c840f13ca53be086f4f250ad4a0bc/narwhals-2.26.0-py3-none-any.whl) | `29326d74f107c347fd1009bd58e38d9f7c7c5b51e6de97bc93dbc325d9038b54` |
| `pandas` | `3.0.6` | [pandas-3.0.6-cp311-cp311-win_amd64.whl](https://files.pythonhosted.org/packages/d3/dc/d2df02854aec5d47659acfb2be352eecc691845b2f86e99c84f1010a8671/pandas-3.0.6-cp311-cp311-win_amd64.whl) | `2e5fa32ff162dfdbc280157d664f44d23049ae414725af9676df339c501d82cd` |
| `protobuf` | `7.36.2` | [protobuf-7.36.2-cp310-abi3-win_amd64.whl](https://files.pythonhosted.org/packages/8a/55/b77bda4e5e5f5971fb51b07663694690e9afdb9402136c16a522bd621cad/protobuf-7.36.2-cp310-abi3-win_amd64.whl) | `a300819d441e078a5608c0d3c709796bb548136058fda017ae51d425b44fd353` |
| `pyarrow` | `25.0.1` | [pyarrow-25.0.1-cp311-cp311-win_amd64.whl](https://files.pythonhosted.org/packages/8e/1c/5236033550633c9b7377b2a53660b2bbb06cb06dc09c4356332d67643ca1/pyarrow-25.0.1-cp311-cp311-win_amd64.whl) | `62cd0d785b8aa6675ee355f9fc02252a340f4441257c42674937826fd7594325` |
| `pydeck` | `0.9.3` | [pydeck-0.9.3-py2.py3-none-any.whl](https://files.pythonhosted.org/packages/6f/34/3998411437aff304a9ed4fa37a6fe1ef3132bcd2b5eac59851b80c86123c/pydeck-0.9.3-py2.py3-none-any.whl) | `d8a47c11c81fb12d51b1feb42427ff4f0e13cb599e48931021b2cba98b6849a6` |
| `python-multipart` | `0.0.32` | [python_multipart-0.0.32-py3-none-any.whl](https://files.pythonhosted.org/packages/e1/04/e8135ebd1ad02c56ec633277529b2602ff99ff634be76cdba5744cf554fd/python_multipart-0.0.32-py3-none-any.whl) | `ff6d3f776f16878c894e52e107296ffc890e913c611b1a4ec6c44e2821fe2e23` |
| `referencing` | `0.37.0` | [referencing-0.37.0-py3-none-any.whl](https://files.pythonhosted.org/packages/2c/58/ca301544e1fa93ed4f80d724bf5b194f6e4b945841c5bfd555878eea9fcb/referencing-0.37.0-py3-none-any.whl) | `381329a9f99628c9069361716891d34ad94af76e461dcb0335825aecc7692231` |
| `requests` | `2.34.2` | [requests-2.34.2-py3-none-any.whl](https://files.pythonhosted.org/packages/a0/f4/c67b0b3f1b9245e8d266f0f112c500d50e5b4e83cb6f3b71b6528104182a/requests-2.34.2-py3-none-any.whl) | `2a0d60c172f83ac6ab31e4554906c0f3b3588d37b5cb939b1c061f4907e278e0` |
| `rpds-py` | `2026.6.3` | [rpds_py-2026.6.3-cp311-cp311-win_amd64.whl](https://files.pythonhosted.org/packages/f2/b7/b7a1695d7af36f521fb11e80d6d3adbd744f73b921859bd3c2a2c0dc706f/rpds_py-2026.6.3-cp311-cp311-win_amd64.whl) | `2c54a076ca4d370980ab57bc0e31df57bbe8d41340436a90ef8b1219a3cbb127` |
| `starlette` | `1.7.0` | [starlette-1.7.0-py3-none-any.whl](https://files.pythonhosted.org/packages/4e/d6/1ec1b290f9e0fb067899b61e1d37a30c923068bad260b216dbe37a7d2967/starlette-1.7.0-py3-none-any.whl) | `67f8e99895493dd2911a03f11314af6ceebeae4e704bb9f43dfc6a9db151c93e` |
| `streamlit` | `1.64.0` | [streamlit-1.64.0-py3-none-any.whl](https://files.pythonhosted.org/packages/d7/8e/e635448a7fd6d92211d4ff2150356b8dffd3fcdc05c00511c61110078871/streamlit-1.64.0-py3-none-any.whl) | `4daf63aa9eaa5452d0edc64a5bdb0c4ad25580fe3c62c270455f3c43e9db5098` |
| `toml` | `0.10.2` | [toml-0.10.2-py2.py3-none-any.whl](https://files.pythonhosted.org/packages/44/6f/7120676b6d73228c96e17f1f794d8ab046fc910d781c8d151120c3f1569e/toml-0.10.2-py2.py3-none-any.whl) | `806143ae5bfb6a3c6e736a764057db0e6a0e05e338b5630894a5f779cabb4f9b` |
| `typing-extensions` | `4.16.0` | [typing_extensions-4.16.0-py3-none-any.whl](https://files.pythonhosted.org/packages/49/d3/b8441a820a491ddfc024b0b0cf0393375b75ea13866d9c66727e54c2fc80/typing_extensions-4.16.0-py3-none-any.whl) | `481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8` |
| `tzdata` | `2026.4` | [tzdata-2026.4-py2.py3-none-any.whl](https://files.pythonhosted.org/packages/f9/bc/8737e8d54cf51106118039b83f485a4783112fab49ea9d044b234978a46e/tzdata-2026.4-py2.py3-none-any.whl) | `c2169a8b0a7a5e9674da5a135ccdfb2b3e671b333ed9fed17b41f73c34476e81` |
| `urllib3` | `2.8.0` | [urllib3-2.8.0-py3-none-any.whl](https://files.pythonhosted.org/packages/92/9d/c4e665119135114480843e7ab388fa94d8480650450e6f8e26b70d323a4c/urllib3-2.8.0-py3-none-any.whl) | `0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3` |
| `uvicorn` | `0.54.0` | [uvicorn-0.54.0-py3-none-any.whl](https://files.pythonhosted.org/packages/38/0c/b54a4fdd7f90a3af8b02ebc9ce6712c2c208b7926a2f7bad95c33ebbe943/uvicorn-0.54.0-py3-none-any.whl) | `505bdb0f318731d45f1f712071fc781a8981f6847a31c902c9f5e652d4f67faf` |
| `watchdog` | `6.0.0` | [watchdog-6.0.0-py3-none-win_amd64.whl](https://files.pythonhosted.org/packages/db/d9/c495884c6e548fce18a8f40568ff120bc3a4b7b99813081c8ac0c936fa64/watchdog-6.0.0-py3-none-win_amd64.whl) | `cbafb470cf848d93b5d013e2ecb245d4aa1c8fd0504e863ccefa32445359d680` |
| `websockets` | `16.1.1` | [websockets-16.1.1-cp311-cp311-win_amd64.whl](https://files.pythonhosted.org/packages/71/b2/e511c1c6f64a95c2f3fc54bffda0e14eaa7e9442be605c29270f7589b918/websockets-16.1.1-cp311-cp311-win_amd64.whl) | `7421fad442de870a8cbf2287d1cad7e706ece0dbfeba5e911df132cbdc1cb56a` |

Exact hash-pinned requirement file used for installation:

```text
altair==6.3.0 --hash=sha256:7defb6ca730676dfc99a299768e2769f51585fcb3dc960ea71aacc368929d65e
anyio==4.15.1 --hash=sha256:6152fdbbf9a77fdec97731721bebf7c4c44f7c29b424b0065826173efc7ed101
attrs==26.1.0 --hash=sha256:c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309
certifi==2026.7.22 --hash=sha256:62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775
charset-normalizer==3.5.1 --hash=sha256:f9b1e28d0e8dbfa858abdba91d6b547beaf2df1a59bec6da6faae7b96a4991a9
click==8.5.0 --hash=sha256:255bc9599cf7748b4b1a446ccc735421bd08a2ae529a8b88597d3de5664ee360
h11==0.16.0 --hash=sha256:63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86
httptools==0.8.0 --hash=sha256:a1b4c8e7a489a0d750d91894e9a8cdc295838f1924c0ca903ae993456fddec07
idna==3.20 --hash=sha256:ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c
itsdangerous==2.2.0 --hash=sha256:c6242fc49e35958c8b15141343aa660db5fc54d4f13a1db01a3f5891b98700ef
jinja2==3.1.6 --hash=sha256:85ece4451f492d0c13c5dd7c13a64681a86afae63a5f347908daf103ce6d2f67
jsonschema==4.26.0 --hash=sha256:d489f15263b8d200f8387e64b4c3a75f06629559fb73deb8fdfb525f2dab50ce
jsonschema-specifications==2025.9.1 --hash=sha256:98802fee3a11ee76ecaca44429fda8a41bff98b00a0f2838151b113f210cc6fe
markupsafe==3.0.3 --hash=sha256:de8a88e63464af587c950061a5e6a67d3632e36df62b986892331d4620a35c01
narwhals==2.26.0 --hash=sha256:29326d74f107c347fd1009bd58e38d9f7c7c5b51e6de97bc93dbc325d9038b54
pandas==3.0.6 --hash=sha256:2e5fa32ff162dfdbc280157d664f44d23049ae414725af9676df339c501d82cd
protobuf==7.36.2 --hash=sha256:a300819d441e078a5608c0d3c709796bb548136058fda017ae51d425b44fd353
pyarrow==25.0.1 --hash=sha256:62cd0d785b8aa6675ee355f9fc02252a340f4441257c42674937826fd7594325
pydeck==0.9.3 --hash=sha256:d8a47c11c81fb12d51b1feb42427ff4f0e13cb599e48931021b2cba98b6849a6
python-multipart==0.0.32 --hash=sha256:ff6d3f776f16878c894e52e107296ffc890e913c611b1a4ec6c44e2821fe2e23
referencing==0.37.0 --hash=sha256:381329a9f99628c9069361716891d34ad94af76e461dcb0335825aecc7692231
requests==2.34.2 --hash=sha256:2a0d60c172f83ac6ab31e4554906c0f3b3588d37b5cb939b1c061f4907e278e0
rpds-py==2026.6.3 --hash=sha256:2c54a076ca4d370980ab57bc0e31df57bbe8d41340436a90ef8b1219a3cbb127
starlette==1.7.0 --hash=sha256:67f8e99895493dd2911a03f11314af6ceebeae4e704bb9f43dfc6a9db151c93e
streamlit==1.64.0 --hash=sha256:4daf63aa9eaa5452d0edc64a5bdb0c4ad25580fe3c62c270455f3c43e9db5098
toml==0.10.2 --hash=sha256:806143ae5bfb6a3c6e736a764057db0e6a0e05e338b5630894a5f779cabb4f9b
typing-extensions==4.16.0 --hash=sha256:481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8
tzdata==2026.4 --hash=sha256:c2169a8b0a7a5e9674da5a135ccdfb2b3e671b333ed9fed17b41f73c34476e81
urllib3==2.8.0 --hash=sha256:0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3
uvicorn==0.54.0 --hash=sha256:505bdb0f318731d45f1f712071fc781a8981f6847a31c902c9f5e652d4f67faf
watchdog==6.0.0 --hash=sha256:cbafb470cf848d93b5d013e2ecb245d4aa1c8fd0504e863ccefa32445359d680
websockets==16.1.1 --hash=sha256:7421fad442de870a8cbf2287d1cad7e706ece0dbfeba5e911df132cbdc1cb56a
```

Exact installation verification, including the pip command:

```json
{
  "command": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-m",
    "pip",
    "install",
    "--index-url",
    "https://pypi.org/simple",
    "--only-binary=:all:",
    "--constraint",
    "C:\\holographiclab\\runs\\m6_acceptance_20260929\\constraints.txt",
    "--require-hashes",
    "--requirement",
    "C:\\holographiclab\\runs\\m6_acceptance_20260929\\reviewed_new_packages.txt",
    "--report",
    "C:\\holographiclab\\runs\\m6_acceptance_20260929\\install_retry_01.json"
  ],
  "exit_code": 0,
  "parent_PIP_NO_INDEX": null,
  "child_PIP_NO_INDEX": "0",
  "parent_environment_unchanged": true,
  "existing_versions_and_metadata_unchanged": true,
  "new_packages": {
    "altair": "6.3.0",
    "anyio": "4.15.1",
    "attrs": "26.1.0",
    "certifi": "2026.7.22",
    "charset-normalizer": "3.5.1",
    "click": "8.5.0",
    "h11": "0.16.0",
    "httptools": "0.8.0",
    "idna": "3.20",
    "itsdangerous": "2.2.0",
    "jinja2": "3.1.6",
    "jsonschema": "4.26.0",
    "jsonschema-specifications": "2025.9.1",
    "markupsafe": "3.0.3",
    "narwhals": "2.26.0",
    "pandas": "3.0.6",
    "protobuf": "7.36.2",
    "pyarrow": "25.0.1",
    "pydeck": "0.9.3",
    "python-multipart": "0.0.32",
    "referencing": "0.37.0",
    "requests": "2.34.2",
    "rpds-py": "2026.6.3",
    "starlette": "1.7.0",
    "streamlit": "1.64.0",
    "toml": "0.10.2",
    "typing-extensions": "4.16.0",
    "tzdata": "2026.4",
    "urllib3": "2.8.0",
    "uvicorn": "0.54.0",
    "watchdog": "6.0.0",
    "websockets": "16.1.1"
  },
  "exact_reviewed_set_installed": true
}
```

Before/after inventory comparison found every protected distribution's
version, metadata digest and recorded location unchanged; exactly the 32
reviewed names were new. Resolver compatibility, actual installation and
runtime behavior remain distinct evidence.

### Pip check and actual import/API probes

```powershell
.\.venv\Scripts\python.exe -B -m pip check
```

```text
No broken requirements found.
```

The import probe loaded the numerical packages and every newly added import
root and confirmed the actual `ohlab` source location. Exact output:

```text
IMPORT OK numpy
IMPORT OK scipy
IMPORT OK PIL
IMPORT OK matplotlib
IMPORT OK streamlit
IMPORT OK pyarrow
IMPORT OK pandas
IMPORT OK altair
IMPORT OK anyio
IMPORT OK attrs
IMPORT OK certifi
IMPORT OK charset_normalizer
IMPORT OK click
IMPORT OK h11
IMPORT OK httptools
IMPORT OK idna
IMPORT OK itsdangerous
IMPORT OK jinja2
IMPORT OK jsonschema
IMPORT OK jsonschema_specifications
IMPORT OK markupsafe
IMPORT OK narwhals
IMPORT OK google.protobuf
IMPORT OK pydeck
IMPORT OK python_multipart
IMPORT OK referencing
IMPORT OK requests
IMPORT OK rpds
IMPORT OK starlette
IMPORT OK toml
IMPORT OK typing_extensions
IMPORT OK tzdata
IMPORT OK urllib3
IMPORT OK uvicorn
IMPORT OK watchdog
IMPORT OK websockets
ohlab source: C:\holographiclab\src\ohlab\__init__.py
AppTest.from_string (script: 'str', *, default_timeout: 'float' = 3) -> 'AppTest'
FileUploader.upload (self, filename: 'str', content: 'bytes', mime_type: 'str' = 'application/octet-stream') -> 'Self'
Upload a single file for testing.

Parameters
----------
filename
    The name of the file.
content
    The file content as bytes.
mime_type
    The MIME type of the file. Defaults to "application/octet-stream".

Returns
-------
FileUploader
    The FileUploader instance for method chaining.
FileUploader.set_value (self, files: 'tuple[str, bytes, str] | Sequence[tuple[str, bytes, str]] | None') -> 'Self'
Set the uploaded file(s) for testing.

Parameters
----------
files
    A tuple of (filename, content, mime_type) for single file upload,
    or a sequence of such tuples for multiple file upload.
    Set to ``None`` to clear uploaded files.

Returns
-------
FileUploader
    The FileUploader instance for method chaining.
FileUploader.clear (self) -> 'Self'
Clear all uploaded files.

Returns
-------
FileUploader
    The FileUploader instance for method chaining.
Installed Streamlit: 1.64.0
```

The installed-version probe actually exercised `FileUploader.upload`,
`set_value` and `clear` with PNG bytes, then inspected the UI signatures and
supported configuration keys. The `SUPPORTED CONFIG` lines below are default
values at that probe stage; they are not the later server's effective values.
The bare-mode Streamlit log warning is preserved; no global warning filter
was added to conceal it.

```text
2026-09-29 22:06:21.189 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
AppTest FileUploader.upload: PASSED (actual PNG bytes/name retained)
AppTest FileUploader.set_value: PASSED
AppTest FileUploader.clear: PASSED
st.button(label: 'str', key: 'Key | None' = None, help: 'str | None' = None, on_click: 'WidgetCallback | None' = None, args: 'WidgetArgs | None' = None, kwargs: 'WidgetKwargs | None' = None, *, type: "Literal['primary', 'secondary', 'tertiary']" = 'secondary', icon: 'str | None' = None, icon_position: 'IconPosition' = 'left', disabled: 'bool' = False, use_container_width: 'bool | None' = None, width: 'Width' = 'content', shortcut: 'str | None' = None, wrap: 'bool | None' = None) -> 'bool'
st.file_uploader(label: 'str', type: 'str | Sequence[str] | None' = None, accept_multiple_files: 'AcceptMultipleFiles' = False, key: 'Key | None' = None, help: 'str | None' = None, on_change: 'WidgetCallback | None' = None, args: 'WidgetArgs | None' = None, kwargs: 'WidgetKwargs | None' = None, *, max_upload_size: 'int | None' = None, disabled: 'bool' = False, label_visibility: 'LabelVisibility' = 'visible', width: 'WidthWithoutContent' = 'stretch') -> 'UploadedFile | list[UploadedFile] | None'
st.pyplot(fig: 'Figure', clear_figure: 'bool' = False, *, width: 'Width' = 'stretch', use_container_width: 'bool | None' = None, **kwargs: 'Any') -> 'DeltaGenerator'
st.json(body: 'object', *, expanded: 'bool | int' = True, width: 'WidthWithoutContent' = 'stretch') -> 'DeltaGenerator'
st.number_input(label: 'str', min_value: 'Number | None' = None, max_value: 'Number | None' = None, value: "Number | Literal['min'] | None" = 'min', step: 'Number | None' = None, format: 'str | None' = None, key: 'Key | None' = None, help: 'str | None' = None, on_change: 'WidgetCallback | OnChangeMode | None' = 'rerun', args: 'WidgetArgs | None' = None, kwargs: 'WidgetKwargs | None' = None, *, placeholder: 'str | None' = None, disabled: 'bool' = False, label_visibility: 'LabelVisibility' = 'visible', icon: 'str | None' = None, width: 'WidthWithoutContent' = 'stretch', bind: 'BindOption' = None, persist_state: 'PersistStateOption' = None) -> 'Number | None'
SUPPORTED CONFIG runner.fastReruns True
SUPPORTED CONFIG server.fileWatcherType 'auto'
SUPPORTED CONFIG server.runOnSave False
SUPPORTED CONFIG server.address None
SUPPORTED CONFIG server.port 8501
SUPPORTED CONFIG server.headless False
SUPPORTED CONFIG server.enableCORS True
SUPPORTED CONFIG server.enableXsrfProtection True
SUPPORTED CONFIG browser.gatherUsageStats True
SUPPORTED CONFIG server.maxUploadSize 200
```

## Test contracts and numerical scope

The three new test files exercise app behavior; all existing tests and
scientific thresholds remain unchanged. There is no new M6 optical tolerance.
Important app properties are exact: immutable submitted settings/input bytes,
one accepted save call, consumed stale tokens, unchanged saved-array bytes,
same display bounds, complete `N+1` samples and precise M5 report values.

Controller fixtures use real public M2–M5 calls. They cover fixed built-in
samples when pitch changes, exact uploaded PNG capture, seed-only creation,
unit conversion, nonblank positive-power requirements, file/resource limits,
safe path membership and link/reparse rejection. Existing-run fixtures cover
explicit-phase initialization, actual nonuniform source amplitude, all five
saved metric types and masks, PSNR parameters and separate verification states.
Tests distinguish synthetic caller-source metadata used to exercise policy
from actual Git provenance/attestation.

Failures before publication consume the operation and cannot inherit an older
success. Save exceptions/interruption do not cause automatic retry. Separate
post-publication plot and owned-temporary-cleanup failures retain the completed
bundle/path/submitted identity. An explicit load/refresh recovers the result.
Replay errors after a preliminary successful load clear that operation's
success badges. Imported-package provenance tests cover unrelated working
directories, invalid/unavailable metadata and changed source state.

Presentation checks inspect the actual Figure objects: target/reconstruction
share a range reaching 1.8 in the overshoot fixture, phase limits are exactly
`(-pi,+pi)` as the two display endpoints, and N=0 as well as longer histories
retain every saved sample. Inputs are not mutated. Saved metric values are
formatted without recomputation; positive-infinite PSNR remains explicit.

AppTest exercises ordinary reruns, changed drafts, same-name/same-size upload
replacement, resource/input errors, disabled/busy controls, old rendered
callbacks, explicit load/replay actions and post-save display recovery. It
does not establish native file-picker behavior, browser event timing or
visual layout. Architecture cases exercise the missing-Streamlit path in
isolation without uninstalling packages and check core/controller independence,
entrypoint import resolution and effective configuration. Missing-framework
skips are not counted as successful installed UI acceptance.

## Exact pytest commands and outputs

Commands ran from `C:\holographiclab`; each `--basetemp` was a dedicated
ignored directory containing task-generated data only. The pre-install
command used `-B` without `-X utf8`; later recorded commands explicitly select
UTF-8. Outputs below are copied from their captured files, not reconstructed
from the summary counts.

### Pre-install accepted baseline — exit 0

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp=runs/m6_acceptance_20260929/pytest_before
```

```text
........................................................................ [  5%]
........................................................................ [ 11%]
........................................................................ [ 16%]
........................................................................ [ 22%]
........................................................................ [ 27%]
........................................................................ [ 33%]
........................................................................ [ 39%]
........................................................................ [ 44%]
........................................................................ [ 50%]
........................................................................ [ 55%]
........................................................................ [ 61%]
........................................................................ [ 66%]
..................................................................s..... [ 72%]
........................................................................ [ 78%]
........................................................................ [ 83%]
........................................................................ [ 89%]
........................................................................ [ 94%]
....................................................................     [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1291 passed, 1 skipped in 20.40s
```

### Post-install unchanged baseline — exit 0

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp=runs/m6_acceptance_20260929/pytest_after_install
```

```text
........................................................................ [  5%]
........................................................................ [ 11%]
........................................................................ [ 16%]
........................................................................ [ 22%]
........................................................................ [ 27%]
........................................................................ [ 33%]
........................................................................ [ 39%]
........................................................................ [ 44%]
........................................................................ [ 50%]
........................................................................ [ 55%]
........................................................................ [ 61%]
........................................................................ [ 66%]
..................................................................s..... [ 72%]
........................................................................ [ 78%]
........................................................................ [ 83%]
........................................................................ [ 89%]
........................................................................ [ 94%]
....................................................................     [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1291 passed, 1 skipped in 12.98s
```

### Controller after final SI-conversion guard — exit 0

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/test_workbench_controller.py -q -p no:cacheprovider --basetemp runs/m6_acceptance_20260929/pytest_controller_conversion_d054b2
```

```text
....................................................................     [100%]
68 passed in 2.09s
```

### Installed AppTest and architecture — exit 0

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/test_workbench_streamlit.py tests/test_workbench_architecture.py -q -p no:cacheprovider --basetemp .pytest_cache/m6-ui-agent-20260929-02
```

```text
....................................                                     [100%]
36 passed in 33.32s
```

### Previous complete candidate suite — exit 0

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp=runs/m6_acceptance_20260929/pytest_final_01
```

```text
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 20%]
........................................................................ [ 25%]
........................................................................ [ 30%]
........................................................................ [ 36%]
........................................................................ [ 41%]
........................................................................ [ 46%]
........................................................................ [ 51%]
........................................................................ [ 56%]
........................................................................ [ 61%]
..................................................................s..... [ 67%]
........................................................................ [ 72%]
........................................................................ [ 77%]
........................................................................ [ 82%]
........................................................................ [ 87%]
........................................................................ [ 92%]
........................................................................ [ 97%]
............................                                             [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1395 passed, 1 skipped in 35.93s
```

### Final limit-display refinement and complete suite — exit 0

Final review found that the controller correctly rejected replay above app
limits but the UI still presented enabled replay buttons. The bounded fix
now disables both replay controls for that loaded bundle and retains cheap
saved configuration/provenance. The new AppTest loads a real valid 1 × 513
M5 bundle, verifies disabled controls and metadata, then opens an in-limit
bundle and checks recovery. This is an app presentation/work-policy change;
it does not change the M5 schema or numerical domain.

Exact focused command and output:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/test_workbench_streamlit.py::test_over_limit_valid_bundle_keeps_metadata_disables_replay_and_open_recovers -q -p no:cacheprovider --basetemp .pytest_cache/m6-ui-overlimit-20260929-01 2>&1 | Tee-Object -FilePath runs/m6_acceptance_20260929/apptest-overlimit-output.txt
```

```text
.                                                                        [100%]
1 passed in 4.47s
```

The final complete suite includes that twentieth AppTest and all preceding
source/test changes. The previous 1395-pass output above remains its own
historical run, rather than being relabelled as this result.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp=runs/m6_acceptance_20260929/pytest_final_02
```

```text
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 20%]
........................................................................ [ 25%]
........................................................................ [ 30%]
........................................................................ [ 36%]
........................................................................ [ 41%]
........................................................................ [ 46%]
........................................................................ [ 51%]
........................................................................ [ 56%]
........................................................................ [ 61%]
..................................................................s..... [ 67%]
........................................................................ [ 72%]
........................................................................ [ 77%]
........................................................................ [ 82%]
........................................................................ [ 87%]
........................................................................ [ 92%]
........................................................................ [ 97%]
.............................                                            [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1396 passed, 1 skipped in 57.91s
```

## Deliberate negative controls

Five separate child processes introduced app-only in-memory faults. The
tracked source/test files were never edited by the controls. Each selected
test produced exactly one intended assertion failure and no setup/collection
failure in the accepted run. The failures below are desired evidence that
the safeguards can detect the injected faults; they are not production-suite
failures.

| Fault | Detecting assertion |
|---|---|
| Repeat the accepted save | Save-call count became 2 instead of 1 |
| Accept a consumed old nonce | A stale callback produced a second save |
| Relabel saved data with draft settings | Rendered saved configuration differed after draft edits |
| Silently make strict replay diagnostic | The actual diagnostic argument became true |
| Swallow an operation error | The required error record was missing |

All 41 `src/`, `apps/` and `tests/` Python-file hashes matched before/after
each accepted child and across the entire control window. The before/after
JSON inventories were equal; their common file SHA-256 was
`e1e01e37105a93dca52ecc9b51036c4940d1aea375c79ff650872605312202c9`.
Restoration consisted of discarding each child process and its memory-only
patches. No unrelated work was restored or overwritten.

The final SI-conversion guard and four additional controller cases followed
that control window. They reject a nonzero signed distance that would round
to zero metres while preserving genuine signed-zero input. Consequently,
`apps/workbench.py` and `tests/test_workbench_controller.py` differ from the
historical control inventory. The 68-case controller run and final complete
suite above include that change. The control hashes are not represented as
hashes of the later final source, and those controls are not a general proof
that every possible app defect is detectable.

### Excluded initial harness failure

The first stale-label control imported UI/AnyIO before pytest could register
its plugin for assertion rewriting. It failed during pytest configuration,
not at the intended test assertion, and is **excluded** from the five accepted
detections. The initial driver/output remain preserved. The corrected driver
performs mutation from `pytest_configure`, after plugin registration, without
disabling plugin autoload or relaxing warning filters. Exact excluded output:

```text
PYTEST_ARGS ["tests/test_workbench_streamlit.py::test_submitted_result_keeps_saved_settings_after_draft_changes", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m6-ui-negative-stale_result_labels"]
Traceback (most recent call last):
  File "C:\holographiclab\runs\m6_acceptance_20260929\negative_controls_ui.py", line 136, in <module>
    raise SystemExit(child(sys.argv[2]) if len(sys.argv) > 1 and sys.argv[1] == "--child" else parent())
                     ^^^^^^^^^^^^^^^^^^
  File "C:\holographiclab\runs\m6_acceptance_20260929\negative_controls_ui.py", line 88, in child
    code = int(pytest.main(command, plugins=[Outcomes()]))
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\holographiclab\.venv\Lib\site-packages\_pytest\config\__init__.py", line 201, in main
    return _main(args=args, plugins=plugins, prog="pytest.main()")
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\holographiclab\.venv\Lib\site-packages\_pytest\config\__init__.py", line 223, in _main
    config = _prepareconfig(new_args, plugins, prog=prog)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\holographiclab\.venv\Lib\site-packages\_pytest\config\__init__.py", line 410, in _prepareconfig
    config: Config = pluginmanager.hook.pytest_cmdline_parse(
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\holographiclab\.venv\Lib\site-packages\pluggy\_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\holographiclab\.venv\Lib\site-packages\pluggy\_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\holographiclab\.venv\Lib\site-packages\pluggy\_callers.py", line 167, in _multicall
    raise exception
  File "C:\holographiclab\.venv\Lib\site-packages\pluggy\_callers.py", line 139, in _multicall
    teardown.throw(exception)
  File "C:\holographiclab\.venv\Lib\site-packages\_pytest\helpconfig.py", line 124, in pytest_cmdline_parse
    config = yield
             ^^^^^
  File "C:\holographiclab\.venv\Lib\site-packages\pluggy\_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
          ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\holographiclab\.venv\Lib\site-packages\_pytest\config\__init__.py", line 1232, in pytest_cmdline_parse
    self.parse(args)
  File "C:\holographiclab\.venv\Lib\site-packages\_pytest\config\__init__.py", line 1574, in parse
    self._consider_importhook()
  File "C:\holographiclab\.venv\Lib\site-packages\_pytest\config\__init__.py", line 1345, in _consider_importhook
    self._mark_plugins_for_rewrite(hook, disable_autoload)
  File "C:\holographiclab\.venv\Lib\site-packages\_pytest\config\__init__.py", line 1369, in _mark_plugins_for_rewrite
    hook.mark_rewrite(name)
  File "C:\holographiclab\.venv\Lib\site-packages\_pytest\assertion\rewrite.py", line 277, in mark_rewrite
    self._warn_already_imported(name)
  File "C:\holographiclab\.venv\Lib\site-packages\_pytest\assertion\rewrite.py", line 284, in _warn_already_imported
    self.config.issue_config_time_warning(
  File "C:\holographiclab\.venv\Lib\site-packages\_pytest\config\__init__.py", line 1654, in issue_config_time_warning
    warnings.warn(warning, stacklevel=stacklevel)
pytest.PytestAssertRewriteWarning: Module already imported so cannot be rewritten; anyio
```

### Exact accepted driver

For later reproduction, copy this driver into a new dedicated directory
directly under `runs/`, with the same filename. Its root calculation relies
on that depth. Keep the original capture directory unchanged; the driver
writes its own transcripts/inventories in its containing directory. Its
pytest base directories are dedicated test data, never user data.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 runs\m6_acceptance_20260929\negative_controls_ui.py
```

The command above identifies the original accepted run. Exact driver:

```python
"""Isolated M6 deliberate faults; no tracked source file is edited."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

CASES = {
    "duplicate_save": "test_one_generate_action_saves_exactly_once_and_reruns_do_not_repeat",
    "stale_nonce": "test_old_rendered_nonce_callback_after_completion_cannot_start_another_save",
    "stale_result_labels": "test_submitted_result_keeps_saved_settings_after_draft_changes",
    "silent_diagnostic": "test_strict_replay_never_silently_enables_diagnostics",
    "swallowed_failure": "test_save_failure_is_visible_and_does_not_claim_or_retry_success",
}


def inventory():
    paths = sorted({*ROOT.glob("src/**/*.py"), *ROOT.glob("apps/**/*.py"), *ROOT.glob("tests/**/*.py")})
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def mutate(name):
    from apps import workbench as wb
    if name == "duplicate_save":
        original = wb.execute_pending_run
        def duplicate(state):
            submitted = state.pending
            result = original(state)
            if submitted is not None:
                state.pending = submitted
                original(state)
            return result
        wb.execute_pending_run = duplicate
    elif name == "stale_nonce":
        def accepts_old_nonce(state, offered_nonce):
            return not state.busy and state.pending is None
        wb._available = accepts_old_nonce
    elif name == "stale_result_labels":
        from types import SimpleNamespace
        from apps import streamlit_app as ui
        original = ui._render_result
        def relabel(state, draft):
            saved = state.bundle
            if saved is None or state.submitted is None:
                return original(state, draft)
            state.bundle = SimpleNamespace(
                arrays=saved.arrays, config=wb._draft_config(draft),
                metrics=saved.metrics, software=saved.software, path=saved.path,
            )
            try:
                return original(state, draft)
            finally:
                state.bundle = saved
        ui._render_result = relabel
    elif name == "silent_diagnostic":
        original = wb.replay_bundle
        def diagnostic_instead_of_strict(*args, **kwargs):
            kwargs["diagnostic"] = True
            return original(*args, **kwargs)
        wb.replay_bundle = diagnostic_instead_of_strict
    elif name == "swallowed_failure":
        def swallow(state, exc):
            state.stage = "completed"
            return False
        wb._failure = swallow
    else:
        raise AssertionError(name)


def child(name):
    import pytest
    before = inventory()
    observed = []
    class Outcomes:
        def pytest_configure(self, config):
            # Register installed pytest plugins before UI import pulls in anyio;
            # warnings remain errors and no filter/autoload bypass is used.
            mutate(name)
        def pytest_runtest_logreport(self, report):
            observed.append({"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome})
    selector = "tests/test_workbench_streamlit.py::" + CASES[name]
    command = [selector, "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", f".pytest_cache/m6-ui-negative-final-{name}"]
    print("PYTEST_ARGS " + json.dumps(command), flush=True)
    code = int(pytest.main(command, plugins=[Outcomes()]))
    failed_calls = [row for row in observed if row["when"] == "call" and row["outcome"] == "failed"]
    other_failures = [row for row in observed if row["when"] != "call" and row["outcome"] == "failed"]
    matching = inventory() == before
    accepted = code == 1 and len(failed_calls) == 1 and failed_calls[0]["nodeid"] == selector and not other_failures and matching
    record = {
        "control": name, "pytest_exit": code, "expected_assertion_failures": len(failed_calls),
        "other_failures": other_failures, "source_test_hashes_unchanged": matching,
        "hashed_files": len(before), "accepted_detection": accepted,
    }
    print("CONTROL_RESULT " + json.dumps(record, sort_keys=True), flush=True)
    return 0 if accepted else 2


def parent():
    before = inventory()
    (EVIDENCE / "negative-controls-ui-final-before.json").write_text(json.dumps(before, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    transcript = []
    all_ok = True
    for name in CASES:
        command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), "--child", name]
        heading = ("COMMAND " + subprocess.list2cmdline(command) + "\n").encode("utf-8")
        transcript.append(heading)
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONUTF8"] = "1"
        result = subprocess.run(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        (EVIDENCE / f"negative-control-ui-final-{name}-output.txt").write_bytes(result.stdout)
        transcript.append(result.stdout)
        print(heading.decode("utf-8"), end="", flush=True)
        sys.stdout.buffer.write(result.stdout)
        sys.stdout.flush()
        same = inventory() == before
        all_ok = all_ok and result.returncode == 0 and same
        if not same:
            print("HASH_WINDOW_CHANGED: stop; no restoration of others' edits is attempted.", flush=True)
            break
    after = inventory()
    (EVIDENCE / "negative-controls-ui-final-after.json").write_text(json.dumps(after, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    final = {"all_expected_controls_detected": all_ok, "restoration": "process-local mutations discarded", "source_test_hashes_unchanged": before == after, "hashed_files": len(before)}
    ending = ("FINAL_RESULT " + json.dumps(final, sort_keys=True) + "\n").encode("utf-8")
    transcript.append(ending)
    (EVIDENCE / "negative-controls-ui-final-transcript.txt").write_bytes(b"".join(transcript))
    print(ending.decode("utf-8"), end="", flush=True)
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(child(sys.argv[2]) if len(sys.argv) > 1 and sys.argv[1] == "--child" else parent())
```

### Accepted control transcript

The display below omits six spaces on each of two otherwise blank assertion
output lines so the documentation passes the staged whitespace check. Every
other character is retained. The exact raw transcript remains unchanged at
[`negative-controls-ui-final-transcript.txt`](../../../runs/m6_acceptance_20260929/negative-controls-ui-final-transcript.txt).

```text
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m6_acceptance_20260929\negative_controls_ui.py --child duplicate_save
PYTEST_ARGS ["tests/test_workbench_streamlit.py::test_one_generate_action_saves_exactly_once_and_reruns_do_not_repeat", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m6-ui-negative-final-duplicate_save"]
F                                                                        [100%]
================================== FAILURES ===================================
E   AssertionError: assert 2 == 1
     +  where 2 = len([((WindowsPath('C:/holographiclab/.pytest_cache/m6-ui-negative-final-duplicate_save/test_one_generate_action_saves0/ru...cache/m6-ui-negative-final-duplicate_save/test_one_generate_action_saves0/runs/m6/.upload-2iu4_1pc/target.png'), ...})])
---------------------------- Captured stderr call -----------------------------
2026-09-29 22:21:44.638 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
------------------------------ Captured log call ------------------------------
WARNING  streamlit.runtime.scriptrunner_utils.script_run_context:script_run_context.py:479 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
C:\holographiclab\tests\test_workbench_streamlit.py:182: AssertionError: assert 2 == 1
=========================== short test summary info ===========================
FAILED tests/test_workbench_streamlit.py::test_one_generate_action_saves_exactly_once_and_reruns_do_not_repeat
1 failed in 3.15s
CONTROL_RESULT {"accepted_detection": true, "control": "duplicate_save", "expected_assertion_failures": 1, "hashed_files": 41, "other_failures": [], "pytest_exit": 1, "source_test_hashes_unchanged": true}
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m6_acceptance_20260929\negative_controls_ui.py --child stale_nonce
PYTEST_ARGS ["tests/test_workbench_streamlit.py::test_old_rendered_nonce_callback_after_completion_cannot_start_another_save", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m6-ui-negative-final-stale_nonce"]
F                                                                        [100%]
================================== FAILURES ===================================
E   AssertionError: assert 2 == 1
     +  where 2 = len([((WindowsPath('C:/holographiclab/.pytest_cache/m6-ui-negative-final-stale_nonce/test_old_rendered_nonce_callba0/runs/...st_cache/m6-ui-negative-final-stale_nonce/test_old_rendered_nonce_callba0/runs/m6/.upload-v5c27kpd/target.png'), ...})])
---------------------------- Captured stderr call -----------------------------
2026-09-29 22:21:48.991 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-09-29 22:21:50.906 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
------------------------------ Captured log call ------------------------------
WARNING  streamlit.runtime.scriptrunner_utils.script_run_context:script_run_context.py:479 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
WARNING  streamlit.runtime.scriptrunner_utils.script_run_context:script_run_context.py:479 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
C:\holographiclab\tests\test_workbench_streamlit.py:255: AssertionError: assert 2 == 1
=========================== short test summary info ===========================
FAILED tests/test_workbench_streamlit.py::test_old_rendered_nonce_callback_after_completion_cannot_start_another_save
1 failed in 3.99s
CONTROL_RESULT {"accepted_detection": true, "control": "stale_nonce", "expected_assertion_failures": 1, "hashed_files": 41, "other_failures": [], "pytest_exit": 1, "source_test_hashes_unchanged": true}
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m6_acceptance_20260929\negative_controls_ui.py --child stale_result_labels
PYTEST_ARGS ["tests/test_workbench_streamlit.py::test_submitted_result_keeps_saved_settings_after_draft_changes", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m6-ui-negative-final-stale_result_labels"]
F                                                                        [100%]
================================== FAILURES ===================================
E   AssertionError: assert [{'grid': {'d...ion': 1, ...}] == [{'grid': {'d...ion': 1, ...}]

      At index 0 diff: {'grid': {'dx_m': 1.1e-05, 'dy_m': 8e-06, 'nx': 64, 'ny': 64}, 'metrics': {'intensity_mse': {}, 'intensity_nmse': {}, 'intensity_psnr': {'data_range': 1.0}}, 'optics': {'distance_m': 0.005, 'wavelength_m': 6.33e-07}, 'schema_version': 1, 'solver': {'algorithm': 'gerchberg_saxton', 'contract': 'm3_periodic_lossless_asm_v1', 'initialization': {'mode': 'seed', 'seed': 987}, 'iterations': 0}} != {'grid': {'dx_m': 8e-06, 'dy_m': 8e-06, 'nx': 64, 'ny': 64}, 'metrics': {'intensity_mse': {}, 'intensity_nmse': {}, 'intensity_psnr': {'data_range': 1.0}}, 'optics'...

      ...Full output truncated (2 lines hidden), use '-vv' to show
---------------------------- Captured stderr call -----------------------------
2026-09-29 22:21:54.202 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.

------------------------------ Captured log call ------------------------------
WARNING  streamlit.runtime.scriptrunner_utils.script_run_context:script_run_context.py:479 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
C:\holographiclab\tests\test_workbench_streamlit.py:211: AssertionError: assert [{'grid': {'d...ion': 1, ...}] == [{'grid': {'d...ion': 1, ...}]
=========================== short test summary info ===========================
FAILED tests/test_workbench_streamlit.py::test_submitted_result_keeps_saved_settings_after_draft_changes
1 failed in 3.30s
CONTROL_RESULT {"accepted_detection": true, "control": "stale_result_labels", "expected_assertion_failures": 1, "hashed_files": 41, "other_failures": [], "pytest_exit": 1, "source_test_hashes_unchanged": true}
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m6_acceptance_20260929\negative_controls_ui.py --child silent_diagnostic
PYTEST_ARGS ["tests/test_workbench_streamlit.py::test_strict_replay_never_silently_enables_diagnostics", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m6-ui-negative-final-silent_diagnostic"]
F                                                                        [100%]
================================== FAILURES ===================================
E   assert True is False
---------------------------- Captured stderr call -----------------------------
2026-09-29 22:21:59.453 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
------------------------------ Captured log call ------------------------------
WARNING  streamlit.runtime.scriptrunner_utils.script_run_context:script_run_context.py:479 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
C:\holographiclab\tests\test_workbench_streamlit.py:386: assert True is False
=========================== short test summary info ===========================
FAILED tests/test_workbench_streamlit.py::test_strict_replay_never_silently_enables_diagnostics
1 failed in 3.20s
CONTROL_RESULT {"accepted_detection": true, "control": "silent_diagnostic", "expected_assertion_failures": 1, "hashed_files": 41, "other_failures": [], "pytest_exit": 1, "source_test_hashes_unchanged": true}
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 C:\holographiclab\runs\m6_acceptance_20260929\negative_controls_ui.py --child swallowed_failure
PYTEST_ARGS ["tests/test_workbench_streamlit.py::test_save_failure_is_visible_and_does_not_claim_or_retry_success", "-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", ".pytest_cache/m6-ui-negative-final-swallowed_failure"]
F                                                                        [100%]
================================== FAILURES ===================================
E   AssertionError: assert (None is None and None)
     +  where None = WorkbenchState(offered_nonce='9e1599e1b580457ea53933056a102e2e', busy=False, pending=None, consumed_tokens={'555d9a64a...failure_is_visible_a0/runs/m6/5d82161f8c83426092c8a23dd13e5568'), last_operation_at='2026-09-29T14:22:03.803696+00:00').bundle
     +  and   None = WorkbenchState(offered_nonce='9e1599e1b580457ea53933056a102e2e', busy=False, pending=None, consumed_tokens={'555d9a64a...failure_is_visible_a0/runs/m6/5d82161f8c83426092c8a23dd13e5568'), last_operation_at='2026-09-29T14:22:03.803696+00:00').error
---------------------------- Captured stderr call -----------------------------
2026-09-29 22:22:02.991 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
------------------------------ Captured log call ------------------------------
WARNING  streamlit.runtime.scriptrunner_utils.script_run_context:script_run_context.py:479 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
C:\holographiclab\tests\test_workbench_streamlit.py:313: AssertionError: assert (None is None and None)
=========================== short test summary info ===========================
FAILED tests/test_workbench_streamlit.py::test_save_failure_is_visible_and_does_not_claim_or_retry_success
1 failed in 1.39s
CONTROL_RESULT {"accepted_detection": true, "control": "swallowed_failure", "expected_assertion_failures": 1, "hashed_files": 41, "other_failures": [], "pytest_exit": 1, "source_test_hashes_unchanged": true}
FINAL_RESULT {"all_expected_controls_detected": true, "hashed_files": 41, "restoration": "process-local mutations discarded", "source_test_hashes_unchanged": true}
```

## Effective server configuration and actual browser acceptance

The configuration probe below is distinct from successful UI interaction.
It records loopback-only address/port, enabled CORS/XSRF protection and the
disabled telemetry/watcher/fast-rerun policies. Exact capture:

```text
ok
{
  "server.address": "127.0.0.1",
  "server.port": 8501,
  "server.headless": true,
  "server.enableCORS": true,
  "server.enableXsrfProtection": true,
  "server.runOnSave": false,
  "server.fileWatcherType": "none",
  "server.maxUploadSize": 8,
  "browser.gatherUsageStats": false,
  "runner.fastReruns": false
}
```

### Observed browser sequence and limits

The engineer used the enabled computer-use browser integration with real
Chrome and the loopback app at `http://127.0.0.1:8501`. These were actual
rendered pages, file uploads and button events. AppTest did not supply this
browser result. The normal launch can be reproduced from the repository root:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m streamlit run .\apps\streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --server.enableCORS true --server.enableXsrfProtection true --browser.gatherUsageStats false
```

The checked-in `.streamlit/config.toml` supplies the remaining policies in the
configuration probe above. Server03's normal launch was recorded at
`2026-09-29T14:34:44.0254570Z`, launcher PID 50824, child PID 30136.
Server02 was the separate, process-local event-observation run described below.
Only the task-owned server was replaced between those runs; this is not a
claim about arbitrary pre-existing processes. A later normal-server recheck of
the final UI refinement is recorded separately below.

| Real-browser action | Observed outcome and capture |
|---|---|
| First launch and ordinary reload | Default controls and empty-result instructions appeared; reload did not submit a run (`browser_fresh_session_initial.txt`, `browser_reload_no_submission.txt`) |
| Default Generate & Save | Server03 published `runs/m6/5f02e7b0a7b849da95b8f52693d61aa8`; saved identity, three images, raw history and saved metrics appeared (`browser_final_generate.txt`) |
| Valid PNG A | Actual 64 × 64 grayscale `a/same.png` uploaded and generated `runs/m6/9e09d4cf1adb4c42a4b3d289def511ce`; displayed submitted PNG hash matched A (`browser_upload_a.txt`) |
| Same-name, same-size replacement | Uploading B changed the draft. The app explicitly retained and labelled A's previous submitted result; it did not relabel A as B (`browser_same_name_replacement.txt`) |
| Explicit generation with PNG B | A new submit published `runs/m6/76d306c2dac04121aed6c3e3d1040ca4`, displaying B's distinct hash and brightness (`browser_upload_b.txt`) |
| Actual invalid PNG | The RGB PNG produced M2's source-color-type `ValueError`, cleared the active result and did not retain the old success badges (`browser_invalid_upload.txt`) |
| Recovery and existing M5 bundle | Explicit Open after that error loaded `runs/m5/example-6993df8ab9a34c1983a5ef2d96ac45bd`, including its saved fourth metric and mask parameters, independent of the current upload draft (`browser_error_recovery_m5.txt`) |
| Rapid clicks and a received event while busy | Three real Generate trigger receipts, one accepted submit, one save and one published path; the old nonce was rejected. This finite instrumented sequence is detailed below |
| Fresh-session reopening | A new session explicitly opened the completed queued-event run `706d7958d5ec407b83c1e6aed5caa329` (`browser_fresh_reopen.txt`). After a later user interruption closed the tabs, a third browser session reopened the already-completed `5f02...` run; screenshots did not require another generation |
| Strict replay with dirty source | Integrity `passed`, qualification `unqualified`, comparison `not_run`; source-state reasons visible (`browser_final_strict.txt`) |
| Explicit diagnostic replay | After checking the diagnostic box and clicking its button: integrity `passed`, qualification stayed `unqualified`, comparison `passed` (`browser_final_diagnostic.txt`) |

Initially, browser file-URL permission prevented selecting the fixture through
the automation route. The user enabled that permission, and the actual A/B/RGB
uploads above subsequently completed. The earlier permission block is not
counted as an upload pass. Blank and 512 × 512 files also exist in the fixture
inventory; their existence alone is not evidence that they were tested in this
browser sequence. Invalid-value/work-budget boundaries are covered by the
separate automated tests.

The default saved settings were 64 × 64, `dy = dx = 8e-6 m`, wavelength
`633e-9 m`, distance `0.005 m`, seed 0, 50 iterations and PSNR `data_range = 1`.
The rendered target/reconstruction shared `[0, 1.0513181]`, including overshoot;
phase used `[-π, +π] rad`, and the history contained all 51 raw amplitude
residual samples. The saved-data panel showed MSE `0.00048156227`, NMSE
`0.011172364`, PSNR `33.173475`, uniform source amplitude `0.29346272`, and
source/target powers each `2.25759372549e-08 a.u.·m²`. These are the UI's rounded
display values, not substituted full-precision metric evidence. Equal power
and plausible images do not establish exact synthesis or optical adequacy.

### Actual upload fixtures and identity

A and B both have basename `same.png` and encoded length 4228 bytes. They are
constant grayscale codes 128 and 64, respectively. Their complete PNG bytes
have distinct SHA-256 hashes:

| Fixture | SHA-256 |
|---|---|
| A | `337692daf7da609effc2f0cb8ee081a5860ada1e21009aa57225e16fd8151154` |
| B | `75fd3466cbfe6a96e5110d21c3118b6139289381d45e7423f7cbdb11f05e2bff` |
| Invalid RGB, 12420 bytes | `aaf03136dbf3818c6ec41df7e269295569b93968e92578149cc17d5fdf4947e7` |

To reproduce, place the exact script below in an owned evidence directory and
run it once with the project interpreter. It refuses to overwrite existing
fixtures. In the real app select upload mode, set both dimensions to 64, choose
A and Generate & Save; replace it with B before the next explicit submit, then
try the RGB file. Preserve the browser observations, resulting run identities
and exact bytes separately. This script prepares input files; it does not
simulate browser upload events.

```python
from pathlib import Path
from PIL import Image
import hashlib
import json

root = Path(__file__).parent / 'browser_fixtures'
fixtures = [('a/same.png','L',(64,64),128),('b/same.png','L',(64,64),64),
            ('invalid/rgb.png','RGB',(64,64),(128,128,128)),
            ('blank/blank.png','L',(64,64),0),('busy/large.png','L',(512,512),128)]
records=[]
for relative, mode, size, color in fixtures:
    target=root/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists()
    Image.new(mode,size,color=color).save(target,format='PNG',compress_level=0)
    payload=target.read_bytes()
    records.append(dict(path=str(target.absolute()),mode=mode,size=size,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest()))
assert records[0]['bytes']==records[1]['bytes']
assert records[0]['sha256']!=records[1]['sha256']
(root/'inventory.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps(records,indent=2))
```

The following are exact contiguous excerpts from the named DOM captures,
not reconstructed UI text. The full captures remain in the ignored evidence
directory. Each excerpt is delimited by its actual line numbers.

`browser_upload_a.txt`, lines 97–107:

```text
- code: C:\holographiclab\runs\m6\9e09d4cf1adb4c42a4b3d289def511ce
- paragraph: "Submitted ID: 90ab3852b86543d1ace391bbd8c2ec84 · Upload SHA-256: 337692daf7da609effc2f0cb8ee081a5860ada1e21009aa57225e16fd8151154"
- paragraph: 完整性 Integrity
- paragraph: passed
- paragraph: 資格 Qualification
- paragraph: not_evaluated
- paragraph: 數值比較 Comparison
- paragraph: not_run
- paragraph: "Last operation: generate · 2026-09-29T14:25:15.200398+00:00 · C:\\holographiclab\\runs\\m6\\9e09d4cf1adb4c42a4b3d289def511ce"
- button "Fullscreen":
- img "0"
```

`browser_same_name_replacement.txt`, lines 95–105:

```text
- code: C:\holographiclab\runs\m6\9e09d4cf1adb4c42a4b3d289def511ce
- paragraph: "Submitted ID: 90ab3852b86543d1ace391bbd8c2ec84 · Upload SHA-256: 337692daf7da609effc2f0cb8ee081a5860ada1e21009aa57225e16fd8151154"
- alert:
  - paragraph: 目前草稿不同；下方仍是上次提交的已儲存結果。Previous submission — saved settings retained.
- paragraph: 完整性 Integrity
- paragraph: passed
- paragraph: 資格 Qualification
- paragraph: not_evaluated
- paragraph: 數值比較 Comparison
- paragraph: not_run
- paragraph: "Last operation: generate · 2026-09-29T14:25:15.200398+00:00 · C:\\holographiclab\\runs\\m6\\9e09d4cf1adb4c42a4b3d289def511ce"
```

`browser_upload_b.txt`, lines 97–105:

```text
- code: C:\holographiclab\runs\m6\76d306c2dac04121aed6c3e3d1040ca4
- paragraph: "Submitted ID: caeb68ed45f0404aab7b46e537cd7435 · Upload SHA-256: 75fd3466cbfe6a96e5110d21c3118b6139289381d45e7423f7cbdb11f05e2bff"
- paragraph: 完整性 Integrity
- paragraph: passed
- paragraph: 資格 Qualification
- paragraph: not_evaluated
- paragraph: 數值比較 Comparison
- paragraph: not_run
- paragraph: "Last operation: generate · 2026-09-29T14:30:08.316111+00:00 · C:\\holographiclab\\runs\\m6\\76d306c2dac04121aed6c3e3d1040ca4"
```

`browser_invalid_upload.txt`, line 92:

```text
  - paragraph: "ValueError: 'C:\\holographiclab\\runs\\m6\\.upload-7l4j_jkn\\target.png': expected source bit depth 8 and grayscale color type 0; got bit depth 8, color type 2"
```

### Real queued-event observation

The observation harness below wrapped the real controller entry points and
Streamlit's `AppSession.request_rerun` in the test process. It preserved their
calls/returns and added a controlled 10-second pause after the first offer was
consumed. That pause widened the window before disabled controls rendered;
all three trigger events came from real browser clicks. No browser trigger or
production file was fabricated or rewritten. This is instrumentation of the
candidate, not a claim that normal computation takes ten seconds.

After stopping only the prior task-owned server, run the embedded harness
from its recorded location:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 runs/m6_acceptance_20260929/browser_queued_event_harness.py --pause-seconds 10
```

Open the page in Chrome, click Generate twice rapidly, and click the still
rendered old Generate button again during the controlled pause. After the save
finishes, preserve the journal. The reproduction will have a new journal UUID,
nonce, session and run path; use that journal in a fresh copy of the verifier,
with a fresh report path. The retained verifier below names the original
journal and creates its report exclusively, so rerunning it against an already
existing report deliberately refuses to overwrite that evidence.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 runs/m6_acceptance_20260929/verify_browser_queued_events.py
```

Recorded result: three Generate events were received, including one while
`busy = true` with the consumed nonce. Exactly one submission was accepted,
one save started, one save completed, and the rejected old callback retained
the original destination. The published bundle
`runs/m6/706d7958d5ec407b83c1e6aed5caa329` passed public M5 integrity verification.
The task-owned instrumented server was stopped at about
`2026-09-29T14:34:44Z`. The later verifier compared that already-closed 13-line
journal twice, 10.001258 seconds apart. Its endpoint was 131.180063 seconds
after the save; that value is elapsed timestamp arithmetic, not a live-server
observation duration or proof that an active server could never save later.
The actual receipt/rejection and one publication were observed before the
server stopped. The closed journal's complete byte hash is
`69be4d746289627574d19f3253f549d82ba94bfbb9a01c4d3168b1cbdb8b0ea7`.

This verifies one finite sequence in one active Chrome session. The observed
late callback ran while busy; the separate AppTest exercises an old callback
after completion. Neither is a durable exactly-once guarantee across reload,
crash, multiple sessions or every event schedule. The single published path
belongs to this observed sequence, not the entire runs directory. Instrumented
logs are neither signed provenance nor continuous monitoring.

Exact harness:

```python
"""Run the unchanged real app with process-local browser-event observations.

The controlled callback pause exposes the interval after an offer is consumed
but before the server renders disabled controls. No browser event is fabricated,
and no production source, configuration, package or numerical data is patched.
Run only after the previous task-owned loopback server has been stopped.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pause-seconds", type=float, default=3.0)
    arguments = parser.parse_args()
    if not 0.0 < arguments.pause_seconds <= 10.0:
        parser.error("pause-seconds must be positive and at most 10 seconds")

    from apps import workbench as wb
    from streamlit import config
    from streamlit.runtime.app_session import AppSession
    from streamlit.web import cli

    events = EVIDENCE / ("browser-queued-events-" + uuid4().hex + ".jsonl")
    with events.open("xb"):
        pass
    lock = threading.Lock()
    counts = {"accepted": 0, "save_started": 0, "save_completed": 0}

    def record(event, **details):
        item = {
            "event": event, "utc": datetime.now(timezone.utc).isoformat(),
            "monotonic_ns": time.monotonic_ns(),
            "thread": threading.current_thread().name, **details,
        }
        with lock:
            with events.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()

    original_submit = wb.submit_generate
    def observed_submit(state, draft, *, offered_nonce, runs_root):
        record("submit_attempt", captured_nonce=offered_nonce,
               offered_nonce=state.offered_nonce, busy=state.busy,
               pending=state.pending is not None)
        accepted = original_submit(state, draft, offered_nonce=offered_nonce, runs_root=runs_root)
        if accepted:
            counts["accepted"] += 1
        record("submit_result", captured_nonce=offered_nonce, accepted=accepted,
               offered_nonce=state.offered_nonce, busy=state.busy,
               destination=None if state.pending is None else str(state.pending.destination),
               accepted_count=counts["accepted"])
        if accepted:
            record("controlled_callback_pause_start", busy=state.busy,
                   consumed_nonce=offered_nonce, seconds=arguments.pause_seconds)
            time.sleep(arguments.pause_seconds)
            record("controlled_callback_pause_end", busy=state.busy,
                   consumed_nonce=offered_nonce)
        return accepted
    wb.submit_generate = observed_submit

    original_save = wb.run_and_save_bundle
    def observed_save(path, **kwargs):
        counts["save_started"] += 1
        record("save_started", path=str(path), count=counts["save_started"])
        try:
            bundle = original_save(path, **kwargs)
        except BaseException as exc:
            record("save_failed", path=str(path), exception_type=type(exc).__name__, message=str(exc))
            raise
        counts["save_completed"] += 1
        record("save_completed", path=str(bundle.path), count=counts["save_completed"],
               manifest_exists=(bundle.path / "manifest.json").is_file())
        return bundle
    wb.run_and_save_bundle = observed_save

    original_rerun = AppSession.request_rerun
    def observed_rerun(self, client_state):
        try:
            state = self._session_state["workbench"]
        except KeyError:
            state = None
        triggers = []
        if client_state is not None:
            for widget in client_state.widget_states.widgets:
                value_kind = widget.WhichOneof("value")
                if value_kind == "trigger_value" and widget.trigger_value:
                    triggers.append({"id": widget.id, "value_kind": value_kind})
        record(
            "rerun_request_received", session_id=self.id,
            client_state_present=client_state is not None,
            caller=sys._getframe(1).f_code.co_name,
            is_auto_rerun=None if client_state is None else client_state.is_auto_rerun,
            busy=None if state is None else state.busy,
            offered_nonce=None if state is None else state.offered_nonce,
            pending_nonce=None if state is None or state.pending is None else state.pending.token,
            triggered_widgets=triggers,
            effective_config={name: config.get_option(name) for name in (
                "server.address", "server.port", "server.enableCORS", "server.enableXsrfProtection",
                "server.runOnSave", "server.fileWatcherType", "runner.fastReruns", "browser.gatherUsageStats",
            )},
        )
        return original_rerun(self, client_state)
    AppSession.request_rerun = observed_rerun

    record("harness_started", app=str(ROOT / "apps" / "streamlit_app.py"),
           pause_seconds=arguments.pause_seconds,
           instrumentation="process-local observers and one callback pause; real browser events only")
    print("BROWSER_EVENT_LOG " + str(events), flush=True)
    cli.main(args=[
        "run", str(ROOT / "apps" / "streamlit_app.py"),
        "--server.address=127.0.0.1", "--server.port=8501",
        "--server.headless=true", "--server.enableCORS=true",
        "--server.enableXsrfProtection=true", "--server.runOnSave=false",
        "--server.fileWatcherType=none", "--runner.fastReruns=false",
        "--browser.gatherUsageStats=false",
    ], prog_name="streamlit")


if __name__ == "__main__":
    main()
```

Exact verifier:

```python
"""Read the real-browser instrumentation journal and verify its saved bundle."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

from ohlab.io.artifacts import verify_run_bundle


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
LOG = EVIDENCE / "browser-queued-events-9511d0c1a55849a4962203ee21bf384e.jsonl"
REPORT = EVIDENCE / "browser-queued-verification-9511d0c1a55849a4962203ee21bf384e.json"


def read():
    raw = LOG.read_bytes()
    records = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    for number, item in enumerate(records, start=1):
        item["journal_line"] = number
    return raw, records


def analyze(records):
    accepted = [item for item in records if item["event"] == "submit_result" and item["accepted"]]
    started = [item for item in records if item["event"] == "save_started"]
    completed = [item for item in records if item["event"] == "save_completed"]
    assert len(accepted) == len(started) == len(completed) == 1
    nonce = accepted[0]["captured_nonce"]
    trigger_suffix = "-generate_" + nonce
    receipts = [
        item for item in records if item["event"] == "rerun_request_received"
        and any(widget["id"].endswith(trigger_suffix) for widget in item["triggered_widgets"])
    ]
    busy_receipts = [item for item in receipts if item["busy"] is True and item["pending_nonce"] == nonce]
    assert len(receipts) >= 2 and busy_receipts
    assert all(item["client_state_present"] and item["is_auto_rerun"] is False for item in receipts)
    pause_start = next(item for item in records if item["event"] == "controlled_callback_pause_start")
    pause_end = next(item for item in records if item["event"] == "controlled_callback_pause_end")
    assert all(pause_start["monotonic_ns"] < item["monotonic_ns"] < pause_end["monotonic_ns"] for item in busy_receipts)
    assert all(item["offered_nonce"] != nonce for item in busy_receipts)
    rejected = [
        item for item in records if item["event"] == "submit_result"
        and not item["accepted"] and item["captured_nonce"] == nonce
    ]
    assert rejected and rejected[-1]["monotonic_ns"] >= busy_receipts[-1]["monotonic_ns"]
    paths = {accepted[0]["destination"], started[0]["path"], completed[0]["path"]}
    assert len(paths) == 1 and started[0]["count"] == completed[0]["count"] == 1
    assert completed[0]["manifest_exists"] is True
    assert completed[0]["monotonic_ns"] >= started[0]["monotonic_ns"] >= pause_end["monotonic_ns"]
    return accepted[0], receipts, busy_receipts, rejected, started[0], completed[0]


initial_bytes, initial_records = read()
analyze(initial_records)
observed_from = datetime.now(timezone.utc)
time.sleep(10.0)
final_bytes, final_records = read()
observed_to = datetime.now(timezone.utc)
assert final_bytes.startswith(initial_bytes), "journal changed non-append-only during observation"
accepted, receipts, busy_receipts, rejected, started, completed = analyze(final_records)
bundle_path = Path(completed["path"])
assert bundle_path.is_relative_to(ROOT / "runs" / "m6")
integrity = verify_run_bundle(bundle_path)
assert integrity.status == "passed"
save_time = datetime.fromisoformat(completed["utc"])
record = {
    "passed": True,
    "log": str(LOG),
    "log_sha256": hashlib.sha256(final_bytes).hexdigest(),
    "journal_lines_initial": len(initial_records),
    "journal_lines_final": len(final_records),
    "observation_start_utc": observed_from.isoformat(),
    "observation_end_utc": observed_to.isoformat(),
    "observation_duration_seconds": (observed_to - observed_from).total_seconds(),
    "seconds_after_save_observed": (observed_to - save_time).total_seconds(),
    "accepted_nonce": accepted["captured_nonce"],
    "accepted_count": 1,
    "save_started_count": 1,
    "save_completed_count": 1,
    "unique_published_paths_observed": [str(bundle_path)],
    "integrity": integrity.status,
    "verified_files": list(integrity.files),
    "generate_trigger_receipts": receipts,
    "busy_old_nonce_receipts": busy_receipts,
    "rejected_old_nonce_callbacks": rejected,
    "save_started": started,
    "save_completed": completed,
    "limits": [
        "Finite observation of one real Chrome interaction sequence and one active session.",
        "A controlled 10-second callback pause widened the pre-disabled-render transport window.",
        "Observed late callback ran while busy; the separate AppTest exercises an old callback after completion.",
        "No claim of durable exactly-once operation across reloads, crashes, multiple sessions, or all event schedules.",
        "One published path associated with this instrumented sequence, not one directory in the entire runs tree.",
        "The log is instrumentation evidence, not signed provenance or a continuous-monitoring claim.",
    ],
}
with REPORT.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, indent=2, sort_keys=True, ensure_ascii=False)
    stream.write("\n")
print(json.dumps({
    "report": str(REPORT), "passed": True,
    "accepted": 1, "save_started": 1, "save_completed": 1,
    "received_generate_events": len(receipts), "busy_old_nonce_events": len(busy_receipts),
    "rejected_old_nonce_callbacks": len(rejected), "integrity": integrity.status,
    "seconds_after_save_observed": record["seconds_after_save_observed"],
}, indent=2))
```

Exact verification report, including actual server-side receipt state:

```json
{
  "accepted_count": 1,
  "accepted_nonce": "4dd4b3fb98df45208f1efd97cd9539b5",
  "busy_old_nonce_receipts": [
    {
      "busy": true,
      "caller": "_handle_rerun_script_request",
      "client_state_present": true,
      "effective_config": {
        "browser.gatherUsageStats": false,
        "runner.fastReruns": false,
        "server.address": "127.0.0.1",
        "server.enableCORS": true,
        "server.enableXsrfProtection": true,
        "server.fileWatcherType": "none",
        "server.port": 8501,
        "server.runOnSave": false
      },
      "event": "rerun_request_received",
      "is_auto_rerun": false,
      "journal_line": 8,
      "monotonic_ns": 1656337859000000,
      "offered_nonce": "3c20abacb31c430db8ea4b73c6ed5726",
      "pending_nonce": "4dd4b3fb98df45208f1efd97cd9539b5",
      "session_id": "5b7ad4c3-3e17-42ce-b8fc-2b0b0fe46346",
      "thread": "MainThread",
      "triggered_widgets": [
        {
          "id": "$$ID-88d6f5c003ea978ff95bbfcf450bd252-generate_4dd4b3fb98df45208f1efd97cd9539b5",
          "value_kind": "trigger_value"
        }
      ],
      "utc": "2026-09-29T14:33:20.902802+00:00"
    }
  ],
  "generate_trigger_receipts": [
    {
      "busy": false,
      "caller": "_handle_rerun_script_request",
      "client_state_present": true,
      "effective_config": {
        "browser.gatherUsageStats": false,
        "runner.fastReruns": false,
        "server.address": "127.0.0.1",
        "server.enableCORS": true,
        "server.enableXsrfProtection": true,
        "server.fileWatcherType": "none",
        "server.port": 8501,
        "server.runOnSave": false
      },
      "event": "rerun_request_received",
      "is_auto_rerun": false,
      "journal_line": 3,
      "monotonic_ns": 1656333515000000,
      "offered_nonce": "4dd4b3fb98df45208f1efd97cd9539b5",
      "pending_nonce": null,
      "session_id": "5b7ad4c3-3e17-42ce-b8fc-2b0b0fe46346",
      "thread": "MainThread",
      "triggered_widgets": [
        {
          "id": "$$ID-88d6f5c003ea978ff95bbfcf450bd252-generate_4dd4b3fb98df45208f1efd97cd9539b5",
          "value_kind": "trigger_value"
        }
      ],
      "utc": "2026-09-29T14:33:16.566567+00:00"
    },
    {
      "busy": false,
      "caller": "_handle_rerun_script_request",
      "client_state_present": true,
      "effective_config": {
        "browser.gatherUsageStats": false,
        "runner.fastReruns": false,
        "server.address": "127.0.0.1",
        "server.enableCORS": true,
        "server.enableXsrfProtection": true,
        "server.fileWatcherType": "none",
        "server.port": 8501,
        "server.runOnSave": false
      },
      "event": "rerun_request_received",
      "is_auto_rerun": false,
      "journal_line": 4,
      "monotonic_ns": 1656333531000000,
      "offered_nonce": "4dd4b3fb98df45208f1efd97cd9539b5",
      "pending_nonce": null,
      "session_id": "5b7ad4c3-3e17-42ce-b8fc-2b0b0fe46346",
      "thread": "MainThread",
      "triggered_widgets": [
        {
          "id": "$$ID-88d6f5c003ea978ff95bbfcf450bd252-generate_4dd4b3fb98df45208f1efd97cd9539b5",
          "value_kind": "trigger_value"
        }
      ],
      "utc": "2026-09-29T14:33:16.569564+00:00"
    },
    {
      "busy": true,
      "caller": "_handle_rerun_script_request",
      "client_state_present": true,
      "effective_config": {
        "browser.gatherUsageStats": false,
        "runner.fastReruns": false,
        "server.address": "127.0.0.1",
        "server.enableCORS": true,
        "server.enableXsrfProtection": true,
        "server.fileWatcherType": "none",
        "server.port": 8501,
        "server.runOnSave": false
      },
      "event": "rerun_request_received",
      "is_auto_rerun": false,
      "journal_line": 8,
      "monotonic_ns": 1656337859000000,
      "offered_nonce": "3c20abacb31c430db8ea4b73c6ed5726",
      "pending_nonce": "4dd4b3fb98df45208f1efd97cd9539b5",
      "session_id": "5b7ad4c3-3e17-42ce-b8fc-2b0b0fe46346",
      "thread": "MainThread",
      "triggered_widgets": [
        {
          "id": "$$ID-88d6f5c003ea978ff95bbfcf450bd252-generate_4dd4b3fb98df45208f1efd97cd9539b5",
          "value_kind": "trigger_value"
        }
      ],
      "utc": "2026-09-29T14:33:20.902802+00:00"
    }
  ],
  "integrity": "passed",
  "journal_lines_final": 13,
  "journal_lines_initial": 13,
  "limits": [
    "Finite observation of one real Chrome interaction sequence and one active session.",
    "A controlled 10-second callback pause widened the pre-disabled-render transport window.",
    "Observed late callback ran while busy; the separate AppTest exercises an old callback after completion.",
    "No claim of durable exactly-once operation across reloads, crashes, multiple sessions, or all event schedules.",
    "One published path associated with this instrumented sequence, not one directory in the entire runs tree.",
    "The log is instrumentation evidence, not signed provenance or a continuous-monitoring claim."
  ],
  "log": "C:\\holographiclab\\runs\\m6_acceptance_20260929\\browser-queued-events-9511d0c1a55849a4962203ee21bf384e.jsonl",
  "log_sha256": "69be4d746289627574d19f3253f549d82ba94bfbb9a01c4d3168b1cbdb8b0ea7",
  "observation_duration_seconds": 10.001258,
  "observation_end_utc": "2026-09-29T14:35:38.531751+00:00",
  "observation_start_utc": "2026-09-29T14:35:28.530493+00:00",
  "passed": true,
  "rejected_old_nonce_callbacks": [
    {
      "accepted": false,
      "accepted_count": 1,
      "busy": true,
      "captured_nonce": "4dd4b3fb98df45208f1efd97cd9539b5",
      "destination": "C:\\holographiclab\\runs\\m6\\706d7958d5ec407b83c1e6aed5caa329",
      "event": "submit_result",
      "journal_line": 11,
      "monotonic_ns": 1656343640000000,
      "offered_nonce": "3c20abacb31c430db8ea4b73c6ed5726",
      "thread": "ScriptRunner.scriptThread",
      "utc": "2026-09-29T14:33:26.682642+00:00"
    }
  ],
  "save_completed": {
    "count": 1,
    "event": "save_completed",
    "journal_line": 13,
    "manifest_exists": true,
    "monotonic_ns": 1656344312000000,
    "path": "C:\\holographiclab\\runs\\m6\\706d7958d5ec407b83c1e6aed5caa329",
    "thread": "ScriptRunner.scriptThread",
    "utc": "2026-09-29T14:33:27.351688+00:00"
  },
  "save_completed_count": 1,
  "save_started": {
    "count": 1,
    "event": "save_started",
    "journal_line": 12,
    "monotonic_ns": 1656344031000000,
    "path": "C:\\holographiclab\\runs\\m6\\706d7958d5ec407b83c1e6aed5caa329",
    "thread": "ScriptRunner.scriptThread",
    "utc": "2026-09-29T14:33:27.082776+00:00"
  },
  "save_started_count": 1,
  "seconds_after_save_observed": 131.180063,
  "unique_published_paths_observed": [
    "C:\\holographiclab\\runs\\m6\\706d7958d5ec407b83c1e6aed5caa329"
  ],
  "verified_files": [
    "config.json",
    "input_target.png",
    "metrics.json",
    "phase.npy",
    "reconstruction_field.npy",
    "reconstruction_intensity.npy",
    "residual_history.npy",
    "source_amplitude.npy",
    "source_field.npy",
    "target_amplitude.npy",
    "target_intensity.npy"
  ]
}
```

### Final normal-server display recheck and screenshots

After the final limit-display refinement, the engineer restarted the normal
app as server04 at `2026-09-29T15:34:02.7758218Z` (launcher PID 38176,
child PID 60412) and explicitly reopened the same completed `5f02...` bundle.
The final ordinary-flow checks passed: Open gave `passed / not_evaluated /
not_run`; strict replay gave `passed / unqualified / not_run`; checking the
diagnostic box and clicking its button gave `passed / unqualified / passed`
at `2026-09-29T15:35:17.833207+00:00`. Those three statuses are integrity,
qualification and comparison, in that order. The dirty-source qualification
reasons remained visible. No fresh generation was required for these saved-run
screenshots; the clean-postcommit fresh-generation gate below remains separate.

Both figures are direct, unaltered bytes returned by the browser screenshot
API, captured from the corrected normal app and visually reviewed by the
engineer. Figure 1 shows all three images and the complete 51-sample history;
figure 2 shows the path, explicit diagnostic checkbox and three statuses.
The metric panel was also inspected below the fold and recorded in the DOM.
The screenshot dimensions below are decoded from the committed PNG bytes;
they are not nominal browser-window dimensions.

| Actual viewport capture | Decoded size | Bytes | SHA-256 |
|---|---|---|---|
| [fig01_create_and_inspect.png](figures/fig01_create_and_inspect.png) | 1707 × 889 | 142840 | `1c73fd8cf36695a7e11673c635197350b648fc6f938177746a8e7eaf2e436f32` |
| [fig02_verify_and_replay.png](figures/fig02_verify_and_replay.png) | 1707 × 889 | 114979 | `7788de5db04c1a90a57816143908460b00f23d89d65a16c8e9b9fd94538b32a2` |

These screenshots document the real viewport, not every control or every
possible state. They do not replace the automated/state/integrity evidence.
The final normal-server DOM captures are embedded in full, unchanged:

`browser_corrected_open.txt`:

```text
- heading "建立實驗 Create" [level=2]
- paragraph: 目標來源 Target
- combobox "目標來源 Target": 固定光斑 · 64 × 64
- button "Open":
- paragraph: 固定 64 × 64 像素；光斑寬度 σ = 7.5 pixels。僅在 8 μm pitch 時對應 60 μm；修改 pitch 不改變像素值。
- paragraph: dy (μm)
- spinbutton "dy (μm)": "8.000000"
- button "Decrement":
- button "Increment":
- paragraph: dx (μm)
- spinbutton "dx (μm)": "8.000000"
- button "Decrement":
- button "Increment":
- paragraph: 波長 Wavelength (nm)
- spinbutton "波長 Wavelength (nm)": "633.00"
- button "Decrement":
- button "Increment":
- paragraph: 傳播距離 Distance (mm)
- spinbutton "傳播距離 Distance (mm)": "5.00"
- button "Decrement":
- button "Increment":
- paragraph: 迭代數 Iterations
- spinbutton "迭代數 Iterations": "50"
- button "Decrement":
- button "Increment":
- paragraph: Seed
- spinbutton "Seed": "0"
- button "Decrement" [disabled]:
- button "Increment":
- paragraph: PSNR data_range
- button "Help for PSNR data_range":
- spinbutton "PSNR data_range": "1.00"
- button "Decrement":
- button "Increment":
- paragraph: 每次明確設定與目標等功率的均勻照明。草稿更動不會計算或儲存。
- button "產生並儲存 Generate & Save":
  - paragraph: 產生並儲存 Generate & Save
- paragraph: App 限制：每邊 1–512、N ≤ 200；ny × nx × max(1,N) ≤ 13,107,200。這些限制不保證光學取樣足夠。
- banner:
  - button "Deploy":
    - generic: Deploy
  - button "Main menu":
- heading "全像重建工作台" [level=1]:
  - text: 全像重建工作台
  - link "Link to heading":
    - /url: "#a94ae6c4"
- paragraph: Open Holographic Lab · 單平面相位合成與可重現實驗 · Local workbench
- generic "keyboard_arrow_down 開啟、驗證與重播 Open · Verify · Replay":
  - generic: keyboard_arrow_down
  - paragraph: 開啟、驗證與重播 Open · Verify · Replay
- paragraph: 既有實驗（清單不代表已驗證）
- combobox "既有實驗（清單不代表已驗證）": 目前顯示的實驗（若有）
- button "Open":
- paragraph: 或輸入 runs/ 下的 bundle 路徑
- button "Help for 或輸入 runs/ 下的 bundle 路徑":
- textbox "或輸入 runs/ 下的 bundle 路徑":
  - /placeholder: ""
  - text: m6/5f02e7b0a7b849da95b8f52693d61aa8
- button "開啟 Open":
  - generic "開啟 Open":
    - paragraph: 開啟 Open
- button "重新驗證並載入 Refresh":
  - generic "重新驗證並載入 Refresh":
    - paragraph: 重新驗證並載入 Refresh
- button "嚴格重播 Strict replay":
  - generic "嚴格重播 Strict replay":
    - paragraph: 嚴格重播 Strict replay
- checkbox "明確啟用 diagnostic replay（不提升 qualification）"
- paragraph: 明確啟用 diagnostic replay（不提升 qualification）
- button "執行診斷重播 Diagnostic replay" [disabled]:
  - paragraph: 執行診斷重播 Diagnostic replay
- paragraph: 路徑與清單皆空白時，使用目前顯示的 bundle。開啟／刷新只檢查完整性，不自動重播。Strict replay 不符合來源／環境資格時維持 not_run。檔案不是持續監控；狀態屬於上次操作。
- heading "已儲存結果 Saved result" [level=3]:
  - text: 已儲存結果 Saved result
  - link "Link to heading":
    - /url: "#saved-result"
- code: C:\holographiclab\runs\m6\5f02e7b0a7b849da95b8f52693d61aa8
- paragraph: 已載入 bundle；以下設定與陣列均來自此 bundle，與左側草稿無關。
- paragraph: 完整性 Integrity
- paragraph: passed
- paragraph: 資格 Qualification
- paragraph: not_evaluated
- paragraph: 數值比較 Comparison
- paragraph: not_run
- paragraph: "Last operation: open · 2026-09-29T15:34:36.770793+00:00 · C:\\holographiclab\\runs\\m6\\5f02e7b0a7b849da95b8f52693d61aa8"
- button "Fullscreen":
- img "0"
- paragraph: Target / reconstruction 共用顯示範圍 [0, 1.0513181]，包含 overshoot；未獨立正規化。Phase 固定 [-π, +π] rad，是理想數值相位，不是校準後的 SLM 驅動圖。
- button "Fullscreen":
- img "0"
- paragraph: 完整 M3 amplitude residual（N+1 點、線性座標）；不是 intensity NMSE，也不是百分比準確率。
- heading "已儲存量測 Metrics" [level=3]:
  - text: 已儲存量測 Metrics
  - link "Link to heading":
    - /url: "#metrics"
- paragraph:
  - strong: intensity_mse
  - text: ": 0.00048156227 · parameters:"
  - code: "{}"
- paragraph:
  - strong: intensity_nmse
  - text: ": 0.011172364 · parameters:"
  - code: "{}"
- paragraph:
  - strong: intensity_psnr
  - text: ": 33.173475 · parameters:"
  - code: "{'data_range': 1.0}"
- paragraph:
  - strong: 照明 Illumination
  - text: ": uniform · amplitude min/max = 0.29346272 / 0.29346272"
- paragraph:
  - strong: P_source
  - text: = 2.25759372549e-08 a.u.·m² ·
  - strong: P_target
  - text: = 2.25759372549e-08 a.u.·m²
- generic "keyboard_arrow_right 已儲存設定與來源 Saved settings & provenance":
  - generic: keyboard_arrow_right
  - paragraph: 已儲存設定與來源 Saved settings & provenance
- paragraph: 單一平面、完整週期性且無消逝波的 M3 模型；等功率不保證精確合成。Integrity 是相對於未簽章 manifest 的檢查，不是作者認證。
- paragraph: 僅供本機軟體實驗。每次操作只保證目前 session 內的重複事件防護；重新載入、崩潰或多個 session 不具持久 exactly-once 保證。
```

`browser_corrected_strict.txt`:

```text
- heading "建立實驗 Create" [level=2]
- paragraph: 目標來源 Target
- combobox "目標來源 Target": 固定光斑 · 64 × 64
- button "Open":
- paragraph: 固定 64 × 64 像素；光斑寬度 σ = 7.5 pixels。僅在 8 μm pitch 時對應 60 μm；修改 pitch 不改變像素值。
- paragraph: dy (μm)
- spinbutton "dy (μm)": "8.000000"
- button "Decrement":
- button "Increment":
- paragraph: dx (μm)
- spinbutton "dx (μm)": "8.000000"
- button "Decrement":
- button "Increment":
- paragraph: 波長 Wavelength (nm)
- spinbutton "波長 Wavelength (nm)": "633.00"
- button "Decrement":
- button "Increment":
- paragraph: 傳播距離 Distance (mm)
- spinbutton "傳播距離 Distance (mm)": "5.00"
- button "Decrement":
- button "Increment":
- paragraph: 迭代數 Iterations
- spinbutton "迭代數 Iterations": "50"
- button "Decrement":
- button "Increment":
- paragraph: Seed
- spinbutton "Seed": "0"
- button "Decrement" [disabled]:
- button "Increment":
- paragraph: PSNR data_range
- button "Help for PSNR data_range":
- spinbutton "PSNR data_range": "1.00"
- button "Decrement":
- button "Increment":
- paragraph: 每次明確設定與目標等功率的均勻照明。草稿更動不會計算或儲存。
- button "產生並儲存 Generate & Save":
  - paragraph: 產生並儲存 Generate & Save
- paragraph: App 限制：每邊 1–512、N ≤ 200；ny × nx × max(1,N) ≤ 13,107,200。這些限制不保證光學取樣足夠。
- banner:
  - button "Deploy":
    - generic: Deploy
  - button "Main menu":
- heading "全像重建工作台" [level=1]:
  - text: 全像重建工作台
  - link "Link to heading":
    - /url: "#a94ae6c4"
- paragraph: Open Holographic Lab · 單平面相位合成與可重現實驗 · Local workbench
- generic "keyboard_arrow_down 開啟、驗證與重播 Open · Verify · Replay":
  - generic: keyboard_arrow_down
  - paragraph: 開啟、驗證與重播 Open · Verify · Replay
- paragraph: 既有實驗（清單不代表已驗證）
- combobox "既有實驗（清單不代表已驗證）": 目前顯示的實驗（若有）
- button "Open":
- paragraph: 或輸入 runs/ 下的 bundle 路徑
- button "Help for 或輸入 runs/ 下的 bundle 路徑":
- textbox "或輸入 runs/ 下的 bundle 路徑":
  - /placeholder: ""
  - text: m6/5f02e7b0a7b849da95b8f52693d61aa8
- button "開啟 Open":
  - generic "開啟 Open":
    - paragraph: 開啟 Open
- button "重新驗證並載入 Refresh":
  - generic "重新驗證並載入 Refresh":
    - paragraph: 重新驗證並載入 Refresh
- button "嚴格重播 Strict replay":
  - generic "嚴格重播 Strict replay":
    - paragraph: 嚴格重播 Strict replay
- checkbox "明確啟用 diagnostic replay（不提升 qualification）"
- paragraph: 明確啟用 diagnostic replay（不提升 qualification）
- button "執行診斷重播 Diagnostic replay" [disabled]:
  - paragraph: 執行診斷重播 Diagnostic replay
- paragraph: 路徑與清單皆空白時，使用目前顯示的 bundle。開啟／刷新只檢查完整性，不自動重播。Strict replay 不符合來源／環境資格時維持 not_run。檔案不是持續監控；狀態屬於上次操作。
- heading "已儲存結果 Saved result" [level=3]:
  - text: 已儲存結果 Saved result
  - link "Link to heading":
    - /url: "#saved-result"
- code: C:\holographiclab\runs\m6\5f02e7b0a7b849da95b8f52693d61aa8
- paragraph: 已載入 bundle；以下設定與陣列均來自此 bundle，與左側草稿無關。
- paragraph: 完整性 Integrity
- paragraph: passed
- paragraph: 資格 Qualification
- paragraph: unqualified
- paragraph: 數值比較 Comparison
- paragraph: not_run
- paragraph: "Last operation: replay · 2026-09-29T15:34:55.200192+00:00 · C:\\holographiclab\\runs\\m6\\5f02e7b0a7b849da95b8f52693d61aa8"
- alert:
  - paragraph: 資格未通過：recorded source state is dirty, expected clean; current source state is dirty, expected clean
- generic "keyboard_arrow_right 重播檢查細節 Replay checks":
  - generic: keyboard_arrow_right
  - paragraph: 重播檢查細節 Replay checks
- button "Fullscreen":
- img "0"
- paragraph: Target / reconstruction 共用顯示範圍 [0, 1.0513181]，包含 overshoot；未獨立正規化。Phase 固定 [-π, +π] rad，是理想數值相位，不是校準後的 SLM 驅動圖。
- button "Fullscreen":
- img "0"
- paragraph: 完整 M3 amplitude residual（N+1 點、線性座標）；不是 intensity NMSE，也不是百分比準確率。
- heading "已儲存量測 Metrics" [level=3]:
  - text: 已儲存量測 Metrics
  - link "Link to heading":
    - /url: "#metrics"
- paragraph:
  - strong: intensity_mse
  - text: ": 0.00048156227 · parameters:"
  - code: "{}"
- paragraph:
  - strong: intensity_nmse
  - text: ": 0.011172364 · parameters:"
  - code: "{}"
- paragraph:
  - strong: intensity_psnr
  - text: ": 33.173475 · parameters:"
  - code: "{'data_range': 1.0}"
- paragraph:
  - strong: 照明 Illumination
  - text: ": uniform · amplitude min/max = 0.29346272 / 0.29346272"
- paragraph:
  - strong: P_source
  - text: = 2.25759372549e-08 a.u.·m² ·
  - strong: P_target
  - text: = 2.25759372549e-08 a.u.·m²
- generic "keyboard_arrow_right 已儲存設定與來源 Saved settings & provenance":
  - generic: keyboard_arrow_right
  - paragraph: 已儲存設定與來源 Saved settings & provenance
- paragraph: 單一平面、完整週期性且無消逝波的 M3 模型；等功率不保證精確合成。Integrity 是相對於未簽章 manifest 的檢查，不是作者認證。
- paragraph: 僅供本機軟體實驗。每次操作只保證目前 session 內的重複事件防護；重新載入、崩潰或多個 session 不具持久 exactly-once 保證。
```

`browser_corrected_diagnostic.txt`:

```text
- heading "建立實驗 Create" [level=2]
- paragraph: 目標來源 Target
- combobox "目標來源 Target": 固定光斑 · 64 × 64
- button "Open":
- paragraph: 固定 64 × 64 像素；光斑寬度 σ = 7.5 pixels。僅在 8 μm pitch 時對應 60 μm；修改 pitch 不改變像素值。
- paragraph: dy (μm)
- spinbutton "dy (μm)": "8.000000"
- button "Decrement":
- button "Increment":
- paragraph: dx (μm)
- spinbutton "dx (μm)": "8.000000"
- button "Decrement":
- button "Increment":
- paragraph: 波長 Wavelength (nm)
- spinbutton "波長 Wavelength (nm)": "633.00"
- button "Decrement":
- button "Increment":
- paragraph: 傳播距離 Distance (mm)
- spinbutton "傳播距離 Distance (mm)": "5.00"
- button "Decrement":
- button "Increment":
- paragraph: 迭代數 Iterations
- spinbutton "迭代數 Iterations": "50"
- button "Decrement":
- button "Increment":
- paragraph: Seed
- spinbutton "Seed": "0"
- button "Decrement" [disabled]:
- button "Increment":
- paragraph: PSNR data_range
- button "Help for PSNR data_range":
- spinbutton "PSNR data_range": "1.00"
- button "Decrement":
- button "Increment":
- paragraph: 每次明確設定與目標等功率的均勻照明。草稿更動不會計算或儲存。
- button "產生並儲存 Generate & Save":
  - paragraph: 產生並儲存 Generate & Save
- paragraph: App 限制：每邊 1–512、N ≤ 200；ny × nx × max(1,N) ≤ 13,107,200。這些限制不保證光學取樣足夠。
- banner:
  - button "Deploy":
    - generic: Deploy
  - button "Main menu":
- heading "全像重建工作台" [level=1]:
  - text: 全像重建工作台
  - link "Link to heading":
    - /url: "#a94ae6c4"
- paragraph: Open Holographic Lab · 單平面相位合成與可重現實驗 · Local workbench
- generic "keyboard_arrow_down 開啟、驗證與重播 Open · Verify · Replay":
  - generic: keyboard_arrow_down
  - paragraph: 開啟、驗證與重播 Open · Verify · Replay
- paragraph: 既有實驗（清單不代表已驗證）
- combobox "既有實驗（清單不代表已驗證）": 目前顯示的實驗（若有）
- button "Open":
- paragraph: 或輸入 runs/ 下的 bundle 路徑
- button "Help for 或輸入 runs/ 下的 bundle 路徑":
- textbox "或輸入 runs/ 下的 bundle 路徑":
  - /placeholder: ""
  - text: m6/5f02e7b0a7b849da95b8f52693d61aa8
- button "開啟 Open":
  - generic "開啟 Open":
    - paragraph: 開啟 Open
- button "重新驗證並載入 Refresh":
  - generic "重新驗證並載入 Refresh":
    - paragraph: 重新驗證並載入 Refresh
- button "嚴格重播 Strict replay":
  - generic "嚴格重播 Strict replay":
    - paragraph: 嚴格重播 Strict replay
- checkbox "明確啟用 diagnostic replay（不提升 qualification）" [checked]
- paragraph: 明確啟用 diagnostic replay（不提升 qualification）
- button "執行診斷重播 Diagnostic replay":
  - paragraph: 執行診斷重播 Diagnostic replay
- paragraph: 路徑與清單皆空白時，使用目前顯示的 bundle。開啟／刷新只檢查完整性，不自動重播。Strict replay 不符合來源／環境資格時維持 not_run。檔案不是持續監控；狀態屬於上次操作。
- heading "已儲存結果 Saved result" [level=3]:
  - text: 已儲存結果 Saved result
  - link "Link to heading":
    - /url: "#saved-result"
- code: C:\holographiclab\runs\m6\5f02e7b0a7b849da95b8f52693d61aa8
- paragraph: 已載入 bundle；以下設定與陣列均來自此 bundle，與左側草稿無關。
- paragraph: 完整性 Integrity
- paragraph: passed
- paragraph: 資格 Qualification
- paragraph: unqualified
- paragraph: 數值比較 Comparison
- paragraph: passed
- paragraph: "Last operation: replay · 2026-09-29T15:35:17.833207+00:00 · C:\\holographiclab\\runs\\m6\\5f02e7b0a7b849da95b8f52693d61aa8"
- alert:
  - paragraph: 資格未通過：recorded source state is dirty, expected clean; current source state is dirty, expected clean
- generic "keyboard_arrow_right 重播檢查細節 Replay checks":
  - generic: keyboard_arrow_right
  - paragraph: 重播檢查細節 Replay checks
- button "Fullscreen":
- img "0"
- paragraph: Target / reconstruction 共用顯示範圍 [0, 1.0513181]，包含 overshoot；未獨立正規化。Phase 固定 [-π, +π] rad，是理想數值相位，不是校準後的 SLM 驅動圖。
- button "Fullscreen":
- img "0"
- paragraph: 完整 M3 amplitude residual（N+1 點、線性座標）；不是 intensity NMSE，也不是百分比準確率。
- heading "已儲存量測 Metrics" [level=3]:
  - text: 已儲存量測 Metrics
  - link "Link to heading":
    - /url: "#metrics"
- paragraph:
  - strong: intensity_mse
  - text: ": 0.00048156227 · parameters:"
  - code: "{}"
- paragraph:
  - strong: intensity_nmse
  - text: ": 0.011172364 · parameters:"
  - code: "{}"
- paragraph:
  - strong: intensity_psnr
  - text: ": 33.173475 · parameters:"
  - code: "{'data_range': 1.0}"
- paragraph:
  - strong: 照明 Illumination
  - text: ": uniform · amplitude min/max = 0.29346272 / 0.29346272"
- paragraph:
  - strong: P_source
  - text: = 2.25759372549e-08 a.u.·m² ·
  - strong: P_target
  - text: = 2.25759372549e-08 a.u.·m²
- generic "keyboard_arrow_right 已儲存設定與來源 Saved settings & provenance":
  - generic: keyboard_arrow_right
  - paragraph: 已儲存設定與來源 Saved settings & provenance
- paragraph: 單一平面、完整週期性且無消逝波的 M3 模型；等功率不保證精確合成。Integrity 是相對於未簽章 manifest 的檢查，不是作者認證。
- paragraph: 僅供本機軟體實驗。每次操作只保證目前 session 內的重複事件防護；重新載入、崩潰或多個 session 不具持久 exactly-once 保證。
```

A separate read-only verification at `2026-09-29T15:34:33.380474+00:00` checked
the exact five then-existing M6 bundle directories, public M5 integrity,
upload payload hashes/target values and displayed values against saved metrics.
The three default/queued/normal runs share the deterministic fixture; the
initial and final normal arrays were bit-identical. All inspected bundle-file
hashes were unchanged by that verification. Its current directory membership
is not a reconstruction of earlier counters: the browser engineer separately
recorded three directories before and after the rejected RGB upload.

Full report (the closed-journal timing clarification is part of this capture):

```json
{
  "verified_utc": "2026-09-29T15:34:33.380474+00:00",
  "passed": true,
  "directory_membership": [
    "28198a64afee4fc8b4057da7fafb0706",
    "5f02e7b0a7b849da95b8f52693d61aa8",
    "706d7958d5ec407b83c1e6aed5caa329",
    "76d306c2dac04121aed6c3e3d1040ca4",
    "9e09d4cf1adb4c42a4b3d289def511ce"
  ],
  "directory_count": 5,
  "bundles": [
    {
      "name": "28198a64afee4fc8b4057da7fafb0706",
      "role": "default",
      "integrity": "passed",
      "verified_files": [
        "config.json",
        "input_target.png",
        "metrics.json",
        "phase.npy",
        "reconstruction_field.npy",
        "reconstruction_intensity.npy",
        "residual_history.npy",
        "source_amplitude.npy",
        "source_field.npy",
        "target_amplitude.npy",
        "target_intensity.npy"
      ],
      "metrics": {
        "intensity_mse": 0.00048156226704156393,
        "intensity_nmse": 0.011172364162158032,
        "intensity_psnr": 33.17347549693817
      },
      "shape": [
        64,
        64
      ]
    },
    {
      "name": "5f02e7b0a7b849da95b8f52693d61aa8",
      "role": "final_normal",
      "integrity": "passed",
      "verified_files": [
        "config.json",
        "input_target.png",
        "metrics.json",
        "phase.npy",
        "reconstruction_field.npy",
        "reconstruction_intensity.npy",
        "residual_history.npy",
        "source_amplitude.npy",
        "source_field.npy",
        "target_amplitude.npy",
        "target_intensity.npy"
      ],
      "metrics": {
        "intensity_mse": 0.00048156226704156393,
        "intensity_nmse": 0.011172364162158032,
        "intensity_psnr": 33.17347549693817
      },
      "shape": [
        64,
        64
      ]
    },
    {
      "name": "706d7958d5ec407b83c1e6aed5caa329",
      "role": "queued",
      "integrity": "passed",
      "verified_files": [
        "config.json",
        "input_target.png",
        "metrics.json",
        "phase.npy",
        "reconstruction_field.npy",
        "reconstruction_intensity.npy",
        "residual_history.npy",
        "source_amplitude.npy",
        "source_field.npy",
        "target_amplitude.npy",
        "target_intensity.npy"
      ],
      "metrics": {
        "intensity_mse": 0.00048156226704156393,
        "intensity_nmse": 0.011172364162158032,
        "intensity_psnr": 33.17347549693817
      },
      "shape": [
        64,
        64
      ]
    },
    {
      "name": "76d306c2dac04121aed6c3e3d1040ca4",
      "role": "upload_b",
      "integrity": "passed",
      "verified_files": [
        "config.json",
        "input_target.png",
        "metrics.json",
        "phase.npy",
        "reconstruction_field.npy",
        "reconstruction_intensity.npy",
        "residual_history.npy",
        "source_amplitude.npy",
        "source_field.npy",
        "target_amplitude.npy",
        "target_intensity.npy"
      ],
      "metrics": {
        "intensity_mse": 0.0002361950551546137,
        "intensity_nmse": 0.0037496541653878803,
        "intensity_psnr": 36.26729198769687
      },
      "shape": [
        64,
        64
      ]
    },
    {
      "name": "9e09d4cf1adb4c42a4b3d289def511ce",
      "role": "upload_a",
      "integrity": "passed",
      "verified_files": [
        "config.json",
        "input_target.png",
        "metrics.json",
        "phase.npy",
        "reconstruction_field.npy",
        "reconstruction_intensity.npy",
        "residual_history.npy",
        "source_amplitude.npy",
        "source_field.npy",
        "target_amplitude.npy",
        "target_intensity.npy"
      ],
      "metrics": {
        "intensity_mse": 0.0009447802206184539,
        "intensity_nmse": 0.003749654165387877,
        "intensity_psnr": 30.24669207441725
      },
      "shape": [
        64,
        64
      ]
    }
  ],
  "uploads": [
    {
      "role": "upload_a",
      "fixture": "C:\\holographiclab\\runs\\m6_acceptance_20260929\\browser_fixtures\\a\\same.png",
      "sha256": "337692daf7da609effc2f0cb8ee081a5860ada1e21009aa57225e16fd8151154",
      "bytes": 4228,
      "expected_intensity": 0.5019607843137255,
      "exact_target_match": true
    },
    {
      "role": "upload_b",
      "fixture": "C:\\holographiclab\\runs\\m6_acceptance_20260929\\browser_fixtures\\b\\same.png",
      "sha256": "75fd3466cbfe6a96e5110d21c3118b6139289381d45e7423f7cbdb11f05e2bff",
      "bytes": 4228,
      "expected_intensity": 0.25098039215686274,
      "exact_target_match": true
    }
  ],
  "display": [
    {
      "role": "default",
      "snapshot": "browser_default.txt",
      "metrics_match_saved_values": true,
      "source_power": 2.2575937254901972e-08,
      "target_power": 2.257593725490196e-08,
      "intensity_display_max": 1.0513181064993404
    },
    {
      "role": "final_normal",
      "snapshot": "browser_final_generate.txt",
      "metrics_match_saved_values": true,
      "source_power": 2.2575937254901972e-08,
      "target_power": 2.257593725490196e-08,
      "intensity_display_max": 1.0513181064993404
    }
  ],
  "default_and_final_arrays_bit_identical": true,
  "all_bundle_file_hashes_unchanged": true,
  "bundle_hashes": {
    "28198a64afee4fc8b4057da7fafb0706\\config.json": "a86b085ffede18c89fab57a31a8caf695f1ef37e3d6e09b674472f11ece69c3a",
    "28198a64afee4fc8b4057da7fafb0706\\input_target.png": "b5fd28fda2ccb077674a0302c49e3d68fe574ab754f7e10e3f0a5f853afbc376",
    "28198a64afee4fc8b4057da7fafb0706\\manifest.json": "e651979b8d8489ccb3953dfa5426b8bfb63453fa69de838294ea371eac6f7623",
    "28198a64afee4fc8b4057da7fafb0706\\metrics.json": "ff7c5286632361b79fbf0117ed2fd8e579afc2e41bd55e4a184a2aa1b4132b8a",
    "28198a64afee4fc8b4057da7fafb0706\\phase.npy": "99c5048b7a632c476143a56aec1d45d5fd58755b0c99de0271269a7a5e73f9a0",
    "28198a64afee4fc8b4057da7fafb0706\\reconstruction_field.npy": "733ec6aad8f2410a6797264565e2b286788a38d8604740e0c1edc4be504fc1a0",
    "28198a64afee4fc8b4057da7fafb0706\\reconstruction_intensity.npy": "5127b55787641b651f1a42684eb20d64176e0bc72a8128d62e74c9e7bb8ce946",
    "28198a64afee4fc8b4057da7fafb0706\\residual_history.npy": "4eae8ffe04b34a3c88ee06902f4b7e40100e395a9fea398f9c081257da3c2c53",
    "28198a64afee4fc8b4057da7fafb0706\\source_amplitude.npy": "da41d91162404f5df324da2e5af98aa99bad4168998b82ada1eecc4f5df6494b",
    "28198a64afee4fc8b4057da7fafb0706\\source_field.npy": "690783925fdc18bd2f342b91e4f1d513eefb8f30e4b8cb431167faa738b779ed",
    "28198a64afee4fc8b4057da7fafb0706\\target_amplitude.npy": "f0488c042c675d66825a6cab50a0a5bb3e1c5a1608d699e14974a9160f621208",
    "28198a64afee4fc8b4057da7fafb0706\\target_intensity.npy": "b55b64b685ff674ee5ba8b185ac3c75aab0932924175146474b9a29b63e420ff",
    "5f02e7b0a7b849da95b8f52693d61aa8\\config.json": "a86b085ffede18c89fab57a31a8caf695f1ef37e3d6e09b674472f11ece69c3a",
    "5f02e7b0a7b849da95b8f52693d61aa8\\input_target.png": "b5fd28fda2ccb077674a0302c49e3d68fe574ab754f7e10e3f0a5f853afbc376",
    "5f02e7b0a7b849da95b8f52693d61aa8\\manifest.json": "e651979b8d8489ccb3953dfa5426b8bfb63453fa69de838294ea371eac6f7623",
    "5f02e7b0a7b849da95b8f52693d61aa8\\metrics.json": "ff7c5286632361b79fbf0117ed2fd8e579afc2e41bd55e4a184a2aa1b4132b8a",
    "5f02e7b0a7b849da95b8f52693d61aa8\\phase.npy": "99c5048b7a632c476143a56aec1d45d5fd58755b0c99de0271269a7a5e73f9a0",
    "5f02e7b0a7b849da95b8f52693d61aa8\\reconstruction_field.npy": "733ec6aad8f2410a6797264565e2b286788a38d8604740e0c1edc4be504fc1a0",
    "5f02e7b0a7b849da95b8f52693d61aa8\\reconstruction_intensity.npy": "5127b55787641b651f1a42684eb20d64176e0bc72a8128d62e74c9e7bb8ce946",
    "5f02e7b0a7b849da95b8f52693d61aa8\\residual_history.npy": "4eae8ffe04b34a3c88ee06902f4b7e40100e395a9fea398f9c081257da3c2c53",
    "5f02e7b0a7b849da95b8f52693d61aa8\\source_amplitude.npy": "da41d91162404f5df324da2e5af98aa99bad4168998b82ada1eecc4f5df6494b",
    "5f02e7b0a7b849da95b8f52693d61aa8\\source_field.npy": "690783925fdc18bd2f342b91e4f1d513eefb8f30e4b8cb431167faa738b779ed",
    "5f02e7b0a7b849da95b8f52693d61aa8\\target_amplitude.npy": "f0488c042c675d66825a6cab50a0a5bb3e1c5a1608d699e14974a9160f621208",
    "5f02e7b0a7b849da95b8f52693d61aa8\\target_intensity.npy": "b55b64b685ff674ee5ba8b185ac3c75aab0932924175146474b9a29b63e420ff",
    "706d7958d5ec407b83c1e6aed5caa329\\config.json": "a86b085ffede18c89fab57a31a8caf695f1ef37e3d6e09b674472f11ece69c3a",
    "706d7958d5ec407b83c1e6aed5caa329\\input_target.png": "b5fd28fda2ccb077674a0302c49e3d68fe574ab754f7e10e3f0a5f853afbc376",
    "706d7958d5ec407b83c1e6aed5caa329\\manifest.json": "e651979b8d8489ccb3953dfa5426b8bfb63453fa69de838294ea371eac6f7623",
    "706d7958d5ec407b83c1e6aed5caa329\\metrics.json": "ff7c5286632361b79fbf0117ed2fd8e579afc2e41bd55e4a184a2aa1b4132b8a",
    "706d7958d5ec407b83c1e6aed5caa329\\phase.npy": "99c5048b7a632c476143a56aec1d45d5fd58755b0c99de0271269a7a5e73f9a0",
    "706d7958d5ec407b83c1e6aed5caa329\\reconstruction_field.npy": "733ec6aad8f2410a6797264565e2b286788a38d8604740e0c1edc4be504fc1a0",
    "706d7958d5ec407b83c1e6aed5caa329\\reconstruction_intensity.npy": "5127b55787641b651f1a42684eb20d64176e0bc72a8128d62e74c9e7bb8ce946",
    "706d7958d5ec407b83c1e6aed5caa329\\residual_history.npy": "4eae8ffe04b34a3c88ee06902f4b7e40100e395a9fea398f9c081257da3c2c53",
    "706d7958d5ec407b83c1e6aed5caa329\\source_amplitude.npy": "da41d91162404f5df324da2e5af98aa99bad4168998b82ada1eecc4f5df6494b",
    "706d7958d5ec407b83c1e6aed5caa329\\source_field.npy": "690783925fdc18bd2f342b91e4f1d513eefb8f30e4b8cb431167faa738b779ed",
    "706d7958d5ec407b83c1e6aed5caa329\\target_amplitude.npy": "f0488c042c675d66825a6cab50a0a5bb3e1c5a1608d699e14974a9160f621208",
    "706d7958d5ec407b83c1e6aed5caa329\\target_intensity.npy": "b55b64b685ff674ee5ba8b185ac3c75aab0932924175146474b9a29b63e420ff",
    "76d306c2dac04121aed6c3e3d1040ca4\\config.json": "a86b085ffede18c89fab57a31a8caf695f1ef37e3d6e09b674472f11ece69c3a",
    "76d306c2dac04121aed6c3e3d1040ca4\\input_target.png": "75fd3466cbfe6a96e5110d21c3118b6139289381d45e7423f7cbdb11f05e2bff",
    "76d306c2dac04121aed6c3e3d1040ca4\\manifest.json": "4d75f6307f5ec6fc5d26a3e3a1ff2fb4cc3371e841481b3fd7efbc964f4d74cc",
    "76d306c2dac04121aed6c3e3d1040ca4\\metrics.json": "ce857b2954d39e7368866599165cc5a49078347a0fe46dfa46217d1e60ecbdc5",
    "76d306c2dac04121aed6c3e3d1040ca4\\phase.npy": "011d343428d4d3e3c0e8d6acf2b5a709903586af67183983b8123d28f44387a5",
    "76d306c2dac04121aed6c3e3d1040ca4\\reconstruction_field.npy": "0489757c2ef81c6d5d1cc973c49e5ba632d167daa997be0103d1b09d487a1f24",
    "76d306c2dac04121aed6c3e3d1040ca4\\reconstruction_intensity.npy": "669ff6beb2bd6aeff3fd4190e687fe77dc83371439da28a93bcadbc33d633a4d",
    "76d306c2dac04121aed6c3e3d1040ca4\\residual_history.npy": "6cf5dddbba3737f1406ba09f755448af3f37f7df326d5f4972f3bd8e2b889e55",
    "76d306c2dac04121aed6c3e3d1040ca4\\source_amplitude.npy": "a183e4c3a6fdb0073de3f01cdf9d9322245ce2029efe9b4d50b59be5eacf2a97",
    "76d306c2dac04121aed6c3e3d1040ca4\\source_field.npy": "b4bd35ba8d066c78fe1fa2378d6fa8b399e84f0091929fa1250fa9c0f090771d",
    "76d306c2dac04121aed6c3e3d1040ca4\\target_amplitude.npy": "a183e4c3a6fdb0073de3f01cdf9d9322245ce2029efe9b4d50b59be5eacf2a97",
    "76d306c2dac04121aed6c3e3d1040ca4\\target_intensity.npy": "bd4e37c743f23088ded27f04f38df6fe012be1e8334e69fcedb62f80aa2b8b32",
    "9e09d4cf1adb4c42a4b3d289def511ce\\config.json": "a86b085ffede18c89fab57a31a8caf695f1ef37e3d6e09b674472f11ece69c3a",
    "9e09d4cf1adb4c42a4b3d289def511ce\\input_target.png": "337692daf7da609effc2f0cb8ee081a5860ada1e21009aa57225e16fd8151154",
    "9e09d4cf1adb4c42a4b3d289def511ce\\manifest.json": "9f2272369bf57832986eb01f369c7d3bbef82193e83a3269fe04dd4da96bd196",
    "9e09d4cf1adb4c42a4b3d289def511ce\\metrics.json": "1bbcb44e89844b1af55c7dabbcf6801a999ac8d9da18b3c797ebc914d73dd585",
    "9e09d4cf1adb4c42a4b3d289def511ce\\phase.npy": "5e8c83862a1895fa35b69b61f6db44173b549b00e876cbf8fa4e9de0024616d7",
    "9e09d4cf1adb4c42a4b3d289def511ce\\reconstruction_field.npy": "b77005176a6bf0f814db5a1174054616e3d36e65f93042ee653991a53ad60881",
    "9e09d4cf1adb4c42a4b3d289def511ce\\reconstruction_intensity.npy": "6c415a0f30787b14032cc5cc5bba61cf926f6134c959e0554cbe1dd68c8f807f",
    "9e09d4cf1adb4c42a4b3d289def511ce\\residual_history.npy": "28dc07a72b0658fb34a3b3d56683ade66caca5b0d7bdfc9637ff534c1d63192d",
    "9e09d4cf1adb4c42a4b3d289def511ce\\source_amplitude.npy": "a721bc63b066ff154c0ca9a6f194c00874b748d41aa18168eea168aec951d16a",
    "9e09d4cf1adb4c42a4b3d289def511ce\\source_field.npy": "6c3edfddef17cc11534e6633b7d5a0b6ca7639d40ad872f7428a28ba98ebe644",
    "9e09d4cf1adb4c42a4b3d289def511ce\\target_amplitude.npy": "a721bc63b066ff154c0ca9a6f194c00874b748d41aa18168eea168aec951d16a",
    "9e09d4cf1adb4c42a4b3d289def511ce\\target_intensity.npy": "a768a599f358c63594a53611a98f384e3fbe79f002a7ec84c3d8fe88a9848ed4"
  },
  "queued_evidence": {
    "prior_report": "C:\\holographiclab\\runs\\m6_acceptance_20260929\\browser-queued-verification-9511d0c1a55849a4962203ee21bf384e.json",
    "prior_report_sha256": "cbe78d7b7192dd63e1d9746ad0ab666943a48257d17265e407b36116b8c2d675",
    "log_sha256_unchanged": true,
    "accepted": 1,
    "save_started": 1,
    "save_completed": 1,
    "busy_old_nonce_receipts": 1,
    "old_nonce_callbacks_rejected": 1,
    "clarification": "Parent reports owned instrumented server stopped at 2026-09-29T14:34:44Z. The prior verifier read the closed log at 14:35:28-14:35:38Z. Its seconds_after_save_observed=131.180063 is elapsed time at verification, not live-server observation duration. Log has no further save after its one completed save. No active monitoring claim is made.",
    "limits": "One finite real-browser sequence with controlled callback latency; rejected callback ran while busy. Separate AppTest covers old callback after completion. No durable exactly-once guarantee."
  },
  "invalid_rgb_counter_provenance": "Parent browser tool observations recorded 3 directories before and after rejected RGB upload. This verifier independently establishes only current exact five-member set, not the historical counters."
}
```

### Observed transport log errors

The task-owned server02, server03 and server04 stderr captures each contain a
`ConnectionResetError: [WinError 10054]` from the Windows asyncio Proactor
connection-close callback. Their appearance was near restart/reload or tab
closure; that timing does not establish a root cause. No clean-server-log claim
is made. The server remained responsive and subsequent fresh-session Open,
strict/diagnostic replay and screenshot inspection succeeded. These transport
messages are preserved separately from successful bundle/test outcomes.

Exact server02 stderr:

```text
2026-09-29 22:32:53.906 Uvicorn server started on 127.0.0.1:8501
Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)
handle: <Handle _ProactorBasePipeTransport._call_connection_lost(None)>
Traceback (most recent call last):
  File "C:\Users\jimli\AppData\Local\Programs\Python\Python311\Lib\asyncio\events.py", line 84, in _run
    self._context.run(self._callback, *self._args)
  File "C:\Users\jimli\AppData\Local\Programs\Python\Python311\Lib\asyncio\proactor_events.py", line 165, in _call_connection_lost
    self._sock.shutdown(socket.SHUT_RDWR)
ConnectionResetError: [WinError 10054] 遠端主機已強制關閉一個現存的連線。
```

Exact server03 stderr:

```text
2026-09-29 22:34:45.099 Uvicorn server started on 127.0.0.1:8501
Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)
handle: <Handle _ProactorBasePipeTransport._call_connection_lost(None)>
Traceback (most recent call last):
  File "C:\Users\jimli\AppData\Local\Programs\Python\Python311\Lib\asyncio\events.py", line 84, in _run
    self._context.run(self._callback, *self._args)
  File "C:\Users\jimli\AppData\Local\Programs\Python\Python311\Lib\asyncio\proactor_events.py", line 165, in _call_connection_lost
    self._sock.shutdown(socket.SHUT_RDWR)
ConnectionResetError: [WinError 10054] 遠端主機已強制關閉一個現存的連線。
```

Exact server04 stderr:

```text
2026-09-29 23:34:04.207 Uvicorn server started on 127.0.0.1:8501
Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)
handle: <Handle _ProactorBasePipeTransport._call_connection_lost(None)>
Traceback (most recent call last):
  File "C:\Users\jimli\AppData\Local\Programs\Python\Python311\Lib\asyncio\events.py", line 84, in _run
    self._context.run(self._callback, *self._args)
  File "C:\Users\jimli\AppData\Local\Programs\Python\Python311\Lib\asyncio\proactor_events.py", line 165, in _call_connection_lost
    self._sock.shutdown(socket.SHUT_RDWR)
ConnectionResetError: [WinError 10054] 遠端主機已強制關閉一個現存的連線。
```

## Clean-postcommit gate and final scope verification

The precommit scope audit recorded the exact twenty approved paths below
and byte preservation for all 111 protected files out of the 114-file tracked
baseline (only README, the ledger and pyproject are approved modifications).
The audit was taken before final evidence-document assembly, so its candidate
document hashes are historical; staging must check the final bytes separately.

```text
.streamlit/config.toml
README.md
apps/__init__.py
apps/presentation.py
apps/provenance.py
apps/streamlit_app.py
apps/workbench.py
docs/handoffs/milestone_6/code_map.md
docs/handoffs/milestone_6/figures/fig01_create_and_inspect.png
docs/handoffs/milestone_6/figures/fig02_verify_and_replay.png
docs/handoffs/milestone_6/implementation_summary.md
docs/handoffs/milestone_6/known_limitations.md
docs/handoffs/milestone_6/math_used.md
docs/handoffs/milestone_6/tests_and_evidence.md
docs/handoffs/milestone_6/tutor_context.md
docs/milestones.md
pyproject.toml
tests/test_workbench_architecture.py
tests/test_workbench_controller.py
tests/test_workbench_streamlit.py
```

The automated/candidate evidence above does not claim qualified replay under
a final M6 commit. After all precommit acceptance passes, the approved single
commit is `feat(m6): add local holographic workbench`. Restart from that clean
checkout, use the real UI to create a fresh small run, and perform strict
replay with diagnostics off. Required outcomes are integrity `passed`,
qualification `qualified`, comparison `passed`, and displayed arrays/settings
corresponding to that saved run. Old M5 bundles need not qualify under M6.

Record the actual final SHA, fresh-run identity, UI observations and output in
ignored captures and the completion report. Do not fabricate them here or
create a self-referential screenshot/documentation commit chain. A failed
postcommit gate stops the push without rewriting history.

Final acceptance also requires the exact twenty-path inventory, preservation
of protected tracked files, normal push and matching local/live-remote/GitHub
API SHAs, a clean working tree, and cleanup or explicit retention reporting
for only task-owned servers/browser sessions. These are publication checks,
not implied by the test summary.
