# -*- coding: utf-8 -*-
"""V0 vs V1 CSV comparison for the migration review (read-only).
Per pair: row counts, unique-row overlap (hash based, memory-safe via sort),
key-column overlap, amount-column sums, header diff.
Run: python -I csv_analyze.py [--only NAME]
"""
import csv
import hashlib
import json
import subprocess
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PS = ROOT.parent
OUT = ROOT / "out"
TMP = OUT / "tmp"
TMP.mkdir(parents=True, exist_ok=True)

KEY_PREFS = ["F1_ASCEND_ID", "EXTERNAL_SYSTEM_ID__C", "EXTERNAL_SYSTEM_ID___C", "ASCEND_ID"]
AMOUNT_RE = ("AMOUNT", "AMT", "VALUE", "TOTAL", "BALANCE", "_SUM")


def h8(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode("utf-8", "replace"), digest_size=8).digest(), "big")


def norm_field(f: str) -> str:
    return (f or "").strip()


def hash_file(src: Path, dest: Path, mode: str, key_idx=None):
    """mode 'row' = hash each data row; 'key' = hash one column. Returns (ncols, header, nrows)."""
    with src.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd, None) or []
        n = 0
        with dest.open("w", encoding="utf-8", newline="\n") as out:
            for row in rd:
                if not any(r.strip() for r in row):
                    continue
                if mode == "key":
                    if key_idx is None or key_idx >= len(row):
                        continue
                    val = norm_field(row[key_idx])
                else:
                    val = "\x1f".join(norm_field(r) for r in row)
                out.write(f"{h8(val):016x}\n")
                n += 1
    return len(header), header, n


def sort_uniq(src: Path, dest: Path) -> int:
    """Deduplicate + sort hash lines in pure Python (Windows has no reliable sort in subprocess PATH)."""
    with src.open() as fh:
        seen = {int(line, 16) for line in fh if line.strip()}
    with dest.open("w", encoding="utf-8", newline="\n") as out:
        out.write("\n".join(f"{x:016x}" for x in sorted(seen)))
        out.write("\n")
    return len(seen)


def merge_count(a: Path, b: Path) -> int:
    common = 0
    with a.open() as fa, b.open() as fb:
        la, lb = fa.readline(), fb.readline()
        while la and lb:
            if la == lb:
                common += 1
                la, lb = fa.readline(), fb.readline()
            elif la < lb:
                la = fa.readline()
            else:
                lb = fb.readline()
    return common


def count_lines(p: Path) -> int:
    n = 0
    with p.open() as fh:
        for _ in fh:
            n += 1
    return n


def scan_stats(src: Path):
    """Second pass: header, amount sums, ncols regularity."""
    with src.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd, None) or []
        amt_idx = [i for i, h in enumerate(header)
                   if any(tok in (h or "").upper() for tok in AMOUNT_RE)]
        sums = {header[i]: Decimal(0) for i in amt_idx}
        bad_cols = 0
        n = 0
        for row in rd:
            if not any(r.strip() for r in row):
                continue
            n += 1
            if len(row) != len(header):
                bad_cols += 1
            for i in amt_idx:
                if i < len(row):
                    v = row[i].strip().replace(" ", "").replace(" ", "")
                    if v and v.upper() != "NULL":
                        try:
                            sums[header[i]] += Decimal(v)
                        except InvalidOperation:
                            pass
    return {"header": header, "amount_sums": {k: str(v) for k, v in sums.items()},
            "rows_irregular_ncols": bad_cols, "nrows": n}


def analyze_pair(v0: Path, v1: Path, name: str):
    res = {"view": name, "v0_file": v0.name, "v1_file": v1.name}
    h0 = TMP / f"{name}.v0.hashes"
    h1 = TMP / f"{name}.v1.hashes"
    s0 = TMP / f"{name}.v0.sorted"
    s1 = TMP / f"{name}.v1.sorted"

    ncols0, head0, n0 = hash_file(v0, h0, "row")
    ncols1, head1, n1 = hash_file(v1, h1, "row")
    u0 = sort_uniq(h0, s0)
    u1 = sort_uniq(h1, s1)
    common = merge_count(s0, s1)

    res.update({
        "rows_v0": n0, "rows_v1": n1,
        "unique_rows_v0": u0, "unique_rows_v1": u1,
        "common_rows": common,
        "row_match_pct_v1": round(100.0 * common / u1, 2) if u1 else None,
        "row_match_pct_max": round(100.0 * common / max(u0, u1), 2) if max(u0, u1) else None,
        "ncols_v0": ncols0, "ncols_v1": ncols1,
        "headers_equal": head0 == head1,
        "headers_v0_only": [h for h in head0 if h not in head1],
        "headers_v1_only": [h for h in head1 if h not in head0],
    })

    key0 = next((h for h in KEY_PREFS if h in head0), None)
    key1 = next((h for h in KEY_PREFS if h in head1), None)
    if key0 and key1:
        k0, k1 = TMP / f"{name}.k0.raw", TMP / f"{name}.k1.raw"
        ks0, ks1 = TMP / f"{name}.k0.sorted", TMP / f"{name}.k1.sorted"
        hash_file(v0, k0, "key", head0.index(key0))
        hash_file(v1, k1, "key", head1.index(key1))
        ku0 = sort_uniq(k0, ks0)
        ku1 = sort_uniq(k1, ks1)
        kc = merge_count(ks0, ks1)
        res["key_column"] = {"v0": key0, "v1": key1,
                             "unique_v0": ku0, "unique_v1": ku1, "common": kc,
                             "key_match_pct_v1": round(100.0 * kc / ku1, 2) if ku1 else None}
    else:
        res["key_column"] = {"v0": key0, "v1": key1, "note": "key column not on both sides"}

    res["v0"] = scan_stats(v0)
    res["v1"] = scan_stats(v1)
    return res


def main():
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    pairs = {}
    for folder in ("Completed", "Testing"):
        d = PS / folder
        for v0 in sorted(d.glob("*_V0.csv")):
            base = v0.name[:-7]          # strip _V0.csv
            v1 = d / (base + "_V1.csv")
            if v1.exists() and base not in pairs:
                pairs[base] = (v0, v1)
    results = []
    for base, (v0, v1) in sorted(pairs.items()):
        if only and only not in base:
            continue
        print(f"=== {base} ===", flush=True)
        r = analyze_pair(v0, v1, base)
        print(f"  rows V0={r['rows_v0']} V1={r['rows_v1']} | unique V0={r['unique_rows_v0']} V1={r['unique_rows_v1']} | common={r['common_rows']}", flush=True)
        print(f"  row match {r['row_match_pct_max']}% (of max) | key match {r['key_column'].get('key_match_pct_v1')}%", flush=True)
        results.append(r)
        json.dump(results, (OUT / "csv_report.json").open("w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)  # checkpoint after each pair


if __name__ == "__main__":
    sys.exit(main())
