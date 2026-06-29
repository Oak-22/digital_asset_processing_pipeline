## Stage 2 Layout

Stage 2 works with Lightroom XMP sidecars that may be updated by the
Lightroom catalog as Develop edits are applied. Because these sidecars
represent mutable working state, Stage 2 must preserve explicit
before/after boundaries before using them as evidence.

Because Lightroom sidecars are mutable working-state files, the pipeline
captures an immutable pre-conditioning XMP checkpoint before Stage 2
Develop edits are applied. This preserves a validated upstream reference
state and allows Stage 2 to prove its transformation through before/after
parameter comparison rather than relying on memory or visual inspection
alone.

Recommended artifact model:

- `../live_workspace/`: mutable Lightroom working set shared by the
  pipeline and not owned by any single stage
- `reference_state/xmp_preconditioning/`: frozen XMP sidecars copied
  before Stage 2 Develop edits begin
- `conditioned_state/xmp_postconditioning/`: frozen XMP sidecars copied
  after Stage 2 baseline conditioning is complete
- `sidecar/`: optional working input location for ad hoc extraction runs
  against an explicit sidecar set

Derived analysis artifacts belong under `outputs/stage2/`, including
develop-setting extracts, parameter audit reports, comparison reports,
and the Stage 2 manifest.
