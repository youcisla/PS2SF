# -*- coding: utf-8 -*-
"""SQL V0 vs V1 analysis for the PeopleSoft->Ascend migration review.
Read-only on all reference data. Writes JSON into YoucefVersion/out/.
Run: python -I sql_analyze.py
"""
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # YoucefVersion/tools
ROOT = HERE.parent                               # YoucefVersion
PS = ROOT.parent                                 # PS_2_SF
V0_DIR = PS                                       # root *.sql = V0 package (verified identical to PS ADV Extracts.zip)
V1_CREATE_ALL = ROOT / "ref" / "V1_package" / "01_CREATE_ALL_V1_VIEWS.sql"
V1_PERVIEW = ROOT / "ref" / "V1_package" / "fichiers_par_vue"
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

CREATE_RE = re.compile(
    r"CREATE\s+OR\s+REPLACE\s+(?:FORCE\s+)?(?:EDITIONABLE\s+|NONEDITIONABLE\s+)?VIEW\s+([A-Za-z0-9_$.]+)",
    re.IGNORECASE,
)


def norm(text: str) -> str:
    """Normalize SQL for similarity: lowercase, strip comments, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"--[^\n]*", " ", text)          # line comments
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)  # block comments
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def norm_lines(text: str) -> list:
    out = []
    for ln in text.lower().splitlines():
        ln = re.sub(r"\s+", " ", ln).strip()
        if ln and not ln.startswith("--"):
            out.append(ln)
    return out


def strip_comments(text: str) -> str:
    """Remove SQL comments with a small state machine that respects string literals,
    so a '/*' token inside a quoted string cannot swallow later statements."""
    out = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "'":
                if i + 1 < n and text[i + 1] == "'":   # escaped quote
                    out.append("'")
                    i += 2
                    continue
                in_str = False
            i += 1
            continue
        if ch == "'":
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "-" and i + 1 < n and text[i + 1] == "-":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_create_all(path: Path):
    raw = strip_comments(path.read_text(encoding="utf-8-sig", errors="replace"))
    matches = [m for m in CREATE_RE.finditer(raw) if m.group(1).split(".")[-1][0].isalpha()]
    blocks = {}
    for i, m in enumerate(matches):
        name = m.group(1).split(".")[-1].upper()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        blocks[name] = raw[start:end]
    return blocks


def main():
    v0 = {p.stem.upper(): p.read_text(encoding="utf-8-sig", errors="replace")
          for p in sorted(V0_DIR.glob("*.sql"))}

    blocks = parse_create_all(V1_CREATE_ALL)
    perview = {}
    for p in sorted(V1_PERVIEW.glob("*.sql")):
        txt = strip_comments(p.read_text(encoding="utf-8-sig", errors="replace"))
        ms = [m for m in CREATE_RE.finditer(txt) if m.group(1).split(".")[-1][0].isalpha()]
        for i, m in enumerate(ms):
            name = m.group(1).split(".")[-1].upper()
            end = ms[i + 1].start() if i + 1 < len(ms) else len(txt)
            perview[name] = {"file": p.name, "body": txt[m.start():end]}

    report = {
        "v0_count": len(v0),
        "v1_create_all_count": len(blocks),
        "v1_perview_count": len(perview),
        "v1_in_create_all_not_perview": sorted(set(blocks) - set(perview)),
        "v1_in_perview_not_create_all": sorted(set(perview) - set(blocks)),
        "views": [],
    }

    v1_names = set(blocks.keys()) | set(perview.keys())
    unmatched_v0, matched_v1 = [], set()

    for stem, body in sorted(v0.items()):
        cand = [n for n in v1_names if n == stem + "_V1"]
        if not cand:
            cand = [n for n in v1_names if n.removesuffix("_V1") == stem]
        if cand:
            v1name = cand[0]
            matched_v1.add(v1name)
            block = blocks.get(v1name) or perview.get(v1name, {}).get("body", "")
            n0, n1 = norm(body), norm(block)
            ratio = difflib.SequenceMatcher(None, n0, n1, autojunk=False).ratio() if n1 else 0.0
            l0, l1 = norm_lines(body), norm_lines(block)
            sm = difflib.SequenceMatcher(None, l0, l1, autojunk=False)
            changed = sum(max(i2 - i1, j2 - j1)
                          for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal")
            pv = perview.get(v1name)
            consist = None
            if pv and v1name in blocks:
                consist = norm(pv["body"]) == norm(blocks[v1name])
            report["views"].append({
                "view": stem, "v1_view": v1name,
                "v0_lines": len(l0), "v1_lines": len(l1),
                "changed_lines": changed,
                "sql_similarity_pct": round(ratio * 100, 1),
                "identical_normalized": n0 == n1,
                "perview_file": pv["file"] if pv else None,
                "perview_matches_create_all": consist,
            })
        else:
            unmatched_v0.append(stem)

    report["v0_without_v1"] = unmatched_v0
    report["v1_without_v0"] = sorted(v1_names - matched_v1)

    json.dump(report, (OUT / "sql_report.json").open("w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    print(f"V0 files: {len(v0)}")
    print(f"V1 views in 01_CREATE_ALL: {len(blocks)}")
    print(f"V1 per-view files: {len(perview)}")
    print(f"V1 in create-all but not per-view: {report['v1_in_create_all_not_perview']}")
    print(f"V1 in per-view but not create-all: {report['v1_in_perview_not_create_all']}")
    print(f"V0 without V1 pair: {unmatched_v0}")
    print(f"V1 without V0 counterpart (new): {report['v1_without_v0']}")
    incons = [v['v1_view'] for v in report['views'] if v['perview_matches_create_all'] is False]
    print(f"per-view file differs from create-all block: {len(incons)} {incons[:12]}")
    ident = sum(1 for v in report['views'] if v['identical_normalized'])
    print(f"views identical V0 vs V1 (normalized): {ident}/{len(report['views'])}")


if __name__ == "__main__":
    sys.exit(main())
