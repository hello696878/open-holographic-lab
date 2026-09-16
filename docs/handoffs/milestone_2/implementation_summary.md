# Milestone 2 — Target image loading

Implemented and validated on **2026-09-16** from accepted baseline
`157d1d6c9f5c433671a62da9b60512c8f007298b`. This delivers only target
preparation and its optional PNG boundary. Milestone 3 is not started.

## Public API

~~~python
from ohlab.targets import grayscale8_to_intensity, intensity_to_amplitude
from ohlab.io.images import load_target_intensity

grayscale8_to_intensity(grayscale: NDArray[np.uint8], *,
                       grid: SamplingGrid) -> NDArray[np.float64]
intensity_to_amplitude(intensity: NDArray[np.float64], *,
                       grid: SamplingGrid) -> NDArray[np.float64]
load_target_intensity(path: str | os.PathLike[str], *,
                      grid: SamplingGrid) -> NDArray[np.float64]
~~~

The array inputs are plain ndarrays, never subclasses, masked arrays or
array-like objects. Grayscale requires `uint8`; supplied intensity requires
native `float64`, finite values in `[0, 1]`. Both require exact shape
`grid.shape == (ny, nx)`. Grid is an existing `SamplingGrid`, with SI pitches.

The fixed design mapping is `I = g / 255` and `A = sqrt(I)`. All-zero targets
are valid. Each result is a fresh, writable, C-contiguous native `float64`
array; it shares no storage with the input. Input bytes and grid parameters
are preserved. Row `i`/column `j` stay at `(grid.x[j], grid.y[i])`, with
`+y` downward. No grid, wavelength or phase is inferred.

## Strict file boundary

Actual PNG content is checked regardless of extension. A supported file has:

- source bit depth 8 and grayscale color type 0;
- decoded mode `L`;
- no transparency and no APNG metadata, including single-frame APNG;
- declared and decoded shape exactly equal to the supplied grid.

The source file is opened normally. Only its fixed 33-byte signature/IHDR
header is initially read. Declared dimensions and source encoding are checked
before reading the rest of the encoded file, full pixel decoding or allocating
a target array. The remaining bytes form one in-memory snapshot.

Pillow is imported lazily. Verification and pixel decoding use separate
`BytesIO` streams and image objects from that same snapshot, reopening after
`verify()` as documented. Metadata is checked before both operations and
again after decoding; array shape is checked before conversion. Context
managers close source/image/stream resources on success and failure.

The explicit APNG test uses the public `get_format_mimetype() == "image/apng"`,
as well as the frame count. A valid one-frame APNG has `n_frames == 1` and
`is_animated == False` in the tested decoder, so those alone are insufficient.
Likewise, 2/4-bit grayscale sources decode to `L`: the fixed-header bit-depth
test is necessary. Only the fixed IHDR is parsed in production.

No resize, interpolation, crop, pad, transpose, automatic orientation,
gamma/profile transform, threshold, clipping, contrast stretch, peak
normalization or power normalization is performed. Gamma/sRGB/ICC/EXIF/DPI
metadata does not transform the raster or grid.

## Errors and resources

| Condition | Result |
|---|---|
| Wrong array/path/grid type, unsupported dtype or byte order | `TypeError` |
| Wrong array dimensions/shape, nonfinite or out-of-range intensity | `ValueError` |
| Unsupported/malformed signature or IHDR, wrong declared dimensions or encoding | `ValueError` with path/actual-versus-expected context |
| Identified decoder/integrity failure or unsupported decoded metadata | `ValueError` with path, stage and chained original exception |
| Missing file, permission, directory or device read failure | Original filesystem `OSError` subclass retained |
| Pillow package unavailable | Informative `ImportError` on loader use; core imports still succeed |
| Broken Pillow extension/internal import | Original import diagnosis retained, not relabeled as an absent extra |
| Pillow excessive-image-size protection | Existing Pillow error/warning behavior retained |

Only the memory-decoder block translates identified
`OSError`/`SyntaxError`/`ValueError`/`EOFError`/`struct.error`/`zlib.error`
failures. Real filesystem operations are outside that block. There is no
blanket `except Exception`, and no guarantee that every malformed PNG is
recognized by this finite boundary.

## Architecture and dependency scope

`targets.py` has array math and existing validators only. Disk decoding lives
in `io/images.py`; plotting/input-fixture creation lives in the example and
figure script. Root executable imports, `__all__` and version are unchanged.
No `ComplexField` is constructed and no propagation or hologram is computed.

`images = ["pillow>=10.0"]` is the new optional extra. Existing base NumPy/SciPy
and dev requirements are retained. The installed Pillow **12.3.0** was used;
no package was installed/upgraded and no editable metadata was refreshed.
Import-isolation subprocess checks do not establish compatibility with every
version allowed by the dependency range.

C06 permits ordinary PIL imports only in exact `io/images.py` and rejects
ordinary `ohlab.io` imports from every non-I/O source, including the root
initializer. Absolute/relative/aliased/function-local forms have bounded
regression cases. Other forbidden roots and the C07 RNG guard remain intact.
Dynamic import analysis is not implemented.

## Evidence and artifacts

The accepted 323-case baseline remains covered. New cases cover pure target
semantics, file decoding and the narrow architecture boundary. See
[tests and evidence](tests_and_evidence.md) for exact counts, unedited output,
tolerances, finite negative controls, environment and reproduction commands.

`examples/load_target.py` uses a deterministic temporary PNG by default,
supports an explicit user path/grid, and shows intensity/amplitude on fixed
`[0, 1]` display scales. `scripts/make_m2_figures.py` generates the three
committed illustrations. They explain tested contracts; they do not establish
physical propagation accuracy.

Existing numerical-core files, M0/M1 handoffs, correction evidence, AGENTS.md,
CLAUDE.md and old figures are unchanged. The six M2 handoff documents support a
separate tutoring conversation and assert no lesson completion.
