#!/usr/bin/env python3
"""Step 1 — download the public TIMSS and PISA files, with provenance.

Run on your own computer (the files total ~2.5 GB):

    pip install -e ".[data]"
    python code/01_fetch.py                  # everything
    python code/01_fetch.py --only timss2023 # one source

Downloads resume if interrupted. Each finished file gets a line in
data/raw/PROVENANCE.txt (date, name, bytes, SHA-256, URL).

Terms. TIMSS data: IEA, non-commercial educational and research use, attribution
required, no redistribution without IEA permission. PISA data: OECD terms of use.
Nothing in data/raw or data/extract is committed or deposited; see .gitignore.
"""
import argparse
import datetime
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

# URLs confirmed on the publishers' pages on 2026-10-06.
SOURCES = {
    "timss2023": [
        ("T23_Data_SPSS_G8.zip", "https://timss2023.org/wp-content/uploads/data/T23_Data_SPSS_G8.zip"),
        ("T23_ItemInformation_G8.xlsx", "https://timss2023.org/wp-content/uploads/data/T23_ItemInformation_G8.xlsx"),
        ("T23_UG-International-Database.pdf", "https://timss2023.org/wp-content/uploads/data/T23_UG-International-Database.pdf"),
    ],
    "timss2019": [
        ("T19_G8_SPSS_Data.zip", "https://timss2019.org/international-database/downloads/T19_G8_SPSS%20Data.zip"),
        ("T19_G8_Item_Information.zip", "https://timss2019.org/international-database/downloads/T19_G8_Item%20Information.zip"),
        ("T19_User_Guide_2nd_Ed.pdf", "https://timss2019.org/international-database/downloads/TIMSS-2019-User-Guide-for-the-International-Database-2nd-Ed.pdf"),
    ],
    "pisa2022": [
        ("PISA2022_STU_COG_SPSS.zip", "https://webfs.oecd.org/pisa2022/STU_COG_SPSS.zip"),
        ("PISA2022_STU_QQQ_SPSS.zip", "https://webfs.oecd.org/pisa2022/STU_QQQ_SPSS.zip"),
    ],
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest):
    import requests
    part = dest + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    with requests.get(url, headers=headers, stream=True, timeout=60) as r:
        if r.status_code == 416:            # already complete
            os.replace(part, dest)
            return
        r.raise_for_status()
        mode = "ab" if r.status_code == 206 else "wb"
        total = int(r.headers.get("Content-Length", 0)) + (have if mode == "ab" else 0)
        done = have if mode == "ab" else 0
        with open(part, mode) as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    sys.stdout.write(f"\r  {os.path.basename(dest)}: {done / 1e6:,.0f} / {total / 1e6:,.0f} MB")
                    sys.stdout.flush()
    print()
    os.replace(part, dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", choices=list(SOURCES), help="sources to fetch")
    ap.add_argument("--skip-pisa-questionnaire", action="store_true",
                    help="skip the PISA student questionnaire file (needed only for weights)")
    a = ap.parse_args()
    os.makedirs(RAW, exist_ok=True)
    log = os.path.join(RAW, "PROVENANCE.txt")
    for src in a.only or SOURCES:
        for name, url in SOURCES[src]:
            if a.skip_pisa_questionnaire and "QQQ" in name:
                continue
            dest = os.path.join(RAW, name)
            if os.path.exists(dest):
                print(f"have {name}")
                continue
            print(f"fetching {name}")
            download(url, dest)
            line = " | ".join([datetime.date.today().isoformat(), name,
                               f"{os.path.getsize(dest)} bytes", f"sha256:{sha256(dest)}", url])
            with open(log, "a") as f:
                f.write(line + "\n")
    print(f"done; provenance in {log}")


if __name__ == "__main__":
    main()
