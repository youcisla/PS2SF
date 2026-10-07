# -*- coding: utf-8 -*-
"""Definitive V0 vs V1 comparison: key-join with per-column diff classification.

CSV layout from SQL Developer (verified on disk):
  line 1: 'SQL> SELECT ...' echo   -> SKIPPED
  line 2: blank                    -> SKIPPED
  line 3: real header (quoted)     -> HEADER
  rest  : data

Metrics per pair:
  - matched keys, v0-only keys, v1-only keys, blank-key rows
  - identical rows, changed rows
  - per-column change counts, split cosmetic (NULL<->empty or whitespace-only) vs business
  - amount sums per decimal column

Run: python -I csv_deep.py   -> out/csv_keydiff.json  (checkpoint per pair)
"""
import codecs
import csv
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PS = ROOT.parent
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

KEY_PREF_ORDER = [
    "UCINN_ASCENDV2__EXTERNAL_SYSTEM_ID__C",
    "F1_ASCEND_ID",
    "EXTERNAL_SYSTEM_ID",
    "INSEAD_EXTERNAL_SYSTEM_ID__C",
    "EMPLID",
]
KEY_NAME_HINT = re.compile(r"(EXTERNAL_SYSTEM_ID|F1_ASCEND_ID|^EMPLID$|_ASCEND_ID|RECORD_KEY|UNIQUE_ID)", re.I)
AMOUNT_HINT = re.compile(r"(AMOUNT|_AMT|VALUE|TOTAL|BALANCE)", re.I)


BOM_JUNK = ("﻿", "ï»¿", "ï»¿".upper())


def clean_cell(c: str) -> str:
    c = c or ""
    for junk in BOM_JUNK:
        if c.startswith(junk):
            c = c[len(junk):]
    return c


def detect_encoding(path: Path) -> str:
    """Scan the whole file with an incremental UTF-8 decoder; first invalid byte => cp1252.
    ASCII-only files pass as utf-8 (equivalent)."""
    dec = codecs.getincrementaldecoder("utf-8")()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                return "utf-8"
            try:
                dec.decode(chunk)
            except UnicodeDecodeError:
                return "cp1252"


def open_csv(path: Path):
    """Return (header, row_iterator). Skips SQL> echo lines and leading blanks.
    Decodes utf-8 when valid else cp1252; strips BOM leftovers in either case."""
    enc = "utf-8-sig" if detect_encoding(path) == "utf-8" else "cp1252"
    raw = path.open("r", encoding=enc, errors="replace" if enc == "cp1252" else "strict", newline="")
    rd = csv.reader(raw)
    for row in rd:
        if not row:
            continue
        first = clean_cell(row[0]).strip()
        if first.upper().startswith("SQL>"):
            continue
        header = [clean_cell(c).strip().upper() for c in row]
        return header, rd
    raise ValueError(f"no header found in {path}")


def norm(f: str) -> str:
    return (f or "").strip()


def pick_key(h0, h1, rows_probe):
    common = [c for c in h0 if c in h1]
    prefs = [c for c in KEY_PREF_ORDER if c in common]
    cands = prefs + [c for c in common if c not in prefs and KEY_NAME_HINT.search(c)]
    best, best_ratio = None, 0.0
    for c in cands[:8]:
        i0 = h0.index(c)
        vals = [norm(r[i0]) for r in rows_probe if i0 < len(r) and norm(r[i0])]
        if not vals:
            continue
        ratio = len(set(vals)) / len(vals)
        if ratio > best_ratio:
            best, best_ratio = c, ratio
        if c in KEY_PREF_ORDER[:2] and ratio > 0.95:
            return c, ratio
    return best, best_ratio


def collect(path: Path, keycols):
    """Return (header, {key: [row,...]}, blank_key_count). keycols = list of column names."""
    if isinstance(keycols, str):
        keycols = [keycols]
    header, rd = open_csv(path)
    kis = [header.index(k) for k in keycols if k in header]
    d = {}
    blank = 0
    for row in rd:
        if not any(norm(c) for c in row):
            continue
        k = "\x1f".join(norm(row[i]) if i < len(row) else "" for i in kis)
        if not k or all(part.upper() == "NULL" for part in k.split("\x1f")):
            blank += 1
            continue
        d.setdefault(k, []).append(tuple(norm(c) for c in row))
    return header, d, blank


TRIM_CHARS = " - –—,:;."


def classify(a: str, b: str) -> str:
    """cosmetic if only case / NULL-empty / whitespace / trailing punctuation differ; else business."""
    if a == b:
        return "same"
    la, lb = a.strip().upper(), b.strip().upper()
    if la in {"", "NULL"} and lb in {"", "NULL"}:
        return "cosmetic_null_empty"
    if la == lb:
        return "cosmetic_case"
    na = " ".join(a.replace(" ", " ").split())
    nb = " ".join(b.replace(" ", " ").split())
    if na == nb:
        return "cosmetic_ws"
    if na.strip(TRIM_CHARS) == nb.strip(TRIM_CHARS):
        return "cosmetic_norm"
    return "business"


def analyze(name: str, p0: Path, p1: Path, probe_limit=20000):
    h0, r0 = open_csv(p0)
    h1, _ = open_csv(p1)
    probe = []
    for i, row in enumerate(r0):
        probe.append(row)
        if i >= probe_limit:
            break
    key, ratio = pick_key(h0, h1, probe)
    if not key:
        return {"view": name, "key": None, "note": "no usable key column found"}

    def compute(keycols):
        label = "+".join(keycols)
        cols0, d0, blank0 = collect(p0, keycols)
        cols1, d1, blank1 = collect(p1, keycols)
        common_cols = [c for c in cols0 if c in cols1]
        idx0 = {c: cols0.index(c) for c in common_cols}
        idx1 = {c: cols1.index(c) for c in common_cols}
        keys0, keys1 = set(d0), set(d1)
        matched = keys0 & keys1
        identical = changed = dup_keys = 0
        col_change = {c: {"business": 0, "cosmetic": 0} for c in common_cols}
        row_has_business_change = 0
        for k in matched:
            rows_a, rows_b = d0[k], d1[k]
            if len(rows_a) != 1 or len(rows_b) != 1:
                dup_keys += 1
                continue
            a, b = rows_a[0], rows_b[0]
            r_changed, r_business = False, False
            for c in common_cols:
                va = a[idx0[c]] if idx0[c] < len(a) else ""
                vb = b[idx1[c]] if idx1[c] < len(b) else ""
                cls = classify(va, vb)
                if cls == "same":
                    continue
                r_changed = True
                if cls == "business":
                    col_change[c]["business"] += 1
                    r_business = True
                else:
                    col_change[c]["cosmetic"] += 1
            if r_changed:
                changed += 1
            else:
                identical += 1
            if r_business:
                row_has_business_change += 1
        return {
            "key": label,
            "matched_keys": len(matched),
            "v0_only_keys": len(keys0 - keys1),
            "v1_only_keys": len(keys1 - keys0),
            "blank_key_rows_v0": blank0, "blank_key_rows_v1": blank1,
            "duplicate_key_groups": dup_keys,
            "identical_rows": identical,
            "changed_rows_any": changed,
            "changed_rows_business": row_has_business_change,
            "pct_rows_identical": round(100.0 * identical / max(1, identical + changed), 2),
            "pct_rows_no_business_change": round(100.0 * (identical + changed - row_has_business_change) / max(1, identical + changed), 2),
            "columns_changed_business_total": sum(v["business"] for v in col_change.values()),
            "columns_changed_cosmetic_total": sum(v["cosmetic"] for v in col_change.values()),
            "per_column": {c: v for c, v in sorted(col_change.items(), key=lambda kv: -(kv[1]["business"] + kv[1]["cosmetic"])) if v["business"] or v["cosmetic"]},
        }

    res = {"view": name}
    r = compute([key])
    r["key_uniqueness_probe"] = round(ratio, 3)
    if r["matched_keys"] == 0 and all(c in h0 and c in h1 for c in ("EMPLID", "F1_SRVC_IND_CD")):
        r = compute(["EMPLID", "F1_SRVC_IND_CD"])
        r["key_uniqueness_probe"] = None
        r["note"] = f"single key '{key}' matched 0; fell back to composite EMPLID+F1_SRVC_IND_CD"
    res.update(r)

    def sums(path):
        header, rd = open_csv(path)
        amt = [i for i, c in enumerate(header) if AMOUNT_HINT.search(c)]
        s = {header[i]: Decimal(0) for i in amt}
        for row in rd:
            for i in amt:
                if i < len(row):
                    v = norm(row[i]).replace(",", "").replace(" ", "")
                    if v and v.upper() != "NULL":
                        try:
                            s[header[i]] += Decimal(v)
                        except InvalidOperation:
                            pass
        return {k: str(v) for k, v in s.items()}

    res["amount_sums_v0"] = sums(p0)
    res["amount_sums_v1"] = sums(p1)
    return res


def main():
    pairs = {}
    for folder in ("Completed", "Testing"):
        d = PS / folder
        for v0 in sorted(d.glob("*_V0.csv")):
            base = v0.name[:-7]
            v1 = d / (base + "_V1.csv")
            if v1.exists() and base not in pairs:
                pairs[base] = (v0, v1)
    results = []
    for base, (v0, v1) in sorted(pairs.items()):
        print(f"=== {base} ===", flush=True)
        try:
            r = analyze(base, v0, v1)
        except Exception as e:  # noqa: BLE001
            r = {"view": base, "error": str(e)}
            print(f"  ERROR {e}", flush=True)
        if "matched_keys" in r:
            print(f"  key={r['key']} matched={r['matched_keys']} v0only={r['v0_only_keys']} v1only={r['v1_only_keys']} "
                  f"identical={r['identical_rows']} identical%={r['pct_rows_identical']} "
                  f"business-change rows={r['changed_rows_business']}", flush=True)
        results.append(r)
        json.dump(results, (OUT / "csv_keydiff.json").open("w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
