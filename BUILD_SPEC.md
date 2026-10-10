# PH-MissBench — Build Spec (v1.0, natality module)

> DRAFT — not verified by the author. Do not cite.

```
PROJECT:        PH-MissBench v1.0. Archetypes: benchmark (#4) + dataset descriptor (paper).
QUESTION:       How well do missing-data methods predict rare birth outcomes when the
                missingness is the real, agency-documented kind found in U.S. public health
                files, rather than simulated masking of complete data?

SOURCES:        NCHS Natality Public Use Files, U.S. births, data years 2022, 2023, 2024
                  Files:  https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/natality/
                          Nat2022us.zip, Nat2023us.zip, Nat2024us.zip (filenames confirmed on the
                          NCHS Vital Statistics Online page, 2026-10-07; zips use Deflate64)
                  Guides: .../Dataset_Documentation/DVS/natality/UserGuide2022.pdf,
                          UserGuide2023.pdf, UserGuide2024.pdf (2024 guide "Revised 2026")
                  Terms:  NCHS public-use data; data-use statement prohibits re-identification.
                          Raw files are NOT redistributed; users rebuild them with 01_fetch.py.
                  Accessed: logged per file in data/raw/PROVENANCE.txt
                Later modules (v1.x): YRBS, BRFSS, NHANES, NSDUH.

UNIT:           One live birth record (singleton, U.S. resident).

MEASURES:       Primary outcome  EPTB   = obstetric-estimate gestation (OEGest_Comb) < 34 weeks
                Secondary outcome VLBW  = birthweight (DBWT) < 1,500 g
                Predictors        pre-pregnancy + prenatal items only (see docs/TASK_SPEC_NATALITY.md)
                Missingness       each predictor cell classed as observed / not stated /
                                  not applicable (structural) / NCHS-imputed (restored to missing)
                Metrics           AUPRC (primary), AUROC, Brier score, calibration slope and
                                  intercept, all on the 2024 test year

OUTPUTS:        tasks/natality/{EPTB,VLBW}/  train/valid/test Parquet, split manifest, task card
                data/processed/missingness_audit.csv + docs/MISSINGNESS_AUDIT_NATALITY.md
                data/processed/qa_report.txt
                paper/stats.json (every number any document quotes)
                FREEZE.json (SHA-256 of every task file; written before any author method runs)
                Baseline results table (step 05, after freeze)

VENUES:         1. GitHub (code, task definitions, split manifests) + Zenodo DOI, Jan 2027
                2. Data-descriptor preprint (arXiv stat.ML or medRxiv epidemiology), Feb 2027
                3. Benchmark paper: journal data-descriptor or datasets/benchmarks track

VERIFY POINTS:  V1  Record-layout positions in code/layout_natality.csv. Automated check on the real
                    2022–2024 files: all 55 fields pass with 0.0000% invalid codes; resident birth
                    totals match NVSR 75(2) exactly. Author confirms against the user guides.
                V2  [RULED 2026-10-10: all excluded] Leakage rulings on pregnancy-onset items (gestational diabetes, gestational
                    hypertension, eclampsia, 2nd/3rd-trimester smoking) — see task spec §4
                V3  Treatment of NCHS-imputed values (default: restored to missing, flagged)
                V4  Training-size tracks (standard subsample vs full) and seeds
                V5  Cohort exclusions and the cohort-flow counts in qa_report.txt
                V6  Independence from MAKD-Natality: FREEZE.json written and committed before
                    MAKD is run on any task

LICENSE:        Code MIT; task definitions, manifests, docs, results CC BY 4.0, with attribution
                to NCHS as the source of the underlying records.

ASSUMPTIONS:    Author rulings received 2026-10-04: prenatal timepoint; singletons only;
                obstetric estimate; temporal split 2022–2023 train / 2024 test.
                V2 ruled 2026-10-10 (all five pregnancy-onset items excluded). V3 and V4 remain at their defaults.
```
