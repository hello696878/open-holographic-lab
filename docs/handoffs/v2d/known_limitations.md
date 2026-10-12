# V2d known limitations

Recorded 2026-10-12. Acceptance outcomes are recorded separately in
tests_and_evidence.md; this document does not predict pending gates.

- Classical coherent monochromatic ideal uniform element actions on one
  stipulated reference plane. No vector propagation, tilted/reflected frame,
  material/thickness/dispersion/coating model, aperture, polarized interference,
  statistical/unpolarized light, Stokes/Mueller, calibration or hardware.
- Gaussian waist is fixed to the sampled plane for this app. The broader
  public source library is unchanged; inherited source geometry validation is
  distinct from the common-plane Jones contract.
- Complex128/float64 arithmetic remains V2c's bounded policy. Invalid/overflow/
  unusable combined norm or ratio fails; small component/intensity tails can
  underflow. No arbitrary dynamic-range or arbitrary-precision guarantee.
- All four complex components determine exact-dark classification. A tiny
  nonzero sample may have zero rounded intensity or invisible displayed motion;
  preserve its values and disclose view-scale/precision limitations.
- One explicit selected sample per operation, maximum nine stage samples.
  Intensity picking elsewhere does not provide another complex vector. A new
  complex sample requires an explicit operation; no full complex field cache.
- Input/final intensity only, no intermediate image stack. Maximum 128 per axis,
  eight elements and thirteen declared sweep points. These are resource caps,
  not physical accuracy/sampling guarantees.
- Element layout, housing and thickness are schematic. No physical z schema;
  camera and selection do not change optics. Axis-drag and analytic overlay are
  deliberately omitted. Coefficients remain explicitly unnormalized.
- Default shared intensity/amplitude scales preserve relative loss. Manual
  magnification/colors change display only and cannot improve numerical accuracy.
  A ratio or signed delta alone is not a causal gain/efficiency measurement.
- Tau is dimensionless optical-phase illustration, not calibrated real-time
  movie playback. One owned callback must detach on teardown; the common bench
  renderer continues serving other modes.
- App-owned persistent 16 MiB/transient 32 MiB accounting excludes JS object/string
  overhead, renderer caches/framebuffers, GPU/driver and whole-process memory.
  Planning arithmetic is distinct from shipped ownership observations.
  The read-only ownedMemory and polarization.budget snapshots cover all three
  modes; legacy twoPath budget debug fields remain narrower two-mode estimates
  for compatibility and must not be used as the current admission inventory.
- Transient local experiment mode only: no save/load, M5 bundle, qualified
  replay badge, public deployment/authentication or external assets/inputs.
- Real production, controlled-child browser and synthetic transport/isolated
  fault evidence have separate claims. A skipped controlled test is not a pass.
- Existing Windows file-symlink privilege skip is retained; junction coverage
  remains separate. No privilege elevation/test changes remove that limitation.
- If Chrome/WebGL, loopback service ownership, build, resource or required
  postcommit smoke fails, publication stops; no automatic repair/install or
  controlled-server fallback substitutes for production acceptance.

V2c historical source/demo/figure measurements and precommit handoffs are
preserved. A dated ledger closeout reads existing publication records only.
Later milestones and learning records remain separate and unchanged.
