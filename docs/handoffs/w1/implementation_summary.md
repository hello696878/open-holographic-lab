# W1 — Computed wave-field sections

## Scope and current validation boundary

W1 adds an optional **Computed Sections** view inside the existing Sequential
bench. It uses the existing experiment editor, Three.js renderer and explicit
submission workflow. Its first supported train is exactly:

**Gaussian source → one circular or rectangular physical aperture → one ideal
thin lens → observation plane**, in the original stored order.

Both focal-length signs, unequal transverse pitches, even/odd sample counts,
zero-distance intervals, dark fields and co-located elements retain V0's
supported numerical semantics. W1 rejects other trains and grids above 128
samples on either axis; it does not resize or reorder them. Ordinary Sequential
behavior and its larger existing limits remain unchanged.

The implementation has numerical, transport, ownership and genuine production
browser acceptance. Exact commands, raw results, retained failures, screenshots
and recording provenance are in [tests_and_evidence.md](tests_and_evidence.md).
Publication is conditional on the separately recorded clean-postcommit gate;
the committed handoff does not substitute for that later gate or remote checks.

## Calculated fields and identity

The new public `ohlab.optics.wave_field` module calls unchanged public
`run_experiment` exactly once, requesting three captures: `source`,
`after:<aperture-id>` and `after:<lens-id>`. Every optional section propagates
directly from its proper upstream complex capture using public ASM with explicit
`pad_factor=1`. No displayed section is used as another section's upstream input.

All six optical events remain distinct: source, aperture before/after, lens
before/after and observation. At equal physical z their event identities and
complex fields remain separate. The canonical terminal complex field is retained
by object identity and unchanged bytes. It is not recomputed through another
path and substituted. Independent tests compare it byte-for-byte with ordinary
V0 on the same captured experiment.

At most19 explicit interior positions supplement the six required events.
Default allocation uses span-proportional floor plus largest remainder, with
stable earlier-gap ties. Zero spans get none; an entirely co-located train has
six event planes. Each returned plane has an exact id, stage, z, upstream
selector, origin and forward separation. Raw sampled intensities are returned
as owned readonly float64 `(K,ny,nx)` data; there is no retained intermediate
complex stack or complex browser transport.

## Integrated product behavior

Mounted equipment, calculated sheets, event-split sampled meridional curtains,
axial diagnostics and a cursor snapping to returned section ids form the bench
view. Curtains represent nearest-sample display bands and are split at thin
elements; they are not additional propagated planes. Co-located sides are not
given an invented physical displacement.

One initial shared linear display range,0–3 amplitude-unit², stays fixed across
recomputation until explicitly changed. Amber opacity/glow is labelled
presentation; authoritative intensities, detector values, sampled norms and
optical parameters are unchanged. No per-plane normalization, Gaussian envelope
fit or simulated side-scattering interpretation is permitted.

Only explicit Simulate calculates. Optical edits detach current attachments;
revision/epoch/request checks reject stale or late attachment. Camera, cursor,
section, precision, color and glow changes use retained data only. Numerical
completion and presentation failure remain separate; presentation recovery must
not replay the calculation. Real-browser acceptance covers all three desktop
sizes, actual 200% Chrome zoom, each parameter edit, cached inspection,
stale/late completion, context recovery, mixed ownership admission and release.

## Current numerical results

Final source-identified numerical report:
`runs/w1_implementation_01/core/validation_final_01/report.json`.
Python3.11.9 / NumPy2.4.6 from the existing project interpreter;
`wave_field.py` SHA256
`156c5681ebbc2d65dee722b7840f84c0809530edc6abcd7208169c48ab43b657`.

- All25 complex sections on eight asymmetric/mixed-parity reference matrices:
  worst relative L2 **1.8348661564757353e-12**, bound2e-11.
- Free Gaussian30/60/120mm:1.1463e-7 /2.2930e-7 /4.5857e-7, bound1e-6.
- Signed80mm lens:worst5.8137e-6, bound5e-5, with absolute phase/prefactor.
- Clean260µm default:separate pitch/window intensity differences0.6623%/0.6058%.
- Strong80µm clipping at128²:16.2646%/15.8519%; retained counterexample.
- Three warmed shipped runs:75.9327/67.4650/61.4378ms; median67.4650ms
  versus the0.5s local bound. Separate traced peak9,103,459B; this is not RSS,
  browser/GPU memory or a universal performance guarantee.

Existing scalar implementations, prior conventions, document schemas, four
mode identities, R03 model and historical evidence are protected. The exact
40-path inventory and protected hashes are recorded in tests_and_evidence.md
and the ignored acceptance manifests. No dependency installation or lockfile,
learning-state or historical-measurement change is part of W1.
