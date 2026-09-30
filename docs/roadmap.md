# Roadmap — content design, then a virtual optics laboratory

Recorded **2026-09-30**. The [milestone ledger](milestones.md) is authoritative
for current acceptance. This roadmap records product direction and approval
boundaries; listing a future stage does not authorize its implementation.

## A. Existing M0–M6 foundation

The implemented foundation comprises sampled fields/grids, angular-spectrum
propagation, strict grayscale target loading, single-plane phase-only
Gerchberg–Saxton synthesis, reconstruction metrics, reproducible run bundles
and the local workbench. Each retains its documented numerical, sampling,
filesystem and provenance limits. M6 publication closeout is recorded in the
[ledger](milestones.md#milestone-6--minimal-application-layer).

## B. M7 — editable 2D target workflow

The approved M7 scope adds disks, axis-aligned rectangles and round-capped
segments, an ordered numeric editor, deterministic intensity rasterization,
versioned editable JSON and explicit submission through the existing M2–M5
workflow. It preserves strict PNG loading and the existing scientific models.
Editable designs live outside completed numerical bundles. Target preview is
not a reconstruction prediction; synthesis runs only after an explicit action.

Text/fonts, freehand drawing, dragging, general transformations, richer editors
and all virtual-laboratory features require later approval. M7 introduces no
hardware requirement and does not imply teaching completion.

## C. Later — 3D Virtual Optics Lab

The intended later product is a browser-accessible 3D optical bench where users
arrange supported components/instruments, configure experiments, simulate
explicitly supported physics and inspect measurement results. It follows
content-design work and is delivered in independently approved stages.

| Stage | Bounded objective | Acceptance boundary |
|---|---|---|
| V0 | A physical experiment schema and ideal source, aperture/slit, thin-lens and detector-plane models | Begin with a restricted aligned sequential beamline; define SI units, geometry, validity domains and independent analytic/reference tests before a 3D editor |
| V1 | A browser 3D bench connected to the validated models | Orbit/pan/zoom, component selection and supported position/parameter editing; actual simulation outputs appear on virtual detectors and plots |
| V2 | Separately validated mirrors, beam splitters, interference paths, polarization components and richer instruments | Branching/recombination, tilted planes, noise and absolute radiometry require explicit models and tests; unsupported geometry stays unsupported |
| V3 | A remotely accessible service with saved/shared experiments and educational templates | Separate security, authentication/authorization, storage, resource limits and remote-compute planning before deployment |

`TargetDesign2D` describes sampled content. Future `OpticalExperimentScene3D`
describes physical arrangements; they are separate schemas, not one universal
scene graph. M5's GS-specific bundle schema cannot be relabelled as a generic
laboratory-experiment schema. Future persistence needs separate approval.

Rendering, physical computation and instrument readout are separate layers.
A render camera is not a simulated detector. A visible beam line is not proof
of wave-optical propagation. Three.js may later be considered for interaction
and rendering; no 3D engine or implementation stack is selected or installed
by this roadmap.

Reuse existing field/propagation conventions and validation practices where
their assumptions apply. The current periodic, lossless GS contract is not a
general optical-bench solver. A physical aperture can remove power; a future
optical train must not normalize that loss away to fit the present GS model.
Arbitrary tilted planes, branching/recombination, polarization, detector noise,
absolute radiometry and hardware twins remain later explicit modelling work.

Physical SLM integration, calibration, vendor SDKs and device services form a
separate optional future track. The virtual laboratory can be useful without
purchasing or connecting physical equipment. No V-stage, public deployment or
hardware feature is implemented as part of M7.
