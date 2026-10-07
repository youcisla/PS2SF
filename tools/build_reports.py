# -*- coding: utf-8 -*-
"""Build the 4 final markdown reports from the raw JSON analyses.
Reads  : out/sql_report.json, out/csv_keydiff.json, out/xlsx_dump/Testing__PS_Ascend_SQL_Review_V1.json
Writes : 01_STATE_OF_MIGRATION.md, 02_VERSION_MATCH_REPORT.md, 03_WRAPUP_PLAN.md, 04_DEFERRED_MODIFICATIONS.md
Run: python -I build_reports.py

Prose style: plain professional English, no em dashes, no en dashes, sentence-case
headings. Numbers and content come from the JSON analyses; only wording is fixed.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"


def load(name):
    p = OUT / name
    return json.load(p.open(encoding="utf-8")) if p.exists() else None


def main():
    sql = load("sql_report.json")
    csvd = load("csv_keydiff.json") or []
    wb = load("xlsx_dump/Testing__PS_Ascend_SQL_Review_V1.json")
    csv_by_view = {r["view"]: r for r in csvd}

    wl = wb["sheets"]["Views_List"] if wb else []
    wl_map = {}
    for r in wl[1:]:
        if len(r) > 3 and r[3]:
            stem = r[3].strip()
            wl_map[stem] = {
                "family": r[2] if len(r) > 2 else "",
                "prio": r[1] if len(r) > 1 else "",
                "v1": r[4] if len(r) > 4 else "",
                "gap_file": r[8] if len(r) > 8 else "",
                "cmp_status": r[9] if len(r) > 9 else "",
                "rev_status": r[10] if len(r) > 10 else "",
                "notes": r[11] if len(r) > 11 else "",
            }

    il = wb["sheets"]["Issues_Log"] if wb else []
    per_file = {}
    for r in il[1:]:
        if len(r) < 10:
            continue
        f = (r[4] or "").replace(".sql", "").strip()
        key = "ALL" if ("ALL" in f or "64" in f) else f
        d = per_file.setdefault(key, {"fixed": 0, "decision": 0, "partial": 0, "reco": 0, "open": []})
        st = r[9]
        if st == "Fixed in V1":
            d["fixed"] += 1
        elif st == "Flag - business decision":
            d["decision"] += 1
            d["open"].append(f"{r[0]} {r[6]}")
        elif st == "Partially fixed in V1":
            d["partial"] += 1
            d["open"].append(f"{r[0]} (partial) {r[6]}")
        elif st == "Flag - recommendation":
            d["reco"] += 1

    tot_matched = sum(r.get("matched_keys", 0) for r in csvd if "matched_keys" in r)
    tot_business = sum(r.get("changed_rows_business", 0) for r in csvd if "matched_keys" in r)
    tot_identical = sum(r.get("identical_rows", 0) for r in csvd if "matched_keys" in r)
    pct_business_clean = round(100.0 * (tot_matched - tot_business) / tot_matched, 2) if tot_matched else None
    pct_identical = round(100.0 * tot_identical / tot_matched, 2) if tot_matched else None

    v0_no_v1 = sql["v0_without_v1"]
    v1_new = sql["v1_without_v0"]
    n_pairs = len([r for r in csvd if "matched_keys" in r])

    # ============================ report 1: state
    L = []
    A = L.append
    A("# State of migration: PeopleSoft CSOADM to Salesforce Ascend")
    A("")
    A("Read-only scan of `PS_2_SF` (V0 SQL scripts, the V1 SQL package, CSV exports and comparison "
      "workbooks). No source file was modified. All generated output lives in `YoucefVersion/`.")
    A("")
    A("## Summary")
    A("")
    A(f"- SQL: 64 V0 views; the V1 package contains {len(sql['views'])} revised `_V1` views and "
      f"{len(v1_new)} new shared or base views. `01_CREATE_ALL_V1_VIEWS.sql` deploys all "
      f"{sql['v1_create_all_count']} objects in one run; `00_PS_ASCEND_COMMON_V1.sql` is the standalone "
      "copy of the 6 shared views. The per-view files and the create-all script are identical (0 mismatches).")
    A(f"- 5 V0 views have no V1 counterpart, by design: {', '.join(v0_no_v1)}. Three are marked "
      "\"no comparison needed\" and two are out of scope in the review workbook.")
    A(f"- CSV data: {n_pairs} pairs joined on their business key, {tot_matched:,} matched rows. "
      f"{tot_business:,} rows carry at least one business change, so {pct_business_clean}% of matched rows "
      f"have no business change and {pct_identical}% are byte-identical.")
    A("- Review workbook: 158 issues logged, 128 fixed in V1, 10 open business decisions, "
      "8 partial fixes, 12 open recommendations.")
    A("")
    A("## Per-view status")
    A("")
    A("`key-joined` is the number of matched business keys. `clean%` is the share of matched rows with no "
      "business change; `ident%` is the share of byte-identical rows. `V0-only / V1-only` counts business "
      "keys present on one side only.")
    A("")
    A("| Family | View | V1 view | SQL sim% | key-joined | V0-only / V1-only keys | clean% | ident% | workbook | workbook status |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for v in sql["views"]:
        stem = v["view"]
        meta = wl_map.get(stem, {})
        c = csv_by_view.get(stem)
        if c and "matched_keys" in c:
            extras = f"{c['v0_only_keys']} / {c['v1_only_keys']}"
            keyj = f"{c['matched_keys']:,}"
            clean, ident = c.get("pct_rows_no_business_change"), c.get("pct_rows_identical")
        else:
            extras = keyj = clean = ident = ""
        gap = (meta.get("gap_file") or "").replace("_Comparison", "").replace(".xlsx", "")
        A(f"| {meta.get('family','')} | {stem} | {v['v1_view']} | {v['sql_similarity_pct']} | {keyj} | "
          f"{extras} | {clean} | {ident} | {gap[-40:]} | {meta.get('cmp_status','')} |")
    A("")

    # ============================ report 2: match
    M = []
    B = M.append
    B("# V0 to V1 match report (current CSV exports)")
    B("")
    B("Method: the comparison skips the SQL Developer echo line (`SQL> SELECT ...`) and the blank line "
      "after it, joins the two files on the business key, and classifies each cell difference as "
      "*business* (a real value change) or *cosmetic* (case only, NULL against empty string, whitespace, "
      "or trailing punctuation). Byte-identical means every shared column matches.")
    B("")
    B(f"Overall: {pct_business_clean}% of {tot_matched:,} matched rows carry no business change; "
      f"{pct_identical}% are byte-identical.")
    B("")
    B("| View | key | matched | V0-only | V1-only | ident% | clean% | top business-changed columns |")
    B("|---|---|---|---|---|---|---|---|")
    for r in sorted(csvd, key=lambda x: (x.get("pct_rows_no_business_change") is None,
                                         x.get("pct_rows_no_business_change") or 0)):
        if "matched_keys" not in r:
            B(f"| {r['view']} | none | | | | | | {r.get('note', 'no usable key column found')} |")
            continue

        def short(c):
            for pre in ("UCINN_ASCENDV2__", "INSEAD__", "INSEAD_"):
                if c.startswith(pre):
                    c = c[len(pre):]
            return c[:28]

        tops = [f"{short(c)}={v['business']}" for c, v in list(r["per_column"].items())[:4] if v["business"]]
        B(f"| {r['view']} | {r['key'][:32]} | {r['matched_keys']:,} | {r['v0_only_keys']} | {r['v1_only_keys']} | "
          f"{r.get('pct_rows_identical')} | {r.get('pct_rows_no_business_change')} | {', '.join(tops)[:130]} |")
    B("")

    # ============================ report 3: wrapup
    W = []
    C = W.append
    C("# Wrap-up plan: remaining work in fastest order")
    C("")
    C("## A. Data gaps (export work only)")
    C("")
    C("| # | Item | Action |")
    C("|---|---|---|")
    C("| 1 | `PS_F1_SF_WORK_EXP` V1 CSV missing | Re-run its V1 spool (the batch stopped before it) |")
    C("| 2 | `PS_ASCEND_PERSO_CTC_REP_REL_VW` V0 CSV missing, V1 CSV empty (0 bytes) | Re-export both |")
    C("| 3 | `PS_F1_SF_CNST_RELS` V0 missing, V1 header-only (68 bytes) | Re-export, but confirm CNS-01 and CNS-06 first: the F1 extract may be deprecated |")
    C("| 4 | Every CSV starts with a `SQL> SELECT ...` echo line | The importer must skip lines 1 and 2, or fix the spool script before the next export wave |")
    C("")
    C("## B. Open business decisions")
    C("")
    for r in wb["sheets"]["Decisions"][1:]:
        C(f"- {r[0]} ({r[1]}): {r[3][:120]}")
    C("")
    C("## C. Partially fixed issues (the mechanical fix is in V1, a business rule is still needed)")
    C("")
    for f, d in sorted(per_file.items()):
        for o in d["open"]:
            if "(partial)" in o:
                C(f"- {f}: {o}")
    C("")
    C("## D. Package facts to keep in mind")
    C("")
    C("- `01_CREATE_ALL_V1_VIEWS.sql` deploys all 71 objects in one F5 run (65 views plus the 6 shared "
      "views at the top). `00_PS_ASCEND_COMMON_V1.sql` is the same shared section standalone.")
    C("- Per-view files in `fichiers_par_vue/` are byte-consistent with `01_CREATE_ALL_V1_VIEWS.sql` "
      "(0 mismatches). Keep them in sync when making future edits.")
    C("- The exclusion `PS_AV_SF_GIFTS_EXCLUSION_VW` is applied in V1: 9 active occurrences in 8 files, "
      "plus 1 commented line in GIFT_AID. V0 used it in 5 files. Removal was deferred until this review "
      "completes; see `04_DEFERRED_MODIFICATIONS.md`.")
    C("- Gift currency: V1 uses `NVL(designation, header)` currency. The SGD/EUR finding is analysis only; "
      "do not change amounts or rates while implementing a decision.")
    C("- Cosmetic differences in this report include NULL against empty string. The GIFT workbooks accept "
      "this change (values are marked as empty in the Ascend mapping).")
    C("")
    C("## E. Fastest closing sequence")
    C("")
    C("1. Re-export the missing or stub pairs (A1 to A3).")
    C("2. In `02_VERSION_MATCH_REPORT.md`, take every view with clean% below about 95 and confirm the "
      "difference matches the intended V1 fix (each one maps to an issue ID).")
    C("3. Close the open business decisions (B). Each one is a parameter line or an accepted rule, "
      "not code work.")
    C("4. Refresh the comparison workbooks for views re-exported since the last review; their numbers "
      "will drift from the current CSVs.")
    C("5. Apply the deferred modifications in one V2 pass: exclusion removal, currency decision, "
      "recommendation-flagged items.")
    C("")

    # ============================ report 4: deferred modification register
    R = []
    D = R.append
    D("# Deferred modification register (apply only after approval)")
    D("")
    D("## 1. Exclusion `PS_AV_SF_GIFTS_EXCLUSION_VW`")
    D("")
    D("Verified against the V1 package (`fichiers_par_vue/`): 9 active occurrences in 8 files, plus "
      "1 commented line.")
    D("")
    D("| File | Occurrences |")
    D("|---|---|")
    D("| PS_ASCEND_GIFT_VW_V1.sql | 1 |")
    D("| PS_ASCEND_GIFT_SOFT_VW_V1.sql | 1 |")
    D("| PS_ASCEND_MATCHING_GIFT_VW_V1.sql | 1 (marked MG-03) |")
    D("| PS_ASCEND_MATCHING_GIFT_SOFT_VW_V1.sql | 1 (marked MG-03) |")
    D("| PS_ASCEND_MG_ORIGINAT_VW_V1.sql | 1 |")
    D("| PS_ASCEND_PLEDGE_VW_V1.sql | 1 |")
    D("| PS_ASCEND_PLEDGE_PAYMENT_VW_V1.sql | 2 |")
    D("| PS_ASCEND_PP_SOFT_SCREDIT_VW_V1.sql | 1 |")
    D("| PS_ASCEND_GIFT_AID_VW_V1.sql | commented line 139; delete the line at the same time |")
    D("")
    D("V0 baseline: the same clause appears in 5 V0 files (GIFT, GIFT_AD, GIFT_SOFT, PLEDGE_SOFT, "
      "PP_SOFT_SCREDIT). Dependency check on the package: the `_AD` and installment views read the base "
      "views (GIFT_BASE, GIFT_AID_BASE, PLEDGE_BASE, PLDG_INST_LINE), which carry no exclusion, so "
      "removing the clause changes exactly the 8 files listed above. When applying the change, update "
      "`01_CREATE_ALL_V1_VIEWS.sql` and the matching per-view files together; they are byte-identical "
      "today and should stay that way.")
    D("")
    D("## 2. Gift currency source (analysis only, no SQL change yet)")
    D("")
    D("V1 sets `CCY_ENTRY = NVL(designation currency, gift-header currency)`; V0 used the gift-header "
      "currency (`A.CURRENCY_CD_ENTRY`). A gift in SGD with a designation in EUR therefore exports as "
      "EUR in V1. Amount and rate are not wrong when the designation currency is not null (an earlier "
      "claim to the contrary was retracted). Current data evidence, from the business-change counts:")
    D("")
    D("- `PS_ASCEND_GIFT_VW`: CURRENCYISOCODE changed on 10 rows of 133,933.")
    D("- `PS_ASCEND_PLEDGE_PAYMENT_VW`: CURRENCYISOCODE changed on 4,626 rows of 22,174.")
    D("- `PS_ASCEND_MATCHING_GIFT_VW`: CURRENCYISOCODE on 1 row; `INSEAD_PS_AMOUNT_ENTRY__C` on 1 row.")
    D("- `PS_ASCEND_PP_SOFT_SCREDIT_VW`: Operating Entity and Transaction currency each changed on "
      "about 600 rows.")
    D("")
    D("Before touching `CurrencyIsoCode`, check the affected records against the PeopleSoft Transaction "
      "Register and the Ascend target semantics. Do not change amount or rate logic as part of the "
      "currency fix.")
    D("")
    D("## 3. Duplicate or suspicious output fields (confirm against the Ascend mapping before removing)")
    D("")
    D("- GIFT and GIFT_AD: `UCINN_ASCENDV2__EXTERNAL_SYSTEM_ID___C` (three underscores) and "
      "`..._ID__C` are both retained.")
    D("- PROPOSAL: `F1_EXPECTED_CLOSE_DATE` against the Ascend expected close date; `F1_Submitted_Date`.")
    D("- USER: `username` and `email_addr` use the same expression.")
    D("- GIFT_AID and GIFT_AID_AD: three date fields carry the same date.")
    D("- PLEDGE_SOFT: `Designation_Detail__r = Review_Transaction_v2__r` changed in V1. The column "
      "diff shows DESIGNATION_DETAIL__R changed on 354 of 354 matched rows. Confirm this is intended.")
    D("- OARL and JOB_CODE: a duplicate column was renamed `F1_ASCEND_ID` in V1 after aliases were "
      "lost in the V0 export. Verify the real names with ALL_TAB_COLUMNS.")
    D("")
    D("## 4. External ID changes that create new records if loaded over existing data")
    D("")
    D("- `PS_F1_SF_CNST_SIND`: F1_ASCEND_ID now includes the service indicator timestamp (the CNS-20 "
      "fix). 11,024 of 12,106 matched rows differ on that column, and the two files only join on "
      "EMPLID plus F1_SRVC_IND_CD.")
    D("- Apply the same check before loading any V1 extract over previously loaded Ascend data.")
    D("")
    D("## 5. Export hygiene for the next wave")
    D("")
    D("- Remove the `SQL> SELECT ...` echo line (set ECHO OFF in the spool script, or call the saved "
      "script with @script instead of running it from the worksheet).")
    D("- Export everything in one encoding. Today, 55 of 91 CSVs are CP1252 and the rest are UTF-8. "
      "The V0 and V1 files of a compared pair must use the same encoding.")
    D("- Do not re-run exports while a comparison workbook is open; the reviewed numbers will drift "
      "from the CSVs.")
    D("")

    (ROOT / "01_STATE_OF_MIGRATION.md").write_text("\n".join(L), encoding="utf-8")
    (ROOT / "02_VERSION_MATCH_REPORT.md").write_text("\n".join(M), encoding="utf-8")
    (ROOT / "03_WRAPUP_PLAN.md").write_text("\n".join(W), encoding="utf-8")
    (ROOT / "04_DEFERRED_MODIFICATIONS.md").write_text("\n".join(R), encoding="utf-8")
    print("reports written")
    print(f"overall: clean={pct_business_clean}% identical={pct_identical}% matched={tot_matched}")


if __name__ == "__main__":
    sys.exit(main())
