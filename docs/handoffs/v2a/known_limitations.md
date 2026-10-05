# V2a known limitations

Recorded 2026-10-05. This is a fixed ideal unfolded classical scalar,
monochromatic two-path experiment, with port order (0,1) and stipulated
identity transverse correspondence. Exact grid metadata cannot demonstrate
physical alignment. There is no reflected/tilted frame, mirror geometry,
coating law, polarization, quantum model, bandwidth, noise, instrument,
calibration, arbitrary topology or hardware integration.

The second mixer is the explicitly selected inverse B_dagger; rotating a
physical beam-splitter cube is not a supported construction rule. Algebraic
combined sampled norm conservation does not calibrate electromagnetic energy
transport of evanescent modes. Norms use arbitrary amplitude-unit²·m² rather
than watts. Input-normalized fractions include forward propagation survival.

Public ASM uses the full periodic window at pad1; no automatic anti-aliasing,
band limiting, resampling, convergence correction or escaped-power assignment
is introduced. Independent direct DFT validates the same discrete model, not
continuum accuracy or adequate pitch/window. Equal-mode uniform phase changes
brightness and cannot produce spatial stripes. Unequal modes may have less
than unit visibility or no perfectly dark output.

Distances/phase must be finite usable binary64. Very large phase arguments have
finite argument precision; very small represented cancellation signals have
input-scaled absolute bounds, not relative accuracy against zero. Small
residuals remain unclamped. A nonzero whole field whose norm underflows is
rejected; individual bounded tails/forward decay may underflow to zero.
This is not arbitrary dynamic-range or arbitrary-phase accuracy.

The 512-per-axis cap belongs only to the runner and is an application resource
limit. Recorded wall times are single-run observations; tracemalloc records
Python-traced allocations, and process snapshots are not total process peaks
or portable runtime/memory guarantees. Dense references use at most256samples.

Returned fields preserve supported constructor copying/read-only semantics.
They do not introduce irreversible write-flag locking. Frozen result records
are not a security boundary; caller mutation through unsupported mechanisms
is not a promised protection. Intermediate scalar records supplied by a caller
cannot authenticate discarded field measurements. The runner measures them.

Raw JSON/NumPy demo evidence has no new load/archive/replay contract or badge.
No browser/3D dual-output transport is added. V1 frontend/build/browser results
are historical and were not rerun for V2a. V2b and later reflection geometry,
polarization, instruments, deployment and hardware require separate approval.

The existing Windows file-symlink skip is retained: this account lacks symlink
privilege and junction behavior is tested separately. No test changes or
privilege elevation were used to remove it. Twelve isolated faults demonstrate
specific detecting assertions; they do not prove gap-free correctness.

Teaching remains separate. This milestone makes no claim about learning-record
changes, course restarts or completion of lessons.
