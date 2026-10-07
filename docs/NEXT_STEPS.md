# Next steps

v0.1 is the first step: a tested estimator, the drafted skill dictionary, the data pipeline
and a synthetic demonstration. Roughly in order over months 1–10:

## Months 1–2 — finish v0.1 and start the JOSS clock
- Work through `VERIFY_CHECKLIST.md` sections A, B, E; release v0.1.0 (software only) on GitHub + Zenodo + PyPI.
  JOSS requires the repository to have been public for **more than six months** with active
  development and evidence of research use, so the earliest JOSS submission is about six
  months after this release.
- Run the R cross-check; add its output to the repository.

## Months 2–4 — the Q-matrix (the expert contribution)
- Extract the US data; draft and rule on the TIMSS 2023 and 2019 Q-matrices.
- Second rater on a random 25% of items; report kappa per skill.
- Fit; review GDI suggestions item by item; log every Q-matrix change in `qmatrix/CHANGELOG.md`.
- Release the Q-matrix and attribute dictionary as a versioned CC BY dataset with its own DOI (technical report).

## Months 4–6 — methods preprint
- TIMSS 2023 as the main sample; TIMSS 2019 as replication (same items where linked);
  PISA 2022 as a check of skill structure in a different population.
- Results: model selection, item-level models, skill prevalences with replicate SEs,
  classification reliability, Q-matrix validation, the 2019→2023 change in skill prevalence
  on linked items.
- Post to arXiv (stat.AP) or EdArXiv; then submit to a measurement journal
  (candidates: *Journal of Educational Measurement*, *Educational Measurement: Issues and Practice*,
  *Large-scale Assessments in Education* — the last is open access and publishes TIMSS/PISA methods work).

## Months 6–10 — software paper and adoption
- JOSS submission once the six-month history and research-use evidence exist (the preprint is that evidence).
- Package features worth adding before JOSS:
  - monotonicity constraints on item probabilities
  - polytomous / partial-credit items (sequential G-DINA)
  - differential item functioning by group (Wald DIF; Hou, de la Torre & Nandakumar 2014)
  - multiple-group models (2019 vs 2023 on linked items)
  - a parallel option for replicate refits
  - a documentation site with a worked TIMSS example
- Partner pilot: one district or dual-credit program applies the package to its own algebra
  placement test; this is the clearest evidence of use beyond the author.
