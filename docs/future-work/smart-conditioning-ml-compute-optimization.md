# Smart Conditioning For ML Compute Optimization

## Purpose

This note scopes a future extension to the digital asset processing
pipeline: using Stage 2 conditioning and Stage 3 semantic anchors as a
measurement surface for downstream machine-learning cost and assurance
analysis.

It is not a model-training plan. It is a data-engineering and
operational-rigor scaffold for asking whether pre/post conditioning can
reduce downstream compute shape while preserving semantically important
image content.


## Core Hypothesis

Smart conditioning can reduce downstream model cost when it removes
irrelevant pixels or visual variance without removing required semantic
context.

The valuable cost reduction is expected to come less from durable
storage savings and more from runtime constraints:

- smaller tensors or image tiles
- lower GPU memory pressure
- improved batch size or throughput
- reduced accelerator wall-clock time
- fewer inference passes over irrelevant background
- lower CPU/GPU transfer and preprocessing overhead


## Existing Evidence Base

The current repository already creates useful ingredients for this
future measurement layer:

```text
Stage 2 preconditioning checkpoint
  -> frozen before-state XMP sidecars
  -> hash manifest
  -> extracted Develop parameters

Stage 2 postconditioning checkpoint
  -> frozen after-state XMP sidecars
  -> hash manifest
  -> extracted Develop parameters

Stage 3 semantic masking
  -> future primary-subject / region anchors
  -> mask-quality review surface
```

The Stage 2 crop, tone, and color parameters describe transformations.
Stage 3 semantic masks can later supply the anchors needed to interpret
whether those transformations preserved the right subject or region
context.


## Assurance Pattern

Transformation parameters alone are not enough to evaluate quality.
For example, a crop delta can show that the frame changed, but not
whether the crop preserved the primary subject.

The future assurance pattern is:

```text
pre/post transformation parameters
+
semantic or anatomical region segmentation
+
margin and coverage policy
=
meaningful assurance check
```

In this portrait-oriented workflow, the likely semantic anchors are:

- primary subject mask
- face region
- head-and-shoulders bounding box
- body bounding box
- eye-line or headroom proxy
- background / foreground separation

In a higher-stakes imaging workflow, the analogous anchors could be
anatomical regions, lesion candidates, organ boundaries, document
regions, geospatial objects, or other domain-specific regions of
interest.


## Candidate Metrics

The future measurement layer should start with simple, inspectable
features before introducing model logic:

- original frame width, height, and pixel area
- post-crop frame width, height, and pixel area
- pixel-area reduction percentage
- subject or region bounding-box area
- subject-to-frame occupancy before and after conditioning
- margin from subject boundary to crop edge
- preserved context margin by side
- crop-center to subject-center offset
- estimated tensor size before and after conditioning
- estimated tile count before and after conditioning
- estimated batch-size or memory-pressure impact

These are operational metrics, not aesthetic claims. They should be
reported as evidence surfaces that a later model or reviewer can use.


## Cost Model Direction

The directional cost model is:

```text
pixel_load_before = original_width x original_height
pixel_load_after = conditioned_width x conditioned_height

pixel_reduction_ratio =
  1 - (pixel_load_after / pixel_load_before)

estimated_tensor_memory_before =
  pixel_load_before x channels x bytes_per_channel

estimated_tensor_memory_after =
  pixel_load_after x channels x bytes_per_channel
```

The business value should be framed as compute-shape optimization:

```text
fewer irrelevant pixels
  -> smaller tensors or fewer tiles
  -> lower memory pressure
  -> better batching or throughput
  -> lower accelerator wall-clock cost
```


## Boundaries

This future-work stream should not claim:

- trained ML accuracy improvements without benchmark evidence
- clinical safety or diagnostic validity
- universal storage or compute savings
- crop quality from crop parameters alone

It can claim a stronger data-engineering direction:

> Stage-aware checkpointing, parameter extraction, and semantic anchors
> can create an inspectable evidence layer for measuring whether
> upstream conditioning reduces downstream compute load without
> discarding required semantic context.


## Future Implementation Shape

A later implementation could add:

```text
scripts/python/stage2/measure_conditioning_geometry.py
scripts/python/stage3/extract_semantic_anchor_geometry.py
outputs/stage2/stage2_conditioning_geometry_report.json
outputs/stage3/stage3_semantic_anchor_geometry.json
outputs/future_work/smart_conditioning_compute_model.json
```

The implementation should remain CLI-inspectable and should produce
physical JSON artifacts before any model-training work is considered.
