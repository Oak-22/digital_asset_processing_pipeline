# Product Requirements

<br>

## Purpose

This document defines the product-level problem, operator need,
constraints, and success criteria for the creative workflow batch
transformation pipeline. It sits between the high-level project
[README](../README.md) and the stage-specific pipeline writeups.

The goal is not to replace the README or restate every stage in full.
Its role is to make the requirements surface explicit: what the system
must accomplish, for whom, under what constraints, and with what
evidence model.

<br>

## Problem Statement

High-volume creative workflows inside GUI tools often begin as
personally effective editing habits rather than explicit systems. As the
working set grows, those habits become harder to audit, scale, hand off,
or reproduce. Repeated manual adjustments create avoidable labor,
inconsistent state, and weak rollback boundaries once changes have been
applied across many images.

The product problem is therefore not only how to edit images well, but
how to convert repeated creative workflow behavior into a bounded,
inspectable, and reproducible multi-stage pipeline that remains useful
inside real tool constraints.

<br>

## Primary User

The primary user is an operator-editor working inside Adobe Lightroom
Classic who needs to:

- reduce repeated manual labor across a culled gallery
- preserve authorship and workflow lineage
- normalize heterogeneous inputs before downstream semantic edits
- apply AI-assisted operations without surrendering review control
- maintain rollback-safe handoff states between major workflow stages

<br>

## Product Goal

Transform a creative editing workflow from an ad hoc sequence of GUI
operations into a deterministic, stage-bounded system that:

- reduces repeated mechanical effort
- preserves non-destructive lineage
- makes validation and handoff points explicit
- supports external inspection through scripts, manifests, and
  structured artifacts

<br>

## Non-Goals

This project does not aim to:

- replace Lightroom with a standalone packaged application
- fully automate final artistic judgment
- prove universal benchmark superiority across all workflows
- eliminate manual review from probabilistic AI-assisted steps
- turn every workflow surface into a mathematically exact optimization
  problem

<br>

## Requirements

### Functional Requirements

- Stage 1 must establish a deterministic metadata baseline before later
  image transformation work begins.
- Stage 2 must produce a cleaner, normalized working state that reduces
  downstream comparison burden.
- Stage 3 must qualify and propagate semantic mask definitions under
  bounded human review.
- Each stage must define a handoff state that is explicit enough to be
  reasoned about separately from the next stage.
- The pipeline must support externalized validation artifacts such as
  sidecars, manifests, scripts, tests, and review outputs.

### System Qualities

- Non-destructive operation
- Reproducible stage boundaries
- Deterministic orchestration around uncertain inputs
- Clear rollback surfaces
- Batch-safe operation where justified
- Human review where uncertainty remains irreducible

<br>

## Constraints

- The workflow is implemented inside an existing GUI application rather
  than a custom execution engine.
- Lightroom Classic writes XMP sidecars as mutable rolling state rather
  than stable stage checkpoints.
- AI masking behavior is probabilistic and image-dependent.
- Image inputs are heterogeneous across capture conditions, luminance,
  and scene composition.
- Some workflow value is rooted in tacit operator knowledge that must be
  documented through observational evidence rather than assumed.

<br>

## Evidence And Validation Model

This project uses multiple evidence surfaces because no single type of
proof is sufficient for the full system:

- workflow evidence explains observed tool behavior and why stage
  boundaries exist
- quantitative or semi-quantitative models justify why a batchable
  pipeline is economically meaningful
- scripts and tests make portions of the workflow externally
  inspectable and reproducible
- review checkpoints keep probabilistic or subjective operations within
  bounded acceptance criteria

<br>

## Product Success Criteria

The project is successful if it demonstrates that:

- repeated workflow labor can be reorganized into bounded stage-local
  transformations
- stage handoffs are explicit enough to support rollback and review
- metadata, normalization, and semantic masking can be reasoned about as
  separate but composable system layers
- external scripting can validate or inspect meaningful parts of the
  workflow without replacing the workflow itself
- the resulting system is easier to explain, reproduce, and evolve than
  an undocumented editing habit
