#!/usr/bin/env python3
"""Extract the benchmark fields from each fixed-width natality file and check the layout.

Writes data/processed/natality_{year}_raw.parquet (raw codes as strings, one row per
record, plus a stable row_id = "<year>-<line number>") and appends a layout check to
data/processed/layout_check.csv. Fails if any field has more than 0.1% invalid codes,
which is what a wrong start/end position produces.

    python code/02_parse.py [years...]
"""
import sys
import zipfile

import pandas as pd

from natality_common import PROCESSED, RAW, YEARS, classify, load_layout, zip_url

MAX_INVALID = 0.001
CHUNK = 500_000


def read_year(year: int, lay: pd.DataFrame) -> pd.DataFrame:
    path = RAW / zip_url(year).rsplit("/", 1)[1]
    colspecs = [(s - 1, e) for s, e in zip(lay["start"], lay["end"])]
    parts, offset = [], 0
    with zipfile.ZipFile(path) as zf:
        member = max(zf.infolist(), key=lambda m: m.file_size).filename
        with zf.open(member) as fh:
            for chunk in pd.read_fwf(fh, colspecs=colspecs, names=list(lay["name"]), header=None,
                                     dtype=str, keep_default_na=False, na_filter=False,
                                     chunksize=CHUNK):
                chunk.index = range(offset + 1, offset + 1 + len(chunk))
                offset += len(chunk)
                parts.append(chunk)
    df = pd.concat(parts)
    df.insert(0, "row_id", [f"{year}-{i:07d}" for i in df.index])
    return df.reset_index(drop=True)


def layout_check(df: pd.DataFrame, lay: pd.DataFrame, year: int) -> pd.DataFrame:
    rows = []
    for _, r in lay.iterrows():
        raw = df[r["name"]]
        if r["kind"] == "flag":
            invalid = ((raw != "") & ~raw.isin(r["valid"].split("|"))).mean()
        else:
            invalid = (classify(df, r) == "X").mean()
        rows.append({"year": year, "field": r["name"], "start": r["start"], "end": r["end"],
                     "invalid_share": invalid, "pass": invalid <= MAX_INVALID})
    out = pd.DataFrame(rows)
    yy = (df["DOB_YY"] == str(year)).mean()
    out.loc[out["field"] == "DOB_YY", "pass"] = yy == 1.0
    return out


def main(years):
    lay = load_layout()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    checks = []
    for y in years:
        df = read_year(y, lay)
        chk = layout_check(df, lay, y)
        checks.append(chk)
        df.to_parquet(PROCESSED / f"natality_{y}_raw.parquet", index=False)
        bad = chk[~chk["pass"]]
        print(f"{y}: {len(df):,} records; layout failures: {len(bad)}")
        for _, b in bad.iterrows():
            print(f"   FAIL {b['field']} ({b['start']}-{b['end']}): "
                  f"{b['invalid_share']:.2%} invalid codes")
    allchk = pd.concat(checks)
    allchk.to_csv(PROCESSED / "layout_check.csv", index=False)
    if not allchk["pass"].all():
        sys.exit("Layout check failed: fix code/layout_natality.csv against the user guide.")


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or YEARS)
