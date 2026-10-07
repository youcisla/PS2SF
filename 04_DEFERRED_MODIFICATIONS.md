# Deferred modification register (apply only after approval)

## 1. Exclusion `PS_AV_SF_GIFTS_EXCLUSION_VW`

Verified against the V1 package (`fichiers_par_vue/`): 9 active occurrences in 8 files, plus 1 commented line.

| File | Occurrences |
|---|---|
| PS_ASCEND_GIFT_VW_V1.sql | 1 |
| PS_ASCEND_GIFT_SOFT_VW_V1.sql | 1 |
| PS_ASCEND_MATCHING_GIFT_VW_V1.sql | 1 (marked MG-03) |
| PS_ASCEND_MATCHING_GIFT_SOFT_VW_V1.sql | 1 (marked MG-03) |
| PS_ASCEND_MG_ORIGINAT_VW_V1.sql | 1 |
| PS_ASCEND_PLEDGE_VW_V1.sql | 1 |
| PS_ASCEND_PLEDGE_PAYMENT_VW_V1.sql | 2 |
| PS_ASCEND_PP_SOFT_SCREDIT_VW_V1.sql | 1 |
| PS_ASCEND_GIFT_AID_VW_V1.sql | commented line 139; delete the line at the same time |

V0 baseline: the same clause appears in 5 V0 files (GIFT, GIFT_AD, GIFT_SOFT, PLEDGE_SOFT, PP_SOFT_SCREDIT). Dependency check on the package: the `_AD` and installment views read the base views (GIFT_BASE, GIFT_AID_BASE, PLEDGE_BASE, PLDG_INST_LINE), which carry no exclusion, so removing the clause changes exactly the 8 files listed above. When applying the change, update `01_CREATE_ALL_V1_VIEWS.sql` and the matching per-view files together; they are byte-identical today and should stay that way.

## 2. Gift currency source (analysis only, no SQL change yet)

V1 sets `CCY_ENTRY = NVL(designation currency, gift-header currency)`; V0 used the gift-header currency (`A.CURRENCY_CD_ENTRY`). A gift in SGD with a designation in EUR therefore exports as EUR in V1. Amount and rate are not wrong when the designation currency is not null (an earlier claim to the contrary was retracted). Current data evidence, from the business-change counts:

- `PS_ASCEND_GIFT_VW`: CURRENCYISOCODE changed on 10 rows of 133,933.
- `PS_ASCEND_PLEDGE_PAYMENT_VW`: CURRENCYISOCODE changed on 4,626 rows of 22,174.
- `PS_ASCEND_MATCHING_GIFT_VW`: CURRENCYISOCODE on 1 row; `INSEAD_PS_AMOUNT_ENTRY__C` on 1 row.
- `PS_ASCEND_PP_SOFT_SCREDIT_VW`: Operating Entity and Transaction currency each changed on about 600 rows.

Before touching `CurrencyIsoCode`, check the affected records against the PeopleSoft Transaction Register and the Ascend target semantics. Do not change amount or rate logic as part of the currency fix.

## 3. Duplicate or suspicious output fields (confirm against the Ascend mapping before removing)

- GIFT and GIFT_AD: `UCINN_ASCENDV2__EXTERNAL_SYSTEM_ID___C` (three underscores) and `..._ID__C` are both retained.
- PROPOSAL: `F1_EXPECTED_CLOSE_DATE` against the Ascend expected close date; `F1_Submitted_Date`.
- USER: `username` and `email_addr` use the same expression.
- GIFT_AID and GIFT_AID_AD: three date fields carry the same date.
- PLEDGE_SOFT: `Designation_Detail__r = Review_Transaction_v2__r` changed in V1. The column diff shows DESIGNATION_DETAIL__R changed on 354 of 354 matched rows. Confirm this is intended.
- OARL and JOB_CODE: a duplicate column was renamed `F1_ASCEND_ID` in V1 after aliases were lost in the V0 export. Verify the real names with ALL_TAB_COLUMNS.

## 4. External ID changes that create new records if loaded over existing data

- `PS_F1_SF_CNST_SIND`: F1_ASCEND_ID now includes the service indicator timestamp (the CNS-20 fix). 11,024 of 12,106 matched rows differ on that column, and the two files only join on EMPLID plus F1_SRVC_IND_CD.
- Apply the same check before loading any V1 extract over previously loaded Ascend data.

## 5. Export hygiene for the next wave

- Remove the `SQL> SELECT ...` echo line (set ECHO OFF in the spool script, or call the saved script with @script instead of running it from the worksheet).
- Export everything in one encoding. Today, 55 of 91 CSVs are CP1252 and the rest are UTF-8. The V0 and V1 files of a compared pair must use the same encoding.
- Do not re-run exports while a comparison workbook is open; the reviewed numbers will drift from the CSVs.
