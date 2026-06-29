# ADR 0004: Hash-Manifested Stage Checkpoints

## Status

Accepted

## Context

Lightroom XMP sidecars behave like mutable working-state files. The
catalog may update them as metadata, Develop settings, virtual-copy
state, or other editor-managed properties change. That behavior is
appropriate for the live editing workflow, but it creates a problem for
this repository: Stage 2 needs before/after evidence that remains stable
after the live workspace moves on.

The project already separates the mutable shared workspace from frozen
Stage 2 XMP checkpoints:

```text
data/live_workspace/
  mutable Lightroom working head

data/stage2/reference_state/xmp_preconditioning/
  frozen sidecars copied before Stage 2 Develop edits

data/stage2/conditioned_state/xmp_postconditioning/
  frozen sidecars copied after Stage 2 baseline conditioning
```

Copying the files establishes a stage boundary, but the repository also
needs a way to prove that later extraction and comparison artifacts were
derived from the same frozen checkpoint files. Without an integrity
record, a checkpoint folder could drift silently and still look like a
valid Stage 2 evidence source.


## Decision

Stage checkpoint folders should be made tamper-evident with local hash
manifests before durable analysis claims depend on them.

For Stage 2, the checkpoint manifest records:

- checkpoint label
- checkpoint root
- mutable origin root
- generation timestamp
- artifact count
- per-XMP checkpoint path, size, and SHA-256 hash
- corresponding live-workspace mutable origin path when present
- mutable origin size and SHA-256 at manifest time
- whether the mutable origin still matched the checkpoint at manifest
  time

The manifest does not make Lightroom secure and does not prove that a
creative edit is correct. It preserves artifact integrity: later readers
can verify whether the checkpoint being analyzed is byte-for-byte the
same evidence snapshot that was manifested.


## Rationale

- **Mutable working state needs external evidence controls:** Lightroom
  can keep updating `data/live_workspace/`; the stage checkpoint
  manifest gives the repository a stable evidence boundary.
- **Hashes are a lightweight provenance control:** SHA-256 records make
  checkpoint drift detectable without adding heavyweight infrastructure.
- **CLI-inspectable artifacts support employer review:** a reader can
  inspect physical XMP files and the manifest JSON rather than relying
  only on prose claims.
- **The pattern transfers to higher-stakes domains:** the same
  pre/post checkpoint design applies to clinical imaging, lab data,
  geospatial imagery, legal review, or other workflows where mutable
  tool state must be converted into auditable evidence.


## Consequences

### Positive

- Stage 2 before/after comparisons gain a stronger provenance basis.
- The repository can distinguish live working state from frozen evidence
  state without preventing Lightroom from behaving normally.
- Checkpoint manifests create an inspectable bridge between GUI
  workflow state and CLI-verifiable artifacts.
- Later automation can validate checkpoint integrity before extracting
  or comparing Develop settings.

### Negative

- Checkpoint folders now require an additional manifest-generation step.
- A regenerated manifest may have a new timestamp even when file hashes
  are unchanged.
- Hashes prove byte-level identity, not semantic correctness or creative
  quality.


## Notes

The initial implementation is
`scripts/python/stage2/build_checkpoint_manifest.py`.

The first generated checkpoint manifest is:

```text
outputs/stage2/stage2_preconditioning_checkpoint_manifest.json
```

The expected postconditioning manifest path is:

```text
outputs/stage2/stage2_postconditioning_checkpoint_manifest.json
```
