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
├── stage1/
│   ├── sidecars/
│   ├── exports/
│   └── manifests/
├── stage2/
│   ├── sidecars/
│   ├── raws/        # optional curated subset, not necessarily committed
│   ├── renders/     # optional rendered exports for comparison
│   └── manifests/
└── stage3/
    ├── sidecars/
    ├── review_sheets/
    └── manifests/

scripts/python/
├── README.md
├── common/
│   ├── __init__.py
│   └── io_utils.py
├── stage1/
│   ├── __init__.py
│   ├── extract_xmp_metadata.py
│   ├── validate_stage1_metadata.py
│   └── build_stage1_manifest.py
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
- `data/stage1/sidecars/`: XMP sidecars used for metadata
  extraction and validation
- `data/stage2/sidecars/`: XMP sidecars used for develop-setting
  extraction and auditing
- `data/stage2/raws/`: optional RAW subset for source-signal or
  normalization analysis
- `data/stage2/renders/`: optional JPEG/TIFF exports for rendered
  output comparison
- `data/stage3/sidecars/`: XMP sidecars or exports related to mask
  propagation state when available
- `data/stage3/review_sheets/`: human review inputs/outputs for
  Stage 3 qualification and evaluation

This keeps qualitative README evidence separate from script inputs and
allows the Python utilities to target a stable artifact layout.

<br>

## Validation Model

The scripts in this directory are expected to support several distinct
validation surfaces over time:

- **XMP and metadata extraction:** prove what Lightroom wrote into
  sidecars or exports
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

Example future output locations:

- `outputs/stage1/`
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

The cleanest initial strategy is:

1. **Stage 1:** XMP sidecars first
2. **Stage 2:** XMP sidecars plus an optional curated RAW subset
3. **Stage 3:** XMP sidecars plus review manifests, with optional
   rendered exports for side-by-side inspection

<br>

## Data Flow

Phase 1

- parse XMP files
- normalize into dataframe / CSV
- document schema

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
