#!/usr/bin/env python3
"""Baseline results for the frozen natality tasks.

Refuses to run unless FREEZE.json exists and every hash in it matches, so baselines
(and any later method) are always scored on the frozen tasks.

Baselines
  Structural not-applicable cells are set to 0 (indicator kept) before B1-B4; they are not missing.
  B1 cc_logit       logistic regression trained on complete cases; at test time,
                    missing cells filled with training medians/modes
  B2 mean_ind_logit mean/mode fill + one missing-indicator per field, logistic regression
  B3 chained_logit  chained-equations single imputation (IterativeImputer, BayesianRidge),
                    logistic regression
  B4 rf_iter_logit  missForest-style iterative imputation (random-forest estimator),
                    logistic regression; standard track only
  (B3 and B4 imputers are fit on a seeded 50,000-row subsample of train, then applied to all rows)
  B5 lgbm_native    LightGBM, native missing-value handling
  B6 lgbm_mclass    LightGBM plus agency missingness-class indicators (S and I per field)

Metrics on the 2024 test set: AUPRC (primary), AUROC, Brier, calibration slope and
intercept; stratified bootstrap 95% intervals for AUPRC and AUROC.

    python code/05_baselines.py [--track standard|full] [--boot 1000] [--only B5,B6]
"""
import argparse
import hashlib
import json
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge, LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

IMPUTER_FIT_N = 50_000  # rows used to fit the B3/B4 imputers

from natality_common import OUTCOMES, PAPER, ROOT, SEED, TASKS, update_stats


def check_freeze():
    fz = ROOT / "FREEZE.json"
    if not fz.exists():
        raise SystemExit("No FREEZE.json: freeze the tasks (04_tasks.py --freeze) before any method runs.")
    for rel, digest in json.loads(fz.read_text())["sha256"].items():
        h = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if h != digest:
            raise SystemExit(f"{rel} does not match FREEZE.json; tasks were changed after the freeze.")


def load(task, track):
    d = TASKS / task
    man = pd.read_csv(TASKS / "split_manifest.csv.gz", usecols=["row_id", f"{task}_standard_track"])
    tr = pd.read_parquet(d / "train.parquet")
    trm = pd.read_parquet(d / "train_mclass.parquet")
    if track == "standard":
        keep = set(man.loc[man[f"{task}_standard_track"] == 1, "row_id"])
        sel = tr["row_id"].isin(keep).to_numpy()
        tr, trm = tr[sel].reset_index(drop=True), trm[sel].reset_index(drop=True)
    va, vam = pd.read_parquet(d / "valid.parquet"), pd.read_parquet(d / "valid_mclass.parquet")
    te, tem = pd.read_parquet(d / "test.parquet"), pd.read_parquet(d / "test_mclass.parquet")
    return (tr, trm), (va, vam), (te, tem)


def is_cat(s):
    return isinstance(s.dtype, pd.CategoricalDtype) or s.dtype == object or \
        str(s.dtype).startswith(("str", "string"))


def feature_cols(df):
    return [c for c in df.columns if c not in ("row_id", "y")]


CHUNK = 250_000  # rows scored at a time, so the 3.5M-row test year fits in memory


def chunked(predict, df, mcl=None):
    out = []
    for i in range(0, len(df), CHUNK):
        sl = slice(i, i + CHUNK)
        out.append(predict(df.iloc[sl], None if mcl is None else mcl.iloc[sl]))
    return np.concatenate(out)


def make_design(train, indicators=False):
    """Return build(df): one-hot categoricals (missing stays NaN in every dummy), numerics as-is."""
    cols = feature_cols(train)
    cats = [c for c in cols if is_cat(train[c])]
    nums = [c for c in cols if c not in cats]
    levels = {c: sorted(train[c].dropna().unique()) for c in cats}

    def build(df):
        parts = [df[nums].astype("float64").reset_index(drop=True)]
        for c in cats:
            dm = pd.get_dummies(df[c].astype("object"), prefix=c, dtype="float64")
            dm = dm.reindex(columns=[f"{c}_{lv}" for lv in levels[c][1:]], fill_value=0.0)
            dm.loc[df[c].isna().to_numpy()] = np.nan
            parts.append(dm.reset_index(drop=True))
        X = pd.concat(parts, axis=1)
        if indicators:
            ind = pd.DataFrame({f"{c}__miss": df[c].isna().astype("float64").to_numpy() for c in nums + cats})
            X = pd.concat([X, ind], axis=1)
        return X

    return build


def fit_logit(Xtr, ytr):
    sc = StandardScaler().fit(Xtr)
    m = LogisticRegression(max_iter=2000, C=1.0)
    m.fit(sc.transform(Xtr), ytr)
    return lambda X: m.predict_proba(sc.transform(X))[:, 1]


def fill_structural(df):
    """Structural 'not applicable' cells (e.g. birth intervals for a first birth) are not missing
    data (task spec section 5): set them to 0 and let the <field>__na_struct indicator carry the
    information, so complete-case and imputation baselines do not treat them as missing."""
    flags = [c for c in df.columns if c.endswith("__na_struct")]
    if not flags:
        return df
    df = df.copy()
    for f in flags:
        base = f[: -len("__na_struct")]
        df[base] = df[base].mask(df[f].to_numpy() == 1, 0.0)
    return df


def fit_logit_baseline(name, tr):
    """Fit on train; return (predict(df, mcl) -> probabilities, info)."""
    tr = fill_structural(tr)
    ytr = tr["y"].to_numpy()
    info = {}
    if name in ("B1", "B2"):
        sub = tr
        if name == "B1":
            cc = tr[feature_cols(tr)].notna().all(axis=1).to_numpy()
            sub, ytr = tr[cc], ytr[cc]
            info["complete_cases_train"] = int(cc.sum())
        build = make_design(sub, indicators=(name == "B2"))
        Xtr = build(sub)
        med = Xtr.median()
        f = fit_logit(Xtr.fillna(med), ytr)
        return (lambda df, mcl: f(build(fill_structural(df)).fillna(med))), info
    build = make_design(tr)
    Xtr = build(tr)
    if name == "B3":
        imp = IterativeImputer(estimator=BayesianRidge(), max_iter=10, random_state=SEED)
    else:
        imp = IterativeImputer(estimator=RandomForestRegressor(n_estimators=20, max_depth=12,
                                                               n_jobs=-1, random_state=SEED),
                               max_iter=5, random_state=SEED)
    # Fit the imputer on a seeded subsample (cost grows steeply with rows), then impute everything.
    imp.fit(Xtr.sample(n=min(IMPUTER_FIT_N, len(Xtr)), random_state=SEED))
    f = fit_logit(imp.transform(Xtr), ytr)
    return (lambda df, mcl: f(imp.transform(build(fill_structural(df))))), info


def lgbm_frame(df, mcl=None, cats=None, levels=None):
    X = df[feature_cols(df)].copy()
    cats = cats or [c for c in X.columns if is_cat(X[c])]
    for c in cats:
        X[c] = X[c].astype("category")
        if levels is not None:
            X[c] = X[c].cat.set_categories(levels[c])
    if mcl is not None:
        for c in mcl.columns:
            if c == "row_id":
                continue
            X[f"{c}__S"] = (mcl[c] == "S").astype("int8").to_numpy()
            X[f"{c}__I"] = (mcl[c] == "I").astype("int8").to_numpy()
    return X, cats


def fit_lgbm(name, tr, trm, va, vam):
    import lightgbm as lgb
    use_m = name == "B6"
    Xtr, cats = lgbm_frame(tr, trm if use_m else None)
    levels = {c: Xtr[c].cat.categories for c in cats}
    Xva, _ = lgbm_frame(va, vam if use_m else None, cats, levels)
    m = lgb.LGBMClassifier(n_estimators=2000, learning_rate=0.03, num_leaves=31,
                           min_child_samples=100, subsample=0.8, subsample_freq=1,
                           colsample_bytree=0.8, random_state=SEED, verbose=-1)
    m.fit(Xtr, tr["y"], eval_set=[(Xva, va["y"])], eval_metric="average_precision",
          callbacks=[lgb.early_stopping(100, verbose=False)])
    del Xva

    def predict(df, mcl):
        X, _ = lgbm_frame(df, mcl if use_m else None, cats, levels)
        return m.predict_proba(X)[:, 1]
    return predict, {"best_iteration": int(m.best_iteration_ or 0)}


def calibration(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    lp = np.log(p / (1 - p)).reshape(-1, 1)
    slope = LogisticRegression(C=1e6, max_iter=1000).fit(lp, y).coef_[0, 0]
    # calibration-in-the-large: intercept with logit(p) as offset (Newton iterations from 0)
    a = 0.0
    for _ in range(50):
        q = 1 / (1 + np.exp(-(a + lp[:, 0])))
        a += (y - q).sum() / max((q * (1 - q)).sum(), 1e-12)
    return float(slope), float(a)


class FastCurves:
    """Exact weighted AUPRC (sklearn's average precision) and AUROC on presorted scores.

    Sorting once and scoring each bootstrap replicate as integer weights makes 1,000 replicates
    on 3.5 million rows practical. With unit weights it equals sklearn's values (checked at run).
    """
    def __init__(self, y, p):
        order = np.argsort(-p, kind="mergesort")
        self.y = y[order].astype(bool)
        ps = p[order]
        self.starts = np.flatnonzero(np.r_[True, ps[1:] != ps[:-1]])   # tie groups

    def scores(self, w):
        tp = np.add.reduceat(np.where(self.y, w, 0), self.starts).astype(float)
        fp = np.add.reduceat(np.where(self.y, 0, w), self.starts).astype(float)
        TP, FP = np.cumsum(tp), np.cumsum(fp)
        P, N = TP[-1], FP[-1]
        # thresholds whose groups drew no records in a replicate contribute nothing (avoid 0/0)
        prec = np.divide(TP, TP + FP, out=np.zeros_like(TP), where=(TP + FP) > 0)
        ap = float(np.sum((tp / P) * prec))
        auc = float(np.sum(tp * (N - FP + fp / 2.0)) / (P * N))   # positives outrank negatives
        return ap, auc


def metrics(y, p, boot, rng):
    fc = FastCurves(y, p)
    ap, auc = fc.scores(np.ones(len(y), dtype=np.int64))
    ref_ap, ref_auc = average_precision_score(y, p), roc_auc_score(y, p)
    if abs(ap - ref_ap) > 1e-9 or abs(auc - ref_auc) > 1e-9:
        raise SystemExit(f"fast metric mismatch: AP {ap} vs {ref_ap}, AUC {auc} vs {ref_auc}")
    out = {"auprc": ref_ap, "auroc": ref_auc, "brier": brier_score_loss(y, p), "prevalence": float(y.mean())}
    out["cal_slope"], out["cal_intercept"] = calibration(y, p)
    if boot:
        ys = fc.y
        pos, neg = np.flatnonzero(ys), np.flatnonzero(~ys)
        bp, br = [], []
        for _ in range(boot):   # stratified bootstrap: resample positives and negatives separately
            w = np.zeros(len(ys), dtype=np.int64)
            w[pos] = np.bincount(rng.integers(0, len(pos), len(pos)), minlength=len(pos))
            w[neg] = np.bincount(rng.integers(0, len(neg), len(neg)), minlength=len(neg))
            a_, r_ = fc.scores(w)
            bp.append(a_); br.append(r_)
        out["auprc_lo"], out["auprc_hi"] = np.percentile(bp, [2.5, 97.5])
        out["auroc_lo"], out["auroc_hi"] = np.percentile(br, [2.5, 97.5])
    return {k: float(v) for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default="standard", choices=["standard", "full"])
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--only", default="B1,B2,B3,B4,B5,B6")
    a = ap.parse_args()
    check_freeze()
    which = a.only.split(",")
    if a.track == "full" and "B4" in which:
        which.remove("B4")  # random-forest imputation does not scale to the full track
    out_csv = PAPER / f"baselines_{a.track}.csv"
    PAPER.mkdir(exist_ok=True)
    for task in OUTCOMES:
        (tr, trm), (va, vam), (te, tem) = load(task, a.track)
        for b in which:
            t0 = time.time()
            rng = np.random.default_rng([SEED, list(OUTCOMES).index(task), int(b[1:])])
            if b in ("B5", "B6"):
                predict, info = fit_lgbm(b, tr, trm, va, vam)
            else:
                predict, info = fit_logit_baseline(b, tr)
            pva = chunked(predict, va, vam)
            pte = chunked(predict, te, tem)
            m = metrics(te["y"].to_numpy(), pte, a.boot, rng)
            m["valid_auprc"] = float(average_precision_score(va["y"], pva))
            row = {"task": task, "track": a.track, "baseline": b, "n_train": len(tr),
                   "seconds": round(time.time() - t0, 1), **m, **info}
            print(task, b, f"AUPRC {m['auprc']:.4f}", f"AUROC {m['auroc']:.4f}", f"{row['seconds']}s", flush=True)
            # merge into the results file after every baseline, so partial runs are kept
            res = pd.read_csv(out_csv) if out_csv.exists() else pd.DataFrame()
            if len(res):
                res = res[~((res["task"] == task) & (res["baseline"] == b))]
            res = pd.concat([res, pd.DataFrame([row])], ignore_index=True).sort_values(["task", "baseline"])
            res.to_csv(out_csv, index=False)
            update_stats(f"baselines_{a.track}", {f"{r['task']}_{r['baseline']}": {k: (None if pd.isna(v) else v)
                                                   for k, v in r.items()} for r in res.to_dict("records")})


if __name__ == "__main__":
    main()
