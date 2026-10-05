#!/usr/bin/env python3
"""Baseline results for the frozen natality tasks.

Refuses to run unless FREEZE.json exists and every hash in it matches, so baselines
(and any later method) are always scored on the frozen tasks.

Baselines
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


def feature_cols(df):
    return [c for c in df.columns if c not in ("row_id", "y")]


def design(train, others, indicators=False):
    """One-hot categoricals (missing stays NaN in every dummy), numerics as-is."""
    cols = feature_cols(train)
    cats = [c for c in cols if train[c].dtype == object or str(train[c].dtype).startswith(("str", "string"))]
    nums = [c for c in cols if c not in cats]
    levels = {c: sorted(train[c].dropna().unique()) for c in cats}

    def build(df):
        parts = [df[nums].astype("float64")]
        for c in cats:
            dm = pd.get_dummies(df[c].astype("object"), prefix=c, dtype="float64")
            dm = dm.reindex(columns=[f"{c}_{lv}" for lv in levels[c][1:]], fill_value=0.0)
            dm.loc[df[c].isna().to_numpy()] = np.nan
            parts.append(dm)
        X = pd.concat(parts, axis=1)
        if indicators:
            ind = pd.DataFrame({f"{c}__miss": df[c].isna().astype("float64") for c in nums + cats})
            X = pd.concat([X, ind], axis=1)
        return X

    return build(train), [build(o) for o in others]


def fill_simple(Xtr, Xs):
    med = Xtr.median()
    return Xtr.fillna(med), [x.fillna(med) for x in Xs]


def logit_fit_predict(Xtr, ytr, Xs):
    sc = StandardScaler().fit(Xtr)
    m = LogisticRegression(max_iter=2000, C=1.0, class_weight=None)
    m.fit(sc.transform(Xtr), ytr)
    return [m.predict_proba(sc.transform(x))[:, 1] for x in Xs]


def run_logit_baseline(name, tr, va, te, track):
    ytr = tr["y"].to_numpy()
    if name == "B1":
        cc = tr[feature_cols(tr)].notna().all(axis=1).to_numpy()
        Xtr, (Xva, Xte) = design(tr[cc], [va, te])
        Xtr, (Xva, Xte) = fill_simple(Xtr, [Xva, Xte])
        return logit_fit_predict(Xtr, ytr[cc], [Xva, Xte]), {"complete_cases_train": int(cc.sum())}
    if name == "B2":
        Xtr, (Xva, Xte) = design(tr, [va, te], indicators=True)
        Xtr, (Xva, Xte) = fill_simple(Xtr, [Xva, Xte])
        return logit_fit_predict(Xtr, ytr, [Xva, Xte]), {}
    Xtr, (Xva, Xte) = design(tr, [va, te])
    if name == "B3":
        imp = IterativeImputer(estimator=BayesianRidge(), max_iter=10, random_state=SEED)
    else:
        imp = IterativeImputer(estimator=RandomForestRegressor(n_estimators=20, max_depth=12,
                                                               n_jobs=-1, random_state=SEED),
                               max_iter=5, random_state=SEED)
    # Fit the imputer on a seeded subsample (cost grows steeply with rows), then impute everything.
    fit_rows = Xtr.sample(n=min(IMPUTER_FIT_N, len(Xtr)), random_state=SEED)
    imp.fit(fit_rows)
    Xtr_i = pd.DataFrame(imp.transform(Xtr), columns=Xtr.columns)
    Xva_i = pd.DataFrame(imp.transform(Xva), columns=Xtr.columns)
    Xte_i = pd.DataFrame(imp.transform(Xte), columns=Xtr.columns)
    return logit_fit_predict(Xtr_i, ytr, [Xva_i, Xte_i]), {}


def lgbm_frame(df, mcl=None, cats=None):
    X = df[feature_cols(df)].copy()
    cats = cats or [c for c in X.columns if X[c].dtype == object or str(X[c].dtype).startswith(("str", "string"))]
    for c in cats:
        X[c] = X[c].astype("category")
    if mcl is not None:
        for c in mcl.columns:
            if c == "row_id":
                continue
            X[f"{c}__S"] = (mcl[c] == "S").astype("int8")
            X[f"{c}__I"] = (mcl[c] == "I").astype("int8")
    return X, cats


def run_lgbm(name, tr, trm, va, vam, te, tem):
    import lightgbm as lgb
    use_m = name == "B6"
    Xtr, cats = lgbm_frame(tr, trm if use_m else None)
    Xva, _ = lgbm_frame(va, vam if use_m else None, cats)
    Xte, _ = lgbm_frame(te, tem if use_m else None, cats)
    for c in cats:
        lv = Xtr[c].cat.categories
        Xva[c] = Xva[c].cat.set_categories(lv)
        Xte[c] = Xte[c].cat.set_categories(lv)
    m = lgb.LGBMClassifier(n_estimators=2000, learning_rate=0.03, num_leaves=31,
                           min_child_samples=100, subsample=0.8, subsample_freq=1,
                           colsample_bytree=0.8, random_state=SEED, verbose=-1)
    m.fit(Xtr, tr["y"], eval_set=[(Xva, va["y"])], eval_metric="average_precision",
          callbacks=[lgb.early_stopping(100, verbose=False)])
    return [m.predict_proba(Xva)[:, 1], m.predict_proba(Xte)[:, 1]], {"best_iteration": int(m.best_iteration_ or 0)}


def calibration(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    lp = np.log(p / (1 - p)).reshape(-1, 1)
    slope = LogisticRegression(C=1e6, max_iter=1000).fit(lp, y).coef_[0, 0]
    # calibration-in-the-large: intercept with logit(p) as offset (one-step Newton from 0)
    a = 0.0
    for _ in range(50):
        q = 1 / (1 + np.exp(-(a + lp[:, 0])))
        a += (y - q).sum() / max((q * (1 - q)).sum(), 1e-12)
    return float(slope), float(a)


def metrics(y, p, boot, rng):
    out = {"auprc": average_precision_score(y, p), "auroc": roc_auc_score(y, p),
           "brier": brier_score_loss(y, p), "prevalence": float(y.mean())}
    out["cal_slope"], out["cal_intercept"] = calibration(y, p)
    if boot:
        pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
        bp, br = [], []
        for _ in range(boot):
            idx = np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))])
            bp.append(average_precision_score(y[idx], p[idx]))
            br.append(roc_auc_score(y[idx], p[idx]))
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
    rows, rng = [], np.random.default_rng(SEED)
    for task in OUTCOMES:
        (tr, trm), (va, vam), (te, tem) = load(task, a.track)
        for b in which:
            t0 = time.time()
            if b in ("B5", "B6"):
                (pva, pte), info = run_lgbm(b, tr, trm, va, vam, te, tem)
            else:
                (pva, pte), info = run_logit_baseline(b, tr, va, te, a.track)
            m = metrics(te["y"].to_numpy(), pte, a.boot, rng)
            m["valid_auprc"] = float(average_precision_score(va["y"], pva))
            rows.append({"task": task, "track": a.track, "baseline": b, "n_train": len(tr),
                         "seconds": round(time.time() - t0, 1), **m, **info})
            print(task, b, f"AUPRC {m['auprc']:.4f}", f"AUROC {m['auroc']:.4f}", f"{rows[-1]['seconds']}s")
    res = pd.DataFrame(rows)
    PAPER.mkdir(exist_ok=True)
    res.to_csv(PAPER / f"baselines_{a.track}.csv", index=False)
    update_stats(f"baselines_{a.track}", {f"{r.task}_{r.baseline}": {k: v for k, v in r._asdict().items()
                                                                       if k not in ("Index",)}
                                           for r in res.itertuples()})


if __name__ == "__main__":
    main()
