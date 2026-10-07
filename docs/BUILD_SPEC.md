# Build spec — AlgebraDx v0.1

```
PROJECT:        AlgebraDx — diagnostic classification models for high-school algebra readiness.
                Archetypes: (2) pipeline/tool [primary] + (8) analysis paper + (9) technical
                report (Q-matrix & attribute dictionary). Two papers ride on one build:
                JOSS software paper and a methods preprint -> measurement journal article.

QUESTION:       Which specific algebra-readiness skills has a student mastered, judged from
                the answers they gave on an algebra test, and how are those skills distributed
                among US grade-8 students?

SOURCES:        1. TIMSS 2023 International Database, Grade 8, SPSS (949 MB zip)
                   https://timss2023.org/wp-content/uploads/data/T23_Data_SPSS_G8.zip
                   Item information: .../T23_ItemInformation_G8.xlsx
                   User guide:       .../T23_UG-International-Database.pdf
                   Terms: IEA — non-commercial, educational & research use; attribution;
                   NO redistribution without IEA permission. Accessed 2026-10-06.
                2. TIMSS 2019 International Database, Grade 8, SPSS (703 MB zip)
                   https://timss2019.org/international-database/downloads/T19_G8_SPSS%20Data.zip
                   Item information: .../T19_G8_Item%20Information.zip ; User guide 2nd ed.
                   Same IEA terms. Accessed 2026-10-06.
                3. PISA 2022 cognitive item file (SPSS)
                   https://webfs.oecd.org/pisa2022/STU_COG_SPSS.zip  (+ STU_QQQ_SPSS.zip for weights)
                   OECD terms of use, research use with attribution. Accessed 2026-10-06.
                Sandbox could not reach any of these (network allowlist); extraction runs on
                the author's computer via code/01_fetch.py and code/02_extract_us.py.

UNIT:           Student (US grade 8 for TIMSS; US 15-year-olds for PISA) x item.

MEASURES:       - Scored item response x_ij in {0,1, missing}: MC correct vs keyed option;
                  CR full credit = 1; omitted = 0; not-reached & not-administered = missing.
                - Attribute profile alpha_i in {0,1}^K, K = 12 drafted (10-14 allowed).
                - Item response functions: G-DINA (identity/logit/log links), DINA, DINO,
                  ACDM, LLM, R-RUM, LCDM (= G-DINA logit; Henson, Templin & Willse 2009).
                - Structural model: saturated, log-linear (order 1/2), optional hierarchy.
                - Estimation: weighted marginal ML via EM; missing-by-design handled in the
                  likelihood; sampling weights TOTWGT (TIMSS) / W_FSTUWT (PISA).
                - SEs: item-wise empirical cross-product; survey-design SEs for prevalences
                  via TIMSS jackknife (JKZONE/JKREP) and PISA Fay BRR (80 replicates).
                - Fit: AIC/BIC, item-pair transformed-correlation & log-odds-ratio z-tests,
                  SRMSR; item-level Wald tests for reduced models.
                - Q-matrix validation: GDI / PVAF (de la Torre & Chiu 2016).
                - Reliability: attribute- and pattern-level classification accuracy and
                  consistency (Johnson & Sinharay 2018).

OUTPUTS:        src/algebradx/            Python package (MIT), CLI `algebradx`
                tests/                    unit + recovery tests
                qmatrix/attributes.csv    attribute dictionary (CC BY 4.0)
                qmatrix/qmatrix_timss.csv item ID -> skills (IDs + codes only, no item text)
                code/01..05               numbered pipeline
                paper/stats.json, paper/figures/*.png, paper/paper.md (JOSS),
                paper/preprint.md (methods preprint, built from stats.json)
                docs/ CODEBOOK, LIMITATIONS, VERIFY_CHECKLIST, NEXT_STEPS, PUBLISH_GUIDE

VENUES:         1. GitHub release + Zenodo DOI (software, Q-matrix, synthetic demo data)
                2. PyPI
                3. Methods preprint (arXiv stat.AP / EdArXiv)
                4. JOSS (after >= ~6 months public history & real-data use)
                5. Measurement journal article (e.g. J. Educational Measurement,
                   Educational Measurement: Issues & Practice, Large-scale Assessments in Education)

VERIFY POINTS:  V1 Attribute list (12 skills) and definitions — Othniel's GCE-based judgment
                V2 Every Q-matrix cell
                V3 Optional prerequisite hierarchy among skills
                V4 Scoring rules: omitted = 0, not-reached = missing, 2-pt CR = 1 only at full credit
                V5 TIMSS 2019/2023 file names, item variable names, weight & jackknife variables,
                   jackknife variance scheme (150 replicates x 1/2 vs 75 x 1) against user guides
                V6 PISA 2022 file names, US filter, scored-item suffix, weight merge
                V7 Model selection decisions on real data (G-DINA vs reduced; structural model)
                V8 All prose in own voice; author block (surname, ORCID, affiliation)

LICENSE:        Code MIT; docs, Q-matrix, attribute dictionary, figures CC BY 4.0.
                TIMSS/PISA microdata are NOT redistributed (IEA terms).

ASSUMPTIONS:    - Python, numpy/scipy/pandas only (no compiled extensions) so it installs anywhere.
                - Until the author runs extraction, the pipeline runs on a synthetic dataset that
                  mimics TIMSS's rotated-booklet design; every number from it is labeled synthetic.
                - "Readiness" scope = TIMSS Algebra domain + the Number items that are algebra
                  prerequisites (signed numbers, fractions, ratio, exponents).
                - PISA 2022 is a secondary sample (cross-check of skill structure on 15-year-olds);
                  its Q-matrix is limited by the item information OECD releases.
```
