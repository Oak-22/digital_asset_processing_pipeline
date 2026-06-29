# Python Utilities

This directory contains stage-scoped Python helpers for extracting,
auditing, validating, and materializing workflow artifacts across the
three documented pipeline stages.

The scripts are not intended to replace the documented workflow or its
embedded visual evidence. Their role is to make the workflow more
inspectable and reproducible by turning Lightroom-adjacent artifacts
such as XMP sidecars, manifests, review sheets, and parameter exports
into structured validation surfaces.

Documentation screenshots and diagrams should remain in each stage's
`assets/` tree. Machine-readable workflow artifacts should live
separately so the scripts do not have to treat README evidence images as
analysis inputs.

<br>

## Evidence Role

At the project level, the intended evidence stack is:

1. workflow/system design evidence expressed through stage prose,
   workflow images, diagrams, and operational notes
2. quantitative or semi-quantitative analysis grounded in underlying
   workflow artifacts such as RAW files, XMP edit parameters, exported
   manifests, and any later pixel- or render-level measurements
3. tests and executable checks that keep those extraction and analysis
   paths reproducible

In other words, the visual workflow artifacts usually establish the
qualitative claim first, while the scripts in this directory are the
bridge to mathematical or structured validation later.

<br>

## Layout

```text
data/
├── live_workspace/       # mixed RAW/XMP rolling Lightroom-sidecar state
├── stage1/
├── stage2/
│   ├── reference_state/
│   │   └── xmp_preconditioning/
│   ├── conditioned_state/
│   │   └── xmp_postconditioning/
│   └── sidecar/
└── stage3/
    └── sidecar/

scripts/python/
├── README.md
├── common/
│   ├── __init__.py
│   └── io_utils.py
├── stage1/
│   ├── __init__.py
│   ├── 01_verify_stage1_xmp_source_pairs.py
│   ├── 02_extract_and_report_stage1_metadata_state.py
│   ├── 03_validate_stage1_metadata.py
│   └── 04_build_stage1_manifest.py
├── stage2/
│   ├── __init__.py
│   ├── extract_develop_settings.py
│   ├── audit_stage2_parameters.py
│   └── build_stage2_manifest.py
└── stage3/
    ├── __init__.py
    ├── create_stage3_review_sheet.py
    ├── ingest_stage3_review_results.py
    └── build_stage3_manifest.py
```

<br>

## Intent

- `common/`: shared filesystem and serialization helpers
- `stage1/`: metadata extraction, validation, and manifest generation
- `stage2/`: develop-setting extraction, parameter auditing, and
  manifest generation
- `stage3/`: review-sheet creation, review-result ingestion, and
  manifest generation

These files are currently lightweight entrypoint stubs so the package
structure exists before implementation details are filled in.

<br>

## Artifact Boundary

- `pipeline_stages/.../assets/images/`: screenshots and workflow-image
  evidence used in the prose
- `pipeline_stages/.../assets/diagrams/`: explanatory diagrams for
  documentation
- `data/live_workspace/`: shared mutable Lightroom workspace holding
  mixed RAW and XMP files; stages observe or checkpoint it, but no
  single stage owns it
- `outputs/stage1/`: durable Stage 1 analysis artifacts, including the
  extracted metadata report, validation report, and manifest
- `data/stage2/reference_state/xmp_preconditioning/`: frozen XMP
  checkpoint captured before Stage 2 Develop edits
- `data/stage2/conditioned_state/xmp_postconditioning/`: frozen XMP
  checkpoint captured after Stage 2 baseline conditioning
- `data/stage2/sidecar/`: optional ad hoc sidecar input location
- `data/stage3/sidecars/`: XMP sidecars or exports related to mask
  propagation state when available
- `data/stage3/review_sheets/`: human review inputs/outputs for
  Stage 3 qualification and evaluation

This keeps qualitative README evidence separate from script inputs and
allows the Python utilities to target a realistic live-workspace model.

<br>

## Validation Model

The scripts in this directory are expected to support several distinct
validation surfaces over time:

- **XMP and metadata extraction:** prove what Lightroom wrote into a
  rolling live workspace and what each extracted checkpoint captured
- **Edit-parameter auditing:** quantify how adjustment settings change
  across a dataset or scene group
- **Manifest generation:** produce stable external records of stage
  inputs, outputs, and review checkpoints
- **Review-sheet support:** structure human evaluation where the proof
  still depends on perceptual judgment
- **Future RAW/pixel analysis:** provide a place for stronger numerical
  analysis if the project later measures source signal, rendered-output
  behavior, or parameter dispersion directly

This means the scripts can eventually support claims at multiple levels:

- what the source image signal looked like
- what edit parameters were applied
- what the workflow state looked like before and after each stage
- what later tests can reproduce or validate automatically

<br>

## Intended Outputs

Future outputs may include:

- normalized metadata extracts
- stage validation reports
- stage manifests
- exception logs
- review sheets
- summary reports

Example output locations:

- `outputs/stage1/extracted_stage1_metadata.json`
- `outputs/stage1/stage1_metadata_validation_report.json`
- `outputs/stage1/stage1_manifest.json`
- `outputs/stage2/`
- `outputs/stage3/`

<br>

## CLI Philosophy

These scripts are currently stubs. Each script is structured as a future
CLI entrypoint with:

- argument parsing
- clear responsibility
- TODO scaffolding
- conservative placeholder output

<br>

## Implementation Priority

The initial version is intentionally lightweight. The first
implementation priority should likely be Stage 1, since XMP metadata
extraction and manifest validation are the clearest bridge between
Lightroom state and external analysis.

Stage 2 is the strongest next candidate because it can eventually
support both qualitative workflow claims and quantitative inspection of
develop settings, scene grouping, tonal adjustments, and downstream
parameter convergence.

The cleanest current strategy is:

1. **Stage 1:** mixed RAW+XMP live workspace first, with extracted
   metadata, validation, and manifest artifacts for auditability
2. **Stage 2:** XMP sidecars plus an optional curated RAW subset.
   Stage 2 extraction can run against any explicit XMP sidecar set, but
   durable claims should use frozen preconditioning and postconditioning
   checkpoints copied from the shared `data/live_workspace/`. The input
   model label records whether the extracted values represent an
   upstream reference state, a conditioned Stage 2 state, or another
   workflow boundary.
3. **Stage 3:** XMP sidecars plus review manifests, with optional
   rendered exports for side-by-side inspection

<br>

## Data Flow

Stage 1 scripts are numbered because their execution order is part of
the workflow contract:

1. `01_verify_stage1_xmp_source_pairs.py`
   confirms RAW/XMP identity before any derived evidence is trusted.
2. `02_extract_and_report_stage1_metadata_state.py`
   normalizes the verified workspace into JSON evidence.
3. `03_validate_stage1_metadata.py`
   applies Stage 1 assertion rules to the extracted JSON.
4. `04_build_stage1_manifest.py`
   packages the validated Stage 1 evidence into a manifest.

Later stages may adopt the same numbering convention when their script
order becomes operationally significant.

Phase 1

- verify source/sidecar pairing
- parse XMP files
- normalize Stage 1 metadata into JSON evidence

Phase 2

- implement Stage 1 validation rules
- generate pass/fail report
- generate completeness stats

Phase 3

- create workflow manifest across stages
- add exception flags
- summarize counts

Phase 4

- add Stage 2 parameter auditing if XMP supports it
- add Stage 3 review manifest/evaluation tables

Phase 5

- add RAW-linked analysis where the source signal itself should be
  measured rather than inferred from edit parameters alone
- add optional rendered-output or pixel-level measurements where visual
  proof should be strengthened quantitatively
- connect those measurements back to stage manifests and review records

Phase 6

- tests
- sample files
- CLI usage
- polished README section showing outputs
