#!/usr/bin/env python3
"""Step 2 — pull the United States grade-8 rows and the mathematics item columns out of the
TIMSS 2019/2023 and PISA 2022 files, then score them 0 / 1 / missing.

Run on your own computer after 01_fetch.py:

    python code/02_extract_us.py --inspect      # print what the files contain; check first
    python code/02_extract_us.py                # extract + score everything

Outputs (local only — never committed or deposited, per IEA/OECD terms):
    data/extract/<source>_usa_scored.csv.gz     id, weights, jackknife vars, one column per item
    data/extract/<source>_items.csv             item id, type, key, points, content domain, topic
    data/extract/<source>_scoring_log.csv       per item: rule used and counts of each outcome

Every assumption this script makes about file and variable names is printed with
--inspect so it can be checked against the user guide before anything is fitted.
"""
import argparse
import fnmatch
import os
import re
import sys
import zipfile

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from algebradx import datasets as DS  # noqa: E402
from algebradx.sav import read_sav  # noqa: E402  (pure-Python fallback when pyreadstat is absent)

RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "extract")

TIMSS = {
    # source: (data zip, item-information file, US achievement-file name pattern)
    "timss2023": ("T23_Data_SPSS_G8.zip", "T23_ItemInformation_G8.xlsx", "bsausa*8.sav"),
    "timss2019": ("T19_G8_SPSS_Data.zip", "T19_G8_Item_Information.zip", "bsausa*7.sav"),
}
ID_VARS = ["IDCNTRY", "IDSCHOOL", "IDCLASS", "IDSTUD", "IDBOOK", "TOTWGT", "JKZONE", "JKREP", "ITSEX"]
PV_VARS = [f"BSMMAT0{i}" for i in range(1, 6)] + [f"BSMALG0{i}" for i in range(1, 6)]


def _extract_member(zpath, pattern, dest_dir):
    with zipfile.ZipFile(zpath) as z:
        hits = [n for n in z.namelist() if fnmatch.fnmatch(os.path.basename(n).lower(), pattern)]
        if not hits:
            raise FileNotFoundError(f"no member matching {pattern} in {zpath}")
        name = hits[0]
        target = os.path.join(dest_dir, os.path.basename(name))
        if not os.path.exists(target):
            z.extract(name, dest_dir)
            os.replace(os.path.join(dest_dir, name), target)
        return target


def read_item_information(path):
    """Read the TIMSS item-information workbook (directly or inside a zip) into one table."""
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            xl = [n for n in z.namelist() if n.lower().endswith((".xlsx", ".xls"))]
            math = [n for n in xl if "math" in n.lower()] or xl
            frames = [pd.read_excel(z.open(n), sheet_name=None) for n in math]
    else:
        frames = [pd.read_excel(path, sheet_name=None)]
    tabs = []
    for book in frames:
        for sheet, df in book.items():
            # header row may not be the first row: find the row that contains an item-ID header
            already = any(str(c).strip().lower() == "item id" for c in df.columns)
            for i in range(0 if already else min(10, len(df))):
                row = df.iloc[i].astype(str).str.lower()
                if row.str.contains("item id|item_id|itemid|variable").any():
                    df.columns = df.iloc[i]
                    df = df.iloc[i + 1:]
                    break
            df = df.assign(_sheet=sheet)
            tabs.append(df)
    info = pd.concat(tabs, ignore_index=True)
    cols = info.columns
    c_id = DS.find_column(cols, "item id", "variable", "itemid")
    c_type = DS.find_column(cols, "item type", "type", "format")
    c_key = DS.find_column(cols, "key", "correct response")
    c_pts = DS.find_column(cols, "maximum points", "max points", "points")
    c_dom = DS.find_column(cols, "content domain", "domain")
    c_top = DS.find_column(cols, "topic")
    c_cog = DS.find_column(cols, "cognitive domain", "cognitive")
    c_lab = DS.find_column(cols, "label", "description", "title")
    out = pd.DataFrame({
        "item": info[c_id].astype(str).str.strip() if c_id else None,
        "type": info[c_type].astype(str) if c_type else "",
        "key": info[c_key] if c_key else np.nan,
        "max_points": pd.to_numeric(info[c_pts], errors="coerce") if c_pts else 1,
        "content_domain": info[c_dom].astype(str) if c_dom else "",
        "topic": info[c_top].astype(str) if c_top else "",
        "cognitive_domain": info[c_cog].astype(str) if c_cog else "",
        "label": info[c_lab].astype(str) if c_lab else "",
        "sheet": info["_sheet"],
    })
    out = out[out["item"].str.match(r"^M[A-Z0-9]{4,}", na=False)].drop_duplicates("item")
    mapping = dict(id=c_id, type=c_type, key=c_key, points=c_pts, domain=c_dom, topic=c_top,
                   cognitive=c_cog, label=c_lab)
    return out.reset_index(drop=True), mapping


def is_mc(t, key):
    t = str(t).lower()
    return ("mc" in t or "multiple" in t or "choice" in t) or (
        pd.notna(key) and str(key).strip().upper() in list("ABCDE12345"))


def key_to_code(key):
    k = str(key).strip().upper()
    if k in "ABCDE" and len(k) == 1:
        return "ABCDE".index(k) + 1
    try:
        return int(float(k))
    except ValueError:
        return None


def _find_sav(zpath, pattern, tmp):
    """Use an already-extracted US file in data/raw if present, else pull it from the zip."""
    for d in (RAW, tmp):
        for fn in os.listdir(d) if os.path.isdir(d) else []:
            if fnmatch.fnmatch(fn.lower(), pattern):
                return os.path.join(d, fn)
    return _extract_member(zpath, pattern, tmp)


def timss(source, inspect=False, partial="zero"):
    zname, iname, pattern = TIMSS[source]
    zpath, ipath = os.path.join(RAW, zname), os.path.join(RAW, iname)
    tmp = os.path.join(OUT, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    sav = _find_sav(zpath, pattern, tmp)
    if not os.path.exists(ipath):
        ipath = os.path.join(RAW, "items", iname)
    items, mapping = read_item_information(ipath)
    full, meta = read_sav(sav)
    cols = list(full.columns)
    item_cols = [c for c in cols if c in set(items["item"])]
    if inspect:
        print(f"\n== {source}: {os.path.basename(sav)}  ({len(cols)} variables)")
        print("item-information columns detected:", mapping)
        print(f"math items in item info: {len(items)}; present in data: {len(item_cols)}")
        print("content domains:", items["content_domain"].value_counts().to_dict())
        print("id/weight vars present:", {v: v in cols for v in ID_VARS})
        for c in item_cols[:4]:
            print(f"  {c}: value labels {meta.value_labels.get(c, {})}")
        return
    df = full[[v for v in ID_VARS + PV_VARS if v in cols] + item_cols]
    if "TOTWGT" not in df.columns:
        raise SystemExit("TOTWGT not in the achievement file: merge from the BSG file (see user guide)")
    log = []
    scored = {}
    for _, r in items[items["item"].isin(item_cols)].iterrows():
        x = df[r["item"]]
        if DS.already_scored(x):
            s = DS.score_pisa(x, max_credit=int(r["max_points"]) if pd.notna(r["max_points"]) else None,
                              partial=partial)
            rule = "pre-scored"
        elif is_mc(r["type"], r["key"]) and key_to_code(r["key"]) is not None:
            s = DS.score_timss_mc(x, key_to_code(r["key"]))
            rule = f"MC key={key_to_code(r['key'])}"
        else:
            pts = int(r["max_points"]) if pd.notna(r["max_points"]) else 1
            s = DS.score_timss_cr(x, max_points=pts, partial=partial)
            rule = f"CR max={pts}"
        scored[r["item"]] = s
        log.append({"item": r["item"], "rule": rule, "n_seen": int((~np.isnan(s)).sum()),
                    "p_correct": float(np.nanmean(s)) if (~np.isnan(s)).any() else np.nan,
                    "n_raw_missing": int(x.isna().sum())})
    out = pd.concat([df[[v for v in ID_VARS + PV_VARS if v in df.columns]].reset_index(drop=True),
                     pd.DataFrame(scored)], axis=1)
    out.insert(0, "id", out["IDSTUD"].astype("int64").astype(str) if "IDSTUD" in out else np.arange(len(out)))
    out.to_csv(os.path.join(OUT, f"{source}_usa_scored.csv.gz"), index=False)
    items.to_csv(os.path.join(OUT, f"{source}_items.csv"), index=False)
    pd.DataFrame(log).to_csv(os.path.join(OUT, f"{source}_scoring_log.csv"), index=False)
    print(f"{source}: {len(out):,} US students, {len(scored)} math items scored -> data/extract/")


def pisa(inspect=False, partial="zero", with_weights=True):
    import pyreadstat
    tmp = os.path.join(OUT, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    cog = _extract_member(os.path.join(RAW, "PISA2022_STU_COG_SPSS.zip"), "*cog*.sav", tmp)
    meta = pyreadstat.read_sav(cog, metadataonly=True)[1]
    cols = meta.column_names
    math = [c for c in cols if re.match(r"^[CD]M\d{3}Q\d{2}[SC]$", c)]
    if inspect:
        print(f"\n== pisa2022: {os.path.basename(cog)} ({len(cols)} variables); scored math items: {len(math)}")
        for c in math[:4]:
            print(f"  {c}: value labels {meta.variable_value_labels.get(c, {})}")
        print("CNT present:", "CNT" in cols, "| W_FSTUWT present:", "W_FSTUWT" in cols)
        return
    keep = ["CNT", "CNTSCHID", "CNTSTUID"] + [c for c in ("W_FSTUWT", "BOOKID") if c in cols] + math
    parts = []
    for chunk, _ in pyreadstat.read_file_in_chunks(pyreadstat.read_sav, cog, chunksize=50000,
                                                   usecols=keep):
        parts.append(chunk[chunk["CNT"] == "USA"])
    df = pd.concat(parts, ignore_index=True)
    if with_weights:
        qqq = _extract_member(os.path.join(RAW, "PISA2022_STU_QQQ_SPSS.zip"), "*stu*qqq*.sav", tmp)
        wcols = ["CNT", "CNTSTUID", "W_FSTUWT"] + [f"W_FSTURWT{i}" for i in range(1, 81)]
        wparts = []
        for chunk, _ in pyreadstat.read_file_in_chunks(pyreadstat.read_sav, qqq, chunksize=50000,
                                                       usecols=wcols):
            wparts.append(chunk[chunk["CNT"] == "USA"])
        w = pd.concat(wparts, ignore_index=True).drop(columns="CNT")
        df = df.drop(columns=[c for c in ("W_FSTUWT",) if c in df.columns]).merge(w, on="CNTSTUID", how="left")
    log, scored = [], {}
    for c in math:
        s = DS.score_pisa(df[c], partial=partial)
        if (~np.isnan(s)).sum() == 0:
            continue
        scored[c] = s
        log.append({"item": c, "rule": "pisa scored", "n_seen": int((~np.isnan(s)).sum()),
                    "p_correct": float(np.nanmean(s))})
    idcols = [c for c in df.columns if c in ("CNTSCHID", "CNTSTUID", "BOOKID", "W_FSTUWT")
              or c.startswith("W_FSTURWT")]
    out = pd.concat([df[idcols].reset_index(drop=True), pd.DataFrame(scored)], axis=1)
    out.insert(0, "id", out["CNTSTUID"].astype("int64").astype(str))
    out.to_csv(os.path.join(OUT, "pisa2022_usa_scored.csv.gz"), index=False)
    pd.DataFrame(log).to_csv(os.path.join(OUT, "pisa2022_scoring_log.csv"), index=False)
    print(f"pisa2022: {len(out):,} US students, {len(scored)} math items scored -> data/extract/")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", choices=["timss2023", "timss2019", "pisa2022"])
    ap.add_argument("--inspect", action="store_true", help="print file contents and detected mappings only")
    ap.add_argument("--partial", choices=["zero", "one"], default="zero",
                    help="score partial credit on 2-point items as 0 (default) or 1")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for s in a.only or ["timss2023", "timss2019", "pisa2022"]:
        if s == "pisa2022":
            pisa(a.inspect, a.partial)
        else:
            timss(s, a.inspect, a.partial)


if __name__ == "__main__":
    main()
