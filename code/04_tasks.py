#!/usr/bin/env python3
"""Build the natality benchmark tasks (EPTB, VLBW) with fixed temporal splits.

Split design (author ruling 2026-10-04): train = 2022-2023, test = 2024.
A seeded 10% of the training years is held out as validation, and a seeded
subsample of the remaining training rows forms the standard track.
Splits are assigned once at the cohort level, so EPTB and VLBW share them.

Outputs, per task, in tasks/natality/<TASK>/:
    train.parquet valid.parquet test.parquet     row_id, y, predictor values
    *_mclass.parquet                             row_id, missingness class per predictor
    task_card.json
Shared: tasks/natality/split_manifest.csv.gz (row_id, split, standard_track)

    python code/04_tasks.py            # build
    python code/04_tasks.py --freeze   # build, then write FREEZE.json (one time only)
"""
import hashlib
import json
import sys
from datetime import date

import numpy as np
import pandas as pd

from natality_common import (OUTCOMES, PROCESSED, ROOT, SEED, STANDARD_TRAIN_N, TASKS,
                             TEST_YEAR, TRAIN_YEARS, VALID_FRACTION, classify, cohort_flow,
                             decode, load_layout, outcome, predictor_rows, update_stats)


def load_cohort():
    frames = []
    for y in TRAIN_YEARS + [TEST_YEAR]:
        df = pd.read_parquet(PROCESSED / f"natality_{y}_raw.parquet")
        frames.append(df[cohort_flow(df)[-1][1]])
    return pd.concat(frames, ignore_index=True)


def assign_splits(df):
    rng = np.random.default_rng(SEED)
    order = df["row_id"].sort_values().index      # assignment never depends on file order
    u = pd.Series(rng.random(len(df)), index=order)
    year = df["row_id"].str[:4].astype(int)
    split = np.where(year == TEST_YEAR, "test",
                     np.where(u < VALID_FRACTION, "valid", "train"))
    return pd.Series(split, index=df.index), u


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(freeze=False):
    if (ROOT / "FREEZE.json").exists():
        sys.exit("FREEZE.json exists; tasks are frozen and will not be rebuilt. A change needs a new version.")
    lay = load_layout()
    preds = predictor_rows(lay)
    df = load_cohort()
    split, u = assign_splits(df)
    TASKS.mkdir(parents=True, exist_ok=True)

    X = pd.DataFrame({"row_id": df["row_id"]})
    M = pd.DataFrame({"row_id": df["row_id"]})
    for _, r in preds.iterrows():
        cls = classify(df, r)
        M[r["name"]] = cls
        X[r["name"]] = decode(df, r, cls)
        if r["kind"] in ("int", "num") and r["not_applicable"]:
            X[r["name"] + "__na_struct"] = (cls == "A").astype("int8")

    manifest = pd.DataFrame({"row_id": df["row_id"], "split": split})
    stats = {}
    for task, spec in OUTCOMES.items():
        y = outcome(df, task)
        ok = y.notna()
        tr = ok & (split == "train")
        rank = u[tr].rank(method="first")
        manifest[f"{task}_eligible"] = ok.astype("int8")
        manifest[f"{task}_standard_track"] = (tr & (rank.reindex(df.index) <= STANDARD_TRAIN_N)).astype("int8")
        tdir = TASKS / task
        tdir.mkdir(exist_ok=True)
        st = {}
        for s in ["train", "valid", "test"]:
            m = ok & (split == s)
            out = X[m].copy()
            out.insert(1, "y", y[m].astype("int8"))
            out.to_parquet(tdir / f"{s}.parquet", index=False)
            M[m].to_parquet(tdir / f"{s}_mclass.parquet", index=False)
            st[s] = {"n": int(m.sum()), "cases": int(y[m].sum()), "prevalence": float(y[m].mean())}
        std = manifest[f"{task}_standard_track"] == 1
        st["train_standard"] = {"n": int(std.sum()), "cases": int(y[std].sum()),
                                "prevalence": float(y[std].mean()) if std.any() else None}
        card = {
            "task": task, "version": "1.0.0-draft", "label": spec["label"],
            "source": "NCHS Natality Public Use Files", "years": {"train": TRAIN_YEARS, "test": TEST_YEAR},
            "cohort": [stage for stage, _ in cohort_flow(df)][1:] + [f"{spec['field']} stated"],
            "outcome_field": spec["field"], "predictors": list(preds["name"]),
            "missingness_classes": {"O": "observed", "S": "not stated", "A": "not applicable (structural)",
                                    "I": "imputed by NCHS, restored to missing"},
            "primary_metric": "AUPRC on test",
            "secondary_metrics": ["AUROC", "Brier score", "calibration slope", "calibration intercept"],
            "seed": SEED, "valid_fraction": VALID_FRACTION, "standard_train_n": STANDARD_TRAIN_N,
            "splits": st,
        }
        (tdir / "task_card.json").write_text(json.dumps(card, indent=2) + "\n")
        stats[task] = st
        print(task, json.dumps(st))
    # mtime=0 so the gzip bytes, and therefore the frozen hash, are reproducible
    manifest.to_csv(TASKS / "split_manifest.csv.gz", index=False,
                    compression={"method": "gzip", "mtime": 0})
    update_stats("tasks", stats)

    if freeze:
        fz = ROOT / "FREEZE.json"
        files = sorted(TASKS.rglob("*.parquet")) + [TASKS / "split_manifest.csv.gz",
                                                    ROOT / "code" / "layout_natality.csv"]
        fz.write_text(json.dumps({"frozen_on": date.today().isoformat(),
                                  "note": "Written before any author-developed method was evaluated.",
                                  "sha256": {str(p.relative_to(ROOT)): sha256(p) for p in files}},
                                 indent=2) + "\n")
        print("Wrote", fz)


if __name__ == "__main__":
    main(freeze="--freeze" in sys.argv)
