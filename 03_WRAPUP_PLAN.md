# Wrap-up plan: remaining work in fastest order

Documents: [Executive summary](00_EXECUTIVE_SUMMARY.md) | [State of migration](01_STATE_OF_MIGRATION.md) | [Match report](02_VERSION_MATCH_REPORT.md) | **Wrap-up plan (you are here)** | [Deferred changes](04_DEFERRED_MODIFICATIONS.md) | [README](README.md)

## A. Data gaps (export work only)

| # | Item | Action |
|---|---|---|
| 1 | `PS_F1_SF_WORK_EXP` V1 CSV missing | Re-run its V1 spool (the batch stopped before it) |
| 2 | `PS_ASCEND_PERSO_CTC_REP_REL_VW` V0 CSV missing, V1 CSV empty (0 bytes) | Re-export both |
| 3 | `PS_F1_SF_CNST_RELS` V0 missing, V1 header-only (68 bytes) | Re-export, but confirm CNS-01 and CNS-06 first: the F1 extract may be deprecated |
| 4 | Every CSV starts with a `SQL> SELECT ...` echo line | The importer must skip lines 1 and 2, or fix the spool script before the next export wave |

## B. Open business decisions

- CNS-01 (Critical): Two relationship extracts with contradictory mappings - PS_ASCEND_CNST_RELS (32 codes, YYYY-MM-DD, soft credit SP+PA) an
- GEN-17 (High): Payment External ID built 5 different ways - GIFT_SOFT: 'CONV-G-g-1-g-1-1' (designation index hard-coded 1). MG_ORIGINAT
- GEN-19 (High): Operating Entity derived 4 different ways - GIFT/MG: PS_GIFT_RECOG_HARD_SOFT_VW; GIFT/GIFT_SOFT: soft-list override (302
- GEN-21 (High): Exclusion list applied to half of the transaction views - PS_AV_SF_GIFTS_EXCLUSION_VW is applied in GIFT(+AD), GIFT_SOFT
- CNS-06 (High): Duplicate of PS_ASCEND_CNST_RELS (see CNS-01) - Same target and key, different code list, mapping and date format; if bo
- CMP-06 (High): Excluded designations still referenced by gifts - MBA88D_SCH, MBA05J_SCH, MBA09J_SCH are removed from the master but gif
- CNS-05 (Medium): Deceased spouse still gets Merge Household + soft credit - PEOPLE_RELATION_DESCR becomes 'Deceased Spouse' but APPLY_SOF
- GFT-11 (Medium): Gift amount filter differs from pledge payments - Gifts require GIFT_AMT<>0; PLEDGE_PAYMENT accepts GIFT_AMT<>0 OR GIFT_
- MG-07 (Medium): Only one soft-credit recipient per matching gift - rr_one keeps one row of PS_GIFT_RECOG_HARD_SOFT_VW per gift x session
- PGV-04 (Medium): CloseDate from rating date (often NULL) - Opportunity.CloseDate is required; Stage and Legacy Type are derived from two 
- CMP-12 (Medium): Speaker flag is global to the person - Anyone who spoke once is flagged speaker at every event attended.
- MOV-03 (Medium): Exclusion ID has 6 digits - '000048' vs 7-digit IDs ('0000053') - probably '0000048', so the exclusion does nothing. Sam
- SOC-05 (Medium): Board COP dates stamped on every club membership - START_DT/END_DT come from board involvement, not the membership.
- GEN-25 (Low): Tender type mapping differs - Gifts map AMEX->'American Express' and UND->'Other'; NAA_SOCIETY_MEMBERSHIP maps both to '

## C. Partially fixed issues (the mechanical fix is in V1, a business rule is still needed)

- ALL: GEN-17 (partial) Payment External ID built 5 different ways
- ALL: GEN-19 (partial) Operating Entity derived 4 different ways
- ALL: GEN-21 (partial) Exclusion list applied to half of the transaction views
- ALL: GEN-04 (partial) Legacy-currency list repeated 60+ times, with and without 'EUR'
- PS_ASCEND_FDR_PLDG_VW: PGV-02 (partial) No filter: every gift announcement becomes a Founders Pledge
- PS_ASCEND_LEGACY_GIV_SOL_VW: PGV-04 (partial) CloseDate from rating date (often NULL)
- PS_ASCEND_MATCHING_GIFT_VW: MG-03 (partial) No exclusion list, no soft-list OE override
- PS_F1_SF_STG_RDNS: MOV-14 (partial) Person and org IDs share one key; no scope

## D. Package facts to keep in mind

- `01_CREATE_ALL_V1_VIEWS.sql` deploys all 71 objects in one F5 run (65 views plus the 6 shared views at the top). `00_PS_ASCEND_COMMON_V1.sql` is the same shared section standalone.
- Per-view files in `fichiers_par_vue/` are byte-consistent with `01_CREATE_ALL_V1_VIEWS.sql` (0 mismatches). Keep them in sync when making future edits.
- The exclusion `PS_AV_SF_GIFTS_EXCLUSION_VW` is applied in V1: 9 active occurrences in 8 files, plus 1 commented line in GIFT_AID. V0 used it in 5 files. Removal was deferred until this review completes; see `04_DEFERRED_MODIFICATIONS.md`.
- Gift currency: V1 uses `NVL(designation, header)` currency. The SGD/EUR finding is analysis only; do not change amounts or rates while implementing a decision.
- Cosmetic differences in this report include NULL against empty string. The GIFT workbooks accept this change (values are marked as empty in the Ascend mapping).

## E. Fastest closing sequence

1. Re-export the missing or stub pairs (A1 to A3).
2. In `02_VERSION_MATCH_REPORT.md`, take every view with clean% below about 95 and confirm the difference matches the intended V1 fix (each one maps to an issue ID).
3. Close the open business decisions (B). Each one is a parameter line or an accepted rule, not code work.
4. Refresh the comparison workbooks for views re-exported since the last review; their numbers will drift from the current CSVs.
5. Apply the deferred modifications in one V2 pass: exclusion removal, currency decision, recommendation-flagged items.
