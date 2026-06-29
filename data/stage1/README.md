## Stage 1 Layout

Stage 1 observes the shared Lightroom workspace at `../live_workspace/`.
That folder holds the mixed RAW and XMP files that represent
Lightroom's rolling metadata state, but it is not owned by Stage 1.

Durable Stage 1 analysis artifacts belong under `outputs/stage1/`,
including the extracted metadata report, validation report, and
manifest.
