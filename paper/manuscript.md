> **DRAFT — generated from stats.json, not verified by the author. Rewrite in your own voice before submission. Do not cite.**

# PH-MissBench: rare-outcome prediction tasks with real, agency-documented missingness from U.S. birth records

**Selorm Buaka**, PhD Student, Applied Statistics and Research Methods, University of Northern Colorado, Greeley, Colorado, USA · ORCID 0009-0005-3991-4859 · othnielbuaka@gmail.com

## Abstract

Methods for missing data are usually compared on complete datasets with values masked by simulation, which fixes the missingness mechanism by design and leaves open how methods behave on the missingness that public health analysts actually face. PH-MissBench is an open benchmark of rare-outcome prediction tasks in which every predictor cell carries the missingness class documented by the data's producing agency: observed, not stated, structurally not applicable, or imputed by the agency. Agency-imputed values are restored to missing. The first module uses the National Center for Health Statistics natality public-use files for 2022–2024 and defines two tasks: early preterm birth (obstetric-estimate gestation under 34 weeks; test-year prevalence [VERIFY: run pipeline]) and very low birthweight (under 1,500 g; [VERIFY: run pipeline]), each with fixed temporal splits (train 2022–2023, test 2024), a missingness profile, and six baselines. Task files are hashed and frozen before any author-developed method is evaluated. Code, task definitions and split manifests are openly licensed; the records themselves are rebuilt from NCHS sources by the released scripts.

## Background and summary

[VERIFY: author to write — the gap (simulated masking in existing imputation benchmarks [CITE]), why rare outcomes (class imbalance makes missing-data errors costly), why agency-documented missingness (MAR/MNAR status is unknown in practice; agencies document what they did), and the intended users (methods researchers, public health analysts).]

## Methods

### Source data
NCHS Natality Public Use Files for data years 2022, 2023 and 2024 (fixed-width records, length 1,330). Files are downloaded by `01_fetch.py`, which records file size and SHA-256 for each file. Record positions follow the NCHS user guide for each year and are validated automatically: a field fails if more than 0.1% of its values fall outside the documented code set.

### Cohort
Records were restricted to U.S. residents, records whose plurality was reported rather than imputed by NCHS, and singletons. Cohort flow by year:

| Stage | 2022 | 2023 | 2024 |
|---|---:|---:|---:|
| All records | [VERIFY: run pipeline] | [VERIFY: run pipeline] | [VERIFY: run pipeline] |
| U.S. residents | [VERIFY: run pipeline] | [VERIFY: run pipeline] | [VERIFY: run pipeline] |
| Plurality not imputed | [VERIFY: run pipeline] | [VERIFY: run pipeline] | [VERIFY: run pipeline] |
| Singletons | [VERIFY: run pipeline] | [VERIFY: run pipeline] | [VERIFY: run pipeline] |

### Outcomes
Early preterm birth (EPTB, primary): obstetric estimate of gestation under 34 completed weeks. The obstetric estimate has been the NCHS standard since 2014 and is not imputed; the LMP-based combined gestation is not used because NCHS imputes some of its values. Very low birthweight (VLBW, secondary): birthweight under 1,500 g. Records with the outcome not stated are excluded from that task and counted.

### Predictors and prediction timepoint
Thirty-five pre-pregnancy and prenatal fields: maternal and paternal demographics, reproductive history and inter-pregnancy intervals, month prenatal care began, WIC, smoking before and in the first trimester, height, pre-pregnancy weight and BMI, pre-existing diabetes and hypertension, previous preterm birth, infertility treatment, previous cesarean, and maternal infections. Prenatal visit count, labor and delivery items, and infant items are excluded as leakage. [VERIFY: final ruling on gestational hypertension, eclampsia, gestational diabetes and second/third-trimester smoking.]

### Missingness classes
Each predictor cell is classed as observed (O), not stated (S), not applicable (A; e.g. birth intervals for a first birth), or imputed by NCHS (I; mother's age, race and marital status, identified by NCHS imputation flags). Classes S and I are missing in the task files; class A is encoded explicitly because it is known, not missing. The class of every cell is released alongside the values.

### Splits and evaluation
Training years 2022–2023 with a seeded 10% validation hold-out; test year 2024. A standard track uses a seeded 250,000-record training subsample so that computationally heavy methods can be compared; a full track uses all training records. The primary metric is AUPRC on the test year; secondary metrics are AUROC, Brier score, and calibration slope and intercept, with stratified bootstrap 95% intervals (1,000 replicates).

## Data records

Per task: `train`, `valid` and `test` Parquet files (row ID, outcome, predictor values), matching `*_mclass` files (missingness class per cell), and `task_card.json`; a shared split manifest; and `FREEZE.json` with SHA-256 hashes. Task sizes:

| Task | Train | Valid | Test | Train (standard) |
|---|---:|---:|---:|---:|
| EPTB | [VERIFY: run pipeline] | [VERIFY: run pipeline] | [VERIFY: run pipeline] | [VERIFY: run pipeline] |
| VLBW | [VERIFY: run pipeline] | [VERIFY: run pipeline] | [VERIFY: run pipeline] | [VERIFY: run pipeline] |

In the 2024 cohort, [VERIFY: run pipeline] of records had at least one predictor missing (mean [VERIFY: run pipeline] missing predictors per record). Item-level rates are in `docs/MISSINGNESS_AUDIT_NATALITY.md`.

## Technical validation

Record-layout validation, cohort-flow counts, outcome prevalence sanity bounds, and invalid-code counts are written to `qa_report.txt` on every build. [VERIFY: compare cohort counts and prevalences with NCHS final-births reports for each year and state agreement here.] Baselines were run only after the freeze and are refused by the code if any task file differs from its frozen hash.

### Baseline results (standard track)

Baseline results (standard track): [VERIFY: run pipeline]

B1 complete-case logistic regression; B2 mean/mode imputation with missingness indicators; B3 chained-equations single imputation; B4 iterative random-forest imputation; B5 LightGBM with native missing-value handling; B6 B5 plus agency missingness-class indicators.

## Usage notes

Users rebuild the tasks with `run_all.sh` (about 900 MB download). Methods must tune only on the validation split and report test metrics once per configuration. New methods should report both tracks where feasible.

## Limitations

See `docs/LIMITATIONS.md`. Principal: no ground truth for missing values; missingness mechanisms are unknown; NCHS flags imputation for only a few items; California marital status is withheld by statute; the public files carry no geography; pregnancy conditions are undated.

## Code availability

https://github.com/[user]/ph-missbench (MIT). Archived release: [10.5281/zenodo.pending].

## Data availability

Underlying records: NCHS Natality Public Use Files (public, subject to NCHS data-use restrictions). Task definitions, split manifests, missingness audit and results: CC BY 4.0, archived at [10.5281/zenodo.pending].

## Declarations

Funding: [VERIFY]. Competing interests: none declared [VERIFY]. Ethics: secondary analysis of de-identified public-use data; [VERIFY: confirm UNC IRB determination or exemption statement]. AI assistance: an AI assistant (Claude, Anthropic) was used to write pipeline code, documentation and a first draft of this manuscript; the author made all analytic decisions, verified every number against the pipeline outputs, and rewrote the text.

## References

[VERIFY: author to add — NCHS user guides 2022–2024; NVSR Births: Final Data for 2024; existing imputation benchmarks; missForest; MICE; LightGBM.]
