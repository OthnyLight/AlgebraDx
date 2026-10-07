"""Empirical Q-matrix validation with the G-DINA discrimination index (GDI).

For item j and a candidate set S of attributes, the GDI is the variance of the item's
success probability across the latent groups that S defines (de la Torre & Chiu 2016):

    zeta^2_j(S) = sum_g pi(g) [P_j(g) - Pbar_j]^2

and the proportion of variance accounted for is PVAF_j(S) = zeta^2_j(S) / zeta^2_j(all K).
The suggested q-vector is the smallest S whose PVAF reaches ``epsilon``. Success
probabilities for every full profile are estimated from the posterior of a fitted
saturated model, so the provisional Q-matrix only enters through that fit.

Suggestions are evidence for a content expert to weigh, never automatic edits:
the method ignores what an item asks the student to do.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd


def _profile_success(model):
    R, Nn = model._R, model._Nn
    with np.errstate(invalid="ignore", divide="ignore"):
        P = np.where(Nn > 1e-8, R / Nn, np.nan)
    # profiles with no information: fall back to the item's overall proportion
    fill = (R.sum(1) / np.maximum(Nn.sum(1), 1e-12))[:, None]
    return np.where(np.isnan(P), fill, P)


def gdi_validation(model, epsilon: float = 0.95, max_attrs: int = 4, plateau: float = 0.01,
                   min_gain: float = 0.02) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (suggestions, mesa) tables.

    suggestions: one row per item with the provisional q-vector, its PVAF, the suggested
    q-vector, its PVAF and whether they differ.
    mesa: for every item, the best PVAF achievable with 1..max_attrs attributes (the data
    behind a mesa plot; de la Torre & Ma 2016).

    Rules. The suggestion is the smallest q-vector with PVAF >= ``epsilon``. With many
    attributes and rotated booklets, posterior estimates of 2^K success probabilities are
    noisy and inflate the denominator, so often no vector reaches ``epsilon``; then the
    suggestion is the smallest vector within ``plateau`` of the best PVAF found (the edge
    of the mesa). An item is flagged only when the suggestion differs from the
    provisional vector *and* raises PVAF by at least ``min_gain``, so tiny noise-driven
    gains are not reported as misspecifications.
    """
    if not model.fitted:
        raise ValueError("fit the model first")
    prof = model.profiles.astype(np.int64)
    L, K = prof.shape
    pi = model.structural.pi
    Phat = _profile_success(model)                         # J x L
    Pbar = Phat @ pi
    zeta_full = ((Phat - Pbar[:, None]) ** 2) @ pi           # J
    PW = Phat * pi                                           # J x L

    cands = [c for s in range(1, min(max_attrs, K) + 1) for c in combinations(range(K), s)]
    J = Phat.shape[0]
    pvaf = np.zeros((J, len(cands)))
    for ci, c in enumerate(cands):
        gid = prof[:, list(c)] @ (1 << np.arange(len(c) - 1, -1, -1))
        G = 1 << len(c)
        pig = np.bincount(gid, weights=pi, minlength=G)
        ind = np.zeros((L, G))
        ind[np.arange(L), gid] = 1.0
        sg = PW @ ind                                        # J x G
        with np.errstate(invalid="ignore", divide="ignore"):
            zeta = np.where(pig > 0, sg ** 2 / pig, 0).sum(1) - Pbar ** 2
        pvaf[:, ci] = zeta / np.maximum(zeta_full, 1e-15)
    sizes = np.array([len(c) for c in cands])

    rows, mesa = [], []
    for j in range(J):
        prov = tuple(np.where(model.q.q[j])[0])
        prov_pvaf = pvaf[j, cands.index(prov)] if prov in cands else np.nan
        best_by_size = {}
        for s in range(1, sizes.max() + 1):
            idx = np.where(sizes == s)[0]
            b = idx[np.argmax(pvaf[j, idx])]
            best_by_size[s] = (cands[b], pvaf[j, b])
            mesa.append({"item": model.q.items[j], "n_attributes": s,
                         "best_q": _fmt(cands[b], model.q.attributes), "pvaf": pvaf[j, b]})
        sugg = None
        for s in sorted(best_by_size):
            if best_by_size[s][1] >= epsilon:
                sugg = best_by_size[s]
                break
        if sugg is None:
            top = max(v[1] for v in best_by_size.values())
            for s in sorted(best_by_size):
                if best_by_size[s][1] >= top - plateau:
                    sugg = best_by_size[s]
                    break
        rows.append({"item": model.q.items[j],
                     "provisional_q": _fmt(prov, model.q.attributes),
                     "provisional_pvaf": prov_pvaf,
                     "suggested_q": _fmt(sugg[0], model.q.attributes),
                     "suggested_pvaf": sugg[1],
                     "gdi_full": zeta_full[j],
                     "differs": bool(tuple(sugg[0]) != prov and
                                     (np.isnan(prov_pvaf) or sugg[1] - prov_pvaf >= min_gain))})
    return pd.DataFrame(rows), pd.DataFrame(mesa)


def _fmt(c, names):
    return "+".join(names[k] for k in c)
