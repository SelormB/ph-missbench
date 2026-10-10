#!/usr/bin/env bash
# Render the manuscript PDF (pandoc -> HTML -> wkhtmltopdf). Run after build_manuscript.py.
#   ./render_pdf.sh            draft: watermark, PH-MissBench_preprint_DRAFT.pdf
#   ./render_pdf.sh --final    no watermark, PH-MissBench_preprint.pdf (only after author verification)
set -euo pipefail
cd "$(dirname "$0")"
css=(--css preprint.css --css draft.css); out=PH-MissBench_preprint_DRAFT.pdf
if [ "${1:-}" = "--final" ]; then css=(--css preprint.css); out=PH-MissBench_preprint.pdf; fi
pandoc manuscript.md -s --embed-resources --resource-path=. "${css[@]}" --metadata pagetitle="PH-MissBench preprint" -o manuscript.html
wkhtmltopdf --quiet --enable-local-file-access -s Letter -T 0.75in -B 0.75in -L 0.8in -R 0.8in manuscript.html "$out"
rm -f manuscript.html
echo "wrote paper/$out"
