"""Shared definitions for the PH-MissBench natality module.

Every raw cell is assigned one missingness class:
  O  observed            value is in the field's valid code set
  S  not stated          the agency's not-stated / unknown code (or blank where blank means unknown)
  A  not applicable      structural code (e.g. 888 = first birth); not missing data
  I  imputed by NCHS     the field's NCHS imputation flag is set; the value is restored to missing
  X  invalid             none of the above; signals a wrong record-layout position (QA fails)
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "code" / "layout_natality.csv"
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
TASKS = ROOT / "tasks" / "natality"
PAPER = ROOT / "paper"

YEARS = [2022, 2023, 2024]
TRAIN_YEARS = [2022, 2023]
TEST_YEAR = 2024
SEED = 20261004            # [V4] fixed split seed
VALID_FRACTION = 0.10      # [V4] share of training years held out for validation
STANDARD_TRAIN_N = 250_000  # [V4] size of the standard-track training subsample

# Fields whose inclusion awaits the author's leakage ruling (task spec section 4).
# Default: excluded from the v1.0 predictor set.
PENDING_INCLUDED: list[str] = []


def zip_url(year: int) -> str:
    return ("https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/natality/"
            f"Nat{year}us.zip")  # [VERIFY] filename pattern


def load_layout() -> pd.DataFrame:
    lay = pd.read_csv(LAYOUT_PATH, dtype=str, keep_default_na=False)
    lay["start"] = lay["start"].astype(int)
    lay["end"] = lay["end"].astype(int)
    return lay


def _codes(spec: str) -> set[str]:
    if not spec:
        return set()
    return {"" if c == "BLANK" else c for c in spec.split("|")}


def _is_valid(raw: pd.Series, kind: str, valid: str) -> pd.Series:
    if kind in ("cat", "yn", "flag"):
        return raw.isin(_codes(valid))
    lo, hi = (float(x) for x in valid.split("-"))
    num = pd.to_numeric(raw, errors="coerce")
    return num.between(lo, hi)


def classify(df: pd.DataFrame, row: pd.Series) -> pd.Series:
    """Return the missingness class (O/S/A/I/X) for one field across all records."""
    raw = df[row["name"]]
    cls = pd.Series("X", index=df.index, dtype="object")
    cls[_is_valid(raw, row["kind"], row["valid"])] = "O"
    cls[raw.isin(_codes(row["not_stated"]))] = "S"
    cls[raw.isin(_codes(row["not_applicable"]))] = "A"
    if row["imp_flag"]:
        cls[df[row["imp_flag"]] != ""] = "I"
    return cls


def cohort_flow(df: pd.DataFrame) -> list[tuple[str, pd.Series]]:
    """Cumulative cohort masks, in order. Outcome-missing exclusions are task-specific."""
    m0 = pd.Series(True, index=df.index)
    m1 = m0 & (df["RESTATUS"] != "4")           # U.S. residents
    m2 = m1 & (df["IMP_PLUR"] == "")            # plurality not imputed by NCHS
    m3 = m2 & (df["DPLURAL"] == "1")            # singletons
    return [("all records", m0), ("U.S. residents", m1),
            ("plurality reported (not imputed)", m2), ("singletons", m3)]


OUTCOMES = {
    "EPTB": {"field": "OEGEST_COMB", "missing": "99", "label": "Early preterm birth (<34 weeks, obstetric estimate)",
             "rule": lambda v: v < 34},
    "VLBW": {"field": "DBWT", "missing": "9999", "label": "Very low birthweight (<1,500 g)",
             "rule": lambda v: v < 1500},
}


def outcome(df: pd.DataFrame, task: str) -> pd.Series:
    """1/0 outcome; NaN where the outcome itself is not stated (record excluded from the task)."""
    spec = OUTCOMES[task]
    v = pd.to_numeric(df[spec["field"]], errors="coerce")
    v = v.where(df[spec["field"]] != spec["missing"])
    return spec["rule"](v).astype("float64").where(v.notna())


def predictor_rows(lay: pd.DataFrame) -> pd.DataFrame:
    keep = (lay["role"] == "predictor") | lay["name"].isin(PENDING_INCLUDED)
    return lay[keep]


def decode(df: pd.DataFrame, row: pd.Series, cls: pd.Series) -> pd.Series:
    """Analysis value: observed values kept; S and I become missing; A handled per kind."""
    raw = df[row["name"]]
    if row["kind"] in ("int", "num"):
        val = pd.to_numeric(raw, errors="coerce").astype("float64")
        return val.where(cls == "O", np.nan)
    val = raw.where(cls == "O", None)
    if row["kind"] == "yn" or row["kind"] == "cat":
        val = val.where(cls != "A", "NA_STRUCT")  # structural: a known category, not missing
    return val.astype("object")


def update_stats(section: str, values: dict) -> None:
    """Merge one section into paper/stats.json (the only source of numbers for documents)."""
    import json
    PAPER.mkdir(parents=True, exist_ok=True)
    path = PAPER / "stats.json"
    stats = json.loads(path.read_text()) if path.exists() else {}
    stats[section] = values
    path.write_text(json.dumps(stats, indent=2, sort_keys=True, default=float) + "\n")
