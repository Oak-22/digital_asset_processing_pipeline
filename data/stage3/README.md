## Stage 3 Layout

Stage 3 captures Lightroom semantic/local conditioning state after the
Stage 2 global Develop baseline. The core evidence question is how
Lightroom persists masks, local adjustment state, and point-color state
across increasingly narrow GUI-assisted edits.

Stage 3 currently uses this checkpoint ladder:

```text
presegmentation
  -> postmasking_no_local_adjustment
  -> postlocal_adjustment
  -> postglobal_point_color
```

Each checkpoint is a frozen sidecar state copied out of the mutable
Lightroom working set. The frozen checkpoint folders are the evidence
inputs for the Stage 3 extraction and comparison outputs.

Recommended artifact model:

- `reference_state/lightroom_sidecars_presegmentation/`: frozen sidecars
  before Stage 3 mask creation
- `conditioned_state/lightroom_sidecars_postmasking_no_local_adjustment/`:
  frozen sidecars after mask creation/copying, before intentional masked
  local Develop changes
- `conditioned_state/lightroom_sidecars_postlocal_adjustment/`: frozen
  sidecars after masked local adjustment changes
- `conditioned_state/lightroom_sidecars_postglobal_point_color/`: frozen
  sidecars after the asset-level global Point Color test
- `spikes/proof_of_capability_mask_sidecar_parsing/`: smaller exploratory
  evidence used to prove Lightroom mask state persistence before
  promoting the shape into the main Stage 3 checkpoint ladder

Derived analysis artifacts belong under `outputs/stage3/`. The current
file names keep `stage3` as a common prefix and encode the state being
extracted or compared:

```text
stage3_extracted_presegmentation_mask_state.json
stage3_extracted_postmasking_no_local_adjustment_mask_state.json
stage3_extracted_postlocal_adjustment_mask_state.json
stage3_extracted_postglobal_point_color_mask_state.json

stage3_mask_state_postmasking_no_local_adjustment_comparison.json
stage3_mask_state_postlocal_adjustment_comparison.json
stage3_mask_state_postglobal_point_color_comparison.json
```

The names are intentionally explicit, but they are becoming visually
dense. If Stage 3 grows further, prefer grouping by folder before
renaming stable artifacts:

```text
outputs/stage3/
  extracts/
    presegmentation_mask_state.json
    postmasking_no_local_adjustment_mask_state.json
    postlocal_adjustment_mask_state.json
    postglobal_point_color_mask_state.json

  comparisons/
    presegmentation_vs_postmasking_no_local_adjustment.json
    postmasking_no_local_adjustment_vs_postlocal_adjustment.json
    postlocal_adjustment_vs_postglobal_point_color.json

  spikes/
    proof_of_capability_mask_sidecar_parsing_report.json
```

That grouping keeps the workflow readable in file explorers while
preserving the conceptual sequence:

```text
source checkpoint
  -> extracted state
  -> comparison report
```

Do not treat `data/live_workspace/` as the durable Stage 3 evidence
source. Lightroom may continue mutating it as the catalog updates. Use
the frozen Stage 3 sidecar folders for repeatable extraction,
comparison, and review.
