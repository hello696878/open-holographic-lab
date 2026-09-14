# M0/M1 contract corrections, evidence, and tutor errata

Dated **2026-09-14**. Corrective maintenance for approved categories A and B;
this is not a new milestone. M0/M1 remain complete. Category C and Milestone 2
were not started.

## Scope and starting evidence

The user approved implementation, validation, documentation, one new commit
named `fix: reconcile M0 M1 contracts tests and evidence`, and normal push to
origin/main. Pre-edit state: clean main, tracking origin/main, 0 ahead /
0 behind. HEAD, tracking ref and live remote main all matched
`1b2e755977e51141f224a2d4a0aa3807359f151b`. No reset or history rewrite.

All Python commands used the existing Windows interpreter
`C:\holographiclab\.venv\Scripts\python.exe`: Python 3.11.9, NumPy 2.4.6,
SciPy 1.17.1, pytest 9.1.1. No environment, dependencies, global Git
configuration, figures, AGENTS.md or CLAUDE.md changes.

Only production executable changes: the exact phase endpoint correction and
diffraction diagnostic text. Propagation edits are docstrings only.

## Findings, reproducers, regressions, and behavior

| Affected file / confirmed problem | Minimal reproducer or evidence | Correction and regression | Public impact |
|---|---|---|---|
| `src/ohlab/field.py`: phase violated declared (-pi,+pi] endpoint | `np.angle(np.array([complex(-1.0,-0.0)]))[0] == -np.pi` | Assign +pi only where the existing angle array equals -pi exactly. F-06b/c/d and F-08b cover signed zeros, conjugation, adjacent angles, shape/dtype and unchanged field bytes | Exactly -pi becomes +pi; other angles unchanged |
| `src/ohlab/grid.py`: fine sampling called “too coarse” | Pitch 100 nm, wavelength 633 nm: lambda/(2*pitch)=3.165>1 | Explain that Nyquist exceeds the propagating-wave cutoff, with no corresponding real angle. G-23 checks message and that the same pitch works at wavelength 100 nm (pi/6) | Message only; same ValueError, domain and result |
| `tests/test_field.py`: weak power assertion | Expected 5.4152968276312954e-9 a.u. m²; multiply by 1.0001. Old approx(rel=1e-15) accepts error 5.4152968276307453e-13 through implicit abs=1e-12 | Explicit rel=1e-15, abs=1e-24; F-09c invokes the actual F-09 assertion with perturbed power and requires failure | None |
| `tests/_helpers.py`: numerical equality claimed bit identity | Old helper accepted +0/-0 and complex(-1,+0)/complex(-1,-0), despite different bytes | Same shape, dtype including endian representation, and element bytes in logical C order. Thirteen helper cases cover copies, zeros, noncontiguous layouts and mismatches | Test helper only |
| `docs/math_conventions.md`, M0/M1 `math_used.md`, propagation docstrings: missing physical-spectrum origin factor | A centered unit impulse at physical x=y=0 must have constant physical spectrum; its raw FFT has nonconstant phase | Derive area/origin factor and inverse cancellation. C-09–C-11 compare independent direct sums on mixed-parity anisotropic grids | No production shifts or normalization changes |
| Same math docs and `tests/test_propagation.py`: unrestricted conjugacy / overstated sign coupling | For kz=i*kappa, H(z)=exp(-kappa*z) but H(-z)=exp(+kappa*z), unlike conj(H(z)); composition and round trip also pass a consistent sign reversal | Restrict conjugacy to real kz. M-04/M-29 descriptions narrowed; analytic plane-wave/Gouy checks pin the selected sign | Signs, forward decay, backward evanescent rejection unchanged |
| Test names/comments/docstrings overclaimed reach | F-18's old name obscured the square-root input relation; F-20 checks ordinary write guards; C-08 runs with dev dependencies installed; A-08/A-12 do not prove general pointwise symmetry/conservation | Narrow descriptions; retain valid assertions. Approximate wrapped residual is near zero, not necessarily exact zero | None |
| M1 historical count split and Gaussian references | Baseline is 72 mechanics + 31 analytic, not 71/32. Recovered probes use different reference definitions | Dated notes preserve original tables/transcripts; provenance below | None |

### Zero-amplitude exception and representation

Before editing, four signed-zero combinations were probed: 0+0j gives +0
phase; 0-0j gives -0; -0+0j gives +pi; -0-0j gives -pi. Thus the exact endpoint
requirement also changes the last representation to +pi. This conflict with
preserving every zero-pixel representation was demonstrated and reported
before implementation. Ordinary zero remains zero; stored real/imaginary
sign bits remain unchanged. Phase at zero amplitude is physically undefined.

Nearby angles [-3.1415926535897927, -3.1415926535897922,
-3.141592653588793] survive unchanged through exp(i*angle) and phase
extraction. No isclose, modulo recomputation, or phase unwrapping is used.
Canonical representation tests remain separate from phase-equivalence tests.

There is a derived floating-point effect for callers that re-exponentiate
the corrected phase, including `with_amplitude`. On a 2×2 field containing
`complex(-1.0, -0.0)`, rebuilding with amplitude 2 previously evaluated
`2*exp(1j*(-pi)) = (-2-2.4492935982947064e-16j)`; the current method returns
`(-2+2.4492935982947064e-16j)`. The measured absolute difference is
`4.898587196589413e-16`. These endpoints are physically equivalent, but the
derived output bytes need not be identical. Existing approximate projection
tests pass; the original stored input bytes remain unchanged. No executable
change to `with_amplitude` was made.

Literal helper evidence before correction:

~~~text
float signed zero: old helper ACCEPTED; C-order bytes equal = False
  left=0000000000000000 right=0000000000000080
complex imaginary signed zero: old helper ACCEPTED; C-order bytes equal = False
  left=000000000000f0bf0000000000000000 right=000000000000f0bf0000000000000080
~~~

The helper compares `tobytes(order="C")` without casting or canonicalizing
zeros. Strides/storage order alone do not matter; equal logical elements
in strided, transposed, reversed and contiguous arrays pass.

## Tolerances and inventory

Baseline AST inventory: 81 approximate-comparison call sites, comprising
52 NumPy assert_allclose, 11 assert_phase_allclose, 10 ComplexField.allclose
and all 8 pytest.approx calls. This includes the shared phase assertion
implementation, not 81 distinct tests. NumPy calls already specify both
rtol/atol. Phase calls specify atol; the helper fixes rtol=0. Nine field
comparisons specify both; the tenth deliberately omits them inside a
TypeError regression. Seven pytest.approx sites lacked abs; G-22 lacked
rel (abs-only already means absolute comparison).

Scalar bounds such as error < tolerance were also reviewed: they are
explicit, not library defaults. Exact comparisons retain deliberate
exactness claims for representation, dimensions and indexing. No existing
explicit threshold was loosened. Every pytest.approx now spells out both
relative and absolute tolerances.

| Site / quantity | Measured baseline discrepancy | Final rel / abs | Justification |
|---|---|---|---|
| F-09, power ≈5.4153e-9 a.u. m² | 0 (same sum expression) | 1e-15 / 1e-24 a.u. m² | Preserve relative threshold; absolute floor below float64 epsilon times this scale. F-09b/F-10 separately cover scaling/invariance |
| F-26, rounded k≈9.926e6 rad/m | 43.139304243028164 rad/m; relative 4.3460915014132743e-6 | 1e-3 / 0 rad/m | Coarse rounded reference, far from zero |
| G-22, rounded angle 4.855 degrees | 0.00050030586635863017 degrees | 0 / 0.01 degrees | Preserve decimal-rounding allowance |
| U-03, wavelength ratio 633 | 0 | 1e-15 / 0 | Nonzero dimensionless unit conversion |
| U-03, pitch ratio 3.74 | 0 | 1e-15 / 0 | Same; no near-zero input |
| A-06, phase 0.49630215696521218 rad | 1.6653345369377348e-16 rad | 1e-9 / 1e-15 rad | Existing phase threshold dominates; absolute term covers measured rounding floor |
| A-10, widths ≈1.12e-4 to 2.24e-4 m | Absolute errors 4.5390651564540356e-11, 1.4353779964745503e-10, 3.631249912577645e-10 m; relative ≤1.6239443295627566e-6 | 2e-3 / 1e-12 m | Preserve model allowance; 1 pm term is immaterial at these widths |
| A-12, peak ratios 0.8/0.5/0.2 | Absolute errors 1.039322297780032e-6, 1.0149581370355598e-6, 2.5983105428339925e-7; relative ≤2.0299162740711201e-6 | 5e-3 / 1e-12 | Preserve model allowance and small dimensionless floor |

Measurements used the existing deterministic fixtures. A-10/A-12 use
w0=100 UM, 512², pitch=4 UM, wavelength=633 NM, at 0.5/1/2 zR, comparing
second-moment width and on-axis intensity with their analytic expressions.
These are current baseline measurements, not historical replacements.

New Fourier comparisons use rel=1e-12 and abs=1e-12 times a quantity scale:
pixel area × sum(abs(field)) for spectra; input peak amplitude for inverse;
direct-reference peak amplitude for same-grid propagation. Absolute terms
cover cancelling bins. Measured
maximum error/scale: 1.4089627996560444e-15 forward,
7.119954476806645e-16 inverse, 9.491689839621659e-16 direct ASM comparison.
Thresholds allow accumulated sum/FFT roundoff while the omitted-origin
control creates order-one relative errors.

### Complete baseline approximate call-site inventory

Line numbers refer to `1b2e755`. “Missing” means absent at that call;
the safe helper/API exceptions are explained above. Other keywords omitted.

| Baseline file:line | Call | Relative | Absolute |
|---|---|---|---|
| `tests/_helpers.py:74` | `np.testing.assert_allclose` | `0.0` | `atol` |
| `tests/test_fft_conventions.py:136` | `np.testing.assert_allclose` | `1e-10` | `0.0` |
| `tests/test_fft_conventions.py:161` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_fft_conventions.py:193` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_fft_conventions.py:238` | `np.testing.assert_allclose` | `1e-10` | `1e-10 * scale` |
| `tests/test_field.py:161` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:162` | `assert_phase_allclose` | `missing` | `1e-12` |
| `tests/test_field.py:184` | `np.testing.assert_allclose` | `0.0` | `1e-12` |
| `tests/test_field.py:208` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:246` | `pytest.approx` | `1e-15` | `missing` |
| `tests/test_field.py:260` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:283` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:286` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:305` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:308` | `assert_phase_allclose` | `missing` | `1e-12` |
| `tests/test_field.py:344` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:347` | `assert_phase_allclose` | `missing` | `1e-12` |
| `tests/test_field.py:364` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:367` | `assert_phase_allclose` | `missing` | `1e-12` |
| `tests/test_field.py:399` | `np.testing.assert_allclose` | `1e-15` | `0.0` |
| `tests/test_field.py:402` | `assert_phase_allclose` | `missing` | `1e-12` |
| `tests/test_field.py:408` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:428` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:449` | `a.allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:450` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:516` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:556` | `sample_field.allclose` | `0.0` | `0.0` |
| `tests/test_field.py:559` | `sample_field.allclose` | `missing` | `missing` |
| `tests/test_field.py:567` | `sample_field.allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:568` | `sample_field.allclose` | `1e-06` | `0.0` |
| `tests/test_field.py:578` | `sample_field.allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:587` | `sample_field.allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:590` | `sample_field.allclose` | `1e-12` | `0.0` |
| `tests/test_field.py:596` | `np.testing.assert_allclose` | `1e-15` | `0.0` |
| `tests/test_field.py:599` | `pytest.approx` | `0.001` | `missing` |
| `tests/test_grid.py:70` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_grid.py:136` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_grid.py:139` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_grid.py:164` | `np.testing.assert_allclose` | `1e-15` | `0.0` |
| `tests/test_grid.py:165` | `np.testing.assert_allclose` | `1e-15` | `0.0` |
| `tests/test_grid.py:171` | `np.testing.assert_allclose` | `1e-15` | `0.0` |
| `tests/test_grid.py:172` | `np.testing.assert_allclose` | `1e-15` | `0.0` |
| `tests/test_grid.py:234` | `np.testing.assert_allclose` | `1e-15` | `0.0` |
| `tests/test_grid.py:237` | `np.testing.assert_allclose` | `1e-15` | `0.0` |
| `tests/test_grid.py:248` | `np.testing.assert_allclose` | `1e-15` | `0.0` |
| `tests/test_grid.py:264` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_grid.py:364` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_grid.py:382` | `pytest.approx` | `missing` | `0.01` |
| `tests/test_plane_wave.py:68` | `np.testing.assert_allclose` | `1e-12` | `1e-15` |
| `tests/test_plane_wave.py:103` | `assert_phase_allclose` | `missing` | `1e-10` |
| `tests/test_plane_wave.py:106` | `assert_phase_allclose` | `missing` | `1e-10` |
| `tests/test_plane_wave.py:145` | `np.testing.assert_allclose` | `1e-10` | `1e-10 * k` |
| `tests/test_plane_wave.py:146` | `np.testing.assert_allclose` | `1e-10` | `1e-10 * k` |
| `tests/test_plane_wave.py:163` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_plane_wave.py:166` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_plane_wave.py:255` | `assert_phase_allclose` | `missing` | `1e-10` |
| `tests/test_plane_wave.py:328` | `np.testing.assert_allclose` | `1e-10` | `0.0` |
| `tests/test_propagation.py:103` | `np.testing.assert_allclose` | `0.0` | `_phase_tolerance(wavelength, z)` |
| `tests/test_propagation.py:139` | `np.testing.assert_allclose` | `0.0` | `1e-12` |
| `tests/test_propagation.py:159` | `np.testing.assert_allclose` | `1e-12` | `1e-14` |
| `tests/test_propagation.py:185` | `np.testing.assert_allclose` | `0.0` | `_phase_tolerance(wavelength, z1 + z2)` |
| `tests/test_propagation.py:553` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_propagation.py:605` | `back.allclose` | `1e-11` | `1e-11` |
| `tests/test_propagation.py:628` | `stepwise.allclose` | `1e-10` | `1e-11` |
| `tests/test_propagation_analytic.py:135` | `np.testing.assert_allclose` | `1e-11` | `1e-11` |
| `tests/test_propagation_analytic.py:136` | `assert_phase_allclose` | `missing` | `1e-10` |
| `tests/test_propagation_analytic.py:140` | `np.testing.assert_allclose` | `1e-11` | `0.0` |
| `tests/test_propagation_analytic.py:162` | `np.testing.assert_allclose` | `1e-12` | `0.0` |
| `tests/test_propagation_analytic.py:170` | `assert_phase_allclose` | `missing` | `1e-10` |
| `tests/test_propagation_analytic.py:171` | `assert_phase_allclose` | `missing` | `1e-10` |
| `tests/test_propagation_analytic.py:209` | `np.testing.assert_allclose` | `1e-11` | `1e-11 * scale` |
| `tests/test_propagation_analytic.py:243` | `np.testing.assert_allclose` | `0.0` | `tolerance` |
| `tests/test_propagation_analytic.py:247` | `np.testing.assert_allclose` | `0.0` | `tolerance` |
| `tests/test_propagation_analytic.py:270` | `pytest.approx` | `1e-09` | `missing` |
| `tests/test_propagation_analytic.py:302` | `np.testing.assert_allclose` | `1e-12` | `1e-12 * scale` |
| `tests/test_propagation_analytic.py:452` | `pytest.approx` | `0.002` | `missing` |
| `tests/test_propagation_analytic.py:487` | `np.testing.assert_allclose` | `0.0` | `0.002` |
| `tests/test_propagation_analytic.py:490` | `np.testing.assert_allclose` | `0.0` | `0.002` |
| `tests/test_propagation_analytic.py:516` | `pytest.approx` | `0.005` | `missing` |
| `tests/test_units.py:43` | `pytest.approx` | `1e-15` | `missing` |
| `tests/test_units.py:44` | `pytest.approx` | `1e-15` | `missing` |

## Fourier derivation and evidence limits

For x[j]=x0+j*dx and y[i]=y0+i*dy, the selected negative analysis kernel gives

    A[p,q] = dx*dy * exp(-2*pi*i*(fx[q]*x0+fy[p]*y0)) * FFT2(U)[p,q].

Paired synthesis divides out pixel area and the same origin factor before
IFFT2. In same-grid ASM, with D the origin factor and dA the pixel area,

    IFFT2((dA*D*FFT2(U)*H)/(dA*D)) = IFFT2(FFT2(U)*H).

This applies to the actual computational grid, including padding, with crop
afterward; it is not a claim about interpolation between different grids.
No production shift is needed or added.

C-09 evaluates both kernel signs on (5,8)/(6,7) grids, dx=3.74e-6 m,
dy=5e-6 m, for a centered impulse and seeded complex data. The reference
builds coordinates and signed bins explicitly and sums scalar complex
exponentials; it calls neither FFT nor the subject's correction helper.
C-10 begins inverse reconstruction with that independent sum. C-11 compares
unchanged ASM with direct analysis/transfer/synthesis. C-11 uses the same
selected transfer model, so it validates the transform pair, not an
independent physical derivation of H.

Time-harmonic choice and Fourier analysis sign are distinct conventions.
Changing analysis sign and its paired inverse consistently relabels spatial
frequencies; free-space H depends on their squares. Changing the physical
time convention changes the representation of a forward wave and associated
propagation sign. NumPy does not force the time convention. Selected
conventions remain exp(-i*omega*t), negative analysis kernel, exp(+i*kz*z).

For real kz, H(-z)=conj(H(z)) and |H|=1. For kz=i*kappa, kappa>0, forward H
decays and backward H grows; conjugating the real decay does not invert it.
The API continues rejecting backward requests on meshes containing
evanescent samples.

## Historical evidence: recovered provenance and uncertainty

Both conflicting tables first appear in commit `6646c7f`. Repository
history did not contain the planning scripts. The original session record
did:

~~~text
C:\Users\jimli\.claude\projects\C--holographiclab\c53c708c-9910-49cc-865b-777b52a6fca5.jsonl
SHA-256: cd3a00e7280c1d6105a0f2d76f6ebcb75590492ce4bde9846e48630a21c16467
~~~

This local artifact was read, not modified or executed. It is not committed
here. Source/output identifiers permit an audit without mistaking the
current probe for a historical rerun.

| Recorded source | UTC source timestamp / line / tool ID | Source SHA-256 | Output |
|---|---|---|---|
| probe_m1b.py | 2026-08-11 08:31:59.382Z / 569 / toolu_011p4xg23DKyrW2i4M3WswEX | b1c2d6600cd4bf13a392d4232b215f7ad24333c00de733bf9b3017140942a163 | line 576, 08:32:13.123Z; run toolu_01QYWzUpvkm1nRLp4FzFcFAq |
| probe_m1c.py | 2026-08-11 08:33:09.686Z / 579 / toolu_01YGBY4cvYmFcvv8tpmEh7a1 | 4383af0c53aa5c14dfe3abbb9055adb1cb1c80029c343dc3fef4efac52d633a2 | line 585, 08:33:37.675Z; run toolu_01R7s9LXTCPpqGLdm2qCLFx5 |
| m1_results.py | 2026-08-11 11:26:06.468Z / 671 / toolu_0192jtbHQsbEJSFCU2gFrFah | 45985a9d78f78078881c0f8ec23ec738ef9337842b123274f13a9a97a49b9589 | line 674, 11:26:30.920Z; run toolu_01VwiUhDDtFWLLaP8qdszPgy |

Recorded command pattern (only the script filename changes for the other
two records):

~~~powershell
cd C:\holographiclab; .\.venv\Scripts\python.exe "C:\Users\jimli\AppData\Local\Temp\claude\C--holographiclab\c53c708c-9910-49cc-865b-777b52a6fca5\scratchpad\probe_m1b.py" 2>&1
~~~

Scratch files need not still exist: their Write-tool source text is in the
record. Source hashes refer to that text encoded as UTF-8.

**Numerical reference, probe_m1b.py.** n=256, pitch=3.74 UM, waist=40 UM,
wavelength=633 NM; source exp(-(x²+y²)/w0²). Reference adds 384 pixels on
each side, producing 1024² (4× linear), then crops to the central original
256². H=exp(i*2*pi*sqrt((1/lambda)²-fx²-fy²)*z), with a rectangular mask:
x limit=1/(lambda*sqrt((2*abs(z)/Lx)²+1)), and analogous y limit.
Error=max(abs(numeric-reference))/max(abs(reference)) on the original crop.
No fitted scaling or global-phase alignment.

Exact relevant recorded output excerpt, not a current run:

~~~text
Q1: BL-ASM vs padded vs plain, against a heavily-padded band-limited
    reference (pad=4x linear, band-limited). Smooth Gaussian source.
============================================================================
  z= 0.005 m   plain=9.127e-13   pad2x=6.171e-13   BL=9.127e-13   BL+pad2x=6.171e-13
  z= 0.020 m   plain=3.403e-09   pad2x=3.669e-12   BL=3.410e-09   BL+pad2x=3.669e-12
  z= 0.100 m   plain=4.976e-01   pad2x=3.109e-04   BL=3.508e-01   BL+pad2x=7.900e-03
~~~

**Analytic reference, probe_m1c.py.** Same parameters, original-grid region
and relative complex maximum metric; reference instead is

    U=(w0/w(z))*exp(-r²/w(z)²)*exp(i*(k*z+k*r²/(2*R(z))-psi(z)))
    zR=pi*w0²/lambda; w(z)=w0*sqrt(1+(z/zR)²)
    R(z)=z*(1+(zR/z)²); psi(z)=atan2(z,zR); k=2*pi/lambda.

No global-phase alignment or fitted scaling. Exact relevant recorded
output excerpt:

~~~text
R1: ANALYTIC GAUSSIAN ground truth. w0=40um, n=256, pitch=3.74um.
    window = 0.957 mm.  zR = 7.94 mm.
    Reported: max|numeric - analytic| / max|analytic|
==============================================================================
    (analytic w(z) reaches the window half-width 479 um at z = 94.70 mm)

     z (mm)   w(z) um       plain       pad2x          BL    BL+pad2x
        2.0      41.2   3.005e-06   3.005e-06   3.005e-06   3.005e-06
        5.0      47.3   5.721e-06   5.721e-06   5.721e-06   5.721e-06
       10.0      64.3   6.179e-06   6.179e-06   6.179e-06   6.179e-06
       20.0     108.4   8.123e-06   8.123e-06   8.123e-06   8.123e-06
       50.0     255.0   2.950e-02   2.136e-05   2.576e-02   2.141e-05
      100.0     505.3   4.976e-01   3.045e-04   3.508e-01   7.901e-03
~~~

Later m1_results.py applies the same analytic equation to the shipped
propagate_angular_spectrum and records the values used in M1
tests_and_evidence.md. Final known_limitations.md Write: line 754,
2026-08-11 11:36:28.836Z, toolu_01PegMcZCRQmQbBcyhLzukqm.

**Supported conclusion:** known_limitations.md 5/20 mm rows match the
numerical-reference probe despite the analytic heading. Its 100 mm padded
entry 3.05e-4 instead matches analytic 3.045e-4, not numerical-reference
3.109e-4. This is mixed reference provenance. Current measurements are
not grounds for replacing historical numbers.

**Still unresolved:** exact manual assembly and rounding of every cell are
not individually recorded; overlapping rounded values cannot uniquely
identify their source. Scratch probes lack a complete independent runtime
manifest. The local log is available evidence, not a portable repository
artifact or guaranteed accessible from another checkout. No explanation
is invented for these remaining gaps. No band-limited implementation was
added, imported from historical probes, or rerun.

### Historical count attribution

M0 acceptance was 188; M1 acceptance was 291. Baseline collection is 72
mechanics cases in test_propagation.py and 31 analytic cases in
test_propagation_analytic.py, totaling 103. The inaccurate 71/32 prose split
is clarified with dated notes; original transcripts are retained.
Maintenance adds 5 field + 13 helper + 14 Fourier cases = 32;
291+32=323. No old tests were deleted.

## Current Gaussian measurement, separate from history

Run from C:\holographiclab:

~~~powershell
.\.venv\Scripts\python.exe -B scripts\probe_m1_gaussian_evidence.py
~~~

The script writes no files. Output captures source hashes, revision and
dirty state at measurement time, environment, SI inputs, equation, crop,
metric, and absence of fitting. Documentation continued afterward; the
dirty-path list is a time-specific snapshot. Hashes identify measured code.
Only shipped plain/padded ASM is measured. Actual unedited output:

~~~json
{
  "measurement_kind": "current shipped ASM vs analytic paraxial Gaussian",
  "timestamp_utc": "2026-09-14T06:34:17.174394+00:00",
  "source_revision": "1b2e755977e51141f224a2d4a0aa3807359f151b",
  "working_tree_dirty": true,
  "working_tree_status_porcelain": [
    " M docs/handoffs/milestone_0/math_used.md",
    " M docs/handoffs/milestone_0/tutor_context.md",
    " M docs/handoffs/milestone_1/implementation_summary.md",
    " M docs/handoffs/milestone_1/known_limitations.md",
    " M docs/handoffs/milestone_1/math_used.md",
    " M docs/handoffs/milestone_1/tests_and_evidence.md",
    " M docs/handoffs/milestone_1/tutor_context.md",
    " M docs/math_conventions.md",
    " M src/ohlab/field.py",
    " M src/ohlab/grid.py",
    " M src/ohlab/propagation.py",
    " M tests/_helpers.py",
    " M tests/test_fft_conventions.py",
    " M tests/test_field.py",
    " M tests/test_grid.py",
    " M tests/test_propagation.py",
    " M tests/test_propagation_analytic.py",
    " M tests/test_units.py",
    "?? scripts/probe_m1_gaussian_evidence.py",
    "?? tests/test_helpers.py"
  ],
  "source_sha256": {
    "src/ohlab/__init__.py": "788ff4a641fbcd969828baf10f8d88b1460e44a63694c6c80d02b51dc5b61eef",
    "src/ohlab/field.py": "cace42f5deb0dda9f2d42e5a7ec7327edfa9442e89b33e6d045d6085f3e1d725",
    "src/ohlab/grid.py": "5448b7e9a2e648a53010d9ca8c0795b98057b325b3958d1de73d6800bad66909",
    "src/ohlab/propagation.py": "e994154e6ea1847a2862d3c8994fd1223c66e26d15e9fd984debd6fffdd84af8",
    "src/ohlab/units.py": "e3b9d6984074c3b66a7dd6d70d597eb44ee91f9807d278de2b0e694e727aac16",
    "src/ohlab/validation.py": "918a52f2cc85f01bf0ac6c5b47d4ccdf9d35e2d3905c37c86e773924804e2ddd",
    "scripts/probe_m1_gaussian_evidence.py": "a54ea6b646058a00fef906a3ac553b9dee217fc71c4bf15bd3d2a35ec51362df"
  },
  "environment": {
    "python": "3.11.9",
    "executable": "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "platform": "Windows-10-10.0.26100-SP0",
    "versions": {
      "ohlab": "0.1.0.dev0",
      "numpy": "2.4.6",
      "scipy": "1.17.1",
      "pytest": "9.1.1"
    }
  },
  "configuration_si": {
    "wavelength_m": 6.33e-07,
    "waist_m": 3.9999999999999996e-05,
    "grid": {
      "ny": 256,
      "nx": 256,
      "dy": 3.74e-06,
      "dx": 3.74e-06
    },
    "source": "U0=exp(-(x^2+y^2)/waist_m^2); peak amplitude 1 a.u."
  },
  "analytic_reference": {
    "equation": "U=(w0/w(z))*exp(-r^2/w(z)^2)*exp(i*(k*z+k*r^2/(2*R(z))-psi(z)))",
    "definitions": "k=2*pi/lambda; zR=pi*w0^2/lambda; w(z)=w0*sqrt(1+(z/zR)^2); R(z)=z*(1+(zR/z)^2); psi=atan2(z,zR)",
    "model": "paraxial; same scalar, coherent, n=1 convention as ASM"
  },
  "comparison": {
    "region": "all 256x256 samples of the original source grid, after the propagator's crop",
    "error": "max(abs(U_numeric-U_reference))/max(abs(U_reference))",
    "normalization": "only division by analytic peak amplitude in the reported relative metric",
    "global_phase_alignment": "none",
    "fitted_scaling": "none"
  },
  "results": [
    {
      "distance_m": 0.005,
      "pad_factor": 1,
      "max_complex_absolute_error_au": 4.84083694514952e-06,
      "reference_peak_amplitude_au": 0.8462224946393287,
      "relative_complex_linf_error": 5.720525010638897e-06
    },
    {
      "distance_m": 0.005,
      "pad_factor": 2,
      "max_complex_absolute_error_au": 4.840836970876894e-06,
      "reference_peak_amplitude_au": 0.8462224946393287,
      "relative_complex_linf_error": 5.720525041041508e-06
    },
    {
      "distance_m": 0.02,
      "pad_factor": 1,
      "max_complex_absolute_error_au": 2.9974526568012685e-06,
      "reference_peak_amplitude_au": 0.3690192208084682,
      "relative_complex_linf_error": 8.122754826250728e-06
    },
    {
      "distance_m": 0.02,
      "pad_factor": 2,
      "max_complex_absolute_error_au": 2.9974527497961514e-06,
      "reference_peak_amplitude_au": 0.3690192208084682,
      "relative_complex_linf_error": 8.122755078256254e-06
    },
    {
      "distance_m": 0.05,
      "pad_factor": 1,
      "max_complex_absolute_error_au": 0.004626846522670562,
      "reference_peak_amplitude_au": 0.1568509037984088,
      "relative_complex_linf_error": 0.029498373363644588
    },
    {
      "distance_m": 0.05,
      "pad_factor": 2,
      "max_complex_absolute_error_au": 3.3503188884070983e-06,
      "reference_peak_amplitude_au": 0.1568509037984088,
      "relative_complex_linf_error": 2.1359895335464978e-05
    },
    {
      "distance_m": 0.1,
      "pad_factor": 1,
      "max_complex_absolute_error_au": 0.0393898088713871,
      "reference_peak_amplitude_au": 0.07915916093866775,
      "relative_complex_linf_error": 0.49760265778848
    },
    {
      "distance_m": 0.1,
      "pad_factor": 2,
      "max_complex_absolute_error_au": 2.410065624393095e-05,
      "reference_peak_amplitude_au": 0.07915916093866775,
      "relative_complex_linf_error": 0.00030445820746639873
    }
  ]
}
~~~

## Validation and controlled negative tests

Baseline command, before edits:

~~~powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
~~~

Exact output (exit 0):

~~~text
........................................................................ [ 24%]
........................................................................ [ 49%]
........................................................................ [ 74%]
........................................................................ [ 98%]
...                                                                      [100%]
291 passed in 3.39s
~~~

Focused helper regressions: 13 passed in 0.08s.
Focused Fourier/propagation command:

~~~powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_fft_conventions.py tests/test_propagation.py
~~~

Exact output (exit 0):

~~~text
........................................................................ [ 72%]
...........................                                              [100%]
99 passed in 0.40s
~~~

Each negative control below ran in a separate Python process, changed one
in-memory callable, and restored it in finally. No repository file was
mutated. Each harness asserts pytest reported TESTS_FAILED and checks all
source/test SHA-256 values unchanged. A harness exit of zero means the
expected defect was detected, not that the mutant tests passed. This proves
detection of these four specific faults, not arbitrary physical accuracy.

| Isolated mutation | Actual test result |
|---|---|
| Remove phase canonicalization | 3 failed, 46 deselected in 0.09s |
| Restore weak F-09 tolerance | 1 failed, 48 deselected in 0.04s |
| Replace literal bytes with numerical equality | 3 failed, 10 deselected in 0.08s |
| Omit physical-spectrum origin factor | 8 failed, 19 deselected in 0.13s |

The exact commands and complete outputs follow. Traceback line numbers and
process addresses describe this run and may differ when reproduced.

### Negative control: phase

~~~powershell
@'
import hashlib, inspect, sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path("tests").resolve()))
paths = sorted(Path("src").rglob("*.py")) + sorted(Path("tests").rglob("*.py"))
before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
from ohlab.field import ComplexField
original = ComplexField.phase
try:
    ComplexField.phase = property(lambda self: np.angle(self.data))
    result = pytest.main(["-q", "-p", "no:cacheprovider", "--tb=line", "tests/test_field.py", "-k", "f06b or f06c or f08b"])
finally:
    ComplexField.phase = original
restored = ComplexField.phase is original

assert restored, "in-memory original was not restored"
assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
print("RESTORED: original in-memory callable; source/test SHA-256 unchanged")
assert result == pytest.ExitCode.TESTS_FAILED, result
print("NEGATIVE CONTROL: detected as expected")

'@ | .\.venv\Scripts\python.exe -B -
~~~

~~~text
FFF                                                                      [100%]
================================== FAILURES ===================================
E   assert np.False_
     +  where np.False_ = <function all at 0x0000016AD670F570>(array([[ 3.14159265, -3.14159265,  3.14159265, -3.14159265,  3.14159265,\n        -3.14159265,  3.14159265, -3.14159265...9265,  3.14159265, -3.14159265,  3.14159265,\n        -3.14159265,  3.14159265, -3.14159265,  3.14159265, -3.14159265]]) == 3.141592653589793)
     +    where <function all at 0x0000016AD670F570> = np.all
     +    and   3.141592653589793 = math.pi
C:\holographiclab\tests\test_field.py:218: assert np.False_
E   assert np.False_
     +  where np.False_ = <function all at 0x0000016AD670F570>(array([[-3.14159265, -3.14159265, -3.14159265, -3.14159265, -3.14159265,\n        -3.14159265, -3.14159265, -3.14159265...9265, -3.14159265, -3.14159265, -3.14159265,\n        -3.14159265, -3.14159265, -3.14159265, -3.14159265, -3.14159265]]) == 3.141592653589793)
     +    where <function all at 0x0000016AD670F570> = np.all
     +    and   array([[-3.14159265, -3.14159265, -3.14159265, -3.14159265, -3.14159265,\n        -3.14159265, -3.14159265, -3.14159265...9265, -3.14159265, -3.14159265, -3.14159265,\n        -3.14159265, -3.14159265, -3.14159265, -3.14159265, -3.14159265]]) = ComplexField(shape=(6, 10), dtype=complex128, wavelength_m=6.33e-07, grid=SamplingGrid(ny=6, nx=10, dy=4.9999999999999996e-06, dx=3.74e-06)).phase
     +    and   3.141592653589793 = math.pi
C:\holographiclab\tests\test_field.py:236: assert np.False_
E   AssertionError: assert b'\x00\x00\x0...DT\xfb!\t\xc0' == b'\x00\x00\x0...18-DT\xfb!\t@'
      
      At index 31 diff: b'\xc0' != b'@'
      Use -v to get more diff
C:\holographiclab\tests\test_field.py:319: AssertionError: assert b'\x00\x00\x0...DT\xfb!\t\xc0' == b'\x00\x00\x0...18-DT\xfb!\t@'
=========================== short test summary info ===========================
FAILED tests/test_field.py::test_f06b_signed_zero_branch_endpoints_preserve_stored_bits
FAILED tests/test_field.py::test_f06c_conjugation_retains_the_positive_pi_endpoint
FAILED tests/test_field.py::test_f08b_signed_zeros_follow_endpoint_policy_without_physical_meaning
3 failed, 46 deselected in 0.09s
RESTORED: original in-memory callable; source/test SHA-256 unchanged
NEGATIVE CONTROL: detected as expected
~~~

### Negative control: power

~~~powershell
@'
import hashlib, inspect, sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path("tests").resolve()))
paths = sorted(Path("src").rglob("*.py")) + sorted(Path("tests").rglob("*.py"))
before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
import test_field as subject
name = "test_f09_power_is_the_discretised_area_integral"
original = getattr(subject, name)
source = inspect.getsource(original)
needle = "pytest.approx(expected, rel=1e-15, abs=1e-24)"
assert source.count(needle) == 1
try:
    exec(compile(source.replace(needle, "pytest.approx(expected, rel=1e-15)"), "<weak-power-mutation>", "exec"), subject.__dict__)
    result = pytest.main(["-q", "-p", "no:cacheprovider", "--tb=line", "tests/test_field.py", "-k", "f09c"])
finally:
    setattr(subject, name, original)
restored = getattr(subject, name) is original

assert restored, "in-memory original was not restored"
assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
print("RESTORED: original in-memory callable; source/test SHA-256 unchanged")
assert result == pytest.ExitCode.TESTS_FAILED, result
print("NEGATIVE CONTROL: detected as expected")

'@ | .\.venv\Scripts\python.exe -B -
~~~

~~~text
F                                                                        [100%]
================================== FAILURES ===================================
E   Failed: DID NOT RAISE AssertionError
C:\holographiclab\tests\test_field.py:355: Failed: DID NOT RAISE AssertionError
=========================== short test summary info ===========================
FAILED tests/test_field.py::test_f09c_power_integral_assertion_rejects_small_relative_perturbation
1 failed, 48 deselected in 0.04s
RESTORED: original in-memory callable; source/test SHA-256 unchanged
NEGATIVE CONTROL: detected as expected
~~~

### Negative control: bytes

~~~powershell
@'
import hashlib, inspect, sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path("tests").resolve()))
paths = sorted(Path("src").rglob("*.py")) + sorted(Path("tests").rglob("*.py"))
before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
import _helpers as subject
original = subject.assert_bit_identical
def numerical_identity(actual, desired):
    assert actual.shape == desired.shape
    assert actual.dtype == desired.dtype and actual.dtype.str == desired.dtype.str
    np.testing.assert_array_equal(actual, desired)
try:
    subject.assert_bit_identical = numerical_identity
    result = pytest.main(["-q", "-p", "no:cacheprovider", "--tb=line", "tests/test_helpers.py", "-k", "signed_zero"])
finally:
    subject.assert_bit_identical = original
restored = subject.assert_bit_identical is original

assert restored, "in-memory original was not restored"
assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
print("RESTORED: original in-memory callable; source/test SHA-256 unchanged")
assert result == pytest.ExitCode.TESTS_FAILED, result
print("NEGATIVE CONTROL: detected as expected")

'@ | .\.venv\Scripts\python.exe -B -
~~~

~~~text
FFF                                                                      [100%]
================================== FAILURES ===================================
E   Failed: DID NOT RAISE AssertionError
C:\holographiclab\tests\test_helpers.py:45: Failed: DID NOT RAISE AssertionError
E   Failed: DID NOT RAISE AssertionError
C:\holographiclab\tests\test_helpers.py:45: Failed: DID NOT RAISE AssertionError
E   Failed: DID NOT RAISE AssertionError
C:\holographiclab\tests\test_helpers.py:45: Failed: DID NOT RAISE AssertionError
=========================== short test summary info ===========================
FAILED tests/test_helpers.py::test_bit_identity_rejects_signed_zero_differences[float-zero]
FAILED tests/test_helpers.py::test_bit_identity_rejects_signed_zero_differences[complex-imaginary-zero]
FAILED tests/test_helpers.py::test_bit_identity_rejects_signed_zero_differences[complex-real-zero]
3 failed, 10 deselected in 0.08s
RESTORED: original in-memory callable; source/test SHA-256 unchanged
NEGATIVE CONTROL: detected as expected
~~~

### Negative control: origin

~~~powershell
@'
import hashlib, inspect, sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path("tests").resolve()))
paths = sorted(Path("src").rglob("*.py")) + sorted(Path("tests").rglob("*.py"))
before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
import test_fft_conventions as subject
original = subject._physical_spectrum_via_fft
source = inspect.getsource(original)
needle = "return grid.pixel_area * origin_phase * raw_spectrum"
assert source.count(needle) == 1
try:
    exec(compile(source.replace(needle, "return grid.pixel_area * raw_spectrum"), "<omitted-origin-mutation>", "exec"), subject.__dict__)
    result = pytest.main(["-q", "-p", "no:cacheprovider", "--tb=line", "tests/test_fft_conventions.py", "-k", "test_c09"])
finally:
    subject._physical_spectrum_via_fft = original
restored = subject._physical_spectrum_via_fft is original

assert restored, "in-memory original was not restored"
assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
print("RESTORED: original in-memory callable; source/test SHA-256 unchanged")
assert result == pytest.ExitCode.TESTS_FAILED, result
print("NEGATIVE CONTROL: detected as expected")

'@ | .\.venv\Scripts\python.exe -B -
~~~

~~~text
FFFFFFFF                                                                 [100%]
================================== FAILURES ===================================
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1.87e-23
    
    Mismatched elements: 36 / 40 (90%)
    First 5 mismatches are at indices:
     [0, 1]: (-1.8700000000000004e-11+0j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 3]: (-1.8700000000000004e-11+0j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 5]: (-1.8700000000000004e-11+0j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 7]: (-1.8700000000000004e-11+0j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [1, 0]: (-1.512861779481152e-11-1.099158421786925e-11j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
    Max absolute difference among violations: 3.74e-11
    Max relative difference among violations: 2.
     ACTUAL: array([[ 1.870000e-11+0.000000e+00j, -1.870000e-11+0.000000e+00j,
             1.870000e-11+0.000000e+00j, -1.870000e-11+0.000000e+00j,
             1.870000e-11+0.000000e+00j, -1.870000e-11+0.000000e+00j,...
     DESIRED: array([[1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j,
            1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j],
           [1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j,...
C:\holographiclab\tests\test_fft_conventions.py:464: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1.87e-23
    
    Mismatched elements: 39 / 42 (92.9%)
    First 5 mismatches are at indices:
     [0, 1]: (-1.6848117829775243e-11-8.113625921498338e-12j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 2]: (1.1659259294758319e-11+1.462024872215216e-11j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 3]: (-4.16114146498308e-12-1.8231151957800105e-11j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 4]: (-4.16114146498308e-12+1.8231151957800105e-11j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 5]: (1.1659259294758319e-11-1.462024872215216e-11j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
    Max absolute difference among violations: 3.74e-11
    Max relative difference among violations: 2.
     ACTUAL: array([[ 1.870000e-11+0.000000e+00j, -1.684812e-11-8.113626e-12j,
             1.165926e-11+1.462025e-11j, -4.161141e-12-1.823115e-11j,
            -4.161141e-12+1.823115e-11j,  1.165926e-11-1.462025e-11j,...
     DESIRED: array([[1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j,
            1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j],
           [1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j,...
C:\holographiclab\tests\test_fft_conventions.py:464: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1.87e-23
    
    Mismatched elements: 36 / 40 (90%)
    First 5 mismatches are at indices:
     [0, 1]: (-1.8700000000000004e-11+0j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 3]: (-1.8700000000000004e-11+0j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 5]: (-1.8700000000000004e-11+0j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 7]: (-1.8700000000000004e-11+0j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [1, 0]: (-1.5128617794811523e-11+1.099158421786925e-11j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
    Max absolute difference among violations: 3.74e-11
    Max relative difference among violations: 2.
     ACTUAL: array([[ 1.870000e-11+0.000000e+00j, -1.870000e-11+0.000000e+00j,
             1.870000e-11+0.000000e+00j, -1.870000e-11+0.000000e+00j,
             1.870000e-11+0.000000e+00j, -1.870000e-11+0.000000e+00j,...
     DESIRED: array([[1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j,
            1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j],
           [1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j,...
C:\holographiclab\tests\test_fft_conventions.py:464: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1.87e-23
    
    Mismatched elements: 39 / 42 (92.9%)
    First 5 mismatches are at indices:
     [0, 1]: (-1.684811782977524e-11+8.113625921498338e-12j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 2]: (1.1659259294758319e-11-1.4620248722152157e-11j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 3]: (-4.161141464983079e-12+1.8231151957800102e-11j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 4]: (-4.161141464983079e-12-1.8231151957800102e-11j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
     [0, 5]: (1.1659259294758319e-11+1.4620248722152157e-11j) (ACTUAL), (1.8700000000000004e-11+0j) (DESIRED)
    Max absolute difference among violations: 3.74e-11
    Max relative difference among violations: 2.
     ACTUAL: array([[ 1.870000e-11+0.000000e+00j, -1.684812e-11+8.113626e-12j,
             1.165926e-11-1.462025e-11j, -4.161141e-12+1.823115e-11j,
            -4.161141e-12-1.823115e-11j,  1.165926e-11+1.462025e-11j,...
     DESIRED: array([[1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j,
            1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j],
           [1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j, 1.87e-11+0.j,...
C:\holographiclab\tests\test_fft_conventions.py:464: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1.06279e-21
    
    Mismatched elements: 36 / 40 (90%)
    First 5 mismatches are at indices:
     [0, 1]: (4.792545623407328e-11+8.384856297035752e-11j) (ACTUAL), (-4.7925456234073214e-11-8.384856297035753e-11j) (DESIRED)
     [0, 3]: (9.447971954881908e-11-1.8334492780509212e-10j) (ACTUAL), (-9.447971954881906e-11+1.8334492780509212e-10j) (DESIRED)
     [0, 5]: (-1.9860705245745912e-11+1.1572562950035102e-10j) (ACTUAL), (1.9860705245745837e-11-1.1572562950035105e-10j) (DESIRED)
     [0, 7]: (6.512560981842085e-12-1.0457496181283369e-10j) (ACTUAL), (-6.512560981842085e-12+1.0457496181283372e-10j) (DESIRED)
     [1, 0]: (-8.644756146220547e-11+1.5493115505365781e-10j) (ACTUAL), (-2.1128701715981474e-11-1.7615453912068081e-10j) (DESIRED)
    Max absolute difference among violations: 7.62270472e-10
    Max relative difference among violations: 2.
     ACTUAL: array([[-2.343516e-10-3.764179e-10j,  4.792546e-11+8.384856e-11j,
             1.360824e-10+5.780197e-12j,  9.447972e-11-1.833449e-10j,
             1.618009e-10-1.542152e-10j, -1.986071e-11+1.157256e-10j,...
     DESIRED: array([[-2.343516e-10-3.764179e-10j, -4.792546e-11-8.384856e-11j,
             1.360824e-10+5.780197e-12j, -9.447972e-11+1.833449e-10j,
             1.618009e-10-1.542152e-10j,  1.986071e-11-1.157256e-10j,...
C:\holographiclab\tests\test_fft_conventions.py:464: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1.12015e-21
    
    Mismatched elements: 39 / 42 (92.9%)
    First 5 mismatches are at indices:
     [0, 1]: (2.383234367174476e-12-5.009434729689425e-11j) (ACTUAL), (1.9587902744090693e-11+4.6167494010816525e-11j) (DESIRED)
     [0, 2]: (8.224725027884851e-11+2.06852435291734e-10j) (ACTUAL), (2.130040679160434e-10+6.46668942796085e-11j) (DESIRED)
     [0, 3]: (2.1463886817142808e-10-1.8941110598292213e-10j) (ACTUAL), (1.3690053269114798e-10+2.5140535982445824e-10j) (DESIRED)
     [0, 4]: (-1.1750871049968397e-10-1.1320938693414708e-10j) (ACTUAL), (-8.422284323470045e-11+1.3975398030384332e-10j) (DESIRED)
     [0, 5]: (-8.451687453610585e-11-5.909910520781655e-11j) (ACTUAL), (-6.4898683210747605e-12-1.0292564270817807e-10j) (DESIRED)
    Max absolute difference among violations: 5.79203171e-10
    Max relative difference among violations: 2.
     ACTUAL: array([[-2.293749e-10-4.007852e-10j,  2.383234e-12-5.009435e-11j,
             8.224725e-11+2.068524e-10j,  2.146389e-10-1.894111e-10j,
            -1.175087e-10-1.132094e-10j, -8.451687e-11-5.909911e-11j,...
     DESIRED: array([[-2.293749e-10-4.007852e-10j,  1.958790e-11+4.616749e-11j,
             2.130041e-10+6.466689e-11j,  1.369005e-10+2.514054e-10j,
            -8.422284e-11+1.397540e-10j, -6.489868e-12-1.029256e-10j,...
C:\holographiclab\tests\test_fft_conventions.py:464: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1.06279e-21
    
    Mismatched elements: 36 / 40 (90%)
    First 5 mismatches are at indices:
     [0, 1]: (6.512560981842085e-12-1.045749618128337e-10j) (ACTUAL), (-6.512560981842085e-12+1.0457496181283372e-10j) (DESIRED)
     [0, 3]: (-1.9860705245745912e-11+1.1572562950035102e-10j) (ACTUAL), (1.9860705245745837e-11-1.1572562950035105e-10j) (DESIRED)
     [0, 5]: (9.447971954881908e-11-1.8334492780509212e-10j) (ACTUAL), (-9.447971954881906e-11+1.8334492780509212e-10j) (DESIRED)
     [0, 7]: (4.792545623407328e-11+8.384856297035752e-11j) (ACTUAL), (-4.7925456234073214e-11-8.384856297035753e-11j) (DESIRED)
     [1, 0]: (-2.738556780410295e-12-2.7197892727263597e-10j) (ACTUAL), (-1.5764966340976986e-10+2.216452575635211e-10j) (DESIRED)
    Max absolute difference among violations: 7.62270472e-10
    Max relative difference among violations: 2.
     ACTUAL: array([[-2.343516e-10-3.764179e-10j,  6.512561e-12-1.045750e-10j,
            -2.994293e-11+2.348537e-11j, -1.986071e-11+1.157256e-10j,
             1.618009e-10-1.542152e-10j,  9.447972e-11-1.833449e-10j,...
     DESIRED: array([[-2.343516e-10-3.764179e-10j, -6.512561e-12+1.045750e-10j,
            -2.994293e-11+2.348537e-11j,  1.986071e-11-1.157256e-10j,
             1.618009e-10-1.542152e-10j, -9.447972e-11+1.833449e-10j,...
C:\holographiclab\tests\test_fft_conventions.py:464: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1.12015e-21
    
    Mismatched elements: 39 / 42 (92.9%)
    First 5 mismatches are at indices:
     [0, 1]: (2.2018765284949943e-11+3.271458651450035e-11j) (ACTUAL), (-5.643894910794194e-12-3.9028408188451136e-11j) (DESIRED)
     [0, 2]: (-8.451687453610582e-11-5.909910520781654e-11j) (ACTUAL), (-6.4898683210747605e-12-1.0292564270817807e-10j) (DESIRED)
     [0, 3]: (-1.1750871049968392e-10-1.132093869341471e-10j) (ACTUAL), (-8.422284323470045e-11+1.3975398030384332e-10j) (DESIRED)
     [0, 4]: (2.1463886817142797e-10-1.894111059829221e-10j) (ACTUAL), (1.3690053269114798e-10+2.5140535982445824e-10j) (DESIRED)
     [0, 5]: (8.224725027884848e-11+2.0685243529173397e-10j) (ACTUAL), (2.130040679160434e-10+6.46668942796085e-11j) (DESIRED)
    Max absolute difference among violations: 5.79203171e-10
    Max relative difference among violations: 2.
     ACTUAL: array([[-2.293749e-10-4.007852e-10j,  2.201877e-11+3.271459e-11j,
            -8.451687e-11-5.909911e-11j, -1.175087e-10-1.132094e-10j,
             2.146389e-10-1.894111e-10j,  8.224725e-11+2.068524e-10j,...
     DESIRED: array([[-2.293749e-10-4.007852e-10j, -5.643895e-12-3.902841e-11j,
            -6.489868e-12-1.029256e-10j, -8.422284e-11+1.397540e-10j,
             1.369005e-10+2.514054e-10j,  2.130041e-10+6.466689e-11j,...
C:\holographiclab\tests\test_fft_conventions.py:464: AssertionError:
=========================== short test summary info ===========================
FAILED tests/test_fft_conventions.py::test_c09_physical_spectrum_matches_independent_coordinate_sum[center_impulse--1-shape0]
FAILED tests/test_fft_conventions.py::test_c09_physical_spectrum_matches_independent_coordinate_sum[center_impulse--1-shape1]
FAILED tests/test_fft_conventions.py::test_c09_physical_spectrum_matches_independent_coordinate_sum[center_impulse-1-shape0]
FAILED tests/test_fft_conventions.py::test_c09_physical_spectrum_matches_independent_coordinate_sum[center_impulse-1-shape1]
FAILED tests/test_fft_conventions.py::test_c09_physical_spectrum_matches_independent_coordinate_sum[complex--1-shape0]
FAILED tests/test_fft_conventions.py::test_c09_physical_spectrum_matches_independent_coordinate_sum[complex--1-shape1]
FAILED tests/test_fft_conventions.py::test_c09_physical_spectrum_matches_independent_coordinate_sum[complex-1-shape0]
FAILED tests/test_fft_conventions.py::test_c09_physical_spectrum_matches_independent_coordinate_sum[complex-1-shape1]
8 failed, 19 deselected in 0.13s
RESTORED: original in-memory callable; source/test SHA-256 unchanged
NEGATIVE CONTROL: detected as expected
~~~

### Full suite after restoration

The same full-suite command was rerun after all four subprocess controls
completed and restored their callables:

~~~powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
~~~

Exact final output (exit 0):

~~~text
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 66%]
........................................................................ [ 89%]
...................................                                      [100%]
323 passed in 2.03s
~~~

## Executable and preservation verification

Compared every production module's AST against baseline 1b2e755 after
removing docstrings. The field AST matches after substituting only the
approved phase body; the grid AST matches after substituting only the
approved diagnostic string. No other production executable AST differs.
SHA-256 comparison uses the pre-edit bytes of every tracked file. Historical
handoff/ledger line order and original fenced blocks were checked separately.
The two historical excerpts were checked against their exact recorded output
text; an omitted separator was restored during documentation review.
Captured pytest output retains its original whitespace, including whitespace
on blank traceback lines; those literal output lines are intentional.

Actual verification output:

~~~text
ALLOWLIST: exact 22 paths (19 existing + 3 new)
PROTECTED FILES: 34 pre-existing tracked files SHA-256 unchanged
__init__.py executable AST: unchanged
field.py AST: only approved exact phase endpoint body
grid.py AST: only approved diagnostic string
propagation.py executable AST: unchanged
units.py executable AST: unchanged
validation.py executable AST: unchanged
CATEGORY C: C06/C07 AST unchanged
HISTORY: all original lines preserved in 7 changed handoffs and ledger; 58 original fenced blocks intact
HISTORICAL EXCERPTS: exact Q1/R1 text found in original recorded outputs
PYTEST.APPROX: all 8 sites have explicit relative and absolute tolerance
~~~

## Tutor errata and boundaries

Use the normative v0.4 explanations and this dated clarification when
teaching M0/M1:

- Distinguish a canonical branch representation from phase equivalence
  modulo 2*pi, and from physically undefined phase at zero amplitude.
- Explain literal representation separately from numerical equality,
  especially signed zeros and dtype/endian representation.
- State quantity scales and both tolerances; the small-power example shows
  why an implicit absolute threshold can hide a relative error.
- Distinguish raw array DFT values from the physical-coordinate spectrum,
  including pixel area and the spatial-origin phase. Show their cancellation
  in a same-grid transform pair before suggesting any shifts.
- Qualify real-kz conjugacy and discuss evanescent decay separately.
  Do not claim Fourier-library choice forces the time-harmonic convention.
- Teach fine pitch as access to higher spatial frequencies; failure of a
  real Nyquist-angle calculation does not make fine sampling invalid.
- State what each test or numerical reference establishes. A numerical
  self-comparison and an analytic paraxial benchmark are different evidence.
  “Ten mutations caught” does not establish “zero possible test gaps.”
- Preserve original milestone measurements and transcripts, with dated
  corrections attached. Use 72/31 for the historical M1 file attribution,
  291 for its acceptance total, and 323 for this maintenance suite.

The brief M0/M1 tutor-context links are technical errata only. No lesson was
assumed complete, no historical learning record was changed, and the user's
course was not restarted. Codex remains the engineering agent; the separate
tutor controls teaching. No category C guard, M2 I/O boundary, target loading,
preprocessing, Band-Limited ASM, Gerchberg-Saxton, new metrics, UI, or hardware
functionality was implemented.
