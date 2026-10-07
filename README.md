# Migration review: PeopleSoft CSOADM to Salesforce Ascend

Generated analysis for the INSEAD Advancement data migration review. Everything in this folder is
generated output. No file outside this folder was created or modified, and the Excel workbooks in
`PS_2_SF/Completed/` and `PS_2_SF/Testing/` were opened read-only and never written to.

## Reports

| File | Content |
|---|---|
| `01_STATE_OF_MIGRATION.md` | Where the project stands: per-view status (SQL, data, workbook verdicts) |
| `02_VERSION_MATCH_REPORT.md` | V0 against V1 match percentages per view, key join with business and cosmetic diff classification |
| `03_WRAPUP_PLAN.md` | Remaining work in fastest order: data gaps, open decisions, partial fixes |
| `04_DEFERRED_MODIFICATIONS.md` | Changes deliberately not applied yet (exclusion removal, currency, duplicate fields) |

## Folder layout

- `tools/` contains the analysis scripts (Python standard library only, nothing to install):
  - `sql_analyze.py` parses the V0 and V1 SQL, measures per-view similarity, and checks that the
    per-view files match `01_CREATE_ALL_V1_VIEWS.sql`.
  - `csv_analyze.py` performs the first-pass row-level hash comparison.
  - `csv_deep.py` performs the definitive key-join comparison with per-column business and
    cosmetic classification.
  - `xlsx_dump.py` reads the workbooks (read-only) and dumps their contents to JSON.
  - `build_reports.py` assembles the four reports from the JSON results.
- `out/` holds the raw results (`sql_report.json`, `csv_report.json`, `csv_keydiff.json`,
  workbook dumps and run logs). It contains exported CRM data and is excluded from version control.
- `ref/` holds read-only extracts of the two SQL zip packages (`V0_package`, `V1_package`).
  It is excluded from version control.

## Regenerate

```bash
cd YoucefVersion
python -I tools/xlsx_dump.py       # refresh workbook dumps (read-only)
python -I tools/sql_analyze.py     # refresh the SQL layer
python -I tools/csv_deep.py        # refresh the data layer (about 10 minutes for the largest CSVs)
python -I tools/build_reports.py   # rebuild the four reports
```

## Data quirks the tools already handle

Know these before trusting any CSV in this project:

1. Every CSV starts with a `SQL> SELECT ...` echo line and a blank line before the real header.
2. 55 of 91 CSVs are CP1252-encoded, not UTF-8. Reading them as UTF-8 turns accented characters
   into mojibake.
3. The business key lives in `UCINN_ASCENDV2__EXTERNAL_SYSTEM_ID__C`, or in `F1_ASCEND_ID` or
   `EMPLID` for the F1 views.
4. Diff classification: cosmetic means case-only differences, NULL against empty string,
   whitespace, or trailing punctuation. Everything else counts as a business change.
