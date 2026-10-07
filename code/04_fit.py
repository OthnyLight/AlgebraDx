#!/usr/bin/env python3
"""Step 4 — fit the diagnostic models to one source and write every result table.

    python code/04_fit.py --source synthetic            # runs anywhere, no restricted data
    python code/04_fit.py --source timss2023 --qmatrix qmatrix/qmatrix_timss2023.csv
    python code/04_fit.py --source timss2019 --qmatrix qmatrix/qmatrix_timss2019.csv
    python code/04_fit.py --source pisa2022  --qmatrix qmatrix/qmatrix_pisa2022.csv

Model sequence (the analysis plan; each step's output is saved):
  1. G-DINA with a second-order log-linear structural model (the general model)
  2. DINA, DINO, ACDM, LLM, R-RUM for every item (relative fit, AIC/BIC)
  3. item-level Wald tests against G-DINA -> one reduced model per item where supported
  4. the mixed model from step 3; absolute fit, classification reliability
  5. Q-matrix validation (GDI/PVAF) on the G-DINA fit
  6. survey-design standard errors of attribute prevalences from replicate weights
     (--replicates N limits the number of replicates for a quick run; 0 skips)

Results go to results/<source>/. Real-data results stay local until verified.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from algebradx import AttributeDictionary, DiagnosticModel, QMatrix  # noqa: E402
from algebradx import fit as F  # noqa: E402
from algebradx import qvalidation as QV  # noqa: E402
from algebradx import simulate as S  # noqa: E402
from algebradx import survey as SV  # noqa: E402

SYN_SEED = 20261006
SYN_N, SYN_J, SYN_BOOKLETS = 8000, 96, 7
SYN_PREVALENCE = [0.72, 0.62, 0.55, 0.66, 0.52, 0.45, 0.50, 0.30, 0.25, 0.58, 0.48, 0.35]


def synthetic():
    """A TIMSS-like synthetic dataset on the 12 drafted skills (fixed seed). Not real data."""
    d = AttributeDictionary.from_csv(os.path.join(ROOT, "qmatrix", "attributes.csv"))
    q0 = S.random_qmatrix(SYN_J, len(d.codes), max_attrs=3, seed=SYN_SEED, prefix="SYN")
    q = QMatrix(q0.q, q0.items, d.codes, d.names)
    alpha = S.correlated_profiles(SYN_N, q.K, rho=0.55, prevalence=SYN_PREVALENCE, seed=SYN_SEED + 1)
    sim = S.simulate_dataset(q=q, alpha=alpha, n_booklets=SYN_BOOKLETS, n_zones=75,
                             weight_cv=0.45, seed=SYN_SEED + 2)
    resp = sim.responses.copy()
    resp.insert(0, "id", [f"S{i + 1:05d}" for i in range(len(resp))])
    resp["TOTWGT"], resp["JKZONE"], resp["JKREP"] = sim.weights, sim.jk_zone, sim.jk_rep
    os.makedirs(os.path.join(ROOT, "data", "processed"), exist_ok=True)
    resp.to_csv(os.path.join(ROOT, "data", "processed", "synthetic_responses.csv.gz"), index=False)
    q.to_csv(os.path.join(ROOT, "qmatrix", "qmatrix_synthetic_demo.csv"))
    truth = {"alpha": alpha, "item_probs": sim.item_probs}
    return resp, q, d, truth


def merge_skills(qpath, merges, d, out_path):
    """Fold skills into others for one analysis, e.g. A09 -> A05 when an assessment has too
    few items to measure A09 separately. Writes the merged Q-matrix next to the results."""
    qdf = pd.read_csv(qpath, dtype={"item": str})
    for src, dst in merges:
        qdf[dst] = qdf[[src, dst]].max(axis=1)
        qdf = qdf.drop(columns=src)
    qdf.to_csv(out_path, index=False)
    table = d.table[~d.table["code"].isin([s for s, _ in merges])].copy()
    for src, dst in merges:
        i = table.index[table["code"] == dst][0]
        table.loc[i, "name"] = f"{table.loc[i, 'name']} (incl. {d.names[src].lower()})"
        table["prerequisites"] = table["prerequisites"].str.replace(src, dst)
    return out_path, AttributeDictionary(table.reset_index(drop=True))


def load_real(source, qpath, allow_draft, merges=(), out=None):
    d = AttributeDictionary.from_csv(os.path.join(ROOT, "qmatrix", "attributes.csv"))
    if merges:
        qpath, d = merge_skills(qpath, merges, d, os.path.join(out, "qmatrix_used.csv"))
    qdf = pd.read_csv(qpath, dtype={"item": str})
    cyc = source[-4:]
    if f"in_{cyc}" in qdf.columns:
        qdf = qdf[qdf[f"in_{cyc}"] == 1]
        qdf.to_csv(os.path.join(out, "qmatrix_used.csv"), index=False)
        qpath = os.path.join(out, "qmatrix_used.csv")
    if "status" in qdf.columns and (qdf["status"].astype(str).str.strip() != "ok").any() and not allow_draft:
        raise SystemExit("Q-matrix still has unverified rows; rule on them first (or --allow-draft "
                         "for an exploratory run whose results must not be reported)")
    q = QMatrix.from_csv(qpath, dictionary=d)
    resp = pd.read_csv(os.path.join(ROOT, "data", "extract", f"{source}_usa_scored.csv.gz"),
                       dtype={"id": str})
    keep = [i for i in q.items if i in resp.columns]
    dropped = sorted(set(q.items) - set(keep))
    if dropped:
        print(f"note: {len(dropped)} Q-matrix items not in the {source} file: {dropped[:8]}")
    return resp, q.subset(keep), d, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="synthetic",
                    choices=["synthetic", "timss2023", "timss2019", "pisa2022"])
    ap.add_argument("--qmatrix")
    ap.add_argument("--allow-draft", action="store_true")
    ap.add_argument("--replicates", type=int, default=-1,
                    help="number of replicate weights to use (-1 all, 0 skip)")
    ap.add_argument("--jk-scheme", default="full", choices=["full", "half"])
    ap.add_argument("--skip-reduced", action="store_true", help="skip step 2 (faster)")
    ap.add_argument("--merge", nargs="*", default=[], metavar="SRC:DST",
                    help="fold one skill into another for this analysis, e.g. A09:A05")
    a = ap.parse_args()

    out = os.path.join(ROOT, "results", a.source)
    os.makedirs(out, exist_ok=True)
    if a.source == "synthetic":
        resp, q, d, truth = synthetic()
    else:
        if not a.qmatrix:
            raise SystemExit("--qmatrix is required for real data")
        merges = [tuple(m.split(":")) for m in a.merge]
        resp, q, d, truth = load_real(a.source, a.qmatrix, a.allow_draft, merges, out)

    wcol = "W_FSTUWT" if a.source == "pisa2022" else "TOTWGT"
    w = resp[wcol].to_numpy(dtype=float)
    X = resp[q.items]
    log = {"source": a.source, "n_students": len(resp), "n_items": q.J, "K": q.K,
           "items_per_student_mean": float(X.notna().sum(axis=1).mean()),
           "coverage": q.coverage().to_dict("records"),
           "identifiability": q.identifiability_report()}
    print(f"{a.source}: {len(resp):,} students, {q.J} items, K = {q.K}; "
          f"{log['items_per_student_mean']:.1f} items answered per student")

    fits = {}
    t = time.time()
    g = DiagnosticModel(q, "GDINA", structural="loglinear2").fit(X, weights=w, tol=1e-4)
    g.compute_standard_errors()
    fits["GDINA"] = g
    print(f"  G-DINA: loglik {g.loglik:,.1f}, {g.n_iter} EM steps, {time.time() - t:.0f}s")
    if not a.skip_reduced:
        for name in ["DINA", "DINO", "ACDM", "LLM", "RRUM"]:
            t = time.time()
            fits[name] = DiagnosticModel(q, name, structural="loglinear2").fit(X, weights=w, tol=1e-4)
            print(f"  {name}: loglik {fits[name].loglik:,.1f}, {time.time() - t:.0f}s")
    wald = F.wald_item_tests(g)
    choice = F.select_item_models(wald)
    t = time.time()
    mixed = DiagnosticModel(q, choice, structural="loglinear2").fit(X, weights=w, tol=1e-4)
    mixed.compute_standard_errors()
    fits["Mixed (Wald)"] = mixed
    print(f"  mixed model: {pd.Series(list(choice.values())).value_counts().to_dict()}, {time.time() - t:.0f}s")

    rel_fit = F.relative_fit(fits)
    rel_fit.to_csv(os.path.join(out, "relative_fit.csv"), index=False)
    wald.to_csv(os.path.join(out, "wald_item_tests.csv"), index=False)
    pd.Series(choice, name="model").rename_axis("item").to_csv(os.path.join(out, "item_model_choice.csv"))

    best_name = rel_fit.sort_values("bic").iloc[0]["model"]
    final = fits["Mixed (Wald)"] if best_name not in fits else fits[best_name]
    final_name = best_name
    af = F.absolute_fit(final)
    af["pairs"].to_csv(os.path.join(out, "fit_item_pairs.csv"), index=False)
    af["items"].to_csv(os.path.join(out, "fit_items.csv"), index=False)
    rel = F.classification_reliability(final)
    rel["attribute"].to_csv(os.path.join(out, "classification_reliability.csv"), index=False)
    qv, mesa = QV.gdi_validation(g)
    qv.to_csv(os.path.join(out, "qmatrix_validation.csv"), index=False)
    mesa.to_csv(os.path.join(out, "qmatrix_mesa.csv"), index=False)
    final.item_parameters().to_csv(os.path.join(out, "item_parameters.csv"), index=False)
    final.guess_slip().to_csv(os.path.join(out, "guess_slip.csv"), index=False)
    final.save(os.path.join(out, "calibration.json"))
    scores = final.score(ids=resp["id"])
    scores.to_csv(os.path.join(out, "student_scores.csv.gz"), index=False)

    # survey-design standard errors for prevalences
    prev = final.attribute_prevalence().rename("estimate").to_frame()
    if a.replicates != 0:
        if a.source == "pisa2022":
            R, factor = SV.pisa_replicate_weights(resp)
        else:
            R, factor = SV.timss_replicate_weights(w, resp["JKZONE"], resp["JKREP"], a.jk_scheme)
        if 0 < a.replicates < R.shape[1]:
            # a subset of replicates gives a rough SE only; rescale the factor accordingly
            factor *= R.shape[1] / a.replicates
            R = R[:, :a.replicates]
        t = time.time()
        se = SV.replicate_standard_errors(
            final, R, factor, statistic=lambda m: m.attribute_prevalence(), max_iter=60, tol=1e-3)
        prev["se_replicate"] = se["se"].to_numpy()
        prev["n_replicates"] = R.shape[1]
        print(f"  replicate SEs: {R.shape[1]} refits, {time.time() - t:.0f}s")
    prev.index.name = "attribute"
    prev["name"] = [d.names.get(k, k) for k in prev.index]
    if truth is not None:
        prev["true_prevalence"] = truth["alpha"].mean(0)
        est = scores.filter(regex="^m_").to_numpy()
        prev["true_classification_agreement"] = (est == truth["alpha"]).mean(0)
        log["true_pattern_agreement"] = float((est == truth["alpha"]).all(1).mean())
        log["item_prob_rmse_vs_truth"] = float(np.sqrt(np.mean(np.concatenate(
            [(it.P - p) ** 2 for it, p in zip(g.item_models, truth["item_probs"])]))))
    prev.to_csv(os.path.join(out, "attribute_prevalence.csv"))

    log.update({"final_model": final_name, "summary": final.summary(),
                "srmsr": af["srmsr"], "max_z_correlation": af["max_z_correlation"],
                "p_adj_correlation": af["p_adj_correlation"],
                "max_z_log_odds": af["max_z_log_odds"], "p_adj_log_odds": af["p_adj_log_odds"],
                "pattern_accuracy": rel["pattern_accuracy"],
                "pattern_consistency": rel["pattern_consistency"],
                "q_items_flagged": int(qv["differs"].sum()),
                "item_model_counts": pd.Series(list(choice.values())).value_counts().to_dict()})
    with open(os.path.join(out, "fit_log.json"), "w") as f:
        json.dump(log, f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"done -> results/{a.source}/")


if __name__ == "__main__":
    main()
