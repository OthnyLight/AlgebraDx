"""Scoring rules and helpers for TIMSS and PISA item-response files.

These functions turn raw responses into the 0 / 1 / missing matrix a diagnostic model
needs. The rules follow the TIMSS 2019 and 2023 international database user guides and
the PISA 2022 codebook, and each is a documented, overridable choice:

TIMSS (per the user guides; confirm against the guide for the cycle you use)
    multiple choice    option chosen 1-5; correct if equal to the key
    constructed resp.  two-digit codes: first digit 1 = 1 point, 2 = 2 points,
                       7 = incorrect; 9x = omitted / not reached
    omitted            coded 9 (MC) or 99 (CR)            -> 0      (``omitted='incorrect'``)
    not reached        coded 6 (MC) or 96 (CR)            -> missing (``not_reached='missing'``)
    not administered   system missing                     -> missing
    two-point items    1 only at full credit              (``partial='zero'``)

PISA 2022 scored cognitive variables (names ending in S or C)
    0 = no credit, 1 = full (or partial when a 2 exists), 2 = full credit;
    codes 5-9 are non-response / not administered / invalid.  By default:
    7 (not administered) -> missing; 6 (not reached) -> missing; 9 (no response) -> 0;
    5 and 8 -> missing.

Item content is not shipped with the package; only item identifiers appear in Q-matrices.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TIMSS_MC_OMIT, TIMSS_MC_NR = 9, 6
TIMSS_CR_OMIT, TIMSS_CR_NR = 99, 96


def score_timss_mc(raw, key, omitted: str = "incorrect", not_reached: str = "missing"):
    raw = pd.to_numeric(pd.Series(raw), errors="coerce").to_numpy(dtype=float)
    out = np.where(np.isnan(raw), np.nan, (raw == float(key)).astype(float))
    out = np.where(raw == TIMSS_MC_OMIT, 0.0 if omitted == "incorrect" else np.nan, out)
    out = np.where(raw == TIMSS_MC_NR, 0.0 if not_reached == "incorrect" else np.nan, out)
    # any other code outside the option range (e.g. invalid 7/8) is treated as missing
    valid = np.isnan(raw) | np.isin(raw, [1, 2, 3, 4, 5, TIMSS_MC_OMIT, TIMSS_MC_NR])
    return np.where(valid, out, np.nan)


def score_timss_cr(raw, max_points: int = 1, omitted: str = "incorrect",
                   not_reached: str = "missing", partial: str = "zero"):
    raw = pd.to_numeric(pd.Series(raw), errors="coerce").to_numpy(dtype=float)
    first = np.floor(raw / 10)
    pts = np.where(first == 1, 1, np.where(first == 2, 2, np.where(first == 7, 0, np.nan)))
    if max_points >= 2:
        full = pts == max_points
        part = pts == 1
        score = np.where(full, 1.0, np.where(part, 0.0 if partial == "zero" else 1.0,
                                             np.where(pts == 0, 0.0, np.nan)))
    else:
        score = np.where(pts >= 1, 1.0, np.where(pts == 0, 0.0, np.nan))
    score = np.where(raw == TIMSS_CR_OMIT, 0.0 if omitted == "incorrect" else np.nan, score)
    score = np.where(raw == TIMSS_CR_NR, 0.0 if not_reached == "incorrect" else np.nan, score)
    return np.where(np.isnan(raw), np.nan, score)


def already_scored(values) -> bool:
    """True when a column holds only 0/1/2 and missing (the file is pre-scored)."""
    v = pd.to_numeric(pd.Series(values), errors="coerce").dropna().unique()
    return len(v) > 0 and set(v) <= {0, 1, 2}


def score_pisa(raw, max_credit: int | None = None, no_response: str = "incorrect",
               partial: str = "zero"):
    raw = pd.to_numeric(pd.Series(raw), errors="coerce").to_numpy(dtype=float)
    if max_credit is None:
        vals = set(np.unique(raw[~np.isnan(raw)]))
        max_credit = 2 if 2 in vals else 1
    out = np.full(raw.shape, np.nan)
    out[raw == 0] = 0
    if max_credit == 2:
        out[raw == 2] = 1
        out[raw == 1] = 0 if partial == "zero" else 1
    else:
        out[raw == 1] = 1
    out[raw == 9] = 0 if no_response == "incorrect" else np.nan
    return out


def find_column(columns, *candidates):
    """First column whose lower-cased name contains every word of one candidate phrase."""
    low = {c: str(c).lower() for c in columns}
    for cand in candidates:
        words = cand.lower().split()
        for c, l in low.items():
            if all(w in l for w in words):
                return c
    return None
