# V1 known limitations

V1 presents the existing V0 aligned scalar monochromatic forward model. It
does not add rays, volumetric beams, calibrated watts, hardware, camera
calibration, dispersion, polarization, decentered/rotated components,
multiple observation planes, meshes, RGB, GPU optics or phase retrieval.

## Numerical and visual interpretation

- The complete sampled window is periodic. Gaussian/lens descriptions are
  paraxial and hard apertures are discrete sample-center masks. Resource caps
  do not guarantee adequate sampling, negligible window wrap or physical
  accuracy for every accepted specification.
- Intensity is arbitrary amplitude-unit². V0 norm/delta/ratio are original
  scalar diagnostics; a ratio is not authenticated efficiency or absorption.
  Undefined zero-incident ratios remain null.
- The bench uses different transverse/longitudinal schematic scales. Lens
  housings/supports are cosmetic; they do not impose an extra aperture. The
  axis guide is a guide, not a computed beam.
- The selected shared grayscale interval may saturate or show weak signals as
  black. Raw maximum/readout and saturation notices preserve the distinction.
  Automatic range is explicit and presentation-only. Cross-GPU screenshots
  need not have identical bytes.
- Only terminal intensity and axes are transferred. Phase, complex amplitudes
  and intermediate fields are not available. Intermediate-stage selection
  shows scalars only and cannot replay or resimulate automatically.

## Interaction, cancellation and ownership

Numeric and rail z changes preserve stored component order. The z rail becomes
unusable when the viewing ray is nearly parallel to its axis; the application
discloses that condition and leaves numeric editing available. No position
clamping, sorting, rotation or transverse element movement is substituted.

Client busy suppresses duplicate clicks in the current actor. It is not durable
exactly-once delivery across sessions, reloads, process crashes or network loss.
HTTP/fetch abort does not cancel an already running Python thread. The server
gate remains occupied until the real worker finishes. There is no forceful
thread cancellation, compute queue, simulation timeout claiming cancellation,
automatic retry or background job framework.

Reload discards editor/view/result state and initializes a passive preset.
There is no experiment persistence, archive, authenticated provenance or new
scientific replay qualification. Optical edits detach old bench textures;
separate old result panels retain the original submitted specification.

Owned geometries/materials/textures/listeners/controls are disposed explicitly
when obsolete. Renderer internal caches need not become zero. Application
resource counters and renderer observations must be assessed over the defined
repeated-operation sequence; one instantaneous count is not a leak proof.

WebGL2 support is required for the 3D bench. Context loss/unsupported rendering
is reported separately without fabricated output or numerical resubmission.
Rendering failures do not remove a completed numerical result. Browser/vendor
rendering evidence is not a hardware-GPU benchmark.

## Service and reproducibility boundaries

The server binds only 127.0.0.1:8510, with exact Host and same-origin POST
checks, local built assets and no public CORS/tunnel. It is a local application,
not a hardened authenticated multiuser/public deployment. No arbitrary file
input or external asset service is needed. The existing port-8501 service is
not task-owned and is neither reused nor managed.

The existing project interpreter, distributions and source locations are
protected. The local npm lock and scripts-disabled Windows native build were
tested in this environment; other platforms/library versions need their own
acceptance. Missing assets/tools, occupied port or required acceptance failure
is a blocker, not permission to install substitutes or repair the environment.

Final precommit Python/frontend/API/browser/control gates passed. Clean-source
postcommit rebuild/browser/publication follows separately. An earlier browser
worker crash (3221226505) remains unexplained; later complete runs pass, without
tool repair. This is recorded as an observed limitation rather than erased.
The production JS bundle retains its >500 kB warning. Screen gesture and GPU
readback acceptance use documented display tolerances; scientific values remain
original float64 and direct discrete V0 comparison is exact on this environment.
Hard-edge sampling can be sensitive to one-ULP input conversion differences;
the literal 40e-6 versus editor 40*1e-6 measurements are explicitly distinguished.
Historical V0 evidence remains untouched. No later stage or teaching is started.
