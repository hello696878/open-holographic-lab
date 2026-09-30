# Milestone 7 — From editable geometry to sampled intensity

The normative contract is [§3.16, version 0.9](../../math_conventions.md#316-editable-2d-designs-and-deterministic-rasterization).
M7 adds a discrete desired-intensity construction, not optical propagation or
an extra approximation to the existing solver.

## Where pixels are sampled

On a canvas with shape `(ny,nx)`, sample pixel `[i,j]` at

```text
x = j - nx//2
y = i - ny//2
```

These are dimensionless pixel coordinates: `+x` follows columns to the right,
`+y` follows rows downward. Both odd and even grids put zero at `[ny//2,nx//2]`.
For example, five columns sample `-2,-1,0,1,2`, while four sample `-2,-1,0,1`.
This follows the existing centered spatial grid when multiplying by pitches:
`x_m=x*dx_m`, `y_m=y*dy_m`. Canvas extents are `nx*dx_m` and `ny*dy_m`.

Changing pitch leaves the raster unchanged. With unequal pitches, a round
pixel-space disk describes an ellipse in physical coordinates. Resizing the
canvas changes the centered sampling window while retaining every object's
position/size; off-canvas geometry is neither moved nor wrapped.

## Inclusive membership

A disk includes a sample if `(x-cx)**2+(y-cy)**2 <= radius**2`. A rectangle
includes it if `abs(x-cx) <= width/2` and `abs(y-cy) <= height/2`.
The equality is intentional. A geometric width of two can include centers
`-1,0,1`, so geometric dimensions are not pixel-count promises.

A finite-width segment contains all samples whose distance to the closest
point on the centerline segment is no greater than half its width. This
includes round end caps. Internally, endpoint tuples are first sorted
lexicographically by `(x,y)`; the user's stored endpoint fields are unchanged.
With ordered endpoints `A,B` and vector `D=B-A`, evaluate

```text
t_raw = ((x-Ax)*Dx + (y-Ay)*Dy) / (Dx*Dx + Dy*Dy)
t = min(1,max(0,t_raw))
Q = A + t*D
inside = (x-Qx)**2 + (y-Qy)**2 <= (width/2)**2
```

Exactly coincident endpoints form a disk of radius `width/2`. Distinct points
whose required arithmetic is unusable fail explicitly. There is no approximate
equality, snapping or epsilon expansion. Sorting endpoints internally makes
reversal follow the same arithmetic, rather than trusting two algebraically
equivalent floating-point paths to round identically.

For `A=(-1.3,-0.2)`, `B=(2.7,1.3)` and `P=(0,0)`, the measured independent
scalar paths on CPython 3.11.9/NumPy 2.4.6 gave squared distances
`0.07246575342465754` and `0.07246575342465755`. Width `0.5383892771022006`
straddles those directions at the represented inclusion threshold. Production
retained origin intensity `0.3` and identical raster bytes after reversal, while
stored endpoints stayed unchanged. These are measured fixture results, not
portable constants. Exact probe code/output and independent tests are in
[tests and evidence](tests_and_evidence.md). Inclusive edges refer to the
specified represented parameters and binary64 operations, not exact symbolic
geometry on all platforms.

## Intensity composition and amplitude

Begin with background intensity. Visit objects in list order and overwrite
every included sample with that object's intensity. Zero is a valid overwrite,
allowing a later object to erase an earlier bright region. Layers are drawing
instructions, not coherent sources; intensities are not summed and fields are
not interfered. There is no alpha blending, antialiasing, peak normalization,
brightness clipping or quantization through an image file.

The raster retains assigned binary64 intensity bits. It is an owned writable
native-float64 C-contiguous array. Amplitude is derived separately by public
M2 as `A_target=sqrt(I_target)`. Thus intensity `0.25` means amplitude `0.5`,
not amplitude `0.25`. Rounded amplitude squared need not reproduce every
original intensity bit; M5 stores these distinct authoritative roles.

Before synthesis, the application explicitly chooses uniform source amplitude

```text
A_source = sqrt(sum(A_target**2)/A_target.size)
```

This is per-target illumination selection outside the solver. Equal total
power does not make an arbitrary target exactly synthesizable or demonstrate
fixed illumination across designs. A zero raster is an admissible drawing but
does not satisfy the existing positive-power synthesis contract.

## Reproducibility and interpretation

The versioned design and rasterizer determine target samples under the declared
environment. Shape/dtype/C-order byte comparisons are exact discrete claims,
not optical-accuracy tolerances. An external drawing can be associated with a
verified numerical run only after its raster matches the saved target by these
checks. Distinct drawings can yield identical sampled rasters; a match proves
neither uniqueness nor authenticated authorship.

Existing M5 replay uses saved actual arrays and does not rasterize the external
drawing. Existing amplitude residual, intensity metrics, source/environment
qualification and strict versus diagnostic replay retain their different
meanings. Hard boundaries can produce diffraction and difficult optimization;
no universal convergence claim or old Gaussian quality threshold is imposed.
The preview is only the desired intensity. Inspect the actual saved
reconstruction and measured metrics to assess a completed synthesis.
