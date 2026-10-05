#!/usr/bin/env bash
# Pre-release check. Files listed below *generate* draft banners, so markers inside them are tolerated;
# everything else, including secrets in every file, must be clean.
cd "$(dirname "$0")"
python code/publish_gate.py . --allow-draft-in code/publish_gate.py code/03_audit.py paper/build_manuscript.py tests/
