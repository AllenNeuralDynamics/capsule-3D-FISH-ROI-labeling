# 3D HCR ROI-quality labeling (capsule)

Interactive CodeOcean capsule (Ubuntu **cloud workstation**) to human-label HCR cell
ROI quality. It runs the `roi-classifier-label` GUI from
[`mfish-roi-classifier`](https://github.com/AllenNeuralDynamics/mfish-roi-classifier).
Scaffold mimics the dev capsule (`/root/capsule`) desktop environment (the GUI needs a display).

## How to run (cloud workstation)
1. Attach: the **inference asset** (`{sid}_features_all.parquet` + tight-bbox) from the
   classifier capsule, the **raw** subject data (for image crops), and any **prior label
   assets** (one `*.jsonl` per past session).
2. In a workstation terminal: `bash code/run` (override `SID`, `CANDIDATES`, `REVIEWER`,
   and the `MFISH_*` / `LABEL_ASSETS` paths via env as needed).

## Labels are per-session, timestamped assets
- Prior labels are **read** from `--label-assets <dir>` (all `*.jsonl`, merged
  **newest-wins** per cell — a re-label supersedes, an undo clears).
- This session is **written** to `--label-out /root/capsule/results` as
  `roi_qc_actions_<UTCstamp>.jsonl`. Publish `/results` as a new label data asset; the
  training capsule attaches the full set of label assets.

## GUI
`g/b/o/e/u` label · `s` skip · `z` undo · `n/p` next/prev subject · `1/2/3` channel ·
`m` MIP · arrows/wheel scroll z. `--candidates <csv>` (sid,hcr_id) walks a fixed
priority list (e.g. a retrain shortlist).

Part of the 3-capsule workflow: classifier (extract+infer) → **this (labeling)** →
classifier-training (MLflow retrain).
