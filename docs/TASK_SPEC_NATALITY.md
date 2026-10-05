# Task specification — PH-MissBench natality module (v1.0)

> DRAFT — not verified by the author. Items tagged [V#] are open rulings listed in `BUILD_SPEC.md`.

## 1. Purpose

Two rare-outcome prediction tasks in which the predictors carry the missingness that actually occurs in U.S. birth certificate data, recorded at the level of each cell. Methods are compared on how well they predict the outcome, not on how well they reconstruct values that cannot be checked.

## 2. Data and cohort

| | |
|---|---|
| Source | NCHS Natality Public Use Files, data years 2022, 2023, 2024 (record length 1,330) |
| Unit | One live-birth record |
| Inclusion | U.S. resident (RESTATUS ≠ 4); plurality reported and not imputed by NCHS (IMP_PLUR blank); singleton (DPLURAL = 1) |
| Task-level exclusion | Outcome itself not stated (OEGest_Comb = 99 for EPTB; DBWT = 9999 for VLBW). Counted and reported, never imputed. |
| Record ID | `<year>-<line number in the NCHS file>`; stable given the file checksum in `data/raw/PROVENANCE.txt` |

Natality is a census of registered births, so no sampling weights or design variables apply. This is why it can serve as the first module; the survey modules (v1.x) will need design-aware splits and weighted metrics.

## 3. Outcomes

| Task | Definition | Field | Role |
|---|---|---|---|
| **EPTB** | Obstetric-estimate gestation < 34 completed weeks | OEGest_Comb | Primary |
| **VLBW** | Birthweight < 1,500 g | DBWT | Secondary |

The obstetric estimate has been the NCHS standard since 2014. The LMP-based combined gestation (COMBGEST) is not used, because NCHS imputes some of its values (COMPGST_IMP), and that would contaminate the outcome.

## 4. Predictors — prediction timepoint: pre-pregnancy and prenatal

Included only if the information is plausibly available during pregnancy, well before delivery.

**Included (35 fields):** mother's age, nativity, race, Hispanic origin, marital status and education; father's age and education; prior live births, prior deaths and other pregnancy outcomes; the three inter-pregnancy intervals; month prenatal care began; WIC; cigarettes per day in the 3 months before pregnancy and in the 1st trimester; height, pre-pregnancy BMI and weight; pre-pregnancy diabetes and hypertension; previous preterm birth; infertility treatment, fertility drugs and ART; previous cesarean and number of cesareans; gonorrhea, syphilis, chlamydia, hepatitis B and C; payment source recode. The full list with record positions is in `code/layout_natality.csv`.

**Excluded for leakage:**
- PREVIS (prenatal visits) — counted through delivery, so earlier births mechanically have fewer visits.
- Infant sex, and all labor, delivery and newborn items.

**Pending your ruling [V2] (default: excluded):**

| Field | Concern |
|---|---|
| RF_GHYPE, RF_EHYPE | Gestational hypertension and eclampsia are frequent reasons for *indicated* preterm delivery. They are recorded at delivery with no diagnosis date, so including them partly encodes the outcome. |
| RF_GDIAB | Usually diagnosed at 24–28 weeks. Less leakage risk, but the diagnosis is undated. |
| CIG_2, CIG_3 | For a birth before 34 weeks, the 3rd trimester is truncated and partly unobserved. CIG_2 is the borderline case. |

A reasonable alternative is a second "late-pregnancy" predictor tier that includes these, reported separately. Adding a field is a one-line change (`PENDING_INCLUDED` in `code/natality_common.py`) and must happen before the freeze.

## 5. Missingness model — what the benchmark preserves

Every predictor cell is assigned a class, shipped in `*_mclass.parquet` alongside the values:

| Class | Meaning | Value in task file |
|---|---|---|
| O | Observed | the value |
| S | Not stated (agency "unknown" code, or blank where blank means unknown) | missing |
| A | Not applicable — structural, e.g. interval 888 = first birth, X = no infertility treatment | categorical: `NA_STRUCT`; numeric: missing plus `<field>__na_struct = 1` |
| I | Imputed by NCHS (flag set) — **restored to missing** [V3] | missing |

NCHS imputation flags used: MAGE_IMPFLG (mother's age), MRACEIMP (mother's race, assigned from the father's race or a preceding record), MAR_IMP (marital status, inferred from whether the father's age is reported), and IMP_PLUR (plurality; used as a cohort exclusion). IMP_SEX and COMPGST_IMP relate to excluded fields and are audited but not used.

Why restore them: an NCHS hot-deck or rule-based fill is itself a missing-data method. Leaving those values in would let every method in the benchmark silently inherit it, and the tasks would understate the real missingness.

Known blind spot: from 2017 on, NCHS withholds record-level marital status for California births by state statute. These cells appear as blank or imputed, and the public file has no geography to separate them, so they are classed with S/I. The limitation is recorded in `docs/LIMITATIONS.md`.

## 6. Splits

| Split | Years | Size |
|---|---|---|
| train | 2022–2023, minus validation | all eligible records ("full track") |
| train, standard track | seeded subsample of train | 250,000 records [V4] |
| valid | seeded 10% of 2022–2023 | — |
| test | 2024 | all eligible records |

Splits are assigned once at the cohort level (seed 20261004), so EPTB and VLBW share them. The temporal test year measures drift as well as accuracy. The standard track exists because some imputation methods (missForest, MICE with many items) do not scale to roughly 6 million rows. The full track is reported separately.

## 7. Evaluation

- **Primary metric:** AUPRC on the 2024 test set. For rare outcomes it is more informative than AUROC.
- **Secondary metrics:** AUROC, Brier score, calibration slope and intercept.
- **Uncertainty:** 1,000 stratified bootstrap replicates of the test set (seeded), with 95% intervals.
- Hyperparameters are tuned on valid only. Test labels are used once per submitted configuration.

**Baselines (step 05, after the freeze):**
1. B1 — Logistic regression trained on complete cases (missing test cells filled with training medians/modes)
2. B2 — Mean/mode imputation plus missingness indicators, logistic regression
3. B3 — Chained-equations *single* imputation (scikit-learn IterativeImputer, Bayesian ridge), logistic regression. This is not full MICE with pooling across multiple imputations; that is a v1.1 addition.
4. B4 — missForest-style iterative random-forest imputation, logistic regression (standard track only)
5. B5 — LightGBM with native missing-value handling, early stopping on valid
6. B6 — B5 plus indicators for the agency missingness class (S, I) of each field, which tests whether knowing the class helps

The B3 and B4 imputers are fit on a seeded 50,000-row subsample of train and then applied to all rows. `05_baselines.py` refuses to run unless every hash in FREEZE.json matches.

## 8. Freeze and independence

`python code/04_tasks.py --freeze` writes `FREEZE.json` containing SHA-256 hashes of every task file, the split manifest and the layout. It refuses to run a second time. FREEZE.json is committed and tagged before MAKD-Natality, or any other author-developed method, is evaluated on these tasks. Any later change to the tasks is a new benchmark version, not an edit.
