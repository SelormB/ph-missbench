# Limitations (DRAFT)

1. **No ground truth for missing values.** The benchmark scores downstream prediction, not reconstruction. A method that imputes badly but predicts well scores well.
2. **The missingness mechanism is unknown.** Classes record what the agency documented (not stated, not applicable, imputed), not whether data are MCAR, MAR or MNAR. `missingness_vs_outcome.csv` shows only whether missingness is associated with the outcome.
3. **Imputation flags cover few items.** NCHS flags imputation for mother's age, race and marital status, plurality, infant sex and combined gestation. Any undocumented edit to other items cannot be reversed.
4. **California marital status** is withheld by state statute from 2017 on, and the public file has no geography to separate it from ordinary non-response.
5. **No geography.** Public-use natality files carry no state or county identifiers, so spatial splits and facility effects are not possible.
6. **Undated pregnancy conditions.** Risk factors are recorded at delivery without diagnosis dates. Prediction-timepoint assignments (task spec §4) are judgments, not facts.
7. **Outcome measurement.** The obstetric estimate has its own error, and records with an unstated outcome are excluded rather than modelled.
8. **Registration completeness.** Births not registered, or registered after the file closed, are absent.
9. **Hash stability.** FREEZE.json hashes the Parquet files as written. Rebuilding with a different pyarrow version can change the bytes but not the content. The split manifest is the binding contract.
10. **Baselines are reference points, not tuned methods.** Hyperparameters are fixed defaults (LightGBM early-stopped on validation); B3 is single, not multiple, imputation; B3/B4 imputers are fit on a 50,000-row subsample. Only the standard track (250,000 training births) has been run; the full track needs HPC.
11. **Undocumented codes.** One 2024 record has blank birth-interval fields that the user guide does not document; it is treated as missing (class X).
