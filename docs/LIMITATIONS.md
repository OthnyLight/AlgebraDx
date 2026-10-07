# Limitations

Read before using or citing anything from this repository. [VERIFY V8: rewrite in your own voice]

1. **The Q-matrix is a hypothesis.** Every result depends on which skills each item is
   coded to require. The v0.1 Q-matrix is drafted (keyword pre-fill plus expert review)
   and has not been independently coded by a second rater. Inter-rater agreement and the
   GDI/PVAF validation (`qmatrix_validation.csv`) are evidence, not proof.

2. **TIMSS is a population survey, not a classroom test.** TIMSS and PISA rotate items
   across booklets, so a US student answers only a fraction of the algebra-readiness pool
   (about a quarter of the items in the synthetic demonstration that mimics the design).
   Skill *prevalences* for the population are estimated well; skill profiles for
   *individual* TIMSS students are uncertain, and the classification-reliability tables
   show how uncertain. Individual-level reports are intended for full-length tests that
   districts administer themselves, calibrated with this package — not for TIMSS students.

3. **Item content cannot be shown.** Most TIMSS 2019/2023 and PISA 2022 items are secure.
   The Q-matrix lists item identifiers only; reviewers outside the author cannot check the
   coding against item text unless they obtain the items from IEA/OECD. Released items are
   the exception and are flagged in the review file.

4. **Twelve skills with a few items each.** Some skills (systems of equations, factoring)
   appear in few grade-8 items; `coverage()` flags any skill with fewer than three items or
   no single-skill item. Such skills are weakly identified and may need to be merged with a
   neighbouring skill.

5. **Grade 8 is not high school.** TIMSS grade 8 measures the end of middle school. The
   skills are framed as *readiness* for high-school algebra; claims about high-school
   algebra performance need a high-school sample (planned: district/dual-credit partners).

6. **PISA 2022 is a different construct and population.** PISA samples 15-year-olds across
   grades and measures mathematical literacy in context. It is used as a secondary sample
   to check whether the skill structure replicates, not to pool with TIMSS.

7. **Scoring choices.** Omitted responses are scored incorrect and not-reached responses
   missing; two-point constructed-response items count as correct only at full credit.
   Other defensible choices exist; `02_extract_us.py --partial one` reruns with partial
   credit as correct.

8. **Weighted likelihood.** Sampling weights enter as a pseudo-likelihood. AIC, BIC and
   likelihood-ratio tests are not strictly valid under weighting; model choices on real data
   rest on item-level Wald tests and replicate-weight standard errors, with information
   criteria reported as descriptive.

9. **Standard errors do not capture model bias.** Model-based standard errors ignore the
   survey design and the covariance between item and structural parameters; report
   replicate-weight standard errors for population quantities. But replicate-weight standard
   errors measure sampling variability only. In the TIMSS-like simulation, some skill
   prevalences were off by several standard errors (see `paper/stats.json`,
   `prevalence_abs_error_max` vs `prevalence_se_max`), because each student answers few items
   per skill and the structural model is an approximation. Treat small differences in
   prevalence (e.g. 2019 vs 2023) with caution even when they are "significant".

10. **Structural model.** With 12 skills the saturated profile distribution has 4,095
    parameters and is not estimable from US samples; the default is a log-linear model with
    all pairwise associations (78 parameters). Higher-order associations are assumed away.

11. **Synthetic results are not findings.** Everything under `results/synthetic/` and
    `results/recovery/` comes from simulated data and demonstrates the software; none of it
    describes US students.

12. **No cross-check against R has been run in this build environment.** The estimator is
    verified against direct numerical maximisation of the likelihood (test suite) and by
    simulation recovery; `validation/crosscheck_gdina.R` compares it with the R package
    GDINA and should be run before release.
