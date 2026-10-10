# arXiv submission kit — PH-MissBench (DRAFT until the author completes VERIFY_CHECKLIST)

Submit at https://arxiv.org/submit (the author must submit personally; submission is an attestation).

**Title**
PH-MissBench: rare-outcome prediction tasks with real, agency-documented missingness from U.S. birth records

**Authors**
Selorm Buaka

**Abstract** (1919 characters; arXiv limit 1,920)
Missing-data methods are usually compared on complete datasets with values deleted by simulation, which fixes the missingness mechanism by design. How methods behave on the missingness that public health analysts actually face is less studied, especially for rare outcomes. PH-MissBench is an open benchmark built from U.S. National Center for Health Statistics natality public-use files for 2022-2024. Every predictor cell carries the missingness class documented by the agency (observed, not stated, structurally not applicable, or agency-imputed), and agency-imputed values are restored to missing. Two tasks predict early preterm birth (obstetric-estimate gestation under 34 weeks) and very low birthweight (under 1,500 g) among singleton births to U.S. residents from 35 pre-pregnancy and prenatal items, with training on 2022-2023 and testing on 2024. Six baselines were evaluated by area under the precision-recall curve (AUPRC) with 1,000-replicate stratified bootstrap intervals. The cohort comprised 6,324,305 training, 703,612 validation and 3,512,264 test births; test-year prevalence was 2.15% for early preterm birth and 1.06% for very low birthweight. The pipeline reproduced the agency's published birth totals exactly for all three years. In 2024, 38.23% of births had at least one predictor missing. Gradient boosting with native missing-value handling performed best (AUPRC 0.082 and 0.050); mean imputation with missing-value indicators (0.067, 0.038) outperformed chained-equations (0.063, 0.035) and iterative random-forest imputation (0.064, 0.036); complete-case analysis performed worst (0.061, 0.034) and was miscalibrated. On population-scale U.S. birth records, approaches that let the model see missingness outperformed imputation alone, consistent with informative missingness. PH-MissBench provides frozen, reproducible tasks for comparing missing-data methods on real public health data.

**Primary category:** stat.ML (Machine Learning, Statistics)
**Cross-list:** stat.AP (Applications); optionally cs.LG
**License:** CC BY 4.0
**Comments:** 9 pages, 3 figures, 3 tables. Code and task definitions: https://github.com/<user>/ph-missbench ; archived release: <Zenodo DOI>
**Journal ref:** leave blank
**MSC/ACM:** leave blank

## Files to upload
- `paper/PH-MissBench_preprint.pdf`, produced by step 4 below (no DRAFT marks)

## Endorsement (only if arXiv asks; first stat.ML submission)
Send to a faculty member who has posted in stat.ML or stat.AP (for example, your advisor):

> Subject: arXiv endorsement request (stat.ML)
>
> Dear Dr. ___,
> I am preparing to post a data-descriptor preprint, "PH-MissBench: rare-outcome prediction tasks with real, agency-documented missingness from U.S. birth records," to arXiv stat.ML. It describes an open benchmark of rare-outcome prediction tasks built from NCHS birth records, with agency-documented missingness and frozen splits, plus baseline results. arXiv has asked me to obtain an endorsement for the category. If you are willing, my endorsement code is ______ (link: https://arxiv.org/auth/endorse).
> Thank you,
> Selorm Buaka

## Order of operations
1. Complete docs/VERIFY_CHECKLIST.md (voice, competing interests, ethics, spot checks).
2. Push the repository and the `tasks-frozen-v1.0` tag to GitHub (commands in docs/PUBLISH_GUIDE.md).
3. Mint the Zenodo DOI from the GitHub release; paste it into CITATION.cff and the manuscript.
4. `python code/06_figures.py --final && python paper/build_manuscript.py --final && paper/render_pdf.sh --final`, then `./gate.sh`.
5. Submit to arXiv with the fields above; record the arXiv ID in the evidence log.
