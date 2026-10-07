---
title: 'AlgebraDx: diagnostic classification models for skill-level diagnosis of algebra readiness in Python'
tags:
  - Python
  - psychometrics
  - cognitive diagnosis
  - diagnostic classification models
  - educational measurement
  - TIMSS
  - PISA
authors:
  - name: Othniel [VERIFY surname]
    orcid: [VERIFY ORCID]
    affiliation: 1
affiliations:
  - name: [VERIFY affiliation]
    index: 1
date: [VERIFY submission date]
bibliography: paper.bib
---

<!-- DRAFT: rewrite in your own voice before submission. JOSS requires >6 months of public
     development history and evidence of research use before this can be submitted. -->

# Summary

A test score says how much a student knows; it does not say what. Diagnostic
classification models (DCMs), also called cognitive diagnosis models, replace the single
score with a profile: for each of a set of skills, the probability that the student has
mastered it [@rupp2010]. The link between items and skills is an expert-built Q-matrix,
and the models estimate how mastering each required skill changes the chance of answering
an item correctly.

`AlgebraDx` is a Python package that fits the G-DINA family of DCMs [@delatorre2011],
including the log-linear cognitive diagnosis model [@henson2009] and the DINA, DINO,
A-CDM, LLM and R-RUM models as item-level special cases, to the data that large-scale
assessments produce: rotated booklets in which each student answers a fraction of the
items, sampling weights, and replicate weights for design-based standard errors. It ships
with a drafted twelve-skill dictionary for high-school algebra readiness and a reproducible
pipeline that applies it to the United States samples of TIMSS 2019 and 2023 (grade 8)
[@timss2019; @timss2023] and PISA 2022 [@pisa2022].

# Statement of need

DCM software is mature in R, where the `GDINA` [@ma2020] and `CDM` [@george2016] packages
cover estimation, model comparison and Q-matrix validation. [VERIFY: confirm the current
feature sets of these packages before claiming any gap.] Python users — including the data
teams in school districts and testing organisations who increasingly work in Python — have
had no equivalent. Applying DCMs to TIMSS or PISA also requires steps that are not packaged
anywhere as one workflow: extracting a country's records, scoring raw responses under
documented rules, handling missing-by-design responses, fitting with sampling weights, and
estimating standard errors with the study's jackknife or balanced-repeated-replication
weights.

`AlgebraDx` provides that workflow with only `numpy`, `scipy` and `pandas` as dependencies:

* marginal maximum likelihood by EM with SQUAREM acceleration [@varadhan2008], chunked over
  students so that 10–14 skills (1,024–16,384 latent classes) fit in ordinary memory;
* saturated, log-linear and hierarchical structural models;
* item-level Wald tests of reduced models against G-DINA and automatic per-item model
  selection [@delatorre2013; @ma2016];
* absolute fit by item-pair residuals and SRMSR [@chen2013; @maydeu2013];
* Q-matrix identifiability checks [@xu2018] and empirical validation by the G-DINA
  discrimination index [@delatorre2016];
* attribute- and pattern-level classification accuracy and consistency [@johnson2018];
* TIMSS jackknife and PISA Fay-BRR replicate standard errors;
* saved calibrations that score new students, and plain-language HTML skill reports for
  teachers.

The intended users are measurement researchers who want DCMs in a Python workflow,
analysts of large-scale assessment data, and districts, dual-credit programs and test
developers who want skill-level reports from their own algebra assessments.

# Validation

The test suite checks that EM reaches the same maximum as direct numerical optimisation of
the marginal likelihood, that integer sampling weights reproduce the fit to replicated rows
exactly, that reduced-model M-steps recover known parameters, that Wald tests retain true
and reject false reduced models, that GDI validation restores deliberately mis-specified
Q-matrix entries, and that model-based standard errors match the empirical spread of
estimates across replications. A simulation study (`code/05_recovery_study.py`) reports
parameter recovery and classification accuracy for complete designs and for a TIMSS-like
rotated design. `validation/crosscheck_gdina.R` compares estimates with the R package
`GDINA` on a shared dataset.

# Acknowledgements

TIMSS data are provided by the IEA and PISA data by the OECD; neither is redistributed.

AI usage disclosure: [VERIFY — keep accurate] Code, tests and documentation were drafted
with Claude (Anthropic, Claude Opus 5.5) in October 2026 from the author's specification.
The author reviewed all code, ran the validation and cross-checks, made every
psychometric and Q-matrix decision, and revised all text, and takes full responsibility
for the software and this paper.

# References
