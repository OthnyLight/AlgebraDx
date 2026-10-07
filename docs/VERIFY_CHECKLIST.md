# Verification checklist — AlgebraDx v0.1

Initial and date each line in your own copy. `python tools/publish_gate.py .` checks the
mechanical items; these are yours. Nothing is published until every box is ticked.

There are two release tracks, because JOSS requires six months of public development
history before submission:

* **Track 1 — software release (v0.1.0)**: package, tests, docs, synthetic demo, attribute
  dictionary. No real-data claims. Can go public as soon as sections A, B, E are done,
  which starts the JOSS clock.
* **Track 2 — findings (v0.2.0+)**: Q-matrix, TIMSS/PISA results, methods preprint. Needs
  sections C and D as well.

## A. Software (Track 1)
- [ ] `pip install -e ".[data,figures,test]"` in a fresh virtual environment; `pytest` passes (23 tests)
- [ ] `algebradx simulate` then `algebradx fit` on the output, following README alone
- [ ] `python validation/export_crosscheck.py && Rscript validation/crosscheck_gdina.R`;
      log-likelihoods agree with GDINA to ~0.01 and item probabilities to ~1e-3. Record the output in `validation/CROSSCHECK_RESULT.txt`
- [ ] Read `src/algebradx/` end to end; every formula you cannot defend is raised as an issue
- [ ] Citations in docstrings checked against the papers (Xu & Shang 2018; de la Torre 2011;
      de la Torre & Chiu 2016; Chen, de la Torre & Zhang 2013; Johnson & Sinharay 2018;
      Ma, Iaconangelo & de la Torre 2016; Varadhan & Roland 2008)

## B. Attribute dictionary (V1, V3)
- [ ] The 12 skills: keep, merge, split or rename; 10–14 allowed
- [ ] Every definition and "mastery looks like" example rewritten in your words
- [ ] Prerequisite hierarchy: accept, edit or drop each link (A01→A04, A05→A07, A07→A08, A05→A09, A11→A12, A02→A12)

## C. Data and scoring (V4–V6) — on your computer
- [ ] `python code/01_fetch.py`; PROVENANCE.txt has a SHA-256 for every file
- [ ] `python code/02_extract_us.py --inspect`: file names, item variables, TOTWGT/JKZONE/JKREP,
      value labels match the TIMSS 2019 and 2023 user guides; PISA CNT, scored-item suffixes
      and weight variables match the PISA 2022 codebook
- [ ] Jackknife scheme for each TIMSS cycle confirmed in the user guide (`--jk-scheme full` = 2 replicates per zone, factor 1/2)
- [ ] Scoring rules: omitted = 0, not reached = missing, 2-point items = full credit only — confirmed or changed
- [ ] US sample sizes after extraction match the published TIMSS/PISA US counts (user guide / international report)
- [ ] Five items' p-values from `*_scoring_log.csv` match the US percent-correct in the TIMSS item almanacs

## D. Q-matrix and models (V2, V7)
- [ ] Every row of `qmatrix/qmatrix_timss_v01.csv` ruled on (see `qmatrix/README.md`), status changed from the VERIFY tag to `ok`; the 9 low-confidence items checked against the items themselves
- [ ] Decide on A09 (factoring): merge into A05 for TIMSS (1 item in 2023), keep for district tests
- [ ] The 17 excluded items in `qmatrix/excluded_items_v01.csv`: agree they are outside algebra readiness
- [ ] `algebradx check-q` on the final Q-matrix: coverage flags resolved or documented
- [ ] Optional but strongly recommended: a second rater codes a random 25% of items; agreement (Cohen's kappa per skill) reported
- [ ] `python code/04_fit.py --source timss2023 --qmatrix ...`; every GDI/PVAF suggestion in
      `qmatrix_validation.csv` reviewed against the item; Q-matrix changes logged with reasons in `qmatrix/CHANGELOG.md`
- [ ] Model choice (mixed Wald model vs G-DINA; structural model) agreed and justified
- [ ] Replicate-weight SEs run with all replicates (`--replicates -1`)

## E. Before anything goes public
- [ ] `AUTHORS.json`, `LICENSE`, `CITATION.cff`, `paper/paper.md` carry your real surname, ORCID and affiliation
- [ ] README, LIMITATIONS, paper.md and the preprint rewritten in your own voice
- [ ] Figures regenerated with `python code/06_figures_stats.py --final`
- [ ] AI-assistance disclosure in `paper/paper.md` is accurate (JOSS requires it)
- [ ] No TIMSS/PISA microdata or student-level outputs anywhere in the repository (`git status`, `.gitignore`)
- [ ] `python tools/publish_gate.py . --allow-draft-in src/ tests/ code/ tools/ paper/in_preparation/ data/` passes (code folders are excluded because array indexing trips the placeholder pattern; the in-preparation preprint is excluded because it is not part of the release)
- [ ] Evidence-log row written the day of release
