#!/usr/bin/env bash
# Launch the HCR ROI-quality labeling GUI in the cloud workstation.
#
# Reads Capsule-1 outputs (features + proba) staged by attach_data.ipynb, walks the
# candidate list (borderline-first, already-labeled excluded), and WRITES labels to
# /scratch (persistent) — NOT /results, which is ephemeral on a cloud workstation.
#
# Usage:  bash code/label.sh "790322"        (or "790322,788406")
# To add +100 more: re-run cell 3 of attach_data.ipynb (regenerates candidates, excluding
# what you just labeled), then re-run this script — new labels append as a new per-session file.
set -euo pipefail

SIDS="${1:-790322}"                                   # comma-separated subject ids
export MFISH_DATA_ROOT=/root/capsule/data
export MFISH_ROI_QUALITY_DIR=/root/capsule/scratch/roi_quality   # staged features_all + proba
export MFISH_CACHE_DIR=/root/capsule/scratch/mfish_cache         # tight-bbox cache (rebuilt here)
LABELS_OUT=/root/capsule/scratch/labels               # persistent label output (survives the session)
ALL_LABELS=/root/capsule/scratch/all_labels           # prior + current labels (skip + priors)
CANDIDATES=/root/capsule/scratch/label_candidates.csv
REVIEWER="${REVIEWER:-anonymous}"

mkdir -p "$LABELS_OUT" "$ALL_LABELS" "$MFISH_CACHE_DIR"

# Rebuild the tight-bbox cache per subject (needs the raw HCR data; Capsule 1 keeps it in
# scratch, not in its output asset). ~1 min/subject; skipped if already built.
IFS=',' read -ra SID_ARR <<< "$SIDS"
for sid in "${SID_ARR[@]}"; do
    sid="$(echo "$sid" | xargs)"
    bb="$MFISH_CACHE_DIR/hcr_cell_tight_bbox/${sid}_hcr_cell_tight_bbox.parquet"
    if [ ! -f "$bb" ]; then
        echo "[label] building tight-bbox for $sid ..."
        python -m roi_classifier.cli build-bbox "$sid"
    fi
done

# --label-assets reads prior+current labels (skips already-labeled, supplies priors);
# --label-out writes this session to /scratch as a new timestamped file (appends across runs).
exec roi-classifier-label --sid "$SIDS" --candidates "$CANDIDATES" \
     --label-out "$LABELS_OUT" --label-assets "$ALL_LABELS" --reviewer "$REVIEWER"
