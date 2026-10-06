# Roadmap — content design, then a virtual optics laboratory

Recorded **2026-09-30**, V0 update **2026-10-01**, V1/V2a update **2026-10-05**, V2c subdivision **2026-10-06**. The [milestone ledger](milestones.md) is authoritative
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
| V0 | Approved aligned sequential scalar computation foundation: exact SI experiment schema, Gaussian/uniform sources, binary apertures, ideal thin lenses and terminal observation | Existing fixed-grid forward ASM, immutable stages, independent direct-DFT/Gaussian/Fresnel references, explicit window/pitch convergence and bounded aperture acceptance; implementation acceptance is recorded in the ledger |
| V1 | Approved local TypeScript/Three.js/WebGL2 bench connected to public V0 through Starlette/Uvicorn | Production assets/API on 127.0.0.1:8510; orbit/pan/zoom, selection, numeric editing and constrained z rail; explicit simulation, original detector float64 readout, stale-result separation and resource limits |
| V2a | Approved coherent two-path numerical foundation: ordered ideal B/B_dagger mixing, two forward ASM arms, extra arm-1 phase and both complex outputs | Exact compatible grids, public constructor ownership, ten sampled norms, independent complex/DFT/evanescent/blocked controls and standalone numerical figures; no V1 connection |
| V2b | Approved dual-output 3D interferometer integration | Separate two-path mode, strict OHLAB2P frames, actual 17-call scalar sweep, atomic paired displays, cross-mode stale separation and shared worker-lifetime gate; current acceptance is recorded in the ledger |
| V2c | Approved ideal Jones polarization numerical foundation at one common transverse plane | Independent complex x/y components, ideal uniform polarizer/retarder actions, explicit phase reference, sampled intensity/norm, loss and focused weak-signal acceptance; no propagation or frontend integration |
| V2d | Separately approved future 3D polarization experiment mode | Connect validated V2c operations to an independently specified bench mode; representation, controls, transport, stale-result behavior and genuine browser acceptance need their own plan and approval |
| Later V2 | Separately modelled polarized interference, reflection/frame geometry and richer instruments | Both port and polarization indices, tilted/reflected frames, coating laws, noise and absolute radiometry each need explicit physical models and tests; unsupported geometry stays unsupported |
| V3 | A remotely accessible service with saved/shared experiments and educational templates | Separate security, authentication/authorization, storage, resource limits and remote-compute planning before deployment |

`TargetDesign2D` describes sampled content. V1 edits the existing V0
`SequentialExperiment`; its Three.js graph and viewing camera are presentation
state, not a new physical schema. A future richer `OpticalExperimentScene3D`
needs separate modelling and persistence approval. M5's GS-specific bundle
schema cannot be relabelled as a generic laboratory-experiment schema.

Rendering, physical computation and instrument readout are separate layers.
A render camera is not a simulated detector. The axis guide is not proof of
wave-optical propagation. V1's selected Three.js stack renders schematic geometry
and actual V0 intensity only; it does not compute browser optics or add components.
Its approved dependency installation/build/browser evidence is recorded in the
[V1 handoff](handoffs/v1/tests_and_evidence.md), separately from planning probes.

V0 has its own [`SequentialExperiment` contract](math_conventions.md#317-v0-aligned-sequential-optics--api-and-schema-contract)
and [handoff](handoffs/v0/implementation_summary.md). It computes one aligned
train on parallel planes; it is not `OpticalExperimentScene3D`, a viewer or
generic M5 bundle. Absolute z positions are authoritative, element actions and
travel are separate, and physical aperture loss is never normalized away.
The existing Streamlit application remains unchanged. V1 is independently
approved. V2a has its own [two-path contract](math_conventions.md#318-v2a-coherent-two-path-interference)
and [handoff](handoffs/v2a/implementation_summary.md); it does not change V0 or
V1's contracts. V2b reuses public V0 source sampling and V2a computation in the
[separate two-path UI](handoffs/v2b/implementation_summary.md), preserving
sequential defaults and protocol behavior. Later V2/V3, remote service and
hardware work require separate authorization.

V2c's [common-plane Jones contract](math_conventions.md#319-v2c-ideal-jones-polarization-at-one-reference-plane)
is a standalone numerical foundation, documented in its
[handoff](handoffs/v2c/implementation_summary.md). It preserves both complex
components and the selected retarder reference phase without changing V0/V2a
schemas, scalar solvers, V1/V2b protocols or existing user interfaces. Pointwise
uniform matrix action is not full-vector propagation or a transversality claim
for arbitrary nonparaxial spatial spectra. V2d remains unstarted.

Virtual-experiment save/load is an acknowledged separate product gap. V2c does
not add persistence, reinterpret M5 bundles or imply a new replay qualification.

Reuse existing field/propagation conventions and validation practices where
their assumptions apply. The current periodic, lossless GS contract is not a
general optical-bench solver. A physical aperture can remove power; a future
optical train must not normalize that loss away to fit the present GS model.
V2a's narrowly fixed unfolded branching/recombination does not establish a
generic topology or reflected-frame solver. Beyond V2c's bounded common-plane
Jones actions, arbitrary tilted planes, polarized propagation/interference,
detector noise, absolute radiometry and hardware twins remain later explicit
modelling work.

Physical SLM integration, calibration, vendor SDKs and device services form a
separate optional future track. The virtual laboratory can be useful without
purchasing or connecting physical equipment. No V-stage, public deployment or
hardware feature is implemented as part of M7.
