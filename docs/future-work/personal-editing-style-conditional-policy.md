# Personal Editing Style As Conditional Policy

## Purpose

This note scopes a future extension for representing a photographer's
editing style as structured, learnable workflow evidence rather than as
a vague aesthetic label.

The goal is not to claim that the repository currently trains a model to
imitate Julian Buccat's editing style. The goal is to define what would
make that idea measurable later: pre/post edit pairs, semantic anchors,
and repeated transformation decisions conditioned on image content.


## Core Framing

Personal editing style should be modeled as conditional behavior:

```text
input image state
+
scene context
+
semantic regions
=>
expected edit decisions
```

In other words, a model should not learn "Julian style" as a single
global preset. It should learn repeated edit policies such as:

- how shadows are lifted when a subject is underexposed
- how highlights are protected in outdoor portraits
- how foliage greens are normalized across a scene
- how crops preserve headroom or subject margin
- how local subject emphasis differs from global exposure correction


## Evidence Ingredients

The current repository already creates some of the ingredients needed
for this future modeling surface:

```text
Stage 2 preconditioning extract
  -> before-state global Develop parameters

Stage 2 postconditioning extract
  -> after-state global Develop parameters

Stage 2 checkpoint manifests
  -> integrity proof for before/after sidecar states

Stage 3 semantic masks
  -> future subject, face, foliage, clothing, background, and foreground anchors
```

The Stage 2 artifacts can show what changed. Stage 3 anchors can later
help explain where and why a change matters.


## Style Decomposition

The future style model should decompose editing behavior into
measurable families of decisions.

### Tone

- exposure correction tendency
- shadow lift preference
- highlight recovery preference
- contrast range
- black/white point behavior

### Color

- white-balance and tint bias
- foliage hue normalization
- saturation and vibrance tendencies
- skin-tone preservation
- scene-level color continuity

### Composition

- crop tightness
- subject-to-frame occupancy
- headroom and side-margin preference
- crop-center to subject-center offset
- empty-edge-space removal

### Local Emphasis

- subject brightening
- background suppression
- face or skin-tone correction
- clothing or detail preservation
- semantic-region-specific contrast or texture decisions

### Cleanup

- distraction removal threshold
- natural texture preservation
- rejection of overly destructive or meaning-changing edits


## Why Semantic Anchors Matter

Global parameter deltas alone can create misleading style claims. For
example, a global exposure increase does not explain whether the editor
intended to brighten the whole frame, recover a shadowed face, or
rebalance a background-heavy composition.

Semantic anchors make the behavior interpretable:

```text
pre/post edit delta
+
primary subject mask
+
face region
+
background / foliage / clothing regions
=
style-relevant edit policy
```

This distinction protects the project from learning shallow
correlations. It also supports assurance checks: the model can be
evaluated against whether it changed the intended region while
preserving required context.


## Candidate Training Examples

A future dataset could represent each edited image as:

```json
{
  "asset_key": "JB107456",
  "scene_group": "outdoor_portrait_green_background",
  "preconditioning_develop_settings": {},
  "postconditioning_develop_settings": {},
  "develop_setting_deltas": {},
  "semantic_anchors": {
    "primary_subject": {},
    "face_region": {},
    "foliage_region": {},
    "background_region": {}
  },
  "derived_style_features": {
    "subject_margin_after_crop": {},
    "foliage_hue_shift": null,
    "shadow_lift_on_subject": null
  }
}
```

This shape is intentionally evidence-oriented. It records what a later
model could learn from without claiming that the model exists today.


## Boundaries

This future-work stream should not claim:

- that style can be captured by one preset
- that global Develop sliders fully explain local editing intent
- that model imitation is desirable without review
- that a trained model would replace final human judgment

The stronger claim is:

> Editing style becomes learnable when it is represented as repeated
> transformation decisions conditioned on scene context and semantic
> regions.


## Future Implementation Shape

A later implementation could add:

```text
scripts/python/stage2/compare_develop_setting_deltas.py
scripts/python/stage3/extract_semantic_style_anchors.py
outputs/future_work/personal_style_edit_policy_examples.json
outputs/future_work/personal_style_feature_summary.json
```

The first implementation should stay descriptive: extract deltas,
attach semantic anchors, and summarize repeated patterns before any
model-training work is introduced.
