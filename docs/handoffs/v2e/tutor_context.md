# V2e context for the separate tutor

This supports a future teaching conversation. It does not assert that any
lesson is complete, restart a course or gate approved engineering work. Assume
introductory physics, single-variable calculus and basic Python. Exact schemas,
limits and implementation details are in the other V2e handoffs; current
measured acceptance is in [tests_and_evidence.md](tests_and_evidence.md).

## What was added

The virtual bench can prepare a JSON file containing one current valid
experiment draft and a short title/notes. Another session can upload it,
validate it, inspect a preview, explicitly confirm replacement and restore the
settings. The user still presses Simulate to obtain a new result. The file
works independently of its original filename, tab and repository path because
it contains complete scientific inputs rather than references to an old session.

Three experiment families are supported: an ordered scalar source/aperture/lens
train; the fixed ideal two-arm scalar interference model; and ordered ideal
Jones polarization actions at one plane. V2e changes none of their optical
equations. Their separate numerical/model handoffs remain the teaching source
for propagation, interference and polarization. The new topic is faithful
representation and controlled restoration of inputs.

## Useful distinctions to teach

**Settings versus results.** A recipe states what to calculate; the calculated
field/intensity is a result. Saving the recipe does not mean the calculation
has run, succeeded or been preserved. V2e saves the recipe only. Earlier visible
results retain their own identities, and import cannot claim they came from
the restored settings.

**Units versus display.** Files store metres and radians. An editor can display
millimetres or a shortened decimal label. The underlying value must remain
authoritative when the user simply focuses, blurs or selects a field. For
example, `0.020000000000000004` m can look like `20` mm, but parsing `20` again
would produce the slightly different `0.02` m. A real edit changes the selected
field; a cosmetic interaction must not change every loaded number.

**JSON text versus a number.** Computers store the supported real inputs as
binary64 numbers. Many decimal fractions cannot be represented exactly.
Canonical output uses a reproducible text spelling of those supported values;
it does not preserve arbitrary precision or the original spacing. Large integer
tokens used in real fields may round once. Nonzero decimal underflow such as
`1e-999` rejects instead of quietly turning into zero. A representable tiny
nonzero value such as `5e-324` can remain distinct from zero if its field allows
it. Negative-zero bits are not part of the browser document guarantee.

**Order is scientific data.** Co-located sequential components and Jones
elements retain their stored order and stable names. Arbitrary complex
coefficients retain their magnitude and phase. Import does not sort the train,
rename elements, normalize coefficients or wrap phases merely to make a file
look simpler.

**File identity versus scientific identity.** A title edit changes file bytes
without changing the optics. The response hash identifies the existing
validated scientific definition, while a hash of complete file bytes identifies
that file. A temporary operation generation prevents a slow old response from
replacing a newer choice. None of these is authorship, a signature, a successful
simulation or qualified replay.

**Validation versus computation.** Validation checks structure, supported
fields, finite values, units/domains and resource limits. It does not sample a
light field or apply an optical element. The two bounded import validations
first check untouched raw bytes, then prepare values through ordinary browser
serialization. Only the final response can be previewed or applied. This also
handles existing signed-zero serialization without changing old scientific
contracts.

## Suggested teaching sequence

1. Inspect a small exported document and locate wrapper, complete experiment
   and metadata. Explain why an empty experiment or unknown field rejects.
2. Identify the SI lengths/radians and distinguish integer grid/readout fields.
3. Predict what a metadata edit, a camera move and one real optical edit should
   change. Compare settings identity with result identity.
4. Walk through export, download, fresh-session import, preview, acknowledgment,
   restore and explicit simulation. Explain why cancellation or an active
   computation prevents an unsafe replacement.
5. Use the unchanged-text decimal example to motivate authoritative numeric
   data and exact comparison. Discuss why screenshots/rounded metrics cannot
   prove complete numerical equality.

These are possible lesson activities, not completed learning records. Any
demonstration should respect the documented tested scope: settings restoration
is not saved-result replay, cross-platform bitwise certification or an extension
of the optical models.
