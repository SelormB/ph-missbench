#!/usr/bin/env bash
# Full natality build. About 3 x 300 MB download; parsing needs ~16 GB RAM.
set -euo pipefail
cd "$(dirname "$0")"
python code/01_fetch.py
python code/02_parse.py
python code/03_audit.py          # add --final after verification
python code/04_tasks.py          # add --freeze only after the author's verification
