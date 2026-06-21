"""Pick which ROIs to put in front of the labeler (excluding already-labeled ones).

Each subject has ~80k cells; we label a small, useful subset. From Capsule 1's
``{sid}_roi_quality_proba.parquet`` (cols: hcr_id, p_bad, p_bad_ok, p_good, p_merged)
we select, per subject:

  * mostly **keep/reject-borderline** cells — smallest ``|p_keep - 0.5|`` where
    ``p_keep = p_good + p_bad_ok`` (the decision the classifier exists to make → the
    most informative to label); plus
  * a few **high-confidence** examples per class (sanity-check + reference).

ROIs that are **already labeled** are excluded, so re-running yields the *next* batch
(e.g. "+100 more"). Already-labeled = active labels (newest-wins) across the given
``label_sources`` — typically this session's ``/scratch/labels`` plus any prior
``HCR-ROI-human-labeling`` assets attached under ``/data``.

Output: a candidates CSV (``sid,hcr_id``) ordered **borderline-first**, for
``roi-classifier-label --candidates``.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

CLASSES = ["bad", "bad_ok", "good", "merged"]
PCOLS = [f"p_{c}" for c in CLASSES]


def _find_proba(sid: str, data_root: Path) -> Path | None:
    """Locate {sid}_roi_quality_proba.parquet under the attached data assets
    (bounded depth, so we don't walk the HCR segmentation zarr)."""
    name = f"{sid}_roi_quality_proba.parquet"
    for pat in (name, f"*/{name}", f"*/*/{name}", f"*/*/*/{name}"):
        hits = sorted(p for p in data_root.glob(pat) if "scratch" not in p.parts)
        if hits:
            return hits[0]
    return None


def already_labeled_ids(sid: str, label_sources: list) -> set[int]:
    """Active-labeled hcr_ids for `sid` across label_sources (dirs or files of *.jsonl),
    newest-wins (a re-label supersedes, an undo clears). Uses the package's resolver so
    the skip logic exactly matches training + the GUI."""
    from roi_classifier.model import _load_label_log, _active_labels
    ids: set[int] = set()
    for src in (label_sources or []):
        src = Path(src)
        if not src.exists():
            continue
        try:
            log = _load_label_log(src)            # accepts a file or a dir of *.jsonl
        except FileNotFoundError:
            continue                              # empty dir / no jsonl
        act = _active_labels(log, str(sid))
        if not act.empty:
            ids |= set(act["hcr_id"].astype(int).tolist())
    return ids


def candidates_for_subject(proba: pd.DataFrame, n: int = 100, frac_ambiguous: float = 0.8,
                           exclude_ids: set[int] | None = None) -> list[int]:
    """Ordered hcr_id list: borderline cells first, then high-confidence per class.
    `exclude_ids` (already-labeled) are dropped before ranking, so this returns the
    *next* fresh batch."""
    df = proba.dropna(subset=PCOLS).copy()
    if exclude_ids:
        df = df[~df["hcr_id"].astype(int).isin(exclude_ids)]
    if df.empty:
        return []
    df["p_keep"] = df["p_good"] + df["p_bad_ok"]
    df["keep_margin"] = (df["p_keep"] - 0.5).abs()

    n = min(n, len(df))
    n_amb = int(round(n * frac_ambiguous))
    n_obv = n - n_amb

    amb = df.nsmallest(n_amb, "keep_margin")
    rest = df[~df["hcr_id"].isin(amb["hcr_id"])].copy()
    obv_ids: list[int] = []
    if n_obv > 0 and not rest.empty:
        rest["pred"] = rest[PCOLS].idxmax(axis=1)
        rest["pred_p"] = rest[PCOLS].max(axis=1)
        per_class = max(1, n_obv // len(CLASSES))
        for c in PCOLS:
            obv_ids += rest[rest["pred"] == c].nlargest(per_class, "pred_p")["hcr_id"].astype(int).tolist()
        obv_ids = obv_ids[:n_obv]

    return amb["hcr_id"].astype(int).tolist() + obv_ids


def make_candidates(sids: list[str], data_root: Path, out_csv: Path,
                    n: int = 100, frac_ambiguous: float = 0.8,
                    label_sources: list | None = None) -> pd.DataFrame:
    rows = []
    for sid in sids:
        p = _find_proba(sid, data_root)
        if p is None:
            print(f"[skip] no {sid}_roi_quality_proba.parquet under {data_root}", flush=True)
            continue
        excl = already_labeled_ids(sid, label_sources)
        ids = candidates_for_subject(pd.read_parquet(p), n=n, frac_ambiguous=frac_ambiguous,
                                     exclude_ids=excl)
        rows += [{"sid": str(sid), "hcr_id": int(h)} for h in ids]
        print(f"  {sid}: {len(ids)} new candidates (excluded {len(excl)} already-labeled)  [{p.name}]",
              flush=True)
    out = pd.DataFrame(rows, columns=["sid", "hcr_id"])
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False)
    print(f"wrote {len(out)} candidates → {out_csv}", flush=True)
    return out


def _parse_sids(s: str) -> list[str]:
    return [x.strip() for x in str(s).split(",") if x.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the labeling candidate list from Capsule-1 proba.")
    ap.add_argument("--sid", required=True, type=_parse_sids,
                    help="Subject id, or comma-separated list (e.g. 790322,788406).")
    ap.add_argument("--data-root", default="/root/capsule/data", type=Path,
                    help="Where the attached classifier-output asset(s) are mounted.")
    ap.add_argument("--out", default="/root/capsule/scratch/label_candidates.csv", type=Path)
    ap.add_argument("--n", type=int, default=100, help="New ROIs per subject this batch")
    ap.add_argument("--frac-ambiguous", type=float, default=0.8,
                    help="Fraction that are keep/reject-borderline (rest = confident examples).")
    ap.add_argument("--label-sources", default=None, type=str,
                    help="Comma-separated dirs/files of prior *.jsonl labels to EXCLUDE "
                         "(already-labeled). E.g. /root/capsule/scratch/all_labels")
    args = ap.parse_args(argv)
    label_sources = ([s.strip() for s in args.label_sources.split(",") if s.strip()]
                     if args.label_sources else None)
    make_candidates(args.sid, args.data_root, args.out, n=args.n,
                    frac_ambiguous=args.frac_ambiguous, label_sources=label_sources)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
