# Publishing guide — AlgebraDx

Nothing has been pushed anywhere yet. This build ran in a sandbox with no GitHub or Zenodo
token and no access to the TIMSS/PISA servers, so every publication step below is yours.
Do them only after `docs/VERIFY_CHECKLIST.md` is complete for the track you are releasing
and `python tools/publish_gate.py . --allow-draft-in src/ tests/ code/ tools/ paper/in_preparation/ data/` passes.

| Step | What | When | Who |
|---|---|---|---|
| 1 | GitHub repository + v0.1.0 release | after checklist A, B, E | you (or `tools/publish_github.py` with your token) |
| 2 | Zenodo DOI via GitHub integration | same day as step 1 | you, one switch |
| 3 | PyPI package | same day | you |
| 4 | Q-matrix + attribute dictionary technical report (Zenodo) | after checklist C, D | you |
| 5 | Methods preprint (arXiv stat.AP or EdArXiv) | after real-data results verified | you (attestation) |
| 6 | Journal article | after preprint | you |
| 7 | JOSS | ≥ 6 months after step 1, with evidence of research use | you |

## 1. GitHub

Automated (token in your shell only, scope: `repo`, revoke afterwards):

```bash
export GITHUB_TOKEN=...            # never in a file
python tools/publish_github.py . --repo algebradx \
  --description "Diagnostic classification models for skill-level algebra diagnosis (G-DINA, LCDM) with survey weights" \
  --release v0.1.0 --release-notes "First public release: estimator, tests, attribute dictionary, TIMSS/PISA pipeline, synthetic demonstration. No real-data results."
```

Manual: create an empty repository `algebradx` at github.com/new (no README), then

```bash
git init -b main && git add -A && git status        # confirm no data/raw, data/extract files
git commit -m "AlgebraDx v0.1.0"
git remote add origin https://github.com/YOUR_USER/algebradx.git && git push -u origin main
```

Releases → Draft a new release → tag `v0.1.0` → paste the release notes above → Publish.
Then put the GitHub URL into `README.md`, `CITATION.cff`, `pyproject.toml` (add a
`[project.urls]` table) and `paper/paper.md`.

Add `.github/workflows/tests.yml` so every push runs the tests (JOSS reviewers look for CI):

```yaml
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy: {matrix: {python: ["3.10", "3.12"]}}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "${{ matrix.python }}"}
      - run: pip install -e ".[test]" && pytest -q
```

## 2. Zenodo DOI

1. Log in at zenodo.org with ORCID.
2. Account → GitHub → flip the switch for `algebradx`.
3. Make (or re-make) the GitHub release `v0.1.0`; Zenodo archives it within minutes and mints a DOI.
4. Edit the Zenodo record: creators from `AUTHORS.json`; licence MIT; keywords from `CITATION.cff`; add the related identifier "is supplemented by" the attribute dictionary record once step 4 exists.
5. Copy the DOI into `CITATION.cff`, the README status line, and the evidence log.

Alternative with a token: `python tools/zenodo_deposit.py --help` (try `--sandbox` first).

## 3. PyPI

```bash
pip install build twine
python -m build
python -m twine upload dist/*        # username __token__, password = a PyPI API token scoped to this project
```

Check the name first at pypi.org/project/algebradx. If taken, rename the distribution (e.g. `algebra-dx`) in `pyproject.toml`; the import name can stay `algebradx`.

## 4. Q-matrix technical report (Zenodo, CC BY 4.0)

Upload type "Dataset": `qmatrix/attributes.csv`, the final `qmatrix_timss2023.csv` and
`qmatrix_timss2019.csv`, `qmatrix/CHANGELOG.md`, the rater-agreement table and a 3–5 page
PDF describing the coding procedure. Item IDs only — no item text (IEA terms).

## 5. Methods preprint

- arXiv `stat.AP` (statistics – applications). First submission in a category may need an
  endorsement; request one at arxiv.org/auth/endorse with this note:

  > I am preparing a methods paper on diagnostic classification models applied to TIMSS
  > grade-8 algebra items, with open-source software (AlgebraDx). Would you be willing to
  > endorse me for stat.AP? The draft is attached.

- Or EdArXiv (osf.io/preprints/edarxiv) — no endorsement, education audience.
- Build `paper/preprint.md` with `python code/07_build_paper.py`, convert to PDF (e.g. pandoc), check every number against `paper/stats.json`.
- Licence CC BY 4.0. Comments field: "Code: GitHub URL; DOI: Zenodo DOI".
- Include the AI-assistance sentence from the manuscript; it must be accurate.

## 6. Journal

Candidates: *Large-scale Assessments in Education* (open access, TIMSS/PISA methods),
*Journal of Educational Measurement*, *Educational Measurement: Issues and Practice*.
Check each journal's AI policy and fees before choosing.

## 7. JOSS

Requirements confirmed on joss.readthedocs.io (Oct 2026): repository public **more than six
months** with active development across that period; evidence of research use (the
preprint qualifies); OSI licence; tests; documentation; `paper/paper.md` + `paper.bib`; a
generative-AI disclosure. Submit at joss.theoj.org/papers/new with the repository URL and
the Zenodo DOI of the release under review.

## After every step

Same day: add a row to your evidence log
(`date,artifact_or_event,type,venue_or_host,link_or_doi,status,prong_tags,metrics_snapshot,files_saved,notes`),
save a PDF of the confirmation page, and update the README status line.
