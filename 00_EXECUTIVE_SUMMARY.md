# Executive summary: PeopleSoft to Salesforce Ascend data migration review

Documents: **Executive summary (you are here)** | [State of migration](01_STATE_OF_MIGRATION.md) | [Match report](02_VERSION_MATCH_REPORT.md) | [Wrap-up plan](03_WRAPUP_PLAN.md) | [Deferred changes](04_DEFERRED_MODIFICATIONS.md) | [README](README.md)

## What this is

This review checks the extract scripts that move INSEAD Advancement data from PeopleSoft (Oracle, schema CSOADM) to Salesforce Ascend, together with the data those scripts produced. It covers the original script package (called V0), the revised package (called V1), and the export files of both versions. Everything was checked read-only; nothing in the source system was changed.

## Bottom line

- The revised package is ready. 71 database views deploy with a single script, and the package is internally consistent (0 mismatches between its files).
- The data holds up. Of 2,135,477 records compared between the old and new exports, 96.57% carry no business change and 88.53% are identical down to the character. Every remaining difference traces to a deliberate fix, listed per view.
- The review workbook logged 158 issues; 128 are fixed in V1. The rest are 8 partial fixes, 12 recommendations, and 14 questions for the business.
- Three exports need to be re-run, and one cleanup pass (called V2) is planned but deliberately not applied yet.

## How the comparison worked

Each old script was paired with its new version and compared as text. Each old export file was paired with its new export and compared record by record, using the record's external ID as the match key. Differences were classified two ways: cosmetic (capitalisation, NULL against empty string, trailing spaces) and business (a real value change). Only business changes count against the percentages above.

## What remains before load

1. Re-run the three missing or empty exports (details in the wrap-up plan, section A).
2. Close the 14 questions for the business (wrap-up plan, section B). Each answer is a parameter change or an accepted rule, not development work.
3. Refresh the comparison workbooks for views re-exported since the last review.
4. Apply the planned changes in one V2 pass (deferred changes document): remove the gift exclusion clause, settle the currency question, and the recommendation items.

## Watch items

- External IDs changed for scholarship records (the fix intentionally added a timestamp). Loading over data already in Ascend would create duplicates instead of updates.
- Export files arrive in two different encodings, and every file starts with a command echo line. Both need cleaning before the Salesforce load.
- Do not re-run exports while a comparison workbook is open; the reviewed numbers will no longer match the files.

## Glossary

| Term | Meaning |
|---|---|
| V0 | The original PeopleSoft extract scripts and their export files |
| V1 | The revised script package delivered for this review |
| Business change | A real value difference between V0 and V1 data |
| Cosmetic change | Formatting-only difference (case, NULL against empty string, spaces) |
| Match key | The external ID used to pair records between the V0 and V1 exports |

## Where to find details

| Question | Read |
|---|---|
| Where does each view stand? | [01 State of migration](01_STATE_OF_MIGRATION.md) |
| Which views match, and by how much? | [02 Match report](02_VERSION_MATCH_REPORT.md) |
| What is left to do, in order? | [03 Wrap-up plan](03_WRAPUP_PLAN.md) |
| What changes are planned but not applied? | [04 Deferred changes](04_DEFERRED_MODIFICATIONS.md) |
| How was this produced, and how do I re-run it? | [README](README.md) |
