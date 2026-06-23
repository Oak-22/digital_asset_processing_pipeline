# ADR 0003: Offline Analysis Before Cloud Operationalization

## Status

Accepted

## Context

ADR 0001 establishes the storage boundary: source assets are centrally
managed, while analytic outputs are local, derived, and reproducible.
This ADR builds on that decision by defining when cloud infrastructure
should enter the workflow and what it is allowed to own.

The creative workflow begins as local Lightroom behavior. RAW masters,
XMP sidecars, virtual copies, metadata presets, keyword writes, and
later edit operations are first produced inside an editor-controlled
desktop workflow. Before that behavior can be represented honestly in
cloud infrastructure, the project must understand what the local files
mean.

The existing Python extraction layer was built for that purpose. It
reads local RAW/XMP payloads, groups records by stable `asset_key`,
infers Stage 1 boundaries from field-level metadata state, and
materializes reproducible JSON evidence for documentation and review.
That layer explains the workflow.

Cloud infrastructure solves a different problem. It can make centralized
asset arrival observable, durable, and recoverable, but it should not
reinterpret Lightroom metadata or duplicate the offline extractor. It
should operationalize an asset boundary only after that boundary is
understood.

## Decision

The project will preserve a strict separation between:

- **offline analytic extraction**, which interprets local workflow state
- **cloud operationalization**, which governs centralized asset intake

Offline analysis remains the first layer because it discovers and
documents the workflow semantics. Cloud operationalization comes later
and applies infrastructure guarantees to the stable asset boundary
defined by ADR 0001 and the offline extractor.

The intended sequence is:

```text
Local Lightroom workflow
  -> offline Python extraction
  -> stage-aware JSON evidence
  -> stable asset model
  -> centralized AWS intake
  -> event-driven validation and manifest state
```

The proposed cloud intake shape is:

```text
S3 source assets
  -> object-created event
  -> SQS intake queue
  -> Lambda intake validator
  -> DynamoDB asset manifest
  -> CloudWatch / DLQ failure visibility
```

## Separation of Concerns

The two layers must not share responsibilities.

### Offline Analytic Extraction Owns

- reading RAW and XMP metadata payloads
- grouping extracted records by `asset_key`
- interpreting field-level metadata state
- inferring Stage 1 workflow boundaries
- producing reproducible local JSON evidence
- supporting documentation, review, and audit of workflow behavior
- explaining what local Lightroom state means

The offline layer does not own:

- cloud object-arrival events
- queueing or retry behavior
- centralized admission control
- durable cloud manifest state
- cloud failure routing or alerting
- infrastructure permissions or access boundaries

### Cloud Operationalization Owns

- intake for centrally managed source assets
- object-arrival event capture
- asynchronous intake queueing
- object-envelope validation such as prefix, extension, and naming
  convention checks
- basic RAW/XMP/JPEG presence and pairing status
- durable intake manifest records
- retryable processing boundaries
- dead-letter handling and operational failure visibility
- access, encryption, and infrastructure governance

The cloud layer does not own:

- parsing Lightroom metadata payloads for creative meaning
- inferring Stage 1 semantic boundaries from metadata fields
- generating local evidence artifacts
- documenting workflow behavior
- deciding whether an edit state is creatively or analytically valid
- replacing the editor-in-the-loop Lightroom workflow

## Asset Identifier Contract

Both layers may use `asset_key`, but they use it for different reasons.

The offline layer uses `asset_key` as an analytic grouping key for
interpreting extracted RAW/XMP records.

The cloud layer uses `asset_key` as an operational routing and manifest
key derived from object naming conventions.

This shared identifier is a contract between layers, not a shared
responsibility. The offline layer explains asset state. The cloud layer
tracks asset intake state.

## Rationale

- **Workflow truth begins locally:** Lightroom behavior is first
  observable in local RAW/XMP files and editor-visible metadata state.
- **Cloud should operationalize stable semantics, not invent them:** the
  extractor establishes the asset model before infrastructure enforces
  intake rules around it.
- **Avoiding duplicate logic keeps the system legible:** metadata
  interpretation stays in the offline analytic layer, while eventing,
  queueing, retry, and manifest state stay in the cloud layer.
- **NoSQL manifest storage fits the intake problem:** DynamoDB can store
  semi-structured asset intake state without forcing every workflow
  metadata field into a rigid schema.

## Consequences

### Positive

- the AWS design is justified by a business and workflow boundary rather
  than by adding services for their own sake
- local analytic outputs remain reproducible evidence rather than
  operational source-of-truth records
- cloud resources gain clear purpose: intake, validation, manifest
  state, and failure visibility
- Stage 2 and Stage 3 can continue to operate as editor-in-the-loop
  local workflow stages while inheriting the same asset identity model
- future automation can be added without collapsing analysis,
  orchestration, and creative interpretation into one layer

### Negative

- the architecture has two distinct state surfaces to reason about:
  local analytic evidence and cloud intake state
- the `asset_key` contract must remain stable enough for both layers to
  coordinate without sharing implementation logic
- adding cloud intake infrastructure introduces deployment and
  observability work that the local-only workflow did not require

## Notes

This ADR does not replace ADR 0001. ADR 0001 decides the source
asset/output storage boundary; this ADR decides the order of operations
and division of responsibility around that boundary.

The current Terraform module provisions the storage baseline only. A
future expansion can add S3 event notifications, SQS, Lambda, DynamoDB,
CloudWatch, and a dead-letter queue without changing the responsibility
of the offline extraction scripts.
