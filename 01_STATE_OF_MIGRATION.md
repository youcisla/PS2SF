# State of migration: PeopleSoft CSOADM to Salesforce Ascend

Documents: [Executive summary](00_EXECUTIVE_SUMMARY.md) | **State of migration (you are here)** | [Match report](02_VERSION_MATCH_REPORT.md) | [Wrap-up plan](03_WRAPUP_PLAN.md) | [Deferred changes](04_DEFERRED_MODIFICATIONS.md) | [README](README.md)

Read-only scan of `PS_2_SF` (V0 SQL scripts, the V1 SQL package, CSV exports and comparison workbooks). No source file was modified. All generated output lives in `YoucefVersion/`.

## Summary

- SQL: 64 V0 views; the V1 package contains 59 revised `_V1` views and 12 new shared or base views. `01_CREATE_ALL_V1_VIEWS.sql` deploys all 71 objects in one run; `00_PS_ASCEND_COMMON_V1.sql` is the standalone copy of the 6 shared views. The per-view files and the create-all script are identical (0 mismatches).
- 5 V0 views have no V1 counterpart, by design: PS_ASCEND_NAA_GVG_STY_VW, PS_ASCEND_NAA_MBR_LVL_PDCT_VW, PS_ASCEND_OPERATING_ENTITY_VW, PS_ASGN_CMP_SRCH, PS_F1_SF_TO_CONV. Three are marked "no comparison needed" and two are out of scope in the review workbook.
- CSV data: 42 pairs joined on their business key, 2,135,477 matched rows. 73,162 rows carry at least one business change, so 96.57% of matched rows have no business change and 88.53% are byte-identical.
- Review workbook: 158 issues logged, 128 fixed in V1, 8 partial fixes, 12 open recommendations, 14 questions for the business.

## Per-view status

`key-joined` is the number of matched business keys. `clean%` is the share of matched rows with no business change; `ident%` is the share of byte-identical rows. `V0-only / V1-only` counts business keys present on one side only.

| Family | View | V1 view | SQL sim% | key-joined | V0-only / V1-only keys | clean% | ident% | workbook | workbook status |
|---|---|---|---|---|---|---|---|---|---|
| Campaign & Designation | PS_ASCEND_CAMPAIGN_VW | PS_ASCEND_CAMPAIGN_VW_V1 | 78.8 |  |  |  |  |  |  |
| Constituent | PS_ASCEND_CNST_RELS | PS_ASCEND_CNST_RELS_V1 | 48.8 |  |  |  |  |  | No files |
| Constituent | PS_ASCEND_CONSTITUENT_TYPE_VW | PS_ASCEND_CONSTITUENT_TYPE_VW_V1 | 48.7 | 159,917 | 0 / 0 | 100.0 | 100.0 |  |  |
| Moves Management | PS_ASCEND_CONTACT_REPORT_VW | PS_ASCEND_CONTACT_REPORT_VW_V1 | 88.0 | 286,501 | 5 / 9302 | 100.0 | 86.49 |  |  |
| Campaign & Designation | PS_ASCEND_CPGN_EVENT_VW | PS_ASCEND_CPGN_EVENT_VW_V1 | 52.0 |  |  |  |  |  |  |
| Campaign & Designation | PS_ASCEND_CPGN_MBR_VW | PS_ASCEND_CPGN_MBR_VW_V1 | 44.9 |  |  |  |  |  |  |
| Moves Management | PS_ASCEND_CTC_REP_REL_VW | PS_ASCEND_CTC_REP_REL_VW_V1 | 78.1 | 200 | 0 / 0 | 100.0 | 100.0 |  |  |
| Campaign & Designation | PS_ASCEND_DESIGNATION_VW | PS_ASCEND_DESIGNATION_VW_V1 | 81.4 | 601 | 1 / 4 | 96.34 | 96.34 |  | Done |
| Planned Giving | PS_ASCEND_FDR_PLDG_VW | PS_ASCEND_FDR_PLDG_VW_V1 | 76.2 | 43 | 0 / 0 | 100.0 | 100.0 |  |  |
| Gift | PS_ASCEND_GIFT_AD_VW | PS_ASCEND_GIFT_AD_VW_V1 | 26.3 | 256 | 0 / 0 | 83.2 | 0.0 |  | Done |
| Gift | PS_ASCEND_GIFT_AID_AD_VW | PS_ASCEND_GIFT_AID_AD_VW_V1 | 37.0 | 56 | 0 / 0 | 0.0 | 0.0 | PS_ASCEND_GIFT_AID_AD | Done |
| Gift | PS_ASCEND_GIFT_AID_VW | PS_ASCEND_GIFT_AID_VW_V1 | 37.1 | 9,430 | 21 / 0 | 0.0 | 0.0 | PS_ASCEND_GIFT_AID | Done |
| Gift | PS_ASCEND_GIFT_SOFT_VW | PS_ASCEND_GIFT_SOFT_VW_V1 | 43.9 | 26,161 | 0 / 0 | 99.74 | 99.74 | PS_ASCEND_GIFT_SOFT_reviewed | Terminé / revu |
| Gift | PS_ASCEND_GIFT_VW | PS_ASCEND_GIFT_VW_V1 | 26.6 | 133,933 | 0 / 0 | 92.55 | 24.32 |  | Done |
| Planned Giving | PS_ASCEND_LEGACY_GIV_SOL_VW | PS_ASCEND_LEGACY_GIV_SOL_VW_V1 | 82.5 |  |  |  |  |  |  |
| Matching Gift | PS_ASCEND_MATCHING_GIFT_AD_VW | PS_ASCEND_MATCHING_GIFT_AD_VW_V1 | 27.7 | 22 | 0 / 0 | 13.64 | 13.64 | _ASCEND_MATCHING_GIFT_AD_comparison_todo | Terminé / revu |
| Matching Gift | PS_ASCEND_MATCHING_GIFT_SOFT_VW | PS_ASCEND_MATCHING_GIFT_SOFT_VW_V1 | 46.7 | 24 | 0 / 0 | 83.33 | 83.33 | PS_ASCEND_MATCHING_GIFT_SOFT_todo | Done |
| Matching Gift | PS_ASCEND_MATCHING_GIFT_VW | PS_ASCEND_MATCHING_GIFT_VW_V1 | 27.6 | 735 | 0 / 1 | 77.69 | 77.69 | PS_ASCEND_MATCHING_GIFT_comparison_todo | In progress |
| Matching Gift | PS_ASCEND_MG_ORIGINAT_VW | PS_ASCEND_MG_ORIGINAT_VW_V1 | 79.7 | 745 | 0 / 0 | 99.6 | 99.6 |  | In progress |
| Societies & Membership | PS_ASCEND_NAA_SOCIETY_MEMBERSHIP_VW | PS_ASCEND_NAA_SOCIETY_MEMBERSHIP_VW_V1 | 65.4 |  |  |  |  |  |  |
| Moves Management | PS_ASCEND_OPP_CONTACT_ROLE_VW | PS_ASCEND_OPP_CONTACT_ROLE_VW_V1 | 84.8 | 78 | 0 / 0 | 100.0 | 100.0 |  |  |
| Moves Management | PS_ASCEND_OPP_TEAM_MBR_VW | PS_ASCEND_OPP_TEAM_MBR_VW_V1 | 63.2 | 9,571 | 0 / 0 | 100.0 | 100.0 |  |  |
| Moves Management | PS_ASCEND_PERSO_CTC_REP_REL_VW | PS_ASCEND_PERSO_CTC_REP_REL_VW_V1 | 59.1 |  |  |  |  |  |  |
| Pledge | PS_ASCEND_PLEDGE_AD_VW | PS_ASCEND_PLEDGE_AD_VW_V1 | 21.3 | 10 | 0 / 209 | 0.0 | 0.0 |  | In progress |
| Pledge | PS_ASCEND_PLEDGE_INSTALLMENT_VW | PS_ASCEND_PLEDGE_INSTALLMENT_VW_V1 | 32.5 | 15,116 | 15312 / 15309 | 99.27 | 99.27 | PS_ASCEND_PLEDGE_INSTALLMENT | Done |
| Pledge | PS_ASCEND_PLEDGE_PAYMENT_VW | PS_ASCEND_PLEDGE_PAYMENT_VW_V1 | 30.2 | 22,174 | 3 / 0 | 0.0 | 0.0 |  | Done |
| Pledge | PS_ASCEND_PLEDGE_SOFT_VW | PS_ASCEND_PLEDGE_SOFT_VW_V1 | 43.1 | 354 | 0 / 0 | 0.0 | 0.0 |  | Terminé / revu |
| Pledge | PS_ASCEND_PLEDGE_VW | PS_ASCEND_PLEDGE_VW_V1 | 21.3 | 7,338 | 1 / 0 | 98.84 | 0.0 | PS_ASCEND_PLEDGE_VW_reviewed | Terminé / revu |
| Pledge | PS_ASCEND_PP_INSTALLMENT_VW | PS_ASCEND_PP_INSTALLMENT_VW_V1 | 31.3 | 11,705 | 10923 / 10829 | 0.0 | 0.0 |  | Done |
| Pledge | PS_ASCEND_PP_SOFT_SCREDIT_VW | PS_ASCEND_PP_SOFT_SCREDIT_VW_V1 | 29.7 | 5,541 | 6 / 0 | 0.0 | 0.0 | PS_ASCEND_PP_SOFT_SCREDIT_Reviewed | Terminé / revu |
| Moves Management | PS_ASCEND_PROPOSAL_VW | PS_ASCEND_PROPOSAL_VW_V1 | 82.4 | 9,131 | 0 / 0 | 91.6 | 91.6 |  | Incomplet |
| Societies & Membership | PS_ASCEND_RCG_STY_VW | PS_ASCEND_RCG_STY_VW_V1 | 93.0 |  |  |  |  |  |  |
| Societies & Membership | PS_ASCEND_SOCIETY_MEMBERSHIP_VW | PS_ASCEND_SOCIETY_MEMBERSHIP_VW_V1 | 92.3 |  |  |  |  |  |  |
| Moves Management | PS_F1_SF_AV_ASGNMT | PS_F1_SF_AV_ASGNMT_V1 | 68.7 | 6,171 | 0 / 0 | 100.0 | 100.0 |  |  |
| Moves Management | PS_F1_SF_AV_CAPRAT | PS_F1_SF_AV_CAPRAT_V1 | 82.7 | 152,048 | 0 / 0 | 100.0 | 100.0 |  |  |
| Moves Management | PS_F1_SF_AV_STRTGY | PS_F1_SF_AV_STRTGY_V1 | 56.0 | 141 | 0 / 0 | 100.0 | 100.0 |  |  |
| Constituent | PS_F1_SF_CNST | PS_F1_SF_CNST_V1 | 74.6 | 110,882 | 0 / 0 | 100.0 | 100.0 |  |  |
| Constituent | PS_F1_SF_CNST_ADDR | PS_F1_SF_CNST_ADDR_V1 | 62.7 | 137,336 | 139699 / 0 | 100.0 | 100.0 |  | Done |
| Constituent | PS_F1_SF_CNST_ADRL | PS_F1_SF_CNST_ADRL_V1 | 71.7 | 154,606 | 31 / 34 | 98.97 | 98.97 |  |  |
| Constituent | PS_F1_SF_CNST_DSCR | PS_F1_SF_CNST_DSCR_V1 | 80.2 | 112,648 | 0 / 0 | 100.0 | 100.0 |  | Done |
| Constituent | PS_F1_SF_CNST_EML | PS_F1_SF_CNST_EML_V1 | 92.4 | 179,894 | 0 / 0 | 100.0 | 100.0 |  | Done |
| Constituent | PS_F1_SF_CNST_NAME | PS_F1_SF_CNST_NAME_V1 | 81.4 | 50,245 | 0 / 0 | 100.0 | 100.0 |  | Done |
| Constituent | PS_F1_SF_CNST_NL | PS_F1_SF_CNST_NL_V1 | 43.1 | 30,486 | 53760 / 0 | 100.0 | 100.0 |  |  |
| Constituent | PS_F1_SF_CNST_NSDG | PS_F1_SF_CNST_NSDG_V1 | 97.8 |  |  |  |  |  | No files |
| Organization | PS_F1_SF_CNST_OARL | PS_F1_SF_CNST_OARL_V1 | 66.2 |  |  |  |  |  | No files |
| Organization | PS_F1_SF_CNST_ORGS | PS_F1_SF_CNST_ORGS_V1 | 75.1 |  |  |  |  |  |  |
| Constituent | PS_F1_SF_CNST_PHNE | PS_F1_SF_CNST_PHNE_V1 | 97.8 | 150,133 | 0 / 0 | 100.0 | 100.0 |  |  |
| Constituent | PS_F1_SF_CNST_RELS | PS_F1_SF_CNST_RELS_V1 | 57.8 |  |  |  |  |  | Incomplet |
| Constituent | PS_F1_SF_CNST_SICD | PS_F1_SF_CNST_SICD_V1 | 59.6 |  |  |  |  |  |  |
| Constituent | PS_F1_SF_CNST_SIND | PS_F1_SF_CNST_SIND_V1 | 51.7 | 12,106 | 1 / 1 | 0.01 | 0.01 |  | Done |
| Constituent | PS_F1_SF_CNST_URLS | PS_F1_SF_CNST_URLS_V1 | 79.5 | 32,896 | 0 / 0 | 100.0 | 100.0 |  |  |
| Constituent | PS_F1_SF_CNT_NL | PS_F1_SF_CNT_NL_V1 | 17.5 | 30,486 | 61026 / 0 | 99.58 | 99.58 |  |  |
| Organization | PS_F1_SF_JOB_CODE | PS_F1_SF_JOB_CODE_V1 | 75.4 |  |  |  |  |  |  |
| Organization | PS_F1_SF_ORG_ADDR | PS_F1_SF_ORG_ADDR_V1 | 43.6 | 226,243 | 138866 / 0 | 100.0 | 100.0 |  | Done |
| Organization | PS_F1_SF_ORG_EMAIL | PS_F1_SF_ORG_EMAIL_V1 | 72.8 | 436 | 0 / 36 | 100.0 | 100.0 |  |  |
| Organization | PS_F1_SF_ORG_PHONE | PS_F1_SF_ORG_PHONE_V1 | 89.7 | 38,178 | 18 / 18 | 100.0 | 100.0 |  | Done |
| Moves Management | PS_F1_SF_STG_RDNS | PS_F1_SF_STG_RDNS_V1 | 43.4 | 10,900 | 33 / 0 | 100.0 | 100.0 |  |  |
| Users | PS_F1_SF_USER | PS_F1_SF_USER_V1 | 25.1 |  |  |  |  |  |  |
| Constituent | PS_F1_SF_WORK_EXP | PS_F1_SF_WORK_EXP_V1 | 60.7 |  |  |  |  |  |  |
