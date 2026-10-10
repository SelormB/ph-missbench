> **Status: v1.0.0-draft (2026-10-10).** Natality tasks frozen (`tasks-frozen-v1.0`); standard-track baselines complete; preprint in preparation. Repository: https://github.com/SelormB/ph-missbench

# PH-MissBench

An open benchmark of rare-outcome prediction tasks built from U.S. public health files, in which the predictors carry **real, agency-documented missingness** rather than simulated masking. Every cell is labelled observed, not stated, structurally not applicable, or imputed by the agency, and agency-imputed values are restored to missing.

v1.0 ships the **natality module**:

| Task | Outcome | Train | Test |
|---|---|---|---|
| EPTB (primary) | Early preterm birth, obstetric estimate < 34 weeks | 2022–2023 | 2024 |
| VLBW (secondary) | Birthweight < 1,500 g | 2022–2023 | 2024 |

Survey modules (YRBS, BRFSS, NHANES, NSDUH) follow in v1.x; see `docs/NEXT_STEPS.md`.

## Build the tasks

The NCHS files are not redistributed. You rebuild the tasks from them:

```bash
pip install -r requirements.txt
./run_all.sh        # fetch -> parse + layout check -> missingness audit -> tasks
```

`01_fetch.py` downloads about 900 MB and logs SHA-256 hashes to `data/raw/PROVENANCE.txt`. `02_parse.py` stops if any field's record-layout position yields invalid codes. Read `data/processed/qa_report.txt` before using the outputs. On a cluster, see `hpc/natality.sbatch`.

## What you get

- `tasks/natality/<TASK>/{train,valid,test}.parquet` — `row_id`, `y`, predictor values
- `tasks/natality/<TASK>/*_mclass.parquet` — missingness class per cell (O/S/A/I)
- `tasks/natality/<TASK>/task_card.json` — definitions, sizes, metrics, seed
- `tasks/natality/split_manifest.csv.gz` — split and standard-track membership for every record
- `docs/MISSINGNESS_AUDIT_NATALITY.md` — item-level missingness and imputation rates, plus outcome prevalence by missingness
- `FREEZE.json` — hashes of the frozen task files

## Documentation

`BUILD_SPEC.md` · `docs/TASK_SPEC_NATALITY.md` · `docs/CODEBOOK.md` · `docs/LIMITATIONS.md` · `docs/VERIFY_CHECKLIST.md`

## Source

National Center for Health Statistics. Natality Public Use Files, 2022–2024. Users must follow the NCHS data-use restrictions; no attempt may be made to identify any individual.

## License and citation

Code MIT; documentation, task definitions, manifests and results CC BY 4.0. Cite via `CITATION.cff` (DOI pending).

Maintainer: Selorm Buaka, PhD Student, University of Northern Colorado · ORCID 0009-0005-3991-4859
