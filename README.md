# 3D HCR ROI-quality labeling (capsule)

Interactive CodeOcean capsule (Ubuntu **cloud workstation**) to human-label HCR cell ROI
quality. It runs the `roi-classifier-label` GUI from
[`mfish-roi-classifier`](https://github.com/jkim0731/mfish-roi-classifier) over a smart
subset of ROIs (the classifier's most uncertain cells + a few confident ones). Not a
Reproducible Run — `code/run` just prints a notice.

## Workflow (in the cloud workstation)

1. **`code/attach_data.ipynb`** — set `SUBJECT_IDS` + `N_ROIS`, run the cells. It:
   - finds & attaches, per subject: Capsule 1's **classifier output**
     (`3D-HCR-ROI-4-class-label`: `{sid}_features_all.parquet` + `{sid}_roi_quality_proba.parquet`),
     the **R1 HCR** data it was derived from (via provenance), and any **prior
     `HCR-ROI-human-labeling` assets** (so already-labeled ROIs are skipped);
   - stages the parquets + all label files, and writes the **candidate list**
     (`/scratch/label_candidates.csv`) — mostly **keep/reject-borderline** ROIs
     (`|P(good)+P(bad_ok) − 0.5|` smallest) + a few **confident** ones per class,
     **excluding already-labeled ROIs**.
2. **`bash code/label.sh "<sids>"`** — rebuilds the tight-bbox cache, launches the GUI on
   the candidate list. Labels are written to **`/scratch/labels`** (persistent) — *not*
   `/results`, which is **ephemeral on a cloud workstation**.
3. **+100 more:** re-run cell 3 of `attach_data.ipynb` (regenerates candidates, excluding
   what you just labeled) → re-run `code/label.sh`. New labels append as a new per-session file.
4. **`code/create_label_asset.ipynb`** — publishes `/scratch/labels` as a new
   `HCR-ROI-human-labeling` data asset (captured from the workstation). The **training
   capsule** attaches all such assets (merged newest-wins).

## Labels
- **Read** (skip + priors): all `*.jsonl` under `/scratch/all_labels` (prior assets from
  `/data` + this session), merged **newest-wins** per cell (a re-label supersedes, an undo clears).
- **Written**: `/scratch/labels/roi_qc_actions_<UTCstamp>.jsonl` — self-contained records
  (embed features, `segmentation_asset`, `code_commit`, `model_proba`).

## GUI keys
`g/b/o/e/u` label (good/bad/bad_ok/merged/unsure) · `s` skip · `z` undo · `n/p` next/prev
subject · `1/2/3` channel · `m` MIP · arrows/wheel scroll z. The proba shown is read from
Capsule 1's contract (no model needed at label time).

Part of the 3-capsule workflow: classifier (extract+infer) → **this (labeling)** →
classifier-training (MLflow retrain).
