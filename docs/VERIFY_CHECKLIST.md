# Verification checklist (author completes before any release)

Initial and date each line in your own copy. The publish gate checks the mechanical items; these are yours.

## Reproduce
- [ ] Fresh fetch via `01_fetch.py`; row counts match PROVENANCE.txt or drift is explained
- [ ] Full pipeline re-run; outputs diff clean against the committed versions
- [ ] Every number in any document re-derived from the stats file after the re-run

## Source-level checks
- [ ] Five records checked by hand against the original source pages
- [ ] Source vintages confirmed current; newer releases noted if they exist
- [ ] Licenses and terms of every source re-read; nothing forbids redistribution

## Row-level spot checks (minimum 15 units)
- [ ] Five units you know personally
- [ ] Five extreme values, each checked against an independent reference
- [ ] Five random units (record the seed)

## Judgment calls to own (edit or document agreement)
- [ ] V1 Record-layout positions in code/layout_natality.csv match the 2022, 2023 and 2024 user guides
- [x] V2 Leakage rulings on RF_GHYPE, RF_EHYPE, RF_GDIAB, CIG_2, CIG_3 (author, 2026-10-10: all excluded)
- [ ] V3 NCHS-imputed values restored to missing; V4 standard-track size 250,000 and seed 20261004; V5 cohort exclusions

## Manuscript (added 2026-10-10)
- [ ] Introduction and discussion rewritten in your own voice (the draft text was written by an AI assistant)
- [ ] Competing-interest statement written (you reported one)
- [ ] Ethics statement confirmed against UNC policy (current text: not human subjects research, no IRB submission)
- [ ] References: 13 checked against sources on 2026-10-10; re-check any you add

## Before it goes public
- [ ] README, limitations, and any manuscript rewritten in your own voice; nothing you cannot defend remains
- [ ] Draft stamps removed by regenerating with `--final`; `publish_gate.py` passes
- [ ] License files, name, ORCID, contact in place
- [ ] Evidence log row written the day of release
- [ ] V6 FREEZE.json written, committed and tagged before MAKD-Natality touches any task

## Benchmark-specific
- [ ] Undocumented codes (class X) in qa_report.txt reviewed; treating them as missing is acceptable (2024: one record, row_id 2024-1239479, blank ILLB_R and ILP_R)
- [ ] Cohort-flow counts in qa_report.txt compared with NCHS published totals for each year
- [ ] EPTB and VLBW prevalence compared with the NVSR final-births report for 2024
- [ ] Five row_ids traced back to their raw lines in the NCHS file
