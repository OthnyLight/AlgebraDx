# AlgebraDx — status (7 October 2026)

## Done
- **Package** (`src/algebradx`): G-DINA / LCDM / DINA / DINO / A-CDM / LLM / R-RUM, log-linear and
  hierarchical skill structures, rotated booklets, sampling weights, TIMSS jackknife and PISA BRR
  standard errors, Wald model selection, item-pair fit, Q-matrix validation (GDI/PVAF),
  classification reliability, teacher HTML reports, saved calibrations, CLI, and a built-in
  SPSS reader (no `pyreadstat` needed). 24 tests pass.
- **Skills**: 12-skill attribute dictionary (`qmatrix/attributes.csv`).
- **Q-matrix v0.1**: 164 TIMSS 2019/2023 items coded, 17 excluded with reasons
  (`qmatrix/qmatrix_timss_v01.csv`, `qmatrix/README.md`); ruled on by the author 2026-10-07.
- **Simulation study** and synthetic worked analysis (`results/`, `paper/figures/`, `paper/stats.json`).
- **Pipeline check on real data**: TIMSS 2019 US bridge sample (1,484 students, 56 items) —
  scoring codes, weights and jackknife variables confirmed; fit runs. Pilot only; not reported.
- **Papers**: JOSS paper (`paper/paper.md`; submittable from April 2027); methods preprint in preparation (`paper/in_preparation/`).
- **Publishing**: public on GitHub (github.com/OthnyLight/AlgebraDx) since 2026-10-07; Zenodo DOI next (`docs/PUBLISH_GUIDE.md`).

## Not done — and the single step that unlocks it
The full US TIMSS fits have not run. The US student files (`bsausam7.sav`, 29 MB, and
`bsausam8.sav` inside `T23_Data_SPSS_G8.zip`) are above the 12 MB limit for copying from
your Mac to the Claude workspace. On your Mac, with Python installed:

```bash
cd algebradx
pip install -e ".[data,figures]"
mkdir -p data/raw/items
cp "../T19_G8_SPSS Data/bsausam7.sav" data/raw/          # adjust paths to your folder
unzip -j ../T23_Data_SPSS_G8.zip '*bsausam8.sav' -d data/raw/
cp ../T23_ItemInformation_G8.xlsx data/raw/
cp "../T19_G8_Item Information.zip" data/raw/T19_G8_Item_Information.zip
python code/02_extract_us.py --only timss2023 timss2019
python code/04_fit.py --source timss2023 --qmatrix qmatrix/qmatrix_timss_v01.csv --merge A09:A05
python code/04_fit.py --source timss2019 --qmatrix qmatrix/qmatrix_timss_v01.csv --merge A09:A05
```

Or start a new Claude session, drag the two `.sav` files into the chat, and ask it to run these steps.

## Still open
1. Run the US TIMSS 2023 and 2019 fits (above), then review the GDI/PVAF suggestions for Q-matrix v0.2.
2. Systems of equations (A08) has 3 items per cycle — keep separate or merge into A07 after seeing its accuracy.
3. PISA zips (83 MB, 59 MB) look incomplete; re-download if PISA stays in scope.
4. Run `validation/crosscheck_gdina.R` against the R package GDINA.
