#!/usr/bin/env python3
"""Extract the benchmark fields from each fixed-width natality file and check the layout.

NCHS distributes the files with Deflate64 compression, which Python's zipfile cannot read,
so the text is streamed through the `unzip` command (Info-ZIP). Records are sliced with
numpy in blocks, so memory stays flat regardless of file size.

Writes data/processed/natality_{year}_raw.parquet (raw codes as trimmed strings, one row per
record, plus a stable row_id = "<year>-<line number>") and data/processed/layout_check.csv.
Fails if any field has more than 0.1% invalid codes, which is what a wrong start/end
position produces.

    python code/02_parse.py [years...]
"""
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from natality_common import read_raw, PROCESSED, RAW, YEARS, classify, load_layout, zip_url

MAX_INVALID = 0.001
BLOCK = 200_000  # records per block


def stream_lines(path):
    if not shutil.which("unzip"):
        sys.exit("The `unzip` command is required (NCHS zips use Deflate64).")
    proc = subprocess.Popen(["unzip", "-p", str(path)], stdout=subprocess.PIPE, bufsize=1 << 24)
    return proc


def parse_year(year, lay):
    path = RAW / zip_url(year).rsplit("/", 1)[1]
    out = PROCESSED / f"natality_{year}_raw.parquet"
    proc = stream_lines(path)
    first = proc.stdout.readline()
    L = len(first)                      # record length including line terminator(s)
    names = ["row_id"] + list(lay["name"])
    schema = pa.schema([(n, pa.string()) for n in names])
    writer = pq.ParquetWriter(out, schema, compression="zstd")
    n_done, buf = 0, first
    while True:
        chunk = proc.stdout.read(BLOCK * L - len(buf))
        data = buf + (chunk or b"")
        buf = b""
        if not data:
            break
        if len(data) % L:
            raise SystemExit(f"{year}: data length not a multiple of record length {L}; "
                             "records are not fixed-width as assumed.")
        arr = np.frombuffer(data, dtype=np.uint8).reshape(-1, L)
        k = arr.shape[0]
        cols = {"row_id": pa.array([f"{year}-{i:07d}" for i in range(n_done + 1, n_done + k + 1)])}
        for name, s, e in zip(lay["name"], lay["start"], lay["end"]):
            w = e - s + 1
            raw = np.ascontiguousarray(arr[:, s - 1:e]).view(f"S{w}").ravel()
            cols[name] = pc.utf8_trim_whitespace(pa.array(raw.astype(f"U{w}")))
        writer.write_table(pa.table(cols, schema=schema))
        n_done += k
        if not chunk:
            break
    writer.close()
    if proc.wait() != 0:
        raise SystemExit(f"unzip failed for {path}")
    return n_done, L


def layout_check(df, lay, year):
    rows = []
    for _, r in lay.iterrows():
        raw = df[r["name"]]
        if r["kind"] == "flag":
            invalid = ((raw != "") & ~raw.isin(r["valid"].split("|"))).mean()
        else:
            invalid = (classify(df, r) == "X").mean()
        rows.append({"year": year, "field": r["name"], "start": r["start"], "end": r["end"],
                     "invalid_share": float(invalid), "pass": bool(invalid <= MAX_INVALID)})
    out = pd.DataFrame(rows)
    out.loc[out["field"] == "DOB_YY", "pass"] = bool((df["DOB_YY"] == str(year)).all())
    return out


def main(years):
    lay = load_layout()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    chk_path = PROCESSED / "layout_check.csv"
    old = pd.read_csv(chk_path) if chk_path.exists() else pd.DataFrame(columns=["year"])
    checks = [old[~old["year"].isin(years)]] if len(old) else []
    for y in years:
        n, L = parse_year(y, lay)
        df = read_raw(y)
        chk = layout_check(df, lay, y)
        del df
        checks.append(chk)
        bad = chk[~chk["pass"]]
        print(f"{y}: {n:,} records (line length {L}); layout failures: {len(bad)}")
        for _, b in bad.iterrows():
            print(f"   FAIL {b['field']} ({b['start']}-{b['end']}): {b['invalid_share']:.2%} invalid codes")
    allchk = pd.concat(checks, ignore_index=True)
    allchk.to_csv(chk_path, index=False)
    if not allchk[allchk["year"].isin(years)]["pass"].all():
        sys.exit("Layout check failed: fix code/layout_natality.csv against the user guide.")


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or YEARS)
