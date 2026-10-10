#!/usr/bin/env python3
"""External validation against NCHS published totals.

Recomputes, from the parsed public-use files, the number of births to U.S. residents and the
all-births percentages of early preterm (<34 weeks, obstetric estimate) and very low birthweight
(<1,500 g), and compares them with the values NCHS publishes in its final-births reports
(docs/external_reference.csv, entered by hand from the cited report). Writes
data/processed/external_validation.csv and stats.json section "external_validation".

    python code/03b_validate.py
"""
import sys

import pandas as pd

from natality_common import PROCESSED, ROOT, YEARS, read_raw, update_stats

TOL = {"births": 0, "eptb_pct": 0.01, "vlbw_pct": 0.01}


def main():
    ref = pd.read_csv(ROOT / "docs" / "external_reference.csv")
    rows = []
    for y in YEARS:
        df = read_raw(y, columns=["RESTATUS", "OEGEST_COMB", "DBWT"])
        df = df[df["RESTATUS"].astype(str) != "4"]
        oe = pd.to_numeric(df["OEGEST_COMB"].astype(str), errors="coerce")
        oe = oe[oe != 99]
        bw = pd.to_numeric(df["DBWT"].astype(str), errors="coerce")
        bw = bw[bw != 9999]
        ours = {"births": len(df), "eptb_pct": round(100 * (oe < 34).mean(), 2),
                "vlbw_pct": round(100 * (bw < 1500).mean(), 2)}
        for measure, val in ours.items():
            r = ref[(ref["year"] == y) & (ref["measure"] == measure)]
            published = float(r["value"].iloc[0]) if len(r) else None
            ok = None if published is None else abs(val - published) <= TOL[measure]
            rows.append({"year": y, "measure": measure, "pipeline": val, "published": published,
                         "match": ok, "source": r["source"].iloc[0] if len(r) else ""})
    out = pd.DataFrame(rows)
    out.to_csv(PROCESSED / "external_validation.csv", index=False)
    print(out.to_string(index=False))
    update_stats("external_validation", {f"{r.year}_{r.measure}": {"pipeline": r.pipeline,
                                         "published": r.published, "match": r.match}
                                         for r in out.itertuples()})
    if (out["match"] == False).any():  # noqa: E712  (None = no published value, not a failure)
        sys.exit("Pipeline totals disagree with NCHS published values; investigate before freezing.")


if __name__ == "__main__":
    main()
