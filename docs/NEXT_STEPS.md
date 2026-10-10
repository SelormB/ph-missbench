# Next steps (DRAFT)

Done (2026-10-10): real 2022–2024 build; external validation against NCHS totals; V2 ruling; tasks frozen; standard-track baselines.

1. Author verification (docs/VERIFY_CHECKLIST.md): reproduce, spot-check rows, rule on V3/V4 defaults, review the one undocumented-code record.
2. Commit FREEZE.json and tag `tasks-frozen-v1.0` before MAKD-Natality touches any task.
3. Full-track baselines on HPC (`python code/05_baselines.py --track full`; B4 skipped).
4. Manuscript: background, references, declarations, rewrite in the author's voice.
5. GitHub + Zenodo release; preprint.
6. v1.1: YRBS module (design-aware splits, weighted metrics). v1.2+: BRFSS, NHANES, NSDUH.
7. Candidate additions: multiple imputation with pooling (MICE proper); a late-pregnancy predictor tier as a separate task.
