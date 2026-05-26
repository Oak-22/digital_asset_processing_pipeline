## Stage 1 Layout

`live_workspace/` is the canonical Stage 1 input. It holds the mixed
RAW and XMP files that represent Lightroom's rolling metadata state.

Per-checkpoint audit artifacts should be written under
`outputs/stage1/snapshots/`, while the broader extracted report belongs
under `outputs/stage1/`.
