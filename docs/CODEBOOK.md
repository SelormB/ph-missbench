# Codebook — natality task files (DRAFT)

The authoritative field list (record positions, valid codes, not-stated and not-applicable codes, imputation flag, label) is `code/layout_natality.csv`. Fields with role `predictor` are task columns.

| Column | Type | Definition |
|---|---|---|
| row_id | string | `<year>-<line number>` in the NCHS file |
| y | int8 | Outcome (1 = case). EPTB: OEGest_Comb < 34. VLBW: DBWT < 1500. |
| `<numeric field>` | float64 | Observed value; NaN if not stated, NCHS-imputed, or not applicable |
| `<numeric field>__na_struct` | int8 | 1 = structurally not applicable (e.g. 888 = first birth). Only for ILLB_R, ILOP_R, ILP_R. |
| `<categorical / Y-N field>` | string | Observed code; `NA_STRUCT` if not applicable; null if not stated or imputed |
| `*_mclass` files | string | O observed · S not stated · A not applicable · I NCHS-imputed (restored to missing) |

The codes of each categorical field are those in the NCHS user guide for the data year.
