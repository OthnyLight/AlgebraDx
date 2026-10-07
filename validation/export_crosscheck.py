#!/usr/bin/env python3
"""Export a fixed simulated dataset and AlgebraDx's estimates so they can be compared with
the R package GDINA (Ma & de la Torre 2020) by validation/crosscheck_gdina.R.

    python validation/export_crosscheck.py
    Rscript validation/crosscheck_gdina.R
"""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
from algebradx import DiagnosticModel, simulate  # noqa: E402

sim = simulate.simulate_dataset(n_students=2000, J=20, K=4, seed=20261006)
sim.responses.astype(int).to_csv(os.path.join(HERE, "crosscheck_data.csv"), index=False)
sim.qmatrix.to_frame().drop(columns="item").to_csv(os.path.join(HERE, "crosscheck_q.csv"), index=False)
res = {}
for model in ("GDINA", "DINA", "ACDM"):
    m = DiagnosticModel(sim.qmatrix, model, structural="saturated").fit(sim.responses, tol=1e-7, max_iter=5000)
    res[model] = {"loglik": m.loglik, "n_params": m.n_params,
                  "item_probs": [it.P.tolist() for it in m.item_models],
                  "prevalence": m.attribute_prevalence().tolist()}
with open(os.path.join(HERE, "crosscheck_algebradx.json"), "w") as f:
    json.dump(res, f, indent=1)
print({k: round(v["loglik"], 3) for k, v in res.items()})
