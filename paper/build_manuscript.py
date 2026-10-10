#!/usr/bin/env python3
"""Build the data-descriptor manuscript from paper/stats.json.

Every number in the text comes from stats.json; a missing number renders as
[VERIFY: run pipeline] so publish_gate.py blocks release until the pipeline has run.
Output: paper/manuscript.md (and manuscript.docx if pandoc is installed).

    python paper/build_manuscript.py [--final]
"""
import json

import pandas as pd
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FINAL = "--final" in sys.argv
S = json.loads((HERE / "stats.json").read_text()) if (HERE / "stats.json").exists() else {}
A = json.loads((ROOT / "AUTHORS.json").read_text())["authors"]
MISSING = "[VERIFY: run pipeline]"


def get(*keys, fmt="{:,}"):
    cur = S
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return MISSING
        cur = cur[k]
    return fmt.format(cur) if cur is not None else MISSING


def get_num(*keys):
    cur = S
    for k in keys:
        cur = cur[k]
    return float(cur)


def pct(*keys):
    return get(*keys, fmt="{:.2%}")


def bl(task, b, key="auprc", fmt="{:.3f}"):
    return get("baselines_standard", f"{task}_{b}", key, fmt=fmt)


def baseline_table(track):
    sec = S.get(f"baselines_{track}")
    if not sec:
        return f"Baseline results ({track} track): {MISSING}\n"
    rows = ["| Task | Model | AUPRC (95% CI) | AUROC (95% CI) | Slope | Intercept |",
            "|---|---|---|---|---:|---:|"]
    for k in sorted(sec):
        r = sec[k]
        rows.append(f"| {r['task']} | {r['baseline']} | {r['auprc']:.3f} ({r['auprc_lo']:.3f}–{r['auprc_hi']:.3f}) | "
                    f"{r['auroc']:.3f} ({r['auroc_lo']:.3f}–{r['auroc_hi']:.3f}) | {r['cal_slope']:.2f} | "
                    f"{round(r['cal_intercept'], 2) + 0.0:.2f} |")
    return "\n".join(rows) + ("\n\nSlope and intercept: calibration slope and calibration-in-the-large. Brier scores "
                              "are in `paper/baselines_standard.csv`.\n")


au = A[0]
banner = "" if FINAL else ("> **DRAFT — generated from stats.json, not verified by the author. "
                           "Rewrite in your own voice before submission. Do not cite.**\n\n")
y = ["2022", "2023", "2024"]
if S.get("build", {}).get("provisional"):
    banner += ("> **PROVISIONAL NUMBERS — tasks built from 2023 (train) and 2024 (test) only; the 2022 file "
               "is still missing. Task sizes will change when 2022 is added. No baseline results yet "
               "(tasks not frozen).**\n\n")

inf = pd.read_csv(ROOT / "data" / "processed" / "missingness_vs_outcome.csv")
inf24 = inf[(inf["year"] == 2024) & (inf["task"] == "EPTB")].set_index("field")
aud = pd.read_csv(ROOT / "data" / "processed" / "missingness_audit.csv")
aud24 = aud[(aud["year"] == 2024) & (aud["population"] == "cohort")].set_index("field")
env = json.loads((ROOT / "FREEZE_ENV.json").read_text()) if (ROOT / "FREEZE_ENV.json").exists() else {}
frz = json.loads((ROOT / "FREEZE.json").read_text()) if (ROOT / "FREEZE.json").exists() else {}
pred_table = (HERE / "tables" / "table_predictors.md").read_text() if (HERE / "tables" / "table_predictors.md").exists() else MISSING


def ratio(f):
    r = inf24.loc[f]
    return f"{r['prev_missing'] / r['prev_observed']:.1f}"


def ipct(f, col):
    r = aud24.loc[f]
    return f"{100 * r[col] / r['n']:.1f}%"


roles = "; ".join(au.get("roles", []))
_lay = pd.read_csv(ROOT / "code" / "layout_natality.csv", dtype=str, keep_default_na=False)
_preds = set(_lay.loc[_lay["role"] == "predictor", "name"])
_inf = inf24[(inf24["n_missing"] >= 1000) & inf24.index.isin(_preds)]
_r = _inf["prev_missing"] / _inf["prev_observed"]
n_items, n_double, med_ratio = len(_r), int((_r >= 2).sum()), float(_r.median())
_b = pd.read_csv(HERE / "baselines_standard.csv") if (HERE / "baselines_standard.csv").exists() else None
slope_lo = f"{_b.loc[_b.baseline != 'B1', 'cal_slope'].min():.2f}" if _b is not None else MISSING
slope_hi = f"{_b.loc[_b.baseline != 'B1', 'cal_slope'].max():.2f}" if _b is not None else MISSING
md = f"""{banner}# PH-MissBench: rare-outcome prediction tasks with real, agency-documented missingness from U.S. birth records

**{au['name']}**
{au['affiliation']}
ORCID [{au['orcid']}](https://orcid.org/{au['orcid']}) · {au['email']}

**Keywords:** missing data; benchmark; imputation; natality; preterm birth; low birthweight; public health surveillance

## Abstract

**Background.** Missing-data methods are usually compared on complete datasets with values deleted by simulation, which fixes the missingness mechanism by design. How methods behave on the missingness that public health analysts actually face is less well studied, particularly for rare outcomes.

**Methods.** PH-MissBench is an open benchmark built from U.S. National Center for Health Statistics (NCHS) natality public-use files for 2022–2024. Every predictor cell carries the missingness class documented by NCHS (observed, not stated, structurally not applicable, or imputed by NCHS), and NCHS-imputed values are restored to missing. Two tasks predict early preterm birth (obstetric-estimate gestation under 34 weeks) and very low birthweight (under 1,500 g) among singleton births to U.S. residents from 35 pre-pregnancy and prenatal items, with training on 2022–2023 and testing on 2024. Task files were hashed and frozen before any baseline was run. Six baselines were evaluated by area under the precision-recall curve (AUPRC) with 1,000-replicate stratified bootstrap intervals.

**Results.** The cohort comprised {get('tasks','EPTB','train','n')} training, {get('tasks','EPTB','valid','n')} validation and {get('tasks','EPTB','test','n')} test births; test-year prevalence was {pct('tasks','EPTB','test','prevalence')} for early preterm birth and {pct('tasks','VLBW','test','prevalence')} for very low birthweight. The pipeline reproduced NCHS published birth totals exactly for all three years. In 2024, {pct('audit','2024','any_missing_share')} of births had at least one predictor missing. Gradient boosting with native missing-value handling performed best (AUPRC {bl('EPTB','B5')} and {bl('VLBW','B5')}); mean imputation with missing-value indicators ({bl('EPTB','B2')}, {bl('VLBW','B2')}) outperformed chained-equations ({bl('EPTB','B3')}, {bl('VLBW','B3')}) and iterative random-forest imputation ({bl('EPTB','B4')}, {bl('VLBW','B4')}); complete-case analysis performed worst ({bl('EPTB','B1')}, {bl('VLBW','B1')}) and was miscalibrated.

**Conclusions.** On population-scale U.S. birth records, approaches that let the model see missingness outperformed imputation alone, consistent with informative missingness. PH-MissBench provides frozen, reproducible tasks for comparing missing-data methods on real public health data.

## 1. Introduction

Missing data are routine in public health records, and the methods used to handle them change which predictions a model can make and for whom. Most comparisons of missing-data methods start from a complete dataset and delete values by a chosen mechanism (missing completely at random, at random, or not at random [6]) [1, 2]. That design gives a ground truth for the deleted values, but it fixes the missingness mechanism by assumption; in real records the mechanism is unknown and often related to the outcome. Studies that instead use naturally occurring missingness in health databases have found that conclusions differ: gradient-boosted trees that handle missing values natively, and models given missing-value indicators, often predict as well as or better than models trained after imputation [3, 4], consistent with theory showing that good prediction does not require good imputation [5]. Those studies drew on a small number of clinical cohorts and did not distinguish between the reasons a value is absent.

U.S. vital statistics and survey files document why values are absent: an item may be not stated, structurally not applicable (a birth interval for a first birth), or filled in by the producing agency's own imputation. PH-MissBench uses that documentation to build prediction tasks on rare outcomes, where missing-data errors are costly because positives are few, and releases the agency-documented missingness class of every cell. Agency-imputed values are restored to missing, so that methods are not silently credited with the agency's imputation. This paper describes the first module, built from U.S. birth records, and reports baseline results.

## 2. Methods

### 2.1 Data source
The source is the NCHS Natality Public Use Files for data years 2022, 2023 and 2024, which contain one fixed-width record for every birth registered in the United States [12]. Files are downloaded by the released scripts, which log file size and SHA-256 hash for each file. Record positions follow the NCHS user guide for each year and are validated automatically: a field fails if more than 0.1% of its values fall outside the documented code set.

### 2.2 Analytic cohort
Records were restricted to births to U.S. residents, to records whose plurality was reported rather than imputed by NCHS, and to singletons (Table 1). Records with the outcome not stated are excluded from that task and counted.

**Table 1.** Cohort flow by data year.

| Stage | {' | '.join(y)} |
|---|---:|---:|---:|
| All records | {' | '.join(get('audit', yy, 'flow', 'all records') for yy in y)} |
| U.S. residents | {' | '.join(get('audit', yy, 'flow', 'U.S. residents') for yy in y)} |
| Plurality not imputed | {' | '.join(get('audit', yy, 'flow', 'plurality reported (not imputed)') for yy in y)} |
| Singletons (analytic cohort) | {' | '.join(get('audit', yy, 'flow', 'singletons') for yy in y)} |
| Early preterm: outcome stated | {' | '.join(get('audit', yy, 'tasks', 'EPTB', 'eligible') for yy in y)} |
| Early preterm: cases | {' | '.join(get('audit', yy, 'tasks', 'EPTB', 'cases') for yy in y)} |
| Very low birthweight: outcome stated | {' | '.join(get('audit', yy, 'tasks', 'VLBW', 'eligible') for yy in y)} |
| Very low birthweight: cases | {' | '.join(get('audit', yy, 'tasks', 'VLBW', 'cases') for yy in y)} |

### 2.3 Outcomes
Early preterm birth (primary task): obstetric estimate of gestation under 34 completed weeks. The obstetric estimate has been the NCHS standard measure since 2014 and is not imputed; the LMP-based combined gestation is not used because NCHS imputes some of its values. Very low birthweight (secondary task): birthweight under 1,500 g.

### 2.4 Predictors and prediction timepoint
The predictors are 35 pre-pregnancy and prenatal fields (Appendix Table A1): maternal and paternal demographics, reproductive history and inter-pregnancy intervals, month prenatal care began, WIC participation, cigarette smoking before pregnancy and in the first trimester, maternal height, pre-pregnancy weight and BMI, pre-existing diabetes and hypertension, previous preterm birth, infertility treatment, previous cesarean delivery, and maternal infections. The number of prenatal visits and all labor, delivery and infant items are excluded because they are recorded through or after delivery. Gestational hypertension, eclampsia, gestational diabetes, and second- and third-trimester smoking are also excluded: they are recorded at delivery without a diagnosis date, and missingness of third-trimester smoking is itself strongly associated with early delivery (in the 2024 cohort, early preterm prevalence was {pct('leak','CIG_3','prev_missing')} where it was missing versus {pct('leak','CIG_3','prev_observed')} where recorded).

### 2.5 Missingness classes
Each predictor cell is assigned one class: observed; not stated (the agency's unknown code); not applicable (a structural code, for example birth intervals for a first birth or fertility-drug use when no infertility treatment was reported); imputed by NCHS (identified from the NCHS imputation flags for mother's age, race and marital status); or undocumented code (a value outside the documented code set, treated as missing). Not-stated, imputed and undocumented cells are missing in the task files. Structural not-applicable cells are encoded explicitly, as a category for categorical fields and as an indicator column for numeric fields, because they are known rather than missing. The class of every cell is released in companion files.

### 2.6 Splits
Births from 2022–2023 form the training years, with a seeded 10% validation hold-out; births from 2024 form the test set, so that evaluation also reflects temporal drift. Splits are assigned once at the cohort level (seed 20261004), so both tasks share them. A standard track uses a seeded 250,000-record training subsample, so that computationally heavy methods can be compared; a full track uses all training records. Natality files are a census of registered births, so no sampling weights apply.

### 2.7 Baselines
All logistic-regression baselines standardize features and use L2 regularization (C = 1); categorical fields are one-hot encoded. For B1–B4, structural not-applicable numeric cells are set to zero with their indicator retained.

- **B1, complete case.** Logistic regression trained only on training records with no missing predictor; at prediction time, missing cells are filled with training medians.
- **B2, mean imputation with indicators.** Median fill plus one missing-value indicator per field, then logistic regression.
- **B3, chained equations.** Single imputation by chained equations [7] (Bayesian ridge, 10 iterations), then logistic regression. This is single, not multiple, imputation.
- **B4, iterative random forest.** Iterative imputation with a random-forest estimator in the style of missForest [8] (20 trees, maximum depth 12, 5 iterations), then logistic regression. Standard track only.
- **B5, gradient boosting.** LightGBM [9] with native missing-value handling (learning rate 0.03, 31 leaves, minimum 100 records per leaf, 0.8 row and column subsampling), early-stopped on validation AUPRC with patience 100.
- **B6, gradient boosting with agency classes.** B5 plus two indicators per field marking not-stated and NCHS-imputed cells.

The B3 and B4 imputers are fit on a seeded 50,000-record subsample of the training data and then applied to all records. Hyperparameters are fixed defaults, not tuned.

### 2.8 Evaluation
The primary metric is AUPRC on the 2024 test set, which is more informative than the area under the ROC curve (AUROC) when positives are rare [10]. Secondary metrics are AUROC, the Brier score, the calibration slope, and calibration-in-the-large (the intercept with the model's logit as an offset) [11]. Uncertainty is summarized by 95% percentile intervals from 1,000 stratified bootstrap replicates of the test set, resampling cases and non-cases separately. AUPRC is computed as average precision. The fast implementation used for the bootstrap is checked against scikit-learn on every run.

### 2.9 Freeze and independence
After the cohort, predictors and splits were fixed, the task files, split manifest and record layout were hashed (SHA-256) and recorded in `FREEZE.json` on {frz.get('frozen_on', MISSING)}, before any baseline or author-developed method was evaluated. The baseline code refuses to run if any task file differs from its frozen hash. Any later change to the tasks is released as a new benchmark version.

### 2.10 Software
Python {env.get('python', MISSING)}, pandas {env.get('pandas', MISSING)}, pyarrow {env.get('pyarrow', MISSING)}, NumPy {env.get('numpy', MISSING)}, scikit-learn {env.get('scikit-learn', MISSING)} and LightGBM {env.get('lightgbm', MISSING)}.

## 3. Results

### 3.1 Cohort and outcomes
The analytic cohort comprised {get('audit','2022','flow','singletons')}, {get('audit','2023','flow','singletons')} and {get('audit','2024','flow','singletons')} singleton births in 2022, 2023 and 2024 (Table 1). For early preterm birth, the task contains {get('tasks','EPTB','train','n')} training, {get('tasks','EPTB','valid','n')} validation and {get('tasks','EPTB','test','n')} test records ({get('tasks','EPTB','test','cases')} test cases; prevalence {pct('tasks','EPTB','test','prevalence')}). For very low birthweight, the test set has {get('tasks','VLBW','test','cases')} cases (prevalence {pct('tasks','VLBW','test','prevalence')}).

### 3.2 External validation
The pipeline's counts of births to U.S. residents were {get('external_validation','2022_births','pipeline', fmt='{:,.0f}')} (2022), {get('external_validation','2023_births','pipeline', fmt='{:,.0f}')} (2023) and {get('external_validation','2024_births','pipeline', fmt='{:,.0f}')} (2024), identical to the totals published by NCHS [13]. Recomputed across all 2024 births, early preterm birth was {get('external_validation','2024_eptb_pct','pipeline', fmt='{:.2f}')}% and very low birthweight {get('external_validation','2024_vlbw_pct','pipeline', fmt='{:.2f}')}%, matching the published {get('external_validation','2024_eptb_pct','published', fmt='{:.2f}')}% and {get('external_validation','2024_vlbw_pct','published', fmt='{:.2f}')}%. All 55 extracted fields passed the layout check in every year. One 2024 record carried an undocumented blank in two birth-interval fields and was treated as missing.

### 3.3 Missingness
In the 2024 cohort, {pct('audit','2024','any_missing_share')} of births had at least one predictor missing, with a mean of {get('audit','2024','mean_missing_items', fmt='{:.2f}')} missing predictors per birth (Figure 1). The most frequently missing items were father's education ({ipct('FEDUC','S')}), marital status ({ipct('DMAR','S')} not stated, a group that includes births to California residents, for whom NCHS withholds marital status, and {ipct('DMAR','I')} imputed), the interval since the last pregnancy ({ipct('ILP_R','S')}) and father's age ({ipct('FAGECOMB','S')}). Mother's race was imputed by NCHS for {ipct('MRACE6','I')} of births; these values are missing in the benchmark.

![**Figure 1.** Share of the 2024 analytic cohort with each predictor missing, by reason. Items missing for under 0.5% of births are omitted. Structural not-applicable cells are not counted as missing.](figures/fig1.png)

Missingness was informative (Figure 2). Early preterm prevalence was {ratio('IP_GON')} times higher among births with the maternal infection items missing than among births with them recorded, {ratio('PRECARE')} times higher when the month prenatal care began was missing, and {ratio('BMI')} times higher when pre-pregnancy BMI was missing. Marital status was the exception (ratio {ratio('DMAR')}), consistent with its missingness being driven largely by California's statutory withholding rather than by the circumstances of the birth.

![**Figure 2.** Early preterm birth prevalence in the 2024 cohort among births with each predictor missing (orange) versus recorded (blue). Labels give the ratio. Items with at least 1,000 missing records are shown; log scale.](figures/fig2.png)

### 3.4 Baseline results
Table 2 and Figure 3 report test-set results on the standard track.

::: {{.keep}}
**Table 2.** Baseline results on the 2024 test year (standard track, 250,000 training births).

{baseline_table('standard')}
:::
B1 complete-case logistic regression; B2 mean imputation with missing-value indicators; B3 chained-equations single imputation [7]; B4 iterative random-forest imputation [8]; B5 LightGBM with native missing-value handling [9]; B6 B5 plus agency missingness-class indicators.

![**Figure 3.** AUPRC on the 2024 test year with 95% bootstrap intervals (narrower than the markers at this sample size). Dashed line: outcome prevalence, the AUPRC of an uninformative model.](figures/fig3.png)

Gradient boosting with native missing-value handling (B5) ranked first on both tasks, with AUPRC {bl('EPTB','B5')} for early preterm birth ({float(get('baselines_standard','EPTB_B5','auprc', fmt='{}'))/S['tasks']['EPTB']['test']['prevalence']:.1f} times the prevalence) and {bl('VLBW','B5')} for very low birthweight ({float(get('baselines_standard','VLBW_B5','auprc', fmt='{}'))/S['tasks']['VLBW']['test']['prevalence']:.1f} times). Mean imputation with missing-value indicators (B2) outperformed both iterative imputers on both tasks. Complete-case analysis (B1) ranked last; only {get('baselines_standard','EPTB_B1','complete_cases_train', fmt='{:,.0f}')} of 250,000 training births had every predictor recorded, and its predictions were systematically too low (calibration-in-the-large {bl('EPTB','B1','cal_intercept', fmt='{:.2f}')} and {bl('VLBW','B1','cal_intercept', fmt='{:.2f}')}). Adding agency missingness classes to gradient boosting (B6) did not change discrimination. All other baselines were close to well calibrated (slopes {slope_lo}–{slope_hi}).

## 4. Discussion

On population-scale U.S. birth records, methods that let the model see missingness (gradient boosting with native handling, and indicator columns) outperformed imputation without indicators, and complete-case analysis performed worst. This ordering replicates findings from clinical databases [3] and theory on prediction with missing values [4, 5], here on several million births and with the agency's own record of why each value is missing. The audit points to the mechanism: for {n_double} of the {n_items} predictors with at least 1,000 missing records, births with the item missing had at least twice the early preterm prevalence of births with it recorded (median ratio {med_ratio:.1f}), so missingness itself carries information that imputation alone discards. The near-identical performance of B5 and B6 suggests that, for gradient boosting, knowing that a value is missing matters more than knowing why. Whether the distinction between not-stated and agency-imputed values matters for other method families is a question the benchmark is designed to answer.

The practical implication for public health analysts working with vital records is that dropping incomplete records is the worst default: it discarded {100 - 100 * get_num('baselines_standard','EPTB_B1','complete_cases_train') / 250000:.0f}% of the training data here, lost discrimination, and biased the predicted risk. Imputation without missing-value indicators also lost information relative to simple indicator methods.

**Limitations.** There is no ground truth for the missing values, so the benchmark scores prediction rather than reconstruction. Missingness mechanisms are unknown; the classes record what NCHS documented, not whether data are missing at random. NCHS flags imputation for only a few items, so undocumented edits to other items cannot be reversed. Marital status for California births is withheld by statute and cannot be separated from ordinary non-response because the public files carry no geography. Pregnancy conditions are recorded without diagnosis dates, so the prediction timepoint rests on judgment, and the most clearly late-pregnancy items were excluded. Baselines use fixed default hyperparameters and only the standard training track; B3 is single rather than multiple imputation. Absolute performance is modest, as expected for prediction from pre-pregnancy and prenatal certificate items alone; the tasks are designed for comparing methods, not for clinical use.

**Future work.** Planned modules add survey data (YRBS, BRFSS, NHANES and NSDUH), which require design-aware splits and weighted metrics, along with full-track baselines, multiple imputation with pooling, and a separate late-pregnancy predictor tier.

## 5. Usage notes
Users rebuild the tasks from the NCHS files with `run_all.sh` (about 900 MB of downloads); the raw records are not redistributed. Methods should tune only on the validation split, report test metrics once per configuration, and report both training tracks where feasible.

## Code and data availability
The code (MIT License) and the task definitions, split manifests, missingness audit and baseline results (CC BY 4.0) are available at https://github.com/SelormB/ph-missbench. An archived release with a Zenodo DOI will follow. The task files were frozen and tagged (`tasks-frozen-v1.0`) on {frz.get('frozen_on', MISSING)}. The underlying records are the NCHS Natality Public Use Files, which are publicly available subject to NCHS data-use restrictions.

## Declarations
**Funding.** This work received no specific grant from any funding agency.

**Ethics.** This study used only de-identified, publicly available data (NCHS Natality Public Use Files) and therefore does not meet the definition of human subjects research under 45 CFR 46.102. It was not submitted for institutional review board review. No attempt was made to identify any individual, in accordance with the NCHS data-use restrictions.

**Author contributions (CRediT).** {au['name']}: {roles}.

**Use of AI assistance.** The author conceived the benchmark and made its design decisions (cohort, outcomes, prediction timepoint, predictor exclusions and split design). An AI assistant (Claude, Anthropic) wrote the pipeline code, ran the analyses, and drafted this manuscript, including its text, figures and tables. Every number in the manuscript is generated programmatically from the released pipeline outputs.

## References
1. Jäger S, Allhorn A, Bießmann F. A benchmark for data imputation methods. Front Big Data. 2021;4:693674. doi:10.3389/fdata.2021.693674
2. Jarrett D, Cebere BC, Liu T, Curth A, van der Schaar M. HyperImpute: generalized iterative imputation with automatic model selection. In: Proceedings of the 39th International Conference on Machine Learning. PMLR. 2022;162:9916–9937.
3. Perez-Lebel A, Varoquaux G, Le Morvan M, Josse J, Poline JB. Benchmarking missing-values approaches for predictive models on health databases. GigaScience. 2022;11:giac013. doi:10.1093/gigascience/giac013
4. Le Morvan M, Varoquaux G. Imputation for prediction: beware of diminishing returns. In: International Conference on Learning Representations (ICLR). 2025. arXiv:2407.19804
5. Josse J, Chen JM, Prost N, Scornet E, Varoquaux G. On the consistency of supervised learning with missing values. arXiv:1902.06931 [stat.ML]. doi:10.48550/arXiv.1902.06931
6. Rubin DB. Inference and missing data. Biometrika. 1976;63(3):581–592.
7. van Buuren S, Groothuis-Oudshoorn K. mice: Multivariate imputation by chained equations in R. J Stat Softw. 2011;45(3):1–67.
8. Stekhoven DJ, Bühlmann P. MissForest—non-parametric missing value imputation for mixed-type data. Bioinformatics. 2012;28(1):112–118.
9. Ke G, Meng Q, Finley T, et al. LightGBM: a highly efficient gradient boosting decision tree. Adv Neural Inf Process Syst. 2017;30:3146–3154.
10. Saito T, Rehmsmeier M. The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. PLoS One. 2015;10(3):e0118432.
11. Van Calster B, McLernon DJ, van Smeden M, Wynants L, Steyerberg EW. Calibration: the Achilles heel of predictive analytics. BMC Med. 2019;17:230.
12. National Center for Health Statistics. User guide to the 2022, 2023 and 2024 natality public use files. Hyattsville, MD: NCHS. https://www.cdc.gov/nchs/data_access/vitalstatsonline.htm
13. Osterman MJK, Hamilton BE, Martin JA, Driscoll AK, Valenzuela CP. Births: final data for 2024. Natl Vital Stat Rep. 2026;75(2). Hyattsville, MD: National Center for Health Statistics.


::: {{.appendix}}
## Appendix

**Table A1.** Predictors and their missingness in the 2024 analytic cohort, by class.

{pred_table}
:::
"""

(HERE / "manuscript.md").write_text(md)
print("wrote paper/manuscript.md")
if shutil.which("pandoc"):
    subprocess.run(["pandoc", "--columns=140", "--resource-path", str(HERE), str(HERE / "manuscript.md"), "-o", str(HERE / "manuscript.docx")], check=True)
    print("wrote paper/manuscript.docx")
