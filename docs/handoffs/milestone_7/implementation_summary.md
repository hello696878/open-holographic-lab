# Milestone 7 — Editable 2D target designer

Implementation handoff prepared **2026-09-30**, from accepted M6 revision
`cc93c949da23de4a6f98acc0c4954c3c2d7f6849`. Current acceptance is recorded in
the [ledger](../../milestones.md); [tests and evidence](tests_and_evidence.md)
separates implemented contracts from performed validation. Precommit acceptance
is complete: automated checks, negative controls, the example, actual browser
interactions, genuine screenshots and scope checks are recorded. Clean
postcommit UI generation and strict qualified replay remain a pending
publication gate; this handoff does not claim a published M7 revision.

M7 creates editable desired-intensity drawings and connects them to the
existing local workbench. It adds no holography physics, solver, metric,
dependency, hardware path or M5 schema. The precise new contract is
[§3.16, version 0.9](../../math_conventions.md#316-editable-2d-designs-and-deterministic-rasterization).

## Public model and I/O

The public model is imported from `ohlab.target_design`:

```python
class TargetDesign2D:
    def __init__(self, spec: Mapping[str, object]) -> None: ...
    def to_dict(self) -> dict[str, object]: ...

def rasterize_target_design(
    design: TargetDesign2D,
) -> NDArray[np.float64]: ...
```

`TargetDesign2D` validates an immutable owned snapshot; `to_dict()` returns
fresh nested data. The design specifies its canvas, background, ordered
objects and versioned coordinate/rasterizer rules. The rasterizer returns a
fresh writable C-contiguous native-float64 intensity array. It does not
generate an amplitude, optical phase or complex field.

The public JSON/file boundary is imported from `ohlab.io.designs`:

```python
def design_to_json(design: TargetDesign2D) -> bytes: ...
def design_from_json(data: bytes) -> TargetDesign2D: ...
def save_design(
    path: str | os.PathLike[str], *, design: TargetDesign2D,
) -> Path: ...
def load_design(path: str | os.PathLike[str]) -> TargetDesign2D: ...
```

JSON is bounded strict UTF-8, with exact fields/versions, duplicate-key and
nonstandard-constant rejection. Canonical output sorts mapping keys, retains
object list order, uses two-space indentation, LF and a final newline.
Supported finite binary64 values retain their representation, including
signed zero. New destinations are exclusive; no overwrite or automatic
repair is offered. Input must be plain `bytes`; a UTF-8 BOM is not accepted.
Schema type errors remain `TypeError`; malformed encoding/syntax and invalid
values raise `ValueError`, while filesystem exceptions retain their diagnosis.

The parent directory must exist. Link/reparse paths and reserved partial
filenames are rejected. Saving exclusively creates an owned temporary sibling,
writes/fsyncs/closes it, rechecks destination absence and renames it. No retry,
directory creation or overwrite is added. Ordinary failure removes only its
owned partial; a cleanup error adds the leftover path to the original exception.
This is not a concurrent hostile-filesystem, POSIX-writer or power-loss
durability guarantee. Direct failure tests belong to
[tests and evidence](tests_and_evidence.md).

## Editing and geometry

The Designer mode offers add/select/edit/delete/reorder for disks, axis-aligned
rectangles and round-capped segments. Stable IDs are unique lowercase 32-digit
hexadecimal strings; selection is separate UI state. Object order is explicit,
and later objects overwrite earlier ones even at zero intensity. There is no
antialiasing, alpha blending, peak normalization or PNG quantization.

The canvas defines `(ny,nx)` and centered pixel coordinates. Resizing preserves
all object parameters and changes only the sampled window. Pitches determine
physical size, not raster content. Off-canvas geometry remains valid without
moving/wrapping. Segments are undirected: lexicographic internal endpoint
ordering makes reversal use the same arithmetic while retaining stored fields.
Coincident endpoints are a disk of radius half the width.
Required NumPy overflow/invalid/division errors or reported underflow raise
`ValueError`; local error-state handling restores caller settings. A
schema-valid drawing can therefore still fail geometric arithmetic explicitly.

Dimensions are 1–512, objects at most 64, JSON at most 256 KiB, coordinates
within ±4096 pixels, and positive sizes/radii no greater than 8192 pixels.
These resource policies do not establish optical sampling adequacy. Existing
run limits apply separately. A fully validated import replaces editor state
atomically; a failed import preserves the prior design and coherent selection.

## One submitted design, one numerical run

Preview edits rasterize only. Selection alone does not change draft identity.
Scientific settings, active mode, canonical design content, order and
rasterizer settings belong to draft identity; content edits label an earlier
result stale without replacing its saved arrays or settings.

An accepted Generate & Save action consumes its operation nonce before
side effects and captures the immutable design. Its canvas supplies the
submitted grid dimensions. The controller rasterizes, derives amplitude with
public M2 and checks positive finite power while explicitly selecting uniform
source amplitude `sqrt(sum(A_target**2)/A_target.size)`. It then saves
`runs/designs/submissions/<run-uuid>.json`. Only after that succeeds does one
public M5 call receive the actual float64 target and `input_png=None`, publishing
`runs/m7/<run-uuid>/`.

Snapshot storage failure prevents M5 execution. If M5 fails afterward, the
editable snapshot remains and is reported. Once M5 succeeds, its completed
bundle/path is recorded before presentation. Rendering failure does not
delete it, report a false pre-save failure or regenerate it. Busy/duplicate
event guards retain their active-session scope. No automatic generation
follows design load, import, mode change, browser reload or reopening.

Built-in and uploaded-PNG modes retain their existing behavior. M7 does not
loosen PNG decoding or alter M3/M4/M5 contracts. Zero designs remain valid for
preview/storage/export but cannot satisfy the solver's positive-power request.
Hard-edged drawings carry no inherited Gaussian convergence threshold.

## Editable documents and verified results stay separate

Saved editable copies live under `runs/designs`; submission files live under
its `submissions` child. Browser filenames never choose server paths.
Completed M5 bundles keep their exact inventory, schema and original bytes.

The explicit associated-design action first loads the bundle through M5,
then validates/rasterizes the external JSON and compares target shape, dtype
and C-order bytes. Missing, malformed and valid-but-mismatched designs do not
replace the editor or prevent numerical inspection/verification/replay.
Matching raster samples neither authenticate authorship nor prove a unique
original design. Replay always uses the run's saved actual arrays.

Changing modes or bundles revokes diagnostic opt-in. Integrity, qualification
and numerical comparison remain distinct. Candidate/older-source runs may be
unqualified, and strict replay must then remain `not_run`; only a separate
explicit diagnostic action permits comparison without upgrading qualification.

The [roadmap](../../roadmap.md) places the separately approved virtual optics
laboratory after this content-design work. No V-stage or lesson completion
is implied by M7.
