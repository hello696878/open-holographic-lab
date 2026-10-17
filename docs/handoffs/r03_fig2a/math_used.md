# Mathematics used by the independent ideal workspace

## Observation before interpretation

For local coherent two-component states E_m and declared probabilities p_m,
the observation is C=Σp_m E_m E_m†, with p_m≥0 and Σp_m=1. It is an
uncentered optical second moment. Neither outer(mean(E),mean(E)†) nor a
centered sample covariance with M−1 is the same measurement. No sample is
normalized individually; source amplitude and analyzer loss remain measurable.

The model assumes this ensemble reduction. Random phases alone do not derive
it from coherent propagation or physical aperture integration. C and Stokes
have amplitude-unit squared, without pixel area or calibrated watts.

## Signed Stokes and undefined values

Cxy=<Ex Ey*>. With (+x,+y) and exp(-iωt), define S0=Cxx+Cyy,
S1=Cxx−Cyy, S2=2ReCxy, S3=−2ImCxy, taking diagonal real values only under
the bounded Hermiticity policy. `(1,i)/sqrt2` has positiveS3. No ambiguous
R/L label or manufacturer convention is imported.

For S0>0, normalized Stokes is S/S0 and DoP=|S|/S0. Polarized direction
S/|S| exists only if |S|>0. C=0 is exactly dark, so DoP and normalized
observables are null. Nonzero unpolarized light has DoP0 and direction null.
DoP can also be obtained independently from C's eigenvalues, but no clipped
eigenvalue or epsilon denominator repairs invalid input.

The linear analyzer a=(cosθ,sinθ) has intensity a†Ca=Σp|a†E_m|².
This direct projection identity independently checks both normalization and
the second-moment reduction. Uniform unitary retarders preserve trace,
eigenvalues and DoP. Polarizers can remove intensity; that loss is not erased.

## One realized Gaussian model

D input is (A,A)/sqrt2. Draw256 iid standard-normal values once with the
recorded local PCG64 Generator, form φ=μ+σZ and retain both φ and mod(φ,2π).
The implementation uses public `default_rng(seed)` and checks PCG64 before
drawing, satisfying the unchanged core RNG guard. Independent explicit-PCG64
references and five before/after phase hashes verify identical realizations.
For a tiny negative subnormal, NumPy modulo can round to the stored2π endpoint;
that actual value is retained and accepted by the periodic display scale.
Apply diag(exp(iφ),1), QWP and HWP. σ is standard deviation in radians,
not variance. There is no clipping, centering, variance correction, fitting,
sorting or retry. The sample orientation is16rows×16columns,C-order.

For this source and probability-mean model,
C_afterSLM=A²[[1,c],[c*,1]]/2, c=Σp exp(iφ). Therefore finiteDoP=|c|,
while mean intensity stays A² within floating-point evaluation error. Uniform
lossless output waveplates change Stokes direction but preserve the same
finite eigenvalues and DoP. At A=0 the optical normalized values are undefined.

For an infinite Gaussian ensemble, E[exp(iφ)]=exp(iμ−σ²/2), giving separately
labelled populationDoP=exp(−σ²/2). This does not replace finite data.
For equal weights, expanding |Σexp(iφ)/M|² into diagonal M terms and
off-diagonal M(M−1) iid terms gives
E[DoP_M²]=|Eexp(iφ)|²+(1−|Eexp(iφ)|²)/M. A test-only uniform-phase case
has expectation1/M, not a requirement that each seed give1/sqrtM.

## Numerical and evidence boundary

Full precision is float64/complex128. Domain envelopes scale with actual
intensity; no floor1 hides material defects in weak states. Raw DoP and
eigenvalues remain visible with a roundoff flag for accepted tiny residuals;
material violations fail. Numerical tolerances and bounded sampling checks
are different evidence, and neither certifies experimental agreement.

Existing public Jones operations require legitimate SI grids. A grid-free
ensemble does not invent a physical pitch merely to call them; independent
tests compare the explicit2×2 action on real test fixtures. The existing
Jones/scalar/ASM/GS implementations and historical conventions are unchanged.

See section3.21 of the normative conventions, exact independent measurements
in tests_and_evidence.md, and the frozen opening model contract in ignored
implementation evidence. No external article equations or datasets are
required as production dependencies.
