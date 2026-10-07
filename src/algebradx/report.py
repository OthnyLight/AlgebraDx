"""Teacher-facing skill reports.

The posterior probability that a student has mastered a skill is turned into one of three
plain-language statuses:

* **mastered**      p >= upper (default 0.8)
* **not yet**       p <= lower (default 0.2)
* **uncertain**     otherwise — the test did not give enough evidence either way

A three-way split is more honest than a single 0.5 cut when a student answered only a
few items on a skill (common with rotated booklets), and it tells the teacher where a
quick check-in would settle the question.
"""
from __future__ import annotations

import html

import numpy as np
import pandas as pd


def mastery_status(p, lower: float = 0.2, upper: float = 0.8):
    p = np.asarray(p)
    return np.where(p >= upper, "mastered", np.where(p <= lower, "not yet", "uncertain"))


def long_scores(scores: pd.DataFrame, attributes, names=None, lower=0.2, upper=0.8,
                id_col: str = "id") -> pd.DataFrame:
    """One row per student x skill, with probability and status."""
    if id_col not in scores.columns:
        scores = scores.assign(**{id_col: np.arange(1, len(scores) + 1)})
    names = names or {}
    rows = []
    for a in attributes:
        p = scores[f"p_{a}"].to_numpy()
        rows.append(pd.DataFrame({id_col: scores[id_col], "skill": a,
                                  "skill_name": names.get(a, a), "p_mastery": p,
                                  "status": mastery_status(p, lower, upper)}))
    return pd.concat(rows, ignore_index=True)


def group_summary(scores: pd.DataFrame, attributes, names=None, group=None, weights=None,
                  lower=0.2, upper=0.8) -> pd.DataFrame:
    """Share of students (optionally weighted, optionally by group) in each status."""
    df = scores.copy()
    df["_w"] = 1.0 if weights is None else np.asarray(weights, dtype=float)
    df["_g"] = "all" if group is None else np.asarray(group)
    names = names or {}
    rows = []
    for g, d in df.groupby("_g"):
        W = d["_w"].sum()
        for a in attributes:
            p = d[f"p_{a}"].to_numpy()
            st = mastery_status(p, lower, upper)
            rows.append({"group": g, "skill": a, "skill_name": names.get(a, a), "n": len(d),
                         "expected_mastery": float((d["_w"] * p).sum() / W),
                         "share_mastered": float(d["_w"][st == "mastered"].sum() / W),
                         "share_uncertain": float(d["_w"][st == "uncertain"].sum() / W),
                         "share_not_yet": float(d["_w"][st == "not yet"].sum() / W)})
    return pd.DataFrame(rows)


def html_report(scores: pd.DataFrame, attributes, names=None, title="Skill report",
                id_col: str = "id", lower=0.2, upper=0.8, max_students: int = 500,
                banner: str | None = None) -> str:
    """A self-contained HTML table: one row per student, one coloured cell per skill."""
    names = names or {}
    if id_col not in scores.columns:
        scores = scores.assign(**{id_col: np.arange(1, len(scores) + 1)})
    sub = scores.head(max_students)
    colours = {"mastered": "#1b7837", "uncertain": "#b8860b", "not yet": "#b2182b"}
    head = "".join(f"<th title='{html.escape(names.get(a, a))}'>{html.escape(a)}</th>"
                   for a in attributes)
    body = []
    for _, r in sub.iterrows():
        cells = []
        for a in attributes:
            p = r[f"p_{a}"]
            s = str(mastery_status(p, lower, upper))
            cells.append(f"<td style='color:{colours[s]}' title='{s}'>{p:.2f}</td>")
        body.append(f"<tr><td>{html.escape(str(r[id_col]))}</td>{''.join(cells)}</tr>")
    legend = " ".join(f"<span style='color:{c}'>■ {s}</span>" for s, c in colours.items())
    key = "".join(f"<li><b>{html.escape(a)}</b> {html.escape(names.get(a, ''))}</li>"
                  for a in attributes)
    ban = f"<p class='banner'>{html.escape(banner)}</p>" if banner else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{html.escape(title)}</title>
<style>body{{font-family:system-ui,sans-serif;margin:16px;background:#fff;color:#111}}
table{{border-collapse:collapse;font-variant-numeric:tabular-nums}}
td,th{{border:1px solid #ddd;padding:3px 6px;text-align:center}}
.banner{{background:#fff3cd;padding:6px 10px;border:1px solid #e0c36b}}
.wrap{{overflow-x:auto}}</style></head><body>
<h1>{html.escape(title)}</h1>{ban}
<p>Each cell is the probability the student has mastered the skill. {legend}
(mastered &ge; {upper}, not yet &le; {lower}).</p>
<div class='wrap'><table><tr><th>Student</th>{head}</tr>{''.join(body)}</table></div>
<h2>Skills</h2><ul>{key}</ul></body></html>"""
