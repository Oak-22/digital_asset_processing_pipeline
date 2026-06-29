# Digital Asset Processing Pipeline

Systems engineering project showing how ambiguous, ad hoc creative production workflows can be structured as deterministic, scalable pipelines.  

<br>

## Executive Summary

Creative production work is modeled as a reproducible, multi-stage
pipeline with explicit boundaries, non-destructive state
transitions, and validation checkpoints. Even when executed inside
GUI-based tools, the workflow is designed with production system qualities rather
than an ad hoc editing sequence.

The core engineering pattern is deterministic orchestration around
uncertain inputs: creative image variance from heterogeneous capture
conditions, and probabilistic semantic segmentation behavior from AI
masking tools.

Across the documented stages, the project demonstrates how ingest-time
metadata application, image normalization, and semantic masking can be
composed into a deterministic workflow that scales more reliably than
repeated manual editing.

<br>

> [!IMPORTANT]
> **Read the shared terminology first.** This repository uses
> project-specific workflow vocabulary such as `gallery`,
> `reference image`, and `canonical image` in narrow, technical ways.
> Open [docs/terminology.md](docs/terminology.md) in a separate tab
> before reading the stage writeups if you want the later diagrams and
> handoff language to make sense on first pass.

<br>

## Reading Paths

Readers will usually benefit from taking one of two paths through the
repository depending on how much context they want up front.

### Quick Path (15 mins)

Use this path if you want a condensed, high-level view of the project
without reading every stage writeup in full:

1. [Shared terminology](docs/terminology.md)
2. [Pipeline Overview Diagram](docs/creative-workflow-pipeline-overview-diagram-v02.png)
3. [Project Abstract](docs/abstract.md)
4. [Batchability Cost Model](docs/batchability-cost-model.md)
5. [Stage 1](pipeline_stages/001_metadata-application-enrichment-query/README.md)
6. [Stage 2](pipeline_stages/002_baseline-conditioning/README.md)
7. [Stage 3](pipeline_stages/003_ai-mask-definition-propagation/README.md)
8. [Case Studies](docs/case-studies)
9. [Scripts](scripts) and [Tests](tests)

### Extensive Path (30 mins)

Use this path if you want the full systems-design argument, stage
evidence, and implementation rationale:

1. [Shared terminology](docs/terminology.md)
2. [Pipeline Overview Diagram](docs/creative-workflow-pipeline-overview-diagram-v02.png)
3. [Project Abstract](docs/abstract.md)
4. [Product Requirements](docs/product-requirements.md)
5. [Stage 1](pipeline_stages/001_metadata-application-enrichment-query/README.md)
6. [Stage 2](pipeline_stages/002_baseline-conditioning/README.md)
7. [Stage 3](pipeline_stages/003_ai-mask-definition-propagation/README.md)
8. [Batchability Cost Model](docs/batchability-cost-model.md)
9. [Future Work](docs/future-work)
10. [Case Studies](docs/case-studies)
11. [Scripts](scripts) and [Tests](tests)
12. [Architecture Decision Records](docs/adr)

<br>

## Project Structure

The project is structured as two parts:

`a) Workflow System Design`
- **Stage prose:** primary system-design artifact
- **Workflow evidence:** visual and operational proof carried by the documented stages
- **Product requirements:** project-level problem, constraints, non-goals, and success criteria

`b) Executable Workflow Analysis`
- **Scripts/tests:** co-equal analytic and validation artifacts that
  make the workflow inspectable, reproducible, and operational in
  structured form

This pipeline is **not a packaged application**. It augments an
existing application: Adobe Lightroom.

<br>

## Decision Records

Architecture and workflow-structure decisions that need stronger
long-lived rationale are recorded under [docs/adr](docs/adr).

Related implementation and governance incidents are recorded under
[docs/case-studies](docs/case-studies). These are smaller than ADRs:
they preserve concrete evidence, remediation steps, and lessons that may
later roll up into a separate AI agent governance case-study repository.

Scoped extensions that are not yet active workflow stages are recorded
under [docs/future-work](docs/future-work).

<br>

## Problem

Creative production workflows often accumulate as several informal editing
habits inside GUI tools, making them hard to reproduce, audit, and
scale across large datasets. Without explicit stage boundaries and
validation checkpoints, small inconsistencies can compound into operator drift causing laborous rework. Weak rollback safety then makes those inconsistencies
more costly to contain once they spread through the working set.

The core systems problem is therefore not only how to optimally perform isolated
editing operations, but how to organize them into a stable pipeline
that remains batch-safe under real tooling limitations, heterogeneous
creative input data, and AI-assisted operations with partial,
non-binary failure modes.

<br>

## Solution Overview

The workflow addresses that problem through three documented stages:

1. Metadata application, enrichment, and query design
2. Baseline conditioning
3. AI mask definition propagation

Each stage isolates a specific class of transformations, defines clear
inputs and outputs, and introduces validation boundaries before later
operations are applied. The result is a workflow that is more
deterministic, easier to reason about, and safer to evolve over time.

The stages build a reliability layer around increasingly uncertain
workflow surfaces: Stage 1 establishes deterministic metadata state,
Stage 2 controls visual variance introduced by capture conditions, and
Stage 3 constrains probabilistic AI mask outputs through qualification,
bounded propagation, and human review.

The pipeline does not replace the final manual editing pass. It prepares
a cleaner, normalized, review-bounded working set so obligatory manual
refinement and final artistic touches happen later with less repeated
effort.

<br>


## Evidence Model

This repository is documented as an applied systems-design case study.
Its claims are supported through two complementary evidence modes: one
for explaining the design and one for expressing the workflow in
executable analytic form.

- **A) Workflow System Design Evidence:** the stage prose, workflow
  image evidence, workflow operational evidence, and any stage-specific
  experiments are used to explain why specific pipeline boundaries,
  validation steps, review points, and design patterns exist. In the
  stage documents, this evidence typically appears as explicit
  `Operational note:` callouts or as `Figure` sections with embedded
  images.
  
- **B) Script/Test Evidence:** scripts, tests, and sample-data
  execution paths that serve as co-equal workflow artifacts. They make
  the pipeline operable, inspectable, and reproducible in practice
  rather than only described in prose.

These materials are used to justify workflow behavior and design
choices. They are not presented as controlled benchmarks or as claims of
universal performance beyond the documented workflow context.

<br>

## Key Constraints

Across the documented stages, the shared engineering constraints and
design themes are:

- stage-bounded workflow design
- deterministic orchestration around heterogeneous creative inputs
- batch-safe operations under tooling constraints
- bounded handling of probabilistic outputs
- reproducibility through clear validation checkpoints
- human review at defined boundaries

<br>

## Cross-Cutting Engineering Concepts

Some of the strongest engineering and software-engineering concepts in
this repository are broader than any one stage's governing principles
or engineering concepts demonstrated. They shape the architecture of the
whole project rather than only one transformation step.

- business-goal-driven system design rather than isolated tool usage
- tacit workflow knowledge converted into explicit evidence and
  operational rules
- deterministic orchestration around uncertain inputs and probabilistic
  tool behavior
- external checkpointing added where the underlying tool only provides
  rolling mutable state
- cost-shape modeling used to justify why batchability matters
- stage-bounded validation and rollback logic instead of monolithic
  editing flow
- hybrid evidence model combining prose, diagrams, experiments,
  artifacts, and scripts

These project-level concerns are summarized more directly in
[docs/product-requirements.md](docs/product-requirements.md).

<br>

## Pipeline Stages

The project is organized as a single multi-stage pipeline with supporting documentation (engineering rationale) for each major stage.

<br>

### Stage 1 – Metadata Application, Enrichment, and Query

Establishes the metadata and query foundation for the workflow.

Location: [Stage 1](pipeline_stages/001_metadata-application-enrichment-query/README.md)

Focus areas:
- deterministic ingest behavior under single-preset constraints
- non-destructive metadata enrichment through non-overlapping field assignments
- metadata-driven indexing and retrieval patterns enabling both rapid ad-hoc queries and declarative views over image records
- stable metadata state before subjective culling or image transformation begins

- **Identity initialization:** Single-preset ingest establishes the protected authorship baseline
- **Semantic enrichment:** Post-import presets and keywords add non-overlapping descriptive metadata
- **Query layer:** Filter-based retrieval and Smart Collections derive reusable views over image records


> **Boundary:** culling separates metadata preparation from image
> transformation.
>
> **Handoff state:** the full image set is narrowed into the working
> set that moves forward to cleanup, normalization, and AI mask
> propagation. Selection is based on usable focus, aesthetic
> uniqueness, subject relevance, and edit potential.

<br>

### Stage 2 – Baseline Conditioning

Establishes the conditioned image baseline for downstream semantic
operations.

Location: [Stage 2](pipeline_stages/002_baseline-conditioning/README.md)

Focus areas:
- local corrective cleanup and dataset-wide tonal normalization across heterogeneous images
- scene-level color normalization that preserves natural hue differences across scenes
- virtual copies for rollbackable experimentation while reducing operator cognitive load
- deterministic conditioning around creative/capture variance from changing light, scene, and camera conditions

- **Input lineage protection:** Initial virtual-copy branching protects
  the culled working set from the original RAW selection
- **Operation 1:** Local corrective cleanup
- **Operation 2:** Dataset-wide tonal normalization with
  scene-level color normalization
- **Output lineage protection:** Post-conditioning virtual-copy
  branching preserves the normalized baseline as a known-good handoff
  state

> **Handoff state:** Stage 3 receives a cleaned, normalized, and
> lineage-protected working state rather than unresolved luminance and
> color variance.

<br>

### Stage 3 – AI Mask Definition Propagation

Applies semantic mask definitions across the conditioned working set and
introduces bounded review around probabilistic AI output.

Location: [Stage 3](pipeline_stages/003_ai-mask-definition-propagation/README.md)


Focus areas:
- procedural mask definitions propagated across datasets rather than copying pixel regions
- dataset-scale application of AI-generated semantic masks to batch edit operations
- qualitative evaluation of mask quality and workflow reliability against manual editing results
- deterministic review boundaries around probabilistic AI segmentation behavior

- **Semantic operations:** Batch AI masking
- **Qualification:** Semantic definitions are qualified before broad propagation
- **Human review:** Manual refinement pass

> **Boundary:** qualification and review separate propagated semantic
> candidates from accepted downstream corrections.
>
> **Handoff state:** the working set carries propagated, review-bounded
> semantic masks forward into final manual refinement rather than
> requiring full local masking from scratch.

<br>
