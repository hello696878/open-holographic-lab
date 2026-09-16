# Milestone 3 — Single-plane phase-only synthesis

Implemented on **2026-09-16** from accepted baseline
`4dfa5c5032adbb627b74ec52ace0b435ac6dba5c`. The approved scope includes
implementation, validation, a standalone demo, three figures, this six-document
handoff, one milestone commit and a normal push. M4 is not started.

## Public API

```python
from ohlab.algorithms import GerchbergSaxtonResult, gerchberg_saxton

gerchberg_saxton(
    *, target_amplitude: NDArray[np.float64],
    source_amplitude: NDArray[np.float64], grid: SamplingGrid,
    wavelength_m: float, distance_m: float, iterations: int,
    seed: int | None = None,
    initial_phase: NDArray[np.float64] | None = None,
) -> GerchbergSaxtonResult
```

The solver takes prescribed source and target amplitudes in arbitrary units,
SI wavelength/distance and one complete grid. Arrays must be plain native
float64 ndarrays, exact shape, finite and nonnegative; they may exceed one.
Read-only and noncontiguous inputs are copied and never modified. Explicit
phase is a finite float64 array of the same shape, in radians on any branch.
Exactly one of a nonnegative integer seed or explicit phase is required.
Iterations is a nonnegative integer; bool is not accepted as a scalar number.

Both energies `S=sum(A**2)` and powers `S*dx*dy` must be finite, positive and
numerically usable. The symmetric compatibility condition is
`abs(S_source-S_target) <= 1e-12*max(S_source,S_target)`, with no absolute
tolerance. No normalization, clipping or target scaling occurs in the solver.
Blank images remain legal M2 inputs but are infeasible solver inputs under
this contract. Equal powers do not guarantee an exactly achievable target.
NumPy-reported underflow, including precision-losing tiny/subnormal
intermediates, is rejected; finite input alone does not promise a usable solve.

Type/dtype failures raise `TypeError`; shape, domain, initialization-choice,
power, mesh and unusable-arithmetic failures raise `ValueError` with context.

## Model and computation

The model is periodic, full-grid and lossless, equivalent to the existing
public ASM with explicit `pad_factor=1`. There is no crop, padding or free
exterior region. Every sampled spatial frequency must be non-evanescent,
even at zero distance or zero iterations. M1's public default remains two.
Near grazing cutoff, the summed-frequency comparison can pass while rounding
makes the public formula's sequential radicand negative. M3 rejects that
unusable lossless geometry even for identity requests, without clamping or
modifying M1. The evidence includes a concrete regression reproducer.

Both `H_z` and `H_minus_z` are obtained once per solve through the existing
public transfer-function implementation. The local application is exactly
`ifft2(fft2(U)*H)` under the established normalization and sign. There is no
second production `kz`, global cache, backend or operator abstraction.
At zero distance, propagation uses identity without FFT, but still performs
all requested projections.

Initialize `U_0=A_source*exp(i*phase_0)`, using
`default_rng(seed).uniform(-pi,pi,grid.shape)` when seeded. Each cycle forwards
the source, records its normalized squared amplitude residual, replaces target
amplitude, propagates backward, then replaces source amplitude. M3 uses phase
zero at exact complex zero, and canonical `(-pi,+pi]` elsewhere. This local
tie rule leaves `ComplexField.phase` unchanged.

For N cycles the solver returns the last source `U_N`, the actual forward
reconstruction `P_z(U_N)`, and N+1 residuals, including initialization at index
zero. It never returns a target-projected intermediate or substitutes a best
iterate. N=0 is a meaningful initialization/reconstruction evaluation. At z=0,
a target-zero pixel may reset the corresponding source phase during a cycle.

## Result ownership

`GerchbergSaxtonResult` is a frozen keyword-only dataclass with `eq=False`,
following the project's identity-equality pattern for array-bearing objects.
It stores `source_field` and `reconstruction` as `ComplexField` instances,
and `residual_history` as an owned read-only native float64 array.
`iterations` is derived from history length; `phase` returns a fresh writable
canonical array from the returned source, zero on its zero support. Phase is
not stored separately. Ordinary read-only flags follow the existing project
convention; this is not a security boundary against deliberate flag changes.

The residual is
`sum((abs(P_z(U_k))-A_target)**2)/sum(A_target**2)`, evaluated before target
replacement. It is not intensity MSE, diffraction efficiency, percent pixels
or percent accuracy. No history clipping, early stopping or generic convergence
flag is provided.

## Demo, evidence and boundaries

The standalone example creates a deterministic grayscale PNG by default,
loads it through M2, explicitly configures uniform illumination, solves and
shows target intensity, ideal phase, actual reconstruction and raw history.
Illumination is configured separately for each target, outside the solver.
Target/reconstruction share a disclosed scale that includes any overshoot.

Independent scalar direct-DFT complete iterations, fixed points, public-ASM
reconstruction checks, power/adjoint/inverse checks, input/ownership regressions,
six deliberate negative-control categories and all twelve predeclared
fixture/seed cases provide finite evidence. See [tests and evidence](tests_and_evidence.md)
for actual measurements and exact commands/output, and [limitations](known_limitations.md)
for what this does not prove.

Only the approved twenty paths are changed. Existing numerical modules,
loader, tests, dependencies, historical evidence, AGENTS.md, CLAUDE.md and
old figures are preserved. The root initializer changes only its docstring.
The separate tutor receives context without any lesson-completion assumption.
