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
import pyarrow as pa
import pyarrow.parquet as pq

from natality_common import (read_raw, PROVISIONAL, OUTCOMES, PROCESSED, ROOT, SEED, STANDARD_TRAIN_N, TASKS,
                             TEST_YEAR, TRAIN_YEARS, VALID_FRACTION, classify, cohort_flow,
                             decode, load_layout, outcome, predictor_rows, update_stats)


def cohort_cols(preds):
    return ["row_id", "RESTATUS", "IMP_PLUR", "DPLURAL"] + \
        sorted({spec["field"] for spec in OUTCOMES.values()} | set(preds["name"]) |
               {f for f in preds["imp_flag"] if f})


def year_cohort(yr, preds):
    df = read_raw(yr, columns=cohort_cols(preds))
    flow = cohort_flow(df)
    return df[flow[-1][1]].reset_index(drop=True), [name for name, _ in flow]


def decode_year(df, preds):
    """Decode one year's cohort to compact dtypes (fixed category lists from the layout)."""
    X = pd.DataFrame({"row_id": df["row_id"]})
    M = pd.DataFrame({"row_id": df["row_id"]})
    for _, r in preds.iterrows():
        cls = classify(df, r)
        M[r["name"]] = cls.astype(pd.CategoricalDtype(["O", "S", "A", "I", "X"]))
        v = decode(df, r, cls)
        if r["kind"] in ("int", "num"):
            X[r["name"]] = v
            if r["not_applicable"]:
                X[r["name"] + "__na_struct"] = (cls == "A").astype("int8")
        else:
            cats = r["valid"].split("|") + (["NA_STRUCT"] if r["not_applicable"] else [])
            X[r["name"]] = v.astype(pd.CategoricalDtype(cats))
    return X, M


def assign_splits(ids):
    """ids: row_id Series for the whole cohort, in year/line order."""
    rng = np.random.default_rng(SEED)
    order = ids.sort_values().index      # assignment never depends on file order
    u = pd.Series(rng.random(len(ids)), index=order).sort_index()
    year = ids.str[:4].astype(int)
    split = np.where(year == TEST_YEAR, "test",
                     np.where(u < VALID_FRACTION, "valid", "train"))
    return pd.Series(split, index=ids.index), u


class Writers:
    """Append-mode Parquet writers, one per output file, so years are written one at a time."""
    def __init__(self):
        self.w = {}

    def write(self, path, df):
        tbl = pa.Table.from_pandas(df, preserve_index=False)
        if path not in self.w:
            self.w[path] = pq.ParquetWriter(path, tbl.schema)
        else:
            tbl = tbl.cast(self.w[path].schema)
        self.w[path].write_table(tbl)

    def close(self):
        for w in self.w.values():
            w.close()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(freeze=False):
    if (ROOT / "FREEZE.json").exists():
        sys.exit("FREEZE.json exists; tasks are frozen and will not be rebuilt. A change needs a new version.")
    if freeze and PROVISIONAL:
        sys.exit("Refusing to freeze a provisional build (PHMB_TRAIN_YEARS is set).")
    lay = load_layout()
    preds = predictor_rows(lay)
    years = TRAIN_YEARS + [TEST_YEAR]

    # Pass 1: cohort row_ids and outcomes only, to assign splits over all years at once.
    ids, Ys, stages = [], [], None
    for yr in years:
        df, stages = year_cohort(yr, preds)
        ids.append(df["row_id"])
        Ys.append(pd.DataFrame({t: outcome(df, t) for t in OUTCOMES}))
        del df
    ids = pd.concat(ids, ignore_index=True)
    Y = pd.concat(Ys, ignore_index=True); del Ys
    split, u = assign_splits(ids)
    manifest = pd.DataFrame({"row_id": ids, "split": split})
    for task in OUTCOMES:
        ok = Y[task].notna()
        tr = ok & (split == "train")
        rank = u[tr].rank(method="first")
        manifest[f"{task}_eligible"] = ok.astype("int8")
        manifest[f"{task}_standard_track"] = (tr & (rank.reindex(ids.index) <= STANDARD_TRAIN_N)).astype("int8")

    # Pass 2: decode one year at a time and append its rows to each task/split file.
    TASKS.mkdir(parents=True, exist_ok=True)
    for task in OUTCOMES:
        (TASKS / task).mkdir(exist_ok=True)
    W = Writers()
    offset = 0
    for yr in years:
        df, _ = year_cohort(yr, preds)
        X, M = decode_year(df, preds)
        del df
        sl = slice(offset, offset + len(X))
        if not (manifest["row_id"].iloc[sl].to_numpy() == X["row_id"].to_numpy()).all():
            raise SystemExit(f"{yr}: pass-2 rows do not line up with pass-1 rows")
        sp = split.iloc[sl].to_numpy()
        for task in OUTCOMES:
            y = Y[task].iloc[sl].to_numpy()
            for s_ in ["train", "valid", "test"]:
                m = (sp == s_) & ~np.isnan(y)
                if not m.any():
                    continue
                out = X[m].copy()
                out.insert(1, "y", y[m].astype("int8"))
                W.write(TASKS / task / f"{s_}.parquet", out)
                W.write(TASKS / task / f"{s_}_mclass.parquet", M[m])
                del out
        offset += len(X)
        print(f"  {yr}: {len(X):,} cohort records written")
        del X, M
    W.close()

    stats = {}
    for task, spec in OUTCOMES.items():
        y = Y[task]
        st = {}
        for s_ in ["train", "valid", "test"]:
            m = y.notna() & (split == s_)
            st[s_] = {"n": int(m.sum()), "cases": int(y[m].sum()), "prevalence": float(y[m].mean())}
        std = manifest[f"{task}_standard_track"] == 1
        st["train_standard"] = {"n": int(std.sum()), "cases": int(y[std].sum()),
                                "prevalence": float(y[std].mean()) if std.any() else None}
        card = {
            "task": task, "version": "1.0.0-draft", "label": spec["label"],
            "source": "NCHS Natality Public Use Files", "years": {"train": TRAIN_YEARS, "test": TEST_YEAR},
            "cohort": stages[1:] + [f"{spec['field']} stated"],
            "outcome_field": spec["field"], "predictors": list(preds["name"]),
            "missingness_classes": {"O": "observed", "S": "not stated", "A": "not applicable (structural)",
                                    "I": "imputed by NCHS, restored to missing",
                                    "X": "undocumented code, treated as missing"},
            "primary_metric": "AUPRC on test",
            "secondary_metrics": ["AUROC", "Brier score", "calibration slope", "calibration intercept"],
            "seed": SEED, "valid_fraction": VALID_FRACTION, "standard_train_n": STANDARD_TRAIN_N,
            "splits": st,
        }
        (TASKS / task / "task_card.json").write_text(json.dumps(card, indent=2) + "\n")
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
