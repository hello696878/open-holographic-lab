# Milestone 5 — Configuration, integrity and replay

Recorded **2026-09-23**, from accepted M4 baseline
`5b8e278d2f105552d8ef7d951aaa5161c01c801a`. M5 adds a filesystem boundary
around the unchanged M2, M3 and M4 public functions. It captures inputs,
computes one coherent run, publishes typed arrays and metadata, and can
verify and replay that run. Numerical algorithms, units and normalization
remain unchanged. Normative contract: [§3.15](../../math_conventions.md#315-configuration-artifact-integrity-and-numerical-replay), version 0.8.
Actual validation and publication evidence is recorded separately in
[tests and evidence](tests_and_evidence.md).
Initial implementation and baseline/probe captures on 2026-09-22 retain their
original dates in that evidence; this date records the completed handoff.

## Public API

Import `RunConfig` from `ohlab.io.config`; import the four functions below
from `ohlab.io.artifacts`. Package root exports remain unchanged. The private
return-record names in these signatures describe results, not additional
public constructors or a configuration framework.

```python
class RunConfig:
    def __init__(self, settings: Mapping[str, object]) -> None: ...
    def to_dict(self) -> dict[str, object]: ...

def run_and_save_bundle(
    path: str | os.PathLike[str], *, config: RunConfig,
    target_intensity: NDArray[np.float64],
    source_amplitude: NDArray[np.float64],
    source_revision: Mapping[str, object] | None = None,
    initial_phase: NDArray[np.float64] | None = None,
    signal_mask: NDArray[np.bool_] | None = None,
    cv_mask: NDArray[np.bool_] | None = None,
    input_png: str | os.PathLike[str] | None = None,
) -> _RunBundle: ...

def verify_run_bundle(path: str | os.PathLike[str]) -> _IntegrityReport: ...
def load_run_bundle(path: str | os.PathLike[str]) -> _RunBundle: ...
def replay_run_bundle(
    path: str | os.PathLike[str], *,
    source_revision: Mapping[str, object] | None = None,
    diagnostic: bool = False,
) -> _ReplayReport: ...
```

`RunConfig` validates scientific settings and retains only immutable canonical
JSON bytes. It retains no caller-owned nested dictionaries; `to_dict()` returns
a fresh deep dictionary. Changing either the original settings or an exported
dictionary cannot bypass validation or change the instance.

Returned bundle records are frozen and provide:

| Attribute | Contract |
|---|---|
| `path` | Absolute bundle `Path` |
| `config` | Immutable scientific `RunConfig` |
| `arrays` | Read-only mapping from logical role to owned, C-contiguous, read-only ndarray |
| `metrics` | Read-only mapping from requested metric name to Python float |
| `software` | Fresh deep dictionary of recorded provenance/environment on each access |

A successful integrity report has `status == "passed"` and `files`, the
sorted tuple of hashed artifact filenames, excluding the manifest. Corruption,
invalid schema or filesystem failures raise; they do not return a successful
report with a hidden failure. Verification also validates array structure and
domains, but does not run the solver or recompute metrics.

A replay report independently exposes `integrity`, `qualification`,
`comparison`, `qualification_reasons`, `checks`, `recorded_source` and
`current_source`. The mappings are read-only. Qualification is `qualified` or
`unqualified`; comparison is `passed`, `failed` or `not_run`. A returned report
has passed integrity; earlier integrity failures raise. Valid computation
whose values differ produces failed checks. Errors that prevent numerical
computation can still raise rather than producing a comparison report.

Wrong input types/dtypes raise `TypeError`; invalid schema, domains and
integrity raise `ValueError`. Filesystem `OSError` subclasses retain their
diagnosis, including `FileExistsError` for an existing destination. There is
no automatic environment repair, fallback decoding or invalid-metric omission.

## Scientific settings and input capture

The exact top-level settings keys are `schema_version`, `grid`, `optics`,
`solver` and `metrics`. Schema version is integer `1`.

| Section | Exact contents |
|---|---|
| `grid` | `ny`, `nx`: positive built-in integers fitting `sys.maxsize`; `dy_m`, `dx_m`: positive finite binary64 values |
| `optics` | Positive finite `wavelength_m`; finite signed `distance_m`, including signed zero |
| `solver` | `algorithm="gerchberg_saxton"`, `contract="m3_periodic_lossless_asm_v1"`, nonnegative `iterations` no greater than `sys.maxsize-1`, and `initialization` |
| Seed initialization | Exactly `{"mode": "seed", "seed": nonnegative_integer}` |
| Explicit phase | Exactly `{"mode": "explicit_phase", "artifact": "initial_phase.npy"}` |
| `metrics` | Any subset, including empty, of the five supported names and their exact parameters below |

Real scalar settings accept built-in Python integers/floats and retain finite
binary64 values; booleans and NumPy scalar types are not accepted as settings.
Lengths are metres and phase is radians. Structural configuration validity
does not establish usable optical geometry, compatible powers or defined
metrics; the existing public functions enforce those conditions when run.

MSE and NMSE use `{}` parameters. PSNR requires `{"data_range": positive_value}`.
The fraction requires `{"mask": "signal_mask.npy"}`; CV requires
`{"mask": "cv_mask.npy"}`. The masks may differ. Unknown/missing keys,
unsupported versions and inconsistent initialization modes are rejected.

Schema v1 accepts M2 normalized design intensity in `[0,1]`; source amplitude
is explicit, finite and nonnegative, without an upper-one restriction.
Inputs must be plain native-float64 arrays of exactly `(ny,nx)`; masks must be
plain Boolean arrays of that shape. Explicit phase is finite float64 on any
branch. Required optional arrays must be supplied exactly when configured;
unused masks or an extra initial phase are rejected.

The wrapper makes owned C-contiguous snapshots without casting, changing
logical element bits, normalizing or retaining caller storage. It calls public
M2 to obtain target amplitude, then public M3 using the original seed or the
captured explicit phase. It does not regenerate seed phase independently or
perform an additional initialization solve. M3 checks power compatibility and
its periodic lossless model. M4 measures the same reconstruction-intensity
snapshot that is saved. Callers cannot supply unrelated output arrays or
metric values to this writer.

## Bundle contents and representation

Every completed bundle contains `config.json`, `manifest.json`, `metrics.json`
and the following eight arrays:

| Role / filename stem | Meaning and storage |
|---|---|
| `target_intensity` | Authoritative M2 design, float64 |
| `target_amplitude` | Actual M3 input, float64; also checked against public M2 conversion during replay |
| `source_amplitude` | Authoritative prescribed illumination, float64 |
| `source_field` | Authoritative actual final source, complex128 |
| `reconstruction_field` | Authoritative actual forward reconstruction, complex128 |
| `residual_history` | Authoritative M3 amplitude residuals, float64 shape `(iterations+1,)` |
| `phase` | Saved float64 derivation from the actual source, checked during replay |
| `reconstruction_intensity` | Saved float64 derivation from the reconstruction, checked during replay |

Array filenames are the role plus `.npy`. `initial_phase.npy`,
`signal_mask.npy` and `cv_mask.npy` are conditional on configuration.
`input_target.png` exists only when PNG provenance was supplied. The actual
complex source is retained; rebuilding it from phase and amplitude is not
treated as a lossless replacement.

Persisted `config.json` adds fixed `target`, `source`, `replay` and `software`
sections to the scientific settings. Target representation is
`normalized_m2_intensity`, mapping is `sqrt_intensity`, references are the two
target filenames, and `input_png` is null or `input_target.png`. Source
references `source_amplitude.npy`. Replay declares `criterion="bitwise_v1"`
and `array_order="C"`. No original absolute input path is authoritative.

JSON is UTF-8, sorted by keys, indented two spaces, with LF and a final newline.
Writers use `allow_nan=False`. Readers reject duplicate keys and nonstandard
constants, then validate numeric finiteness/domains independently. Ordinary
finite JSON numbers preserve the supported binary64 scalar representation.
`metrics.json` contains exactly `schema_version` and `values`; names must match
the requested metrics. Only positive-infinite PSNR uses the string `"+inf"`.
Other metrics remain finite numbers. Negative PSNR and M4's finite rounding
results are retained, including a fraction slightly above one from different
reduction orders; the I/O boundary adds no clipping or tighter upper bound.

NPY is version 1.0, C-order, with only role-defined simple float64, complex128
or Boolean dtype. The reader checks the bounded 10,000-byte header, version,
dtype, shape, order and exact payload length before `np.load` with
`allow_pickle=False`. Object/structured arrays, NPZ, other NPY versions,
truncation and trailing bytes are rejected. Manifest metadata must agree
independently with the role, config and header. Stored byte order is retained
when loading, without conversion.

The manifest contains `schema_version=1`, `hash_algorithm="sha256"` and a
path-sorted `artifacts` list. Each entry has `logical_name`, `path`,
`size_bytes`, `sha256`; arrays additionally have `dtype`, `shape`, `order`.
Hashes cover whole file bytes, including config, metrics and NPY headers.
The manifest excludes itself. Only schema-defined flat filenames are accepted;
duplicate paths/wrong roles, missing/extra files, links and reparse entries
are rejected. Every artifact digest passes before configuration, metrics or
arrays are interpreted. Loading decodes these same verified byte snapshots.

For PNG capture, the wrapper copies the exact bytes into its staging directory,
decodes that copy with public M2, and requires exact agreement with the captured
target. Later load/replay hashes the retained PNG but does not decode it or
need its former external path. Array-only runs require no original PNG.

## Qualification, replay and publication

`source_revision` is exactly `{revision, state, method}`. State is `clean`,
`dirty` or `unavailable`; method is `git` or `caller`. Clean/dirty records require
a 40-character lowercase hexadecimal SHA; unavailable requires null. Omission
records unavailable caller provenance. The reusable API never invokes Git.
Caller-supplied metadata remains a claim, not attestation of executing code.
The example independently anchors Git detection to the imported package's
checkout and verifies its tracked `src/ohlab/__init__.py` location.

Qualification requires both sources clean with equal revisions, equal package
version and exact equality of all `required_environment` fields: Python
implementation/full version, NumPy/SciPy versions, Pillow version when PNG was
captured (otherwise null), platform, machine, processor, byte order, pointer
width and FFT identifier `numpy.fft`. Source `method` stays visible but is not
an equality gate. Python executable path and CPU count are informational.
Current runtime information is collected independently, never copied from the
bundle. Matching metadata is a bounded qualification policy, not a universal
determinism or authenticity guarantee.

Unqualified default replay reports `not_run`. Explicit diagnostic replay may
compute and compare but remains unqualified. Replay checks saved derivations,
recomputes metrics on saved intensity, runs M3 from saved actual input amplitudes
and the original initialization, then compares all five output arrays and
newly computed metrics. Arrays require equal dtype representation, shape and
C-order bytes; finite metric values require identical binary64 bits, while
PSNR infinity is compared separately. There is no tolerance fallback.
Foreign-endian arrays remain inspectable; attempted diagnostic numerical replay
reports a failed native-byte-order gate and comparison `not_run`, instead of
casting into the core or implying that numerical comparisons executed.

The destination's parent must exist. Saving refuses existing destinations,
uses an exclusive reserved temporary sibling, exclusively creates artifacts,
flushes/fsyncs/closes files, writes the manifest last, verifies staged contents,
and renames on the same filesystem. Public readers reject reserved partial
directory names. Ordinary failure cleanup removes only paths registered after
successful exclusive creation, preserves the original error, and adds notes
if cleanup leaves staging behind. Windows no-clobber publication behavior is
tested; there is no concurrent POSIX-writer or power-loss durability promise.

On Windows only, publication retries `PermissionError` with `winerror == 5`
while the destination remains absent: at most four rename attempts, separated
by waits of 10, 30 and 100 milliseconds (140 milliseconds total explicit
waiting). Destination existence is checked before and after each wait. No
other error is retried, and exhaustion raises the first access-denial error
for ordinary owned cleanup. This adds no overwrite, lock or copy fallback.
Candidate validation encountered intermittent access denials during ordinary
rename, including outside the sandbox; a separate 100-save probe did not
reproduce them. No handle leak or cause was identified. Exact observations and
retry safety checks are recorded in [tests and evidence](tests_and_evidence.md).

Precommit evidence explicitly records dirty candidate code. The approved final
workflow separately runs a fresh example after the single clean M5 commit,
before pushing. That output belongs in ignored run captures and the completion
report, not a self-referential documentation-commit sequence. No final SHA or
postcommit success is inferred here. M6 remains outside this handoff.

The standalone headless example and diagram generator run from the repository
root with the existing interpreter:

```powershell
.\.venv\Scripts\python.exe -B examples\run_bundle.py
.\.venv\Scripts\python.exe -B scripts\make_m5_figures.py
```
