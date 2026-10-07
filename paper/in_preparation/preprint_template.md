---
title: "Which algebra skills are US eighth graders missing? Diagnostic classification of TIMSS responses with a twelve-skill readiness Q-matrix"
author: "Othniel [VERIFY surname] ([VERIFY affiliation]; ORCID [VERIFY ORCID])"
status: "In preparation — sections 1–5 drafted; section 6 (US TIMSS results) awaits the real-data fits. Not for citation."
---

<!-- Built by code/07_build_paper.py. Edit THIS template, never preprint.md. Every double-brace key is
     replaced from stats.json; nothing numeric is typed by hand. -->

## Abstract

[VERIFY: write last, after the TIMSS results exist.] Large-scale assessments report how much
mathematics students know but not which skills they lack. We define twelve algebra-readiness
skills, code TIMSS grade-8 items to them, and fit diagnostic classification models that
account for rotated booklets, sampling weights and replicate-weight variance estimation,
using the open-source Python package AlgebraDx. In a simulation that mimics the TIMSS
design ({{recovery.B_items_per_student}} items answered per student, twelve skills), skill
prevalences were recovered to within {{recovery.B_prevalence_error_max}} and individual skills
were classified correctly {{recovery.B_attr_agreement}} of the time, but whole profiles only
{{recovery.B_pattern_agreement}} of the time — TIMSS supports population skill estimates far
better than individual diagnosis. [Empirical results: VERIFY pending TIMSS 2023 run.]

## 1. Introduction

- Why a single score is not enough for reteaching; the promise of diagnostic classification models (Rupp, Templin & Henson 2010).
- Prior DCM applications to TIMSS (e.g. fraction and algebra items); what is new here: an algebra-*readiness* skill set grounded in examination-writing practice, a survey-design-aware estimation workflow, and open software. [VERIFY: literature review of TIMSS/PISA DCM applications]
- Research questions: (1) Can twelve readiness skills be measured from TIMSS grade-8 items? (2) Which skills do US eighth graders lack, and how did that change from 2019 to 2023? (3) How reliable are skill classifications under the TIMSS design?

## 2. Skills and Q-matrix

- The twelve skills (Table 1, from `qmatrix/attributes.csv`) and the proposed prerequisite structure.
- Coding procedure: keyword pre-fill, expert ruling by an experienced GCE examiner, second-rater agreement, and empirical GDI/PVAF validation (de la Torre & Chiu 2016).

## 3. Data

- TIMSS 2023 and 2019 grade-8 US student achievement files; PISA 2022 US cognitive file. Scoring rules (omitted = incorrect, not reached = missing, two-point items correct at full credit).
- Item pool: all Algebra items plus Number items tied to readiness skills.

## 4. Models and estimation

- G-DINA (de la Torre 2011) and its reduced forms; log-linear structural model with pairwise associations.
- Weighted marginal maximum likelihood by EM with SQUAREM acceleration; missing-by-design responses contribute nothing to the likelihood.
- Item-level model selection by Wald tests (de la Torre & Lee 2013; Ma, Iaconangelo & de la Torre 2016).
- Fit: item-pair transformed correlations and log-odds ratios (Chen, de la Torre & Zhang 2013); SRMSR.
- Standard errors: TIMSS jackknife repeated replication; PISA Fay BRR.
- Classification reliability: Johnson & Sinharay (2018).

## 5. Simulation study

Study A (complete data, five skills, 30 items, {{recovery.A_reps}} replications per condition):
the RMSE of item success probabilities fell from {{recovery.A_rmse_by_N.500}} with 500 students
to {{recovery.A_rmse_by_N.4000}} with 4,000; skill-level classification agreement with the true
profile was {{recovery.A_attr_agreement_by_N.500}} and {{recovery.A_attr_agreement_by_N.4000}},
and the model's own predicted accuracy was {{recovery.A_pred_accuracy_by_N.500}} and
{{recovery.A_pred_accuracy_by_N.4000}}. [VERIFY interpretation: the index is slightly optimistic
in the smallest samples, where item parameters are least precise, and close to the truth by
2,000 students.] Whole-profile agreement was {{recovery.A_pattern_agreement_by_N.500}} and
{{recovery.A_pattern_agreement_by_N.4000}}.

Study B (TIMSS-like design, twelve skills, 96 items in seven rotated booklets, 8,000 students
with unequal weights, {{recovery.B_reps}} replications): each student answered
{{recovery.B_items_per_student}} items; item probabilities were recovered with RMSE
{{recovery.B_rmse_P}}, prevalences to within {{recovery.B_prevalence_error_max}}; skill-level
classification agreement was {{recovery.B_attr_agreement}} (predicted {{recovery.B_pred_accuracy}})
and whole-profile agreement {{recovery.B_pattern_agreement}}. Replicate-weight standard errors
capture sampling variability only: in the worked synthetic analysis below, the largest
prevalence error ({{prevalence_abs_error_max}}) exceeded the largest replicate standard error
({{prevalence_se_max}}) several-fold, so model-based bias under sparse rotated designs must be
reported alongside design-based uncertainty. One G-DINA fit took about
{{recovery.B_seconds}} seconds on a two-core machine.

Worked synthetic analysis (`results/synthetic`): the analysis plan selected {{final_model}} by BIC;
SRMSR = {{srmsr}}; expected skill classification accuracy ranged from {{attribute_accuracy_min}}
to {{attribute_accuracy_max}}; {{q_items_flagged}} items were flagged by GDI validation.

## 6. Results: US grade 8, TIMSS 2023 and 2019

[VERIFY pending real-data run: model selection; item-level models; skill prevalences with
replicate SEs; 2019→2023 change on linked items; classification reliability; Q-matrix
revisions; PISA 2022 replication of the skill structure.]

## 7. Discussion

- What the skill profile adds for teachers and for placement into algebra.
- Population diagnosis vs individual diagnosis under rotated designs.
- Limitations (see docs/LIMITATIONS.md).

## Software and data availability

AlgebraDx (MIT) and the Q-matrix and attribute dictionary (CC BY 4.0): [VERIFY GitHub URL and Zenodo DOI].
TIMSS and PISA data are available from IEA and OECD and are not redistributed.

## AI assistance

[VERIFY keep accurate] Software and an initial draft of this manuscript's structure were produced
with Claude (Anthropic). The author made all methodological and coding decisions, verified every
number against the analysis outputs, and wrote the final text.
