#!/usr/bin/env python3
"""SYNTHETIC test fixture. Not NCHS data; used only to exercise the pipeline code.

Writes fake fixed-width Nat{year}us.zip files into <root>/data/raw following
code/layout_natality.csv, with planted not-stated, structural, and imputed cells.

    python tests/make_fixture.py <root> <records per year, default 20000>
"""
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(sys.argv[1])
n = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
lay = pd.read_csv(root / "code" / "layout_natality.csv", dtype=str, keep_default_na=False)
rng = np.random.default_rng(1)


def valid_value(r):
    k, v = r["kind"], r["valid"]
    w = int(r["end"]) - int(r["start"]) + 1
    if k in ("cat", "yn"):
        return rng.choice(v.split("|"))
    lo, hi = (float(x) for x in v.split("-"))
    if k == "num":
        return f"{rng.uniform(lo, hi):{w}.1f}"
    return str(int(rng.integers(int(lo), int(hi) + 1))).zfill(w)


(root / "data" / "raw").mkdir(parents=True, exist_ok=True)
for year in (2022, 2023, 2024):
    lines = []
    for _ in range(n):
        rec = [" "] * 1330
        vals = {}
        for _, r in lay.iterrows():
            s, e, w = int(r["start"]), int(r["end"]), int(r["end"]) - int(r["start"]) + 1
            if r["kind"] == "flag":
                val = ""
            elif r["name"] == "DOB_YY":
                val = str(year)
            elif r["name"] == "DPLURAL":
                val = "1" if rng.random() < 0.97 else "2"
            elif r["name"] == "RESTATUS":
                val = "4" if rng.random() < 0.003 else "1"
            elif r["name"] == "OEGEST_COMB":
                val = "99" if rng.random() < 0.002 else str(int(np.clip(rng.normal(38.6, 2.2), 17, 47)))
            elif r["name"] == "DBWT":
                val = "9999" if rng.random() < 0.001 else str(int(np.clip(rng.normal(3300, 700), 227, 8165))).zfill(4)
            else:
                u = rng.random()
                if r["not_stated"] and u < 0.05:
                    val = rng.choice(r["not_stated"].split("|")).replace("BLANK", "")
                elif r["not_applicable"] and u < 0.35:
                    val = r["not_applicable"]
                else:
                    val = valid_value(r)
            vals[r["name"]] = val
            rec[s - 1:e] = list(str(val).rjust(w)[:w])
        for _, r in lay[lay["imp_flag"] != ""].iterrows():
            if rng.random() < 0.01:
                p = int(lay.loc[lay["name"] == r["imp_flag"], "start"].iloc[0])
                rec[p - 1] = "1"
        lines.append("".join(rec))
    with zipfile.ZipFile(root / "data" / "raw" / f"Nat{year}us.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"Nat{year}PublicUS.c.txt", "\n".join(lines) + "\n")
    print("wrote fixture", year)
