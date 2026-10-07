#!/usr/bin/env python3
"""Step 3b — the v0.1 Q-matrix for TIMSS 2019 and 2023 grade 8 (US eTIMSS forms).

These codes were drafted from the official item-information files (topic area, cognitive
area, item type and the short item label), replacing the keyword pre-fill of
03_draft_qmatrix.py with item-by-item judgment, and were ruled on by the author on 2026-10-07.

confidence: H = the label states the task unambiguously; M = plausible reading of the label;
L = the label is too thin to know what the item demands — check against the item itself
(available to registered users through IEA; released items in the TIMSS released-item sets).

Items deliberately left out (whole-number place value and computation, primes and factors,
number puzzles) are listed in EXCLUDED with the reason; they are not algebra-readiness skills.

    python code/03b_qmatrix_draft_v01.py
writes qmatrix/qmatrix_timss_v01.csv (IDs + codes, shareable) and
data/extract/qmatrix_timss_review_v01.csv (adds IEA labels; local only).
"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from algebradx import AttributeDictionary  # noqa: E402

# item: (skills, confidence, note)
Q = {
    # ---------------- TIMSS 2023 (and trend items shared with 2019) ----------------
    "ME72188": ("A01", "H", ""),
    "ME72035": ("A01 A07", "H", "fraction coefficient in a one-step equation"),
    "ME72055": ("A01 A02", "H", "percent-fraction-decimal equivalence"),
    "ME72222": ("A03 A04", "H", "substitution into a square-root expression"),
    "ME72090": ("A06 A07", "M", "write an inequality from a geometric situation"),
    "ME72233": ("A06 A07", "M", "balance model; may be solvable arithmetically"),
    "ME72106A": ("A10", "H", "extend pattern to figure 7"),
    "ME72106B": ("A10", "H", "far term (figure 50) needs the rule"),
    "ME72106C": ("A10 A06", "H", "state the rule symbolically"),
    "ME72001": ("A01", "H", "signed-number product/sum"),
    "ME72019": ("A01", "H", ""),
    "ME72189": ("A01", "H", ""),
    "ME72024": ("A01", "H", ""),
    "ME72043": ("A02", "H", ""),
    "ME72221": ("A04 A03", "H", "quadratic expression evaluated at a value"),
    "ME72220": ("A05", "H", "distribute and combine like terms incl. negative factor"),
    "ME72225": ("A06 A07", "L", "label 'number of pizzas' — check what is required"),
    "ME72110A": ("A10", "H", ""),
    "ME72110B": ("A10 A06", "H", ""),
    "ME82214A": ("A01", "H", ""),
    "ME82214B": ("A01", "H", ""),
    "MQ82N03": ("A06 A07", "L", "problem-solving item; may be arithmetic only"),
    "ME82320": ("A02", "H", ""),
    "MQ72D01": ("A02", "H", ""),
    "MQ72D02B": ("A06 A11", "M", "formula relating two measured quantities"),
    "MQ72D03": ("A04", "M", "apply the formula"),
    "MQ72D06A": ("A02 A04", "M", ""),
    "MQ72D06B": ("A02 A04", "M", ""),
    "MQ72D07A": ("A02 A04", "M", "speed from formula"),
    "MQ72D07B": ("A02 A04", "M", "2-point justification"),
    "MQ72D08A": ("A02 A11", "M", ""),
    "MQ72D08B": ("A02 A11", "M", ""),
    "MQ82C01": ("A06", "H", ""),
    "MQ82C02": ("A06 A07", "M", "profit target -> set up and solve"),
    "MQ82C03": ("A08 A06", "M", "two pricing plans equal — break-even"),
    "MQ82C05": ("A02", "L", "maximum points — check whether proportional"),
    "ME82116": ("A01", "H", "negative temperature on a scale"),
    "ME82322": ("A02", "H", ""),
    "ME82199B": ("A02", "M", ""),
    "ME82106": ("A01", "L", "number pyramid — check whether negatives/algebra involved"),
    "ME82309": ("A02", "H", ""),
    "ME82403": ("A06 A05", "M", "perimeter as an expression, simplified"),
    "ME82205": ("A01", "H", ""),
    "ME82512": ("A12", "H", "compare rates of change of lines"),
    "ME82201": ("A01", "M", "fractions of an amount, working backwards"),
    "ME82310": ("A01 A02", "H", ""),
    "ME82112": ("A01", "H", ""),
    "ME82203": ("A01", "H", ""),
    "ME82404": ("A07", "H", ""),
    "ME82206": ("A01", "H", ""),
    "ME82103": ("A01", "H", ""),
    "ME62271": ("A01", "M", ""),
    "ME62215": ("A02", "H", ""),
    "ME62143": ("A02", "H", ""),
    "ME62230": ("A05 A09", "H", "simplify rational expression by factoring numerator"),
    "ME62095": ("A06 A12", "H", "linear cost model"),
    "ME62076": ("A06", "M", ""),
    "ME62030": ("A11 A12", "H", "read and extend a linear table"),
    "ME82104": ("A01", "H", "order negative temperatures"),
    "ME82402": ("A05", "H", ""),
    "ME82410": ("A06 A07", "M", ""),
    "ME82315": ("A02", "H", ""),
    "ME62214": ("A01", "M", "decimal money"),
    "ME62146": ("A02", "H", ""),
    "ME62154": ("A02", "H", ""),
    "ME62067": ("A07", "H", ""),
    "ME62341": ("A12", "H", ""),
    "ME62242": ("A12 A11", "H", ""),
    "ME82216": ("A01", "H", ""),
    "ME82105": ("A04", "L", "order expressions in N — may be A05 (compare forms)"),
    "ME82405": ("A04", "H", ""),
    "ME82313": ("A02", "H", "constant rate"),
    "ME82503": ("A11 A12", "M", "equation fitting a table"),
    "ME82407": ("A05", "L", "'Is Peggy correct' — check the claim"),
    "ME82312A": ("A02", "M", ""),
    "ME82312B": ("A01 A02", "M", ""),
    "ME82420": ("A04 A05", "H", "x + 2x"),
    "ME82510": ("A11", "H", "read sign of y from a graph"),
    "ME82207": ("A01", "H", ""),
    "ME82219": ("A01", "H", ""),
    "ME82415": ("A06 A07", "H", ""),
    "ME82314": ("A02", "H", ""),
    "ME82411": ("A07 A05", "H", "variables on both sides with brackets"),
    "ME82511": ("A11 A10", "M", ""),
    "ME72178": ("A03", "H", "perfect squares"),
    "ME72020": ("A01", "H", ""),
    "ME72027": ("A01", "H", ""),
    "ME72052": ("A02 A11", "H", "proportional table"),
    "ME72067": ("A04 A01", "H", "substitution with a negative value"),
    "ME72083A": ("A06 A07", "M", ""),
    "ME72083B": ("A06 A07", "H", "inequality from context"),
    "ME72108A": ("A10", "H", ""),
    "ME72108B": ("A10 A06", "H", ""),
    "ME72021": ("A02 A01", "H", "equivalent fractions / proportion"),
    "ME72026": ("A01", "H", ""),
    "ME72041A": ("A02", "H", ""),
    "ME72041B": ("A02", "H", ""),
    "ME72223": ("A06", "H", ""),
    "ME72094": ("A07", "H", ""),
    "ME72059": ("A04 A06", "M", ""),
    "ME72080": ("A05", "H", ""),
    "ME72081": ("A08 A06", "H", "write a pair of equations"),
    "ME72187": ("A03", "H", ""),
    "ME72022": ("A01", "H", "product of points on a number line"),
    "ME72038": ("A01", "H", ""),
    "ME72045": ("A02", "H", ""),
    "ME72049": ("A02", "H", ""),
    "ME72069": ("A04", "H", ""),
    "ME72074": ("A05", "H", ""),
    "ME72013": ("A04", "M", ""),
    "ME72095": ("A08", "H", ""),
    "ME72109": ("A11 A06", "H", ""),
    # ---------------- TIMSS 2019 only ----------------
    "ME52024": ("A01", "H", ""),
    "ME52058B": ("A02", "H", ""),
    "ME52229": ("A01", "H", ""),
    "ME52063": ("A06 A05", "H", ""),
    "ME52072": ("A03 A05", "H", "laws of exponents"),
    "ME52146A": ("A10", "H", ""),
    "ME52146B": ("A10 A06", "H", ""),
    "ME52092": ("A12 A11", "H", ""),
    "ME72007": ("A01", "M", ""),
    "ME72025": ("A01", "H", ""),
    "ME72017": ("A01", "M", ""),
    "ME72190": ("A02", "M", ""),
    "ME72068": ("A05", "H", ""),
    "ME72076": ("A05 A09 A03", "H", "common factor with exponents"),
    "ME72056": ("A04", "H", ""),
    "ME72098": ("A06 A07", "H", ""),
    "ME72103": ("A12", "H", ""),
    "ME62164": ("A01", "H", ""),
    "ME62142": ("A02 A01", "H", ""),
    "ME62084": ("A07", "H", ""),
    "ME62351": ("A12", "H", ""),
    "ME62223": ("A06 A05", "H", ""),
    "ME62027": ("A12 A11", "H", ""),
    "ME52413": ("A01", "M", ""),
    "ME52134": ("A01", "H", ""),
    "ME52078": ("A02", "H", ""),
    "ME52034": ("A01", "H", ""),
    "ME52174A": ("A02", "L", "kilocalories — check whether a rate"),
    "ME52174B": ("A02", "L", ""),
    "ME52130": ("A05", "H", ""),
    "ME52073": ("A04 A01", "H", ""),
    "ME52110": ("A04", "H", "formula substitution"),
    "ME52105": ("A12", "H", ""),
    "ME62150": ("A01", "H", ""),
    "ME62335": ("A02", "H", ""),
    "ME62219": ("A02", "H", ""),
    "ME62149": ("A06", "H", ""),
    "ME62241": ("A12 A06", "H", ""),
    "ME62105": ("A06 A09 A05", "H", "expand x(2x + 1); 2-point item"),
    "ME52079": ("A02", "H", ""),
    "ME52215": ("A01", "H", ""),
    "ME52147": ("A02", "L", "'which statement is true' — check"),
    "ME52067": ("A04", "H", ""),
    "ME52068": ("A05", "H", ""),
    "ME52087": ("A08", "H", ""),
    "ME62151": ("A02", "H", ""),
    "ME62346": ("A02", "H", "unit price"),
    "ME62212": ("A01", "M", ""),
    "ME62056": ("A05", "H", ""),
    "ME62317": ("A11 A04", "H", "table from a quadratic rule"),
    "ME62350": ("A12", "H", ""),
    "ME62078": ("A06 A07", "H", ""),
}

EXCLUDED = {
    "ME72002": "perfect numbers (number theory)", "ME82111": "primes", "ME82109": "place value",
    "ME82101": "whole-number digit puzzle", "ME62001": "whole-number multiplication",
    "ME62152": "whole-number division in context", "ME82119": "number puzzle",
    "ME72234": "whole-number reasoning", "ME72005": "factors", "ME52058A": "time arithmetic",
    "ME52125": "multiples", "ME62005": "whole-number division", "ME62139": "whole-number word problem",
    "ME62002": "digit placement puzzle", "ME52204": "primes", "ME52364": "whole-number word problem",
    "ME62329": "place value",
}


def main():
    d = AttributeDictionary.from_csv(os.path.join(ROOT, "qmatrix", "attributes.csv"))
    items_dir = os.path.join(ROOT, "data", "raw", "items")
    t23 = pd.read_excel(os.path.join(items_dir, "T23_ItemInformation_G8.xlsx"), sheet_name="T23 G8")
    t19 = pd.read_excel(os.path.join(items_dir, "eT19_G8_Item Information.xlsx"), sheet_name="MAT")
    t19.columns = [c.replace("\n", " ") for c in t19.columns]
    meta = pd.concat([t23.assign(cycle="2023"), t19.assign(cycle="2019")])
    meta = meta[meta["Subject"] == "M"]
    in23 = set(t23["Item ID"])
    in19 = set(t19["Item ID"])
    rows, review = [], []
    status = "ok"   # all rows ruled on by the author, 2026-10-07 (qmatrix/CHANGELOG.md)
    for item, (codes, conf, note) in Q.items():
        m = meta[meta["Item ID"] == item].iloc[0]
        r = {"item": item, "in_2023": int(item in in23), "in_2019": int(item in in19),
             "content_domain": m["Content Domain"], "topic": m["Topic Area"],
             "max_points": int(m["Maximum Points"])}
        for c in d.codes:
            r[c] = int(c in codes.split())
        r.update({"confidence": conf, "status": status})
        rows.append(r)
        review.append({**r, "label": m["Label"], "cognitive_area": m.get("Cognitive Area", m.get("Cognitive Domain")),
                       "item_type": m["Item Type"], "note": note})
    q = pd.DataFrame(rows)
    q.to_csv(os.path.join(ROOT, "qmatrix", "qmatrix_timss_v01.csv"), index=False)
    os.makedirs(os.path.join(ROOT, "data", "extract"), exist_ok=True)
    pd.DataFrame(review).to_csv(os.path.join(ROOT, "data", "extract", "qmatrix_timss_review_v01.csv"), index=False)
    pd.Series(EXCLUDED, name="reason").rename_axis("item").to_csv(
        os.path.join(ROOT, "qmatrix", "excluded_items_v01.csv"))
    for cyc in ("2023", "2019"):
        s = q[q[f"in_{cyc}"] == 1]
        single = s[s[d.codes].sum(1) == 1]
        print(f"TIMSS {cyc}: {len(s)} items; per skill:",
              {c: int(s[c].sum()) for c in d.codes}, "| single-skill:",
              {c: int(single[c].sum()) for c in d.codes})
    print("confidence:", q["confidence"].value_counts().to_dict(), "| excluded:", len(EXCLUDED))


if __name__ == "__main__":
    main()
