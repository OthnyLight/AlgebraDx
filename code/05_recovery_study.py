#!/usr/bin/env python3
"""Step 5 — parameter-recovery and classification-accuracy study (simulation).

Study A  complete data, K = 5 skills, J = 30 items, N in {500, 1000, 2000, 4000},
         G-DINA generating and fitted model, 20 replications per N.
Study B  TIMSS-like rotated-booklet design, K = 12 skills, J = 96 items, 7 booklets
         (each student answers about 27 items), N = 8000, sampling weights, 3 replications.

For each replication: RMSE and bias of item success probabilities, error in attribute
prevalence, agreement between true and estimated mastery per skill, whole-profile
agreement, and the model's own predicted accuracy (Johnson & Sinharay 2018) — a
well-calibrated index should predict the agreement actually achieved.

    python code/05_recovery_study.py            # writes results/recovery/recovery.csv
    python code/05_recovery_study.py --quick    # 3 replications in study A, 1 in B
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from algebradx import DiagnosticModel  # noqa: E402
from algebradx import fit as F  # noqa: E402
from algebradx import simulate as S  # noqa: E402

SEED = 7310


def one(study, N, J, K, booklets, rep, structural, weight_cv):
    seed = SEED + 1000 * rep + N + 7 * K
    sim = S.simulate_dataset(n_students=N, J=J, K=K, n_booklets=booklets, rho=0.5,
                             weight_cv=weight_cv, seed=seed)
    t = time.time()
    m = DiagnosticModel(sim.qmatrix, "GDINA", structural=structural).fit(
        sim.responses, weights=sim.weights, tol=1e-4)
    secs = time.time() - t
    err = np.concatenate([it.P - p for it, p in zip(m.item_models, sim.item_probs)])
    sc = m.score()
    est = sc.filter(regex="^m_").to_numpy()
    agree = (est == sim.alpha).mean(0)
    rel = F.classification_reliability(m)
    return {"study": study, "N": N, "J": J, "K": K, "booklets": booklets, "rep": rep,
            "items_per_student": float(sim.responses.notna().sum(axis=1).mean()),
            "rmse_P": float(np.sqrt(np.mean(err ** 2))), "bias_P": float(np.mean(err)),
            "max_abs_prevalence_error": float(np.abs(m.attribute_prevalence().values
                                                     - sim.alpha.mean(0)).max()),
            "attribute_agreement_mean": float(agree.mean()),
            "attribute_agreement_min": float(agree.min()),
            "pattern_agreement": float((est == sim.alpha).all(1).mean()),
            "predicted_attribute_accuracy": float(rel["attribute"]["accuracy"].mean()),
            "predicted_pattern_accuracy": float(rel["pattern_accuracy"]),
            "converged": m.converged, "em_steps": m.n_iter, "seconds": secs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    out = os.path.join(ROOT, "results", "recovery")
    os.makedirs(out, exist_ok=True)
    rows = []
    reps_a, reps_b = (3, 1) if a.quick else (20, 3)
    for N in (500, 1000, 2000, 4000):
        for r in range(reps_a):
            rows.append(one("A", N, 30, 5, 1, r, "saturated", 0.0))
        print(f"study A N={N} done")
    for r in range(reps_b):
        rows.append(one("B", 8000, 96, 12, 7, r, "loglinear2", 0.45))
        print(f"study B rep {r} done ({rows[-1]['seconds']:.0f}s)")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out, "recovery.csv"), index=False)
    print(df.groupby(["study", "N"]).mean(numeric_only=True)[
        ["rmse_P", "attribute_agreement_mean", "predicted_attribute_accuracy", "pattern_agreement"]].round(3))


if __name__ == "__main__":
    main()
