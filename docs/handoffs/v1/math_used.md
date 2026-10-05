# V1 mathematical and presentation contract

V1 adds a presentation/transport boundary. The normative scientific contract
remains [math_conventions.md](../../math_conventions.md), especially section
3.17, and the existing public V0 implementation. No optical convention,
propagation/source/lens formula, normalization or persistence schema changes.

## Scientific values and units

The exact `SequentialExperiment` schema uses metres internally, radians for
phase and arbitrary field-amplitude units. Grid axis 0 is row/y and axis 1 is
column/x. Sources remain Gaussian or uniform; components remain aligned
circular/rectangular apertures and ideal signed thin lenses. List order is
authoritative, including separate IDs at a shared z. Observation stays at or
downstream of the last component.

The frontend converts wavelength nm, transverse dimensions/pitches µm and
longitudinal positions/focal length mm only at numeric editor boundaries.
Python V0 performs authoritative validation. No browser optical solver exists.
The complete periodic grid, public M1 propagation and V0 numerical safeguards
are unchanged.

Intensity is the actual terminal `ComplexField.intensity`, in
amplitude-unit². Scalar `norm` is V0's complete-window sampled norm in
amplitude-unit²·m². V0's intensity and norm arithmetic use different equivalent
floating-point expressions; their small rounding differences are preserved.
V1 does not replace a norm with a newly reduced intensity array.

Stage delta is signed current-minus-previous norm. Ratio is current/previous
norm; undefined source or zero-incident ratios remain JSON `null`. A ratio is
not calibrated efficiency or an absorption claim. Supplied V0 values are
retained after finite/chain/consistency validation.

## Coordinates and surface geometry

Physical sample centers are

```text
x(column) = (column - floor(nx/2))*dx
y(row)    = (row    - floor(ny/2))*dy
```

The fixed schematic mapping is

```text
world.x = 1000*x_m
world.y = -1000*y_m
world.z = 100*z_m
```

One world unit is 1 mm transversely and 10 mm longitudinally. The y sign makes
increasing array rows physically y-down while world y points upward. Camera
orbit/pan/zoom changes no SI value. Cosmetic housings do not impose an aperture;
the axis guide is not a simulated volumetric beam.

Cell edges and center are

```text
x_left   = (-floor(nx/2)-0.5)*dx
x_right  = (nx-1-floor(nx/2)+0.5)*dx
y_top    = (-floor(ny/2)-0.5)*dy
y_bottom = (ny-1-floor(ny/2)+0.5)*dy
surface_center_x = ((nx-1)/2-floor(nx/2))*dx
surface_center_y = ((ny-1)/2-floor(ny/2))*dy
```

An even-axis surface is centered at `-pitch/2`; an odd-axis surface is centered
at zero. Detector aspect is the physical width/height `nx*dx/(ny*dy)`, not the
count ratio. The 512×512, 4 µm preset spans −1026 to +1022 µm per axis.

Original numerical rows are never reversed. Display-only texture RGBA reverses
rows explicitly because Three plane UV v increases toward world +y.
`flipY=false`, nearest filtering and disabled mipmaps are explicit. A sample's
UV center is `u=(column+0.5)/nx`, `v=1-(row+0.5)/ny`.

Picking uses half-open cells: physical left/top included, right/bottom excluded;
equivalently `0≤u<1` and `0<v≤1`. Nonfinite or outside clicks yield no pixel,
without clamping. Readout retains the original decoded float64 value.

The independent 3×4 fixture with dx=2 µm, dy=5 µm has x edges [−5,+3] µm,
y edges [−7.5,+7.5] µm and aspect 8/15. Distinct entries 11–14, 21–24,
31–34 detect axis/row reversal. The complementary 2×5 fixture checks odd x/even
y independently.

## Display transfer and resource bounds

The initial shared display interval is 0–10 amplitude-unit². RGBA conversion
maps that disclosed interval to an sRGB-coded grayscale byte; color clipping is
a display operation only. Raw maximum, saturation notice and pixel values
remain visible. No per-result automatic normalization hides aperture loss.
An explicit user automatic-range action modifies colors only. Zero results
remain valid black arrays.

The detector is unlit, its sRGB texture/output handling is explicit and tone
mapping is disabled. Intermediate-gray acceptance checks prevent an unintended
second transfer operation; cross-GPU screenshot bit identity is not claimed.

The z rail derives a position from browser viewing geometry, never an optical
formula. It previews one z value and commits only an order-valid release.
Near a degenerate viewing direction the rail is disabled, with numeric z
editing available. No rotations, transverse element movement or sorting exist.

V1 bounds are 512 samples per axis, eight components, no intermediate recorded
fields, 32,768 request bytes, 16,384 unpadded header bytes and 2.25 MiB response
bytes. These are application resource limits, not claims of optical sampling
accuracy. The drawing buffer is bounded to four million pixels and DPR ≤2.

## Transient binary representation

`OHLABV1\0` occupies eight bytes. The next uint32 little-endian value is the
unpadded UTF-8 header byte length; the following uint32 is reserved zero. Zero
padding aligns the payload to eight bytes, with
`payload_start=16+ceil(header_length/8)*8`. Descriptor offsets are relative to
payload start.

Exactly three arrays follow without gaps, overlaps or trailing data: C-order
intensity `[ny,nx]`, x metres `[nx]`, y metres `[ny]`, all `float64-le`.
Descriptor names, order, units, shape, offsets and byte lengths are validated.
Every value must be finite; intensity is nonnegative, coordinate centers must
match the echoed grid and the declared maximum must equal decoded maximum.
DataView decoding explicitly requests little-endian conversion. Fresh float64
buffers retain numerical readout precision; GPU/display products are not inputs.

Full schema/specification, active UUID and validated server digest checks occur
before publication. This protocol is a bounded transient response, not a
scientific archive, authenticated provenance or a qualified-replay contract.
