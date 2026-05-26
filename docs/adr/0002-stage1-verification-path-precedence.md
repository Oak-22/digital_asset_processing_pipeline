# ADR 0002: Stage 1 Verification Path Precedence

## Status

Accepted

## Context

Stage 1 snapshot verification originally centered on JPEG/XMP pairing
because JPEG companions were easy to inspect visually and easy to
co-locate with XMP sidecars. As the Stage 1 data model matured, this
became too narrow.

The project now distinguishes between:

- RAW-backed `01_pre_identity` evidence
- later XMP-backed metadata snapshots
- optional JPEG companions used mainly for human-friendly inspection

This requires an explicit verification precedence model so the verifier
does not imply that JPEGs are always required or that all pairing modes
have equal evidentiary strength.

## Decision

Stage 1 verification should follow this precedence:

1. `RAW + XMP` when both are present: preferred verification path
2. `JPEG + XMP` when RAW is unavailable: fallback verification path
3. `RAW only`: pre-identity source evidence, not a sidecar pairing case
4. `XMP only`: extractable snapshot artifact but weak for provenance

The verifier should report which path is being used rather than treating
every case as one generic JPEG/XMP comparison.

## Rationale

- **RAW + XMP is closest to Lightroom's native sidecar model:** this is
  the strongest practical provenance check for post-import sidecars.
- **JPEG + XMP remains useful:** it provides a workable fallback when
  RAW masters are unavailable in the local workspace.
- **RAW-only is a legitimate stage state:** `01_pre_identity` should be
  treated as source evidence rather than as a failed pairing case.
- **Different paths have different evidentiary strength:** the verifier
  should make that explicit rather than hiding it behind one generic
  branch.

## Consequences

### Positive

- verification language becomes more semantically honest
- `01_pre_identity` is modeled more cleanly as RAW-backed evidence
- later XMP-backed stages can retain stronger provenance checks
- JPEGs are reclassified as optional support rather than mandatory
  infrastructure

### Negative

- verifier logic becomes slightly more complex
- users must understand which verification mode they are seeing
- mixed local folders may still need temporary transitional handling

## Notes

This decision does not require mutating existing XMP sidecars. In the
current repo model, Lightroom-like rolling state lives in one mixed
`data/stage1/live_workspace/` folder, while audit checkpoints are
captured as extracted JSON snapshots under `outputs/stage1/snapshots/`.
