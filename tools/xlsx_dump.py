# -*- coding: utf-8 -*-
"""Read-only dump of comparison workbooks to JSON (stdlib only, no openpyxl).
NEVER writes to the .xlsx files - only opens them as zip archives for reading.
Run: python -I xlsx_dump.py
"""
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PS = ROOT.parent
OUT = ROOT / "out" / "xlsx_dump"
OUT.mkdir(parents=True, exist_ok=True)
MAX_ROWS = 5000  # cap per sheet

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def col_to_idx(ref: str) -> int:
    letters = re.match(r"([A-Z]+)", ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_shared_strings(zf):
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out = []
    for si in root.findall("m:si", NS):
        out.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    return out


def sheet_names(zf):
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid2target = {rel.get("Id"): rel.get("Target") for rel in rels}
    sheets = []
    for sh in wb.find("m:sheets", NS):
        rid = sh.get("{%s}id" % NS["r"])
        target = rid2target.get(rid, "").lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        sheets.append((sh.get("name"), target))
    return sheets


def read_sheet(zf, path, sstrings):
    root = ET.fromstring(zf.read(path))
    rows = []
    for row in root.iter("{%s}row" % NS["m"]):
        cells = {}
        for c in row.findall("m:c", NS):
            ref = c.get("r") or ""
            t = c.get("t")
            v = c.find("m:v", NS)
            isel = c.find("m:is", NS)
            if t == "s" and v is not None:
                idx = int(v.text) if v.text else -1
                val = sstrings[idx] if 0 <= idx < len(sstrings) else ""
            elif t == "inlineStr" and isel is not None:
                val = "".join(x.text or "" for x in isel.iter("{%s}t" % NS["m"]))
            elif v is not None:
                val = v.text or ""
            else:
                val = ""
            if val != "":
                cells[col_to_idx(ref) if ref else len(cells)] = val
        if cells:
            width = max(cells) + 1
            rows.append([cells.get(i, "") for i in range(width)])
        if len(rows) >= MAX_ROWS:
            rows.append(["__TRUNCATED_AT_%d_ROWS__" % MAX_ROWS])
            break
    return rows


def main():
    files = sorted(list((PS / "Completed").glob("*.xlsx")) + list((PS / "Testing").glob("*.xlsx")))
    index = []
    for f in files:
        try:
            with zipfile.ZipFile(f) as zf:
                sstrings = read_shared_strings(zf)
                sheets = sheet_names(zf)
                dump = {"file": f.name, "folder": f.parent.name, "sheets": {}}
                for name, path in sheets:
                    try:
                        dump["sheets"][name] = read_sheet(zf, path, sstrings)
                    except Exception as e:  # noqa: BLE001 - report and continue
                        dump["sheets"][name] = [["__ERROR__", str(e)]]
            dest = OUT / (f.parent.name + "__" + f.stem.replace(" ", "_") + ".json")
            json.dump(dump, dest.open("w", encoding="utf-8"), ensure_ascii=False)
            sizes = {k: len(v) for k, v in dump["sheets"].items()}
            index.append({"file": f.name, "folder": f.parent.name, "sheets": sizes,
                          "dump": dest.name})
            print(f"OK  {f.parent.name}/{f.name}: {sizes}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {f.parent.name}/{f.name}: {e}")
            index.append({"file": f.name, "folder": f.parent.name, "error": str(e)})
    json.dump(index, (ROOT / "out" / "xlsx_index.json").open("w", encoding="utf-8"),
              indent=1, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
