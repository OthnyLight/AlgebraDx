# Codebook

## Inputs

### `qmatrix/attributes.csv` — attribute (skill) dictionary
| column | meaning |
|---|---|
| `code` | skill code used as a Q-matrix column (A01–A12) |
| `name` | short name |
| `definition` | what mastery of the skill means |
| `prerequisites` | codes of skills assumed mastered first (`;`-separated); used only with `--hierarchy` |
| `timss_keywords` | words that trigger the automatic pre-fill in `03_draft_qmatrix.py` |
| `mastery_looks_like` | a concrete example of a mastered performance |

### `qmatrix/qmatrix_<source>.csv` — Q-matrix
| column | meaning |
|---|---|
| `item` | item identifier as in the TIMSS/PISA data file (no item text) |
| `source`, `content_domain`, `topic` | provenance of the item (TIMSS framework categories) |
| `A01`…`A12` | 1 if the item requires the skill, else 0 |
| `status` | review status; anything other than `ok` blocks real-data fits |

### `data/extract/<source>_usa_scored.csv.gz` — local only, never shared
| column | meaning |
|---|---|
| `id` | student identifier (TIMSS `IDSTUD`, PISA `CNTSTUID`) |
| `IDSCHOOL`, `IDCLASS`, `IDBOOK` | TIMSS school, class and booklet |
| `TOTWGT` | TIMSS total student weight |
| `JKZONE`, `JKREP` | TIMSS jackknife zone and replicate indicator |
| `W_FSTUWT`, `W_FSTURWT1`–`80` | PISA final student weight and Fay BRR replicate weights |
| one column per item | 1 correct, 0 incorrect or omitted, blank not administered or not reached |

## Outputs (`results/<source>/`)

| file | content |
|---|---|
| `relative_fit.csv` | log-likelihood, parameters, AIC, BIC per model (descriptive under weights) |
| `wald_item_tests.csv` | per item with ≥2 skills: Wald statistic and p-value for DINA, DINO, A-CDM, LLM, R-RUM vs G-DINA |
| `item_model_choice.csv` | the model chosen for each item by the Wald rule |
| `item_parameters.csv` | per item × latent group: success probability `P` and its SE; `group` lists the item's required skills as a 0/1 pattern in Q-matrix order |
| `guess_slip.csv` | P(correct with none of the required skills), 1 − P(correct with all), item discrimination (GDI) |
| `attribute_prevalence.csv` | estimated share of students who have mastered each skill, replicate-weight SE; for synthetic data, the true value and true-vs-estimated agreement |
| `classification_reliability.csv` | per skill: expected classification accuracy and consistency |
| `fit_items.csv`, `fit_item_pairs.csv` | observed vs model-implied proportions correct and item-pair correlations / log-odds ratios with z-statistics |
| `qmatrix_validation.csv` | per item: provisional q-vector and PVAF, suggested q-vector and PVAF, flag |
| `qmatrix_mesa.csv` | best PVAF with 1–4 skills per item (mesa plot data) |
| `student_scores.csv.gz` | per student: `p_<skill>` mastery probability, `m_<skill>` classification at 0.5, MAP profile and its probability (local only for real data) |
| `calibration.json` | the fitted model, reusable with `algebradx score` |
| `fit_log.json` | sample sizes, coverage, identifiability checks, summary statistics |

## Paper (`paper/`)
| file | content |
|---|---|
| `stats.json` | every number quoted in any document, written by `06_figures_stats.py` |
| `figures/*.png` | figures; stamped until regenerated with `--final` |
| `paper.md`, `paper.bib` | JOSS software paper |
| `preprint.md` | methods preprint built by `07_build_paper.py` from `preprint_template.md` and `stats.json` |
