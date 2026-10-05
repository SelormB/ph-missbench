#!/usr/bin/env python3
"""Download the NCHS natality public-use files and log provenance.

Run on a machine with ordinary internet access (laptop or HPC login node).
Files are ~200-300 MB each and are not redistributed by this project.

    python code/01_fetch.py            # all years in natality_common.YEARS
    python code/01_fetch.py 2024       # one year
"""
import subprocess
import sys
import urllib.request

from natality_common import RAW, ROOT, YEARS, zip_url


def main(years):
    RAW.mkdir(parents=True, exist_ok=True)
    for y in years:
        url = zip_url(y)
        dest = RAW / url.rsplit("/", 1)[1]
        if dest.exists():
            print(f"[skip] {dest.name} already present")
            continue
        print(f"[get]  {url}")
        tmp = dest.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(dest)
        subprocess.run([sys.executable, str(ROOT / "code" / "provenance.py"), str(dest), url,
                        "--log", str(RAW / "PROVENANCE.txt"),
                        "--note", "NCHS natality public-use file, direct FTP-over-HTTPS link"],
                       check=True)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or YEARS)
