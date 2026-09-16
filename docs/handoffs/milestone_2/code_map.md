# Milestone 2 — Code map

All paths below are repository-relative. Read
[the implementation contract](implementation_summary.md) before modifying code.

| Path | Responsibility |
|---|---|
| `src/ohlab/targets.py` | Strict array validation; `grayscale8_to_intensity` and `intensity_to_amplitude` |
| `src/ohlab/io/__init__.py` | I/O package marker, with no eager decoder import |
| `src/ohlab/io/images.py` | Fixed PNG header contract, metadata rejection, lazy Pillow verification/decode, filesystem/decoder error split |
| `tests/test_targets.py` | Independent Decimal references, scaling, orientation, invalid inputs, ownership and determinism |
| `tests/test_images.py` | Encoded fixtures, strict formats/size, APNG/transparency, lifecycle, exceptions and optional import isolation |
| `tests/test_fft_conventions.py` | Existing C01–C11 coverage plus bounded C06 import guard and new guard cases; C07 body and numerical cases preserved |
| `examples/load_target.py` | Temporary default image or explicit user file; fixed-scale plots and residual report |
| `scripts/make_m2_figures.py` | Reproducible synthetic figures through the public APIs |
| `pyproject.toml` | Optional images extra; existing base/dev requirements retained |
| `src/ohlab/__init__.py` | Documentation-only orientation change; root API/version unchanged |
| `README.md` | User API/demo commands, setup boundary and current engineering orientation |
| `docs/math_conventions.md` | Normative §3.12 and version 0.5 Change Log |
| `docs/milestones.md` | Authoritative dated M2 acceptance and deferred work |
| `docs/handoffs/milestone_2/` | Six handoff documents and three figures |

## Data path

~~~text
caller SamplingGrid + plain uint8 array
    -> grayscale8_to_intensity -> float64 intensity
    -> intensity_to_amplitude -> float64 amplitude

caller SamplingGrid + path
    -> open/read fixed PNG header -> check IHDR dimensions/encoding
    -> read remaining encoded bytes -> close source file
    -> lazy Pillow -> verify metadata/integrity -> close image/stream
    -> reopen memory snapshot -> decode/check metadata -> copy uint8 raster
    -> final shape check -> grayscale8_to_intensity -> float64 intensity
~~~

`_require_target_array` reuses existing shape/dimension validators; it adds
the plain-ndarray, exact-dtype and grid contracts locally.
`intensity_to_amplitude` also reuses the finite-value validator.

`_validate_header` inspects only signature/first IHDR layout, dimensions,
bit depth and color type. It does not implement a chunk parser.
`_validate_decoded_metadata` uses public Pillow metadata.

`_assert_import_boundaries` in the C06 test parses ordinary imports with
`ast.walk` and resolves relative names from the source module package.
It is a bounded architecture regression guard, not a runtime sandbox or
general dependency analyzer.

## Figures

- [Code, intensity and amplitude](figures/fig01_code_intensity_amplitude.png):
  a rectangular code raster and the 256-code transfer curves.
- [Rectangular orientation](figures/fig02_rectangular_orientation.png):
  shapes `(5, 8)` and `(6, 7)`, unequal SI pitches, corner identities and
  the `N//2` physical origin.
- [Cross-image brightness](figures/fig03_cross_image_brightness.png):
  code maxima 64 and 128 on identical display scales; intensity ratio 2,
  amplitude ratio `sqrt(2)`.

No existing field, grid, propagation, validation or units implementation is
modified. There is no M3 algorithm, target class, phase assignment or web app.
