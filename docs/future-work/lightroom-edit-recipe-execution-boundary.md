# Lightroom Edit Recipe Execution Boundary

## Purpose

This note scopes a future extension for executing model-suggested edit
recipes inside or adjacent to Lightroom Classic.

The goal is not to claim that the current repository can automate
Lightroom AI masking or perform pixel-level ML edits inside Lightroom.
The goal is to define a realistic deployment boundary:

```text
external model
  -> auditable edit recipe
  -> Lightroom-side executor for supported controls
  -> checkpointed XMP state
  -> human review and correction
```


## Desired Outcome

The desired outcome is a workflow where an external model writes a
structured recommendation and a lightweight Lightroom-side executor
applies the supported parts.

Example:

```json
{
  "asset_key": "JB107456",
  "global_develop_settings": {
    "Exposure2012": 0.35,
    "Highlights2012": -40,
    "Shadows2012": 25,
    "Vibrance": 12,
    "Tint": 8
  },
  "crop": {
    "CropTop": 0.02,
    "CropLeft": 0.08,
    "CropBottom": 0.94,
    "CropRight": 0.91
  },
  "review_policy": {
    "requires_human_acceptance": true,
    "unsupported_operations": []
  }
}
```

This keeps the model output inspectable. It also avoids treating a GUI
workflow as fully automatable before the control surface has been
verified.


## Capability Levels

### Level 1: Global Recipe Automation

This is the most realistic near-term target.

The model can suggest global edits such as:

- exposure, highlights, shadows, whites, and blacks
- white balance, tint, vibrance, saturation, and hue normalization
- crop values
- lens profile and process-version settings where supported

A Lightroom plug-in or script can then be tested as a recipe executor
for the subset of settings exposed by Lightroom's scripting or plug-in
interfaces.

This level maps cleanly to the current Stage 2 evidence model.


### Level 2: Existing Mask Adjustment Automation

This level is plausible but unproven.

The key question is whether a Lightroom-side executor can safely read,
preserve, or modify local adjustment settings when masks already exist.
For this project, that matters because Stage 3 may create predictable
mask families such as:

- one-person subject masks
- two-person, three-person, or four-person group masks
- background or foliage masks
- face or subject-emphasis masks

The first useful test is not full AI mask generation. It is whether an
executor can apply or preserve local edit values without damaging masks
that were created through the GUI.


### Level 3: AI Mask Generation Automation

This level should be treated as unproven until a spike demonstrates it.

The GUI may support AI subject, person, or background masks, but that
does not prove that a plug-in can create, refine, or batch-apply those
masks programmatically. Stage 3 should therefore begin with
human-operated or GUI-assisted mask generation and use the pipeline to
capture the resulting local edit state.


## Execution Boundary

The future architecture should keep these responsibilities separate:

```text
ML model:
  produce a suggested edit recipe

Lightroom executor:
  apply supported settings
  preserve unsupported state
  mark unsupported suggestions for review

Pipeline:
  checkpoint pre/post XMP state
  compare develop parameters
  record accepted, rejected, or manually corrected suggestions

Human reviewer:
  approve, adjust, or reject model recommendations
```

This makes the workflow auditable even when some operations remain
manual.


## Capability Spikes

Before making stronger automation claims, run small proof-of-capability
spikes:

```text
Spike A:
  Can the executor read global develop settings from the active photo?

Spike B:
  Can the executor apply a global recipe without damaging existing XMP
  state?

Spike C:
  Can the executor apply a preset or setting change while preserving
  existing masks?

Spike D:
  Can the executor inspect local adjustment or mask-related settings in
  a way that is stable enough for comparison?

Spike E:
  Can the executor create or trigger Lightroom AI masks? If not, can it
  cleanly hand off those operations to the GUI?
```

Each spike should produce a small physical artifact, such as a recipe
JSON, a pre/post XMP checkpoint, and a comparison report.


## Relationship To Stage 3

Stage 3 should be framed as semantic/local conditioning evidence before
it is framed as automation.

The initial Stage 3 value is:

```text
create or apply masks in Lightroom
  -> capture pre/post local edit state
  -> compare masked develop parameters
  -> record human review outcome
```

The later automation value is:

```text
model suggests region-aware recipe
  -> executor applies supported operations
  -> unsupported mask operations remain GUI-assisted
  -> corrections become future training/evaluation evidence
```

This supports a realistic business objective: reduce repetitive editing
time while preserving photographer-specific judgment and maintaining
inspectable workflow evidence.


## Boundaries

This future-work stream should not claim:

- that Lightroom AI mask generation is scriptable before it is tested
- that every model suggestion can be executed inside Lightroom
- that a recipe executor can replace human review
- that XMP parameter deltas are the same thing as pixel-level image
  quality measurements

The stronger claim is:

> Model-suggested edit recipes can become operationally useful when the
> repository distinguishes learnable recommendations, executable
> Lightroom controls, unsupported GUI-assisted operations, and
> checkpointed evidence of the resulting state.


## Future Implementation Shape

A later implementation could add:

```text
recipes/stage2/global_develop_recipe_example.json
recipes/stage3/masked_local_recipe_example.json
scripts/lightroom/recipe_executor_spike.lua
scripts/python/future_work/validate_edit_recipe.py
outputs/future_work/lightroom_recipe_execution_spike_report.json
```

The first implementation should prove the execution boundary with a
minimal recipe and a reversible test asset before attempting batch
application.
