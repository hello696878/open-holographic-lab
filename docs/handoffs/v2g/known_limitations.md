# V2g limits and evidence boundaries

- This is an ideal aligned, unfolded, low-angle Jones-envelope experiment on
  a periodic sampled grid. It is not full-vector Maxwell, reflected-frame or
  coating/material optics, a physical detector, calibrated power, or a quantum
  experiment. It adds no arbitrary topology, tilted planes, hardware or deployment.
- Each arm has zero to two terminal polarizer/retarder actions. Source grids
  have at most 128 samples on each axis. Public numerical intersection failures
  remain visible; static validation is not a guarantee of numerical success.
- Only output intensity images and axes are transported. Full intermediate
  complex fields and ellipse animation are excluded. Sweep rows are scalar;
  selecting a row does not compute its image. An explicit single simulation is
  required. The finite 17-point extrema do not establish continuous visibility.
- Version-1 settings documents remain closed to sequential, two_path and
  polarization. Version 2 accepts only polarized_two_path. Documents contain
  settings and literal metadata, no result arrays, sweep recipe, completion
  status or qualified-replay claim. Import is not numerical validation.
- The fixed app-owned resource budgets are 16 MiB persistent and 32 MiB
  transient. Ownership accounting includes scientific arrays, document buffers,
  incoming decoding, display preparation and rollback overlap, deduplicating
  aliases. It is not a browser-process memory measurement or a GPU-driver quota.
  Internal live renderer caches need not be zero after releasing result owners.
  Synchronous garbage collection is neither required nor claimed.
- Explicit release discards retained calculations in all modes and result views;
  it preserves settings, invalid edits, documents and camera. Admission rejection
  does not evict automatically or retry. Release cannot cancel a running backend
  worker. A disconnected request remains unknown until that worker terminates.
- The service binds only 127.0.0.1:8510 with the existing local Host/Origin,
  framing and static-file policies. It is not an internet deployment or an
  authentication system. No unrelated service or port8501 is managed.
- Genuine production browser observations, controlled failures, isolated-copy
  mutations and independent mathematical references are separate evidence
  layers. A permission/setup failure is not successful fault detection. Prior
  milestone results remain historical, and measured timings are not guarantees.
- The existing Windows file-symlink privilege skip remains; junction behavior
  is tested separately. No elevation is used to remove that skip.
- Teaching is handled separately. These handoffs assert no lesson completion.
  No stage after V2g is authorized or begun.
