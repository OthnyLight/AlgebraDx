# AlgebraDx

**Status:** v0.1.0, released 2026-10-07 (software, skill dictionary and Q-matrix v0.1; US TIMSS results to follow) | **Maintainer:** Othniel ([@OthnyLight](https://github.com/OthnyLight)) | **License:** code MIT; docs, Q-matrix and figures CC BY 4.0

AlgebraDx reads a student's answers on an algebra test and reports **which specific skills
they have and have not mastered** — rational-number operations, equivalent expressions,
linear equations, systems, factoring, functions and so on — instead of one overall score.
A single score tells a teacher that a student is behind; a skill profile tells them *why*,
which is what targeted reteaching needs.

It is a Python package for **diagnostic classification models** (cognitive diagnosis
models) in the G-DINA family, built for the data large-scale assessments actually produce:
rotated booklets where each student sees a fraction of the items, sampling weights, and
jackknife or BRR replicate weights. It ships with a drafted 12-skill **attribute
dictionary** for algebra readiness and a pipeline that applies it to the US grade-8 TIMSS
2019 and 2023 samples and the US PISA 2022 sample.

## What it does

| | |
|---|---|
| Item models | G-DINA (identity, logit, log links), LCDM / log-linear CDM, DINA, DINO, A-CDM, LLM, R-RUM — and any mix, item by item |
| Skill structure | saturated, log-linear (main effects or all pairwise associations), optional prerequisite hierarchy |
| Estimation | marginal ML by EM with SQUAREM acceleration; missing-by-design; sampling weights; chunked E-step for 10–14 skills |
| Inference | item-wise sandwich SEs; TIMSS jackknife and PISA Fay-BRR replicate SEs |
| Model checking | AIC/BIC, item-pair residuals (transformed correlation, log-odds ratio), SRMSR, item-level Wald tests with automatic reduced-model selection |
| Q-matrix tools | coverage and identifiability checks (Xu & Shang 2018), empirical validation by GDI/PVAF (de la Torre & Chiu 2016) |
| Reporting | per-student mastery probabilities with mastered / uncertain / not-yet status, classification accuracy and consistency, group summaries, a standalone HTML class report |
| Re-use | save a calibration, then score new students on your own test with it (`algebradx score`) |

Dependencies: numpy, scipy, pandas. No compiled extensions — it even reads the SPSS files TIMSS and PISA ship in, with its own small reader (`algebradx.sav`).

## Install

```bash
git clone https://github.com/OthnyLight/AlgebraDx
cd AlgebraDx
pip install -e ".[test]"          # add ,data for the TIMSS/PISA scripts, ,figures for plots
pytest                            # or: python tests/run_tests.py
```

## Two-minute example

```bash
algebradx simulate --n 2000 --items 30 --attributes 5 --out demo
algebradx fit --responses demo/responses.csv --qmatrix demo/qmatrix.csv \
              --id id --weight weight --out demo/results
open demo/results/report.html
```

```python
import pandas as pd
from algebradx import DiagnosticModel, QMatrix, AttributeDictionary
from algebradx import fit as F

skills = AttributeDictionary.from_csv("qmatrix/attributes.csv")
q = QMatrix.from_csv("my_qmatrix.csv", dictionary=skills)       # item, A01..A12
responses = pd.read_csv("my_test_scored.csv")                   # one 0/1/blank column per item

model = DiagnosticModel(q, "GDINA", structural="loglinear2").fit(responses[q.items])
model.compute_standard_errors()
wald = F.wald_item_tests(model)                                 # which items are DINA, A-CDM, ...
better = DiagnosticModel(q, F.select_item_models(wald), structural="loglinear2").fit(responses[q.items])

scores = better.score(ids=responses["student_id"])              # p_A01..p_A12, m_A01..m_A12, MAP profile
print(F.classification_reliability(better)["attribute"])        # how trustworthy each skill call is
better.save("calibration.json")                                 # reuse to score next year's students
```

## Applying it to your own assessment (districts, dual-credit programs, test developers)

1. Score each item 0/1 (blank = not administered).
2. Write a Q-matrix: one row per item, a 1 under each skill the item requires. Start from
   `qmatrix/attributes.csv`, or define your own skills.
3. `algebradx check-q --qmatrix your_q.csv --attributes qmatrix/attributes.csv`
4. `algebradx fit ...`, then read `qmatrix_validation.csv` and `classification_reliability.csv`
   before trusting any individual report.

A full-length test where every student answers every item gives far more reliable
individual profiles than TIMSS does (see Limitations).

## The TIMSS / PISA pipeline

The microdata are free to download but **may not be redistributed** (IEA and OECD terms),
so they are fetched and processed on your own computer and never committed.

```bash
pip install -e ".[data,figures]"
python code/01_fetch.py                         # ~2.5 GB, resumable, logs SHA-256 provenance
python code/02_extract_us.py --inspect          # check variable names against the user guides
python code/02_extract_us.py                    # US rows, math items, scored 0/1/missing
python code/03b_qmatrix_draft_v01.py           # the v0.1 expert-draft Q-matrix (164 items)
#   ... rule on every row: see qmatrix/README.md ...
python code/04_fit.py --source timss2023 --qmatrix qmatrix/qmatrix_timss_v01.csv --merge A09:A05
python code/06_figures_stats.py                 # figures + paper/stats.json
python code/07_build_paper.py                   # manuscript text with numbers from stats.json
```

Without any restricted data, the whole pipeline runs on a synthetic dataset that mimics
the TIMSS design: `python code/04_fit.py --source synthetic`.

```
src/algebradx/   the package            tests/         unit, recovery and CLI tests
code/            numbered pipeline      qmatrix/       attribute dictionary, Q-matrices
data/raw/        downloads (local only) data/extract/  US extracts (local only)
results/         model outputs          paper/         stats.json, figures, JOSS paper, preprint
docs/            spec, codebook, limitations, checklist, next steps, publishing guide
validation/      cross-check against the R package GDINA
tools/           publish gate, GitHub and Zenodo helpers, provenance logger
```

## Sources

| Source | Vintage | Terms | Accessed |
|---|---|---|---|
| TIMSS 2023 International Database, grade 8 (IEA), timss2023.org/data | 2024 release | non-commercial research use, attribution, no redistribution | 2026-10-06 |
| TIMSS 2019 International Database, grade 8 (IEA), timss2019.org/international-database | 2nd ed. | as above | 2026-10-06 |
| PISA 2022 Database (OECD), webfs.oecd.org/pisa2022 | 2023 release | OECD terms of use | 2026-10-06 |

## Limitations

See `docs/LIMITATIONS.md` before using or citing anything here. In one line: the skill
coding is an expert hypothesis under validation, and TIMSS supports population-level skill
estimates far better than individual student profiles.

## Citation

See `CITATION.cff`. DOI: minted on the first Zenodo release.

AI assistance: the code, tests and documentation were drafted with Claude (Anthropic) and
reviewed, verified and revised by the author; see `paper/paper.md`.
