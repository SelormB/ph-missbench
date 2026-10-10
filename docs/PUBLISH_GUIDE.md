# Publish guide — PH-MissBench v1.0 (natality)

Do these steps only after every line of `docs/VERIFY_CHECKLIST.md` is initialled and `./gate.sh` passes. Target: GitHub + Zenodo in January 2027, preprint in February 2027.

## 0. Final build (on your Mac or HPC)

```bash
./run_all.sh                                # fetch, parse, audit, tasks
python code/04_tasks.py --freeze            # ONCE; then commit FREEZE.json before anything else
python code/05_baselines.py --track standard
python code/05_baselines.py --track full    # HPC; B4 skipped automatically
python paper/build_manuscript.py --final
./gate.sh
```

Commit `FREEZE.json` and tag it `tasks-frozen-v1.0` **before** running MAKD-Natality on any task. That commit's date is your evidence of independence.

## 1. GitHub

1. Create an empty repository named `ph-missbench` at github.com/new (public, no README).
2. In the project folder:
   ```bash
   git init -b main && git add -A
   git commit -m "PH-MissBench v1.0.0: natality module"
   git remote add origin https://github.com/<you>/ph-missbench.git
   git push -u origin main
   ```
   `.gitignore` already keeps the NCHS zips and every Parquet file out of the repository. The split manifest (`split_manifest.csv.gz`) is committed if it is under 100 MB; otherwise it goes to Zenodo only.
3. Releases → Draft a new release → tag `v1.0.0` → title "PH-MissBench v1.0.0 — natality module" → notes: the two tasks, years, the freeze date, and a pointer to `docs/TASK_SPEC_NATALITY.md`.

## 2. Zenodo (DOI)

1. Log in to zenodo.org with your ORCID (0009-0005-3991-4859).
2. Account → GitHub → turn on `ph-missbench`. Re-publish the v1.0.0 release (or create it after turning this on); Zenodo mints the DOI within minutes.
3. Edit the record:
   - Upload type: Dataset
   - Creator: Buaka, Selorm (ORCID attached), University of Northern Colorado
   - License: CC BY 4.0
   - Keywords: missing data; benchmark; natality; preterm birth; low birthweight; public health
   - Related identifier: the GitHub URL ("is supplemented by")
4. Upload `split_manifest.csv.gz`, `missingness_audit.csv`, `missingness_vs_outcome.csv` and the baseline CSVs as extra files if they are not in the release archive.
5. Paste the DOI into `CITATION.cff`, the README status line, and both `[10.5281/zenodo.pending]` placeholders in the manuscript; rebuild the manuscript.

## 3. Preprint — arXiv (recommended: stat.ML, cross-list stat.AP)

1. Build the PDF: `pandoc paper/manuscript.md -o paper/manuscript.pdf` (or export the .docx to PDF from Word).
2. If this is your first stat.ML submission, arXiv may ask for an endorsement. Request one from a faculty member who has posted in stat.ML or stat.AP, with this note:
   > "I'm submitting a data-descriptor paper for PH-MissBench, an open benchmark of rare-outcome prediction tasks with agency-documented missingness from NCHS birth records (DOI: …). Would you be willing to endorse me for stat.ML? My endorsement code is …"
3. At arxiv.org/submit:
   - Upload the PDF.
   - Title as in the manuscript; author "Selorm Buaka".
   - Paste the abstract from the manuscript.
   - Primary category stat.ML; cross-list stat.AP; license CC BY 4.0.
   - Comments: "Code: github.com/<you>/ph-missbench; data DOI: …".
4. Submit. The paper appears at the next announcement after moderation, usually one to three days. Log the arXiv ID.

**Alternative: medRxiv (Epidemiology).** The declarations are already in the manuscript: ethics, funding, competing interests, data availability and AI assistance. Confirm the IRB statement with UNC first; public-use secondary data is usually "not human subjects research", but medRxiv wants your institution's wording.

## 4. Evidence log (the same day as each step)

| Date | Artifact | Venue | Identifier | Status |
|---|---|---|---|---|
| | PH-MissBench v1.0.0 code | GitHub | URL | released |
| | PH-MissBench v1.0.0 | Zenodo | DOI | published |
| | Data descriptor | arXiv | arXiv ID | posted |
