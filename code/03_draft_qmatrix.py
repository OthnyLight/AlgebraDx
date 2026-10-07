#!/usr/bin/env python3
"""Step 3 — pre-fill a Q-matrix draft for Othniel to rule on.

Reads the item metadata written by 02_extract_us.py (or the item-information file directly)
and proposes skill codes for every Algebra item and every Number item that touches an
algebra-readiness skill, using the keyword lists in qmatrix/attributes.csv.

    python code/03_draft_qmatrix.py --source timss2023
    python code/03_draft_qmatrix.py --source timss2019

Writes two files:
    qmatrix/qmatrix_<source>_draft.csv      item IDs + 0/1 skill columns + status. Public-safe:
                                            no item text. This is the file that gets reviewed,
                                            edited and eventually committed.
    data/extract/qmatrix_<source>_review.csv  same rows plus the item label/description and
                                            the matched keywords, to review against. Local only.

The keyword pre-fill is a convenience, not a coding decision. Every row starts with
status = "[VERIFY]"; change it to "ok" (or edit the 0/1 cells) as each item is ruled on.
fit scripts refuse to treat a Q-matrix as final while any "[VERIFY]" remains.
"""
import argparse
import os
import re
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from algebradx import AttributeDictionary  # noqa: E402

DOMAIN_DEFAULT = {  # fallback when no keyword matches, by TIMSS topic area
    "expressions": "A05", "equation": "A07", "relationship": "A11", "function": "A11",
}
STATUS = "[" + "VERIFY" + "]"   # written into the output; split here so the gate scans outputs, not this script


def propose(text, dictionary):
    hits = {}
    t = text.lower()
    for _, r in dictionary.table.iterrows():
        kws = [k.strip().lower() for k in str(r.get("timss_keywords", "")).split(";") if k.strip()]
        found = [k for k in kws if re.search(r"\b" + re.escape(k), t)]
        if found:
            hits[r["code"]] = found
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, choices=["timss2023", "timss2019"])
    ap.add_argument("--items", help="item metadata CSV (default data/extract/<source>_items.csv)")
    a = ap.parse_args()
    d = AttributeDictionary.from_csv(os.path.join(ROOT, "qmatrix", "attributes.csv"))
    path = a.items or os.path.join(ROOT, "data", "extract", f"{a.source}_items.csv")
    items = pd.read_csv(path, dtype=str).fillna("")
    rows, review = [], []
    for _, it in items.iterrows():
        dom = it["content_domain"].lower()
        if not ("algebra" in dom or "number" in dom):
            continue
        # keywords are matched on the item's own description; the topic area is only a fallback,
        # because topic names such as "Expressions, Operations, and Equations" match everything
        hits = propose(it["label"], d)
        note = ""
        if not hits:
            hits = propose(it["topic"], d)
            note = "matched on topic area only" if hits else ""
        if "number" in dom:
            hits = {k: v for k, v in hits.items() if k in ("A01", "A02", "A03")}
            if not hits:
                continue                      # number item outside the readiness skills
        if not hits:
            for key, code in DOMAIN_DEFAULT.items():
                if key in it["topic"].lower():
                    hits = {code: ["(topic default)"]}
                    break
            note = "no keyword match"
        row = {"item": it["item"], "source": a.source, "content_domain": it["content_domain"],
               "topic": it["topic"]}
        for c in d.codes:
            row[c] = int(c in hits)
        row["status"] = STATUS
        rows.append(row)
        review.append({**row, "label": it["label"], "matched": "; ".join(
            f"{k}: {', '.join(v)}" for k, v in hits.items()), "note": note})
    q = pd.DataFrame(rows)
    out = os.path.join(ROOT, "qmatrix", f"qmatrix_{a.source}_draft.csv")
    q.to_csv(out, index=False)
    rv = os.path.join(ROOT, "data", "extract", f"qmatrix_{a.source}_review.csv")
    pd.DataFrame(review).to_csv(rv, index=False)
    print(f"{len(q)} items drafted -> {out}")
    print("items per skill:", q[d.codes].sum().to_dict())
    print(f"items with no keyword match: {sum(r['note'] != '' for r in review)}  (see {rv})")


if __name__ == "__main__":
    main()
