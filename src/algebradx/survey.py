"""Survey-design standard errors with replicate weights.

Large-scale assessments sample schools, then classes, so students are not independent
and model-based standard errors are too small. TIMSS and PISA publish replicate weights
(or the ingredients to build them); refitting the model under each replicate weight and
measuring the spread of the estimates gives design-consistent standard errors
(Rust & Rao 1996).

* TIMSS: jackknife repeated replication from ``JKZONE`` and ``JKREP``.
  ``scheme="full"`` makes two replicates per zone (one per half) with variance factor 1/2,
  the approach documented from TIMSS 2015 onward; ``scheme="half"`` makes one replicate per
  zone with factor 1, the approach of earlier cycles. Check the user guide for the cycle
  you analyse (Foy & LaRoche 2017; Martin, von Davier & Mullis 2020).
* PISA 2022: 80 Fay-adjusted balanced repeated replication weights ``W_FSTURWT1``-``80``
  with Fay factor k = 0.5, so the variance factor is 1 / (80 (1 - 0.5)^2) = 1/20 (OECD 2024).
"""
from __future__ import annotations

import copy
from typing import Callable

import numpy as np
import pandas as pd


def timss_replicate_weights(weight, jkzone, jkrep, scheme: str = "full"):
    """Return (replicate weight matrix N x R, variance factor)."""
    w = np.asarray(weight, dtype=float)
    z = np.asarray(jkzone).astype(int)
    r = np.asarray(jkrep).astype(int)
    zones = np.unique(z[z > 0])
    reps = []
    for h in zones:
        inz = z == h
        a = w.copy()
        a[inz & (r == 1)] *= 2
        a[inz & (r == 0)] = 0
        reps.append(a)
        if scheme == "full":
            b = w.copy()
            b[inz & (r == 0)] *= 2
            b[inz & (r == 1)] = 0
            reps.append(b)
    if scheme not in ("full", "half"):
        raise ValueError("scheme must be 'full' or 'half'")
    return np.column_stack(reps), (0.5 if scheme == "full" else 1.0)


def pisa_replicate_weights(frame: pd.DataFrame, prefix: str = "W_FSTURWT", n: int = 80,
                           fay: float = 0.5):
    cols = [f"{prefix}{i}" for i in range(1, n + 1)]
    missing = [c for c in cols if c not in frame.columns]
    if missing:
        raise ValueError(f"replicate weight columns missing: {missing[:3]}...")
    return frame[cols].to_numpy(dtype=float), 1.0 / (n * (1 - fay) ** 2)


def default_statistics(model) -> pd.Series:
    """Attribute prevalences, then each item's guessing and slipping parameters."""
    prev = model.attribute_prevalence()
    gs = model.guess_slip()
    parts = [prev.rename(lambda a: f"prevalence:{a}"),
             pd.Series(gs["guess"].to_numpy(), index=[f"guess:{i}" for i in gs["item"]]),
             pd.Series(gs["slip"].to_numpy(), index=[f"slip:{i}" for i in gs["item"]])]
    return pd.concat(parts)


def replicate_standard_errors(model, replicate_weights: np.ndarray, factor: float,
                              statistic: Callable = default_statistics, max_iter: int = 300,
                              tol: float = 1e-4, progress: bool = False) -> pd.DataFrame:
    """Refit ``model`` (already fitted with the full weight) under every replicate weight,
    starting from the full-sample solution, and return estimate, SE and the number of
    replicates per statistic."""
    if not model.fitted:
        raise ValueError("fit the model with the full-sample weight first")
    full = statistic(model)
    X = model._X
    reps = []
    R = replicate_weights.shape[1]
    for r in range(R):
        m = copy.deepcopy(model, {id(model._X): model._X, id(model._w): model._w})
        m._cov = None
        m.fit(X, weights=replicate_weights[:, r], max_iter=max_iter, tol=tol,
              warm_start=True, chunk_size=model._chunk)
        reps.append(statistic(m).reindex(full.index).to_numpy())
        if progress and (r + 1) % 10 == 0:
            print(f"  replicate {r + 1}/{R}")
    reps = np.array(reps)
    se = np.sqrt(factor * ((reps - full.to_numpy()) ** 2).sum(0))
    return pd.DataFrame({"statistic": full.index, "estimate": full.to_numpy(), "se": se,
                         "n_replicates": R})
