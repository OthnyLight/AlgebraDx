"""Command-line interface: ``algebradx fit | score | check-q | simulate``."""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

from . import __version__
from . import fit as F
from . import qvalidation as QV
from . import report as RP
from . import simulate as S
from .model import DiagnosticModel
from .qmatrix import AttributeDictionary, QMatrix


def _load_q(args):
    d = AttributeDictionary.from_csv(args.attributes) if getattr(args, "attributes", None) else None
    q = QMatrix.from_csv(args.qmatrix, dictionary=d)
    return q, d


def _read_responses(path, id_col):
    df = pd.read_csv(path, dtype={id_col: str}) if id_col else pd.read_csv(path)
    return df


def cmd_fit(args):
    q, d = _load_q(args)
    df = _read_responses(args.responses, args.id)
    present = [i for i in q.items if i in df.columns]
    if len(present) < q.J:
        print(f"note: {q.J - len(present)} Q-matrix items absent from responses; dropped", file=sys.stderr)
        q = q.subset(present)
    hier = d.hierarchy() if (d is not None and args.hierarchy) else None
    w = df[args.weight].to_numpy(dtype=float) if args.weight else None
    m = DiagnosticModel(q, args.model, structural=args.structural, hierarchy=hier)
    m.fit(df[q.items], weights=w, tol=args.tol, max_iter=args.max_iter, n_starts=args.starts,
          verbose=args.verbose)
    os.makedirs(args.out, exist_ok=True)
    m.save(os.path.join(args.out, "calibration.json"))
    m.compute_standard_errors()
    m.item_parameters().to_csv(os.path.join(args.out, "item_parameters.csv"), index=False)
    m.guess_slip().to_csv(os.path.join(args.out, "guess_slip.csv"), index=False)
    m.attribute_prevalence().to_csv(os.path.join(args.out, "attribute_prevalence.csv"))
    ids = df[args.id] if args.id else None
    scores = m.score(ids=ids)
    scores.to_csv(os.path.join(args.out, "student_scores.csv"), index=False)
    af = F.absolute_fit(m)
    af["pairs"].to_csv(os.path.join(args.out, "fit_item_pairs.csv"), index=False)
    rel = F.classification_reliability(m)
    rel["attribute"].to_csv(os.path.join(args.out, "classification_reliability.csv"), index=False)
    qv, mesa = QV.gdi_validation(m)
    qv.to_csv(os.path.join(args.out, "qmatrix_validation.csv"), index=False)
    mesa.to_csv(os.path.join(args.out, "qmatrix_mesa.csv"), index=False)
    if args.model.upper() in ("GDINA", "LCDM"):
        F.wald_item_tests(m).to_csv(os.path.join(args.out, "wald_item_tests.csv"), index=False)
    names = d.names if d is not None else {}
    summary = m.summary() | {k: v for k, v in af.items() if not isinstance(v, pd.DataFrame)} | {
        "pattern_accuracy": rel["pattern_accuracy"], "pattern_consistency": rel["pattern_consistency"],
        "q_items_flagged": int(qv["differs"].sum()), "algebradx_version": __version__}
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=float)
    with open(os.path.join(args.out, "report.html"), "w") as f:
        f.write(RP.html_report(scores, q.attributes, names,
                               title="AlgebraDx skill report"))
    print(json.dumps({k: summary[k] for k in ("n_students", "n_items", "K", "loglik", "aic", "bic",
                                              "srmsr", "pattern_accuracy", "converged")},
                     indent=2, default=float))
    print(f"wrote results to {args.out}/")


def cmd_score(args):
    m = DiagnosticModel.load(args.calibration)
    df = _read_responses(args.responses, args.id)
    for i in m.q.items:
        if i not in df.columns:
            df[i] = np.nan          # items the new test did not use carry no information
    scores = m.score(df[m.q.items], ids=df[args.id] if args.id else None,
                     threshold=args.threshold)
    scores.to_csv(args.out, index=False)
    if args.html:
        with open(args.html, "w") as f:
            f.write(RP.html_report(scores, m.q.attributes, m.q.attribute_names))
    print(f"scored {len(scores)} students -> {args.out}")


def cmd_check_q(args):
    q, d = _load_q(args)
    print(q.coverage().to_string(index=False))
    print(json.dumps(q.identifiability_report(), indent=2))
    if d is not None and d.hierarchy():
        from .qmatrix import permissible_profiles
        idx = [(q.attributes.index(a), q.attributes.index(b)) for a, b in d.hierarchy()]
        print(f"hierarchy: {len(d.hierarchy())} prerequisite links, "
              f"{len(permissible_profiles(q.K, idx))} of {2 ** q.K} profiles permissible")


def cmd_simulate(args):
    sim = S.simulate_dataset(n_students=args.n, J=args.items, K=args.attributes, model=args.model,
                             n_booklets=args.booklets, weight_cv=args.weight_cv, seed=args.seed)
    os.makedirs(args.out, exist_ok=True)
    resp = sim.responses.copy()
    resp.insert(0, "id", [f"S{i + 1:05d}" for i in range(len(resp))])
    resp["weight"] = sim.weights
    resp.to_csv(os.path.join(args.out, "responses.csv"), index=False)
    sim.qmatrix.to_csv(os.path.join(args.out, "qmatrix.csv"))
    pd.DataFrame(sim.alpha, columns=sim.qmatrix.attributes).assign(id=resp["id"]).to_csv(
        os.path.join(args.out, "true_profiles.csv"), index=False)
    print(f"wrote simulated data to {args.out}/")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="algebradx", description=__doc__)
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fit", help="calibrate a model and score the calibration sample")
    f.add_argument("--responses", required=True, help="CSV: one row per student, 0/1/blank per item")
    f.add_argument("--qmatrix", required=True)
    f.add_argument("--attributes", help="attribute dictionary CSV (code,name,definition,prerequisites)")
    f.add_argument("--id", help="student id column")
    f.add_argument("--weight", help="sampling weight column")
    f.add_argument("--model", default="GDINA")
    f.add_argument("--structural", default="loglinear2")
    f.add_argument("--hierarchy", action="store_true", help="apply prerequisites in the dictionary")
    f.add_argument("--tol", type=float, default=1e-4)
    f.add_argument("--max-iter", type=int, default=2000)
    f.add_argument("--starts", type=int, default=1)
    f.add_argument("--out", default="algebradx_results")
    f.add_argument("--verbose", action="store_true")
    f.set_defaults(func=cmd_fit)

    s = sub.add_parser("score", help="score new students with a saved calibration")
    s.add_argument("--calibration", required=True)
    s.add_argument("--responses", required=True)
    s.add_argument("--id")
    s.add_argument("--threshold", type=float, default=0.5)
    s.add_argument("--out", default="scores.csv")
    s.add_argument("--html")
    s.set_defaults(func=cmd_score)

    c = sub.add_parser("check-q", help="coverage and identifiability checks for a Q-matrix")
    c.add_argument("--qmatrix", required=True)
    c.add_argument("--attributes")
    c.set_defaults(func=cmd_check_q)

    m = sub.add_parser("simulate", help="write a simulated demonstration dataset")
    m.add_argument("--n", type=int, default=2000)
    m.add_argument("--items", type=int, default=30)
    m.add_argument("--attributes", type=int, default=5)
    m.add_argument("--model", default="GDINA")
    m.add_argument("--booklets", type=int, default=1)
    m.add_argument("--weight-cv", type=float, default=0.0)
    m.add_argument("--seed", type=int, default=1)
    m.add_argument("--out", default="simulated")
    m.set_defaults(func=cmd_simulate)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
