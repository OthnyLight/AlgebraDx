"""Model fit, item-level model comparison and classification reliability."""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

from .items import EPS, design_matrix, link, saturated_terms


# --------------------------------------------------------------- absolute fit
def _implied_moments(model):
    PL = np.clip(model._prob_matrix(), EPS, 1 - EPS)
    pi = model.structural.pi
    p1 = PL @ pi
    p11 = (PL * pi) @ PL.T
    return p1, p11


def absolute_fit(model, min_pairs: int = 30, alpha: float = 0.05) -> dict:
    """Item-pair residual statistics (Chen, de la Torre & Zhang 2013) and SRMSR
    (Maydeu-Olivares 2013), computed from the pairs of items a student actually answered.

    Model-implied moments use the estimated population profile distribution, which applies
    to any random subsample of students, so rotated booklet designs are handled naturally.
    Observed statistics use the fitted sampling weights; standard errors use unweighted
    counts and ignore parameter estimation, as in Chen et al. (2013).

    Returns a dict with ``srmsr``, the maximum absolute z-statistics and Bonferroni-adjusted
    p-values for proportion correct, transformed correlation and log-odds ratio, and the
    item-pair table.
    """
    X, w = model._X, model._w
    obs = ~np.isnan(X)
    x1 = np.where(obs, np.nan_to_num(X), 0.0)
    p1, p11 = _implied_moments(model)
    J = X.shape[1]

    # proportion correct
    nj = obs.sum(0)
    wj = (w[:, None] * obs).sum(0)
    pobs = (w[:, None] * x1).sum(0) / np.maximum(wj, 1e-12)
    z_p = (pobs - p1) / np.sqrt(p1 * (1 - p1) / np.maximum(nj, 1))
    item_tab = pd.DataFrame({"item": model.q.items, "n": nj, "p_obs": pobs, "p_model": p1, "z": z_p})

    rows = []
    W1 = w[:, None] * x1
    Wo = w[:, None] * obs
    n_both = obs.T.astype(float) @ obs.astype(float)
    w_both = Wo.T @ obs.astype(float)
    w11 = W1.T @ x1
    w1_ = W1.T @ obs.astype(float)          # [j,k]: weight with x_j=1 among both observed
    for j, k in combinations(range(J), 2):
        n = n_both[j, k]
        if n < min_pairs:
            continue
        tot = w_both[j, k]
        a = w11[j, k] / tot                  # P(1,1)
        pj = w1_[j, k] / tot                 # P(x_j = 1)
        pk = w1_[k, j] / tot                 # P(x_k = 1)
        b, c, d = pj - a, pk - a, 1 - pj - pk + a
        m11 = p11[j, k]
        mj, mk = p1[j], p1[k]
        mb, mc, md = mj - m11, mk - m11, 1 - mj - mk + m11
        # transformed correlation
        def corr(p11_, pj_, pk_):
            den = np.sqrt(pj_ * (1 - pj_) * pk_ * (1 - pk_))
            return (p11_ - pj_ * pk_) / den if den > 0 else 0.0
        r_o, r_m = corr(a, pj, pk), corr(m11, mj, mk)
        z_r = (np.arctanh(np.clip(r_o, -0.999, 0.999)) - np.arctanh(np.clip(r_m, -0.999, 0.999))) \
            * np.sqrt(max(n - 3, 1))
        # log odds ratio (0.5 correction on observed counts)
        cells = np.array([a, b, c, d]) * n + 0.5
        lor_o = np.log(cells[0] * cells[3] / (cells[1] * cells[2]))
        mcells = np.clip(np.array([m11, mb, mc, md]), 1e-12, None)
        lor_m = np.log(mcells[0] * mcells[3] / (mcells[1] * mcells[2]))
        z_l = (lor_o - lor_m) / np.sqrt((1 / cells).sum())
        rows.append((model.q.items[j], model.q.items[k], int(n), r_o, r_m, z_r, lor_o, lor_m, z_l))
    pairs = pd.DataFrame(rows, columns=["item_1", "item_2", "n", "r_obs", "r_model", "z_r",
                                        "lor_obs", "lor_model", "z_lor"])

    def maxstat(z, m):
        if len(z) == 0:
            return np.nan, np.nan
        zmax = float(np.max(np.abs(z)))
        p = min(1.0, 2 * stats.norm.sf(zmax) * m)
        return zmax, p

    m_pairs = len(pairs)
    zp, pp = maxstat(item_tab["z"].to_numpy(), J)
    zr, pr = maxstat(pairs["z_r"].to_numpy(), m_pairs)
    zl, pl = maxstat(pairs["z_lor"].to_numpy(), m_pairs)
    srmsr = float(np.sqrt(np.mean((pairs["r_obs"] - pairs["r_model"]) ** 2))) if m_pairs else np.nan
    return {"srmsr": srmsr, "n_pairs": m_pairs,
            "max_z_proportion": zp, "p_adj_proportion": pp,
            "max_z_correlation": zr, "p_adj_correlation": pr,
            "max_z_log_odds": zl, "p_adj_log_odds": pl,
            "share_pairs_flagged_correlation": float((2 * stats.norm.sf(np.abs(pairs["z_r"])) * m_pairs < alpha).mean()) if m_pairs else np.nan,
            "items": item_tab, "pairs": pairs}


def relative_fit(models: dict) -> pd.DataFrame:
    """AIC, BIC, -2LL and parameter counts for several fitted models on the same data."""
    rows = []
    for name, m in models.items():
        rows.append({"model": name, "loglik": m.loglik, "deviance": m.deviance,
                     "n_params": m.n_params, "aic": m.aic, "bic": m.bic})
    df = pd.DataFrame(rows)
    df["delta_aic"] = df["aic"] - df["aic"].min()
    df["delta_bic"] = df["bic"] - df["bic"].min()
    return df


def likelihood_ratio(reduced, full) -> dict:
    """LR test of nested models (e.g. DINA nested in G-DINA). Valid only without sampling
    weights; with weights use the Wald tests in :func:`wald_item_tests` or replicate weights."""
    stat = 2 * (full.loglik - reduced.loglik)
    df = full.n_params - reduced.n_params
    return {"statistic": stat, "df": df, "p": float(stats.chi2.sf(stat, df)) if df > 0 else np.nan}


# ------------------------------------------------------------- Wald tests
def _restriction(Kj: int, target: str) -> tuple[np.ndarray, str]:
    """Restriction matrix R (on group probabilities, or on link-scale saturated
    parameters) whose rows must equal zero under the reduced model."""
    G = 2 ** Kj
    target = target.upper()
    if target == "DINA":       # all groups except the full-mastery group are equal
        R = np.zeros((G - 2, G))
        for r, g in enumerate(range(1, G - 1)):
            R[r, 0], R[r, g] = -1, 1
        return R, "identity"
    if target == "DINO":       # all groups except group 0 are equal
        R = np.zeros((G - 2, G))
        for r, g in enumerate(range(2, G)):
            R[r, 1], R[r, g] = -1, 1
        return R, "identity"
    D, _ = design_matrix(Kj, "saturated")
    Dinv = np.linalg.inv(D)
    inter = [i for i, t in enumerate(saturated_terms(Kj)) if len(t) > 1]   # interaction terms
    lk = {"ACDM": "identity", "LLM": "logit", "RRUM": "log"}[target]
    return Dinv[inter], lk


def wald_item_tests(model, targets=("DINA", "DINO", "ACDM", "LLM", "RRUM")) -> pd.DataFrame:
    """Item-level Wald tests of reduced models against G-DINA (de la Torre & Lee 2013;
    Ma, Iaconangelo & de la Torre 2016). ``model`` must be a saturated-item fit (GDINA or
    LCDM) with standard errors computed. Items requiring one attribute are skipped."""
    if model._cov is None:
        model.compute_standard_errors()
    rows = []
    for j, it in enumerate(model.item_models):
        if it.n_params != it.n_groups:
            raise ValueError("Wald tests need a saturated item model (GDINA or LCDM)")
        if it.Kj < 2:
            continue
        cov = model._cov[j]
        rec = {"item": model.q.items[j], "K_j": it.Kj}
        for t in targets:
            R, lk = _restriction(it.Kj, t)
            if lk == "identity":
                theta, J = it.P, np.eye(it.n_groups)
            else:
                eta = link(it.P, lk)
                theta = eta
                J = np.diag(1 / {"logit": it.P * (1 - it.P), "log": it.P}[lk])
            V = R @ J @ cov @ J.T @ R.T
            v = R @ theta
            try:
                W = float(v @ np.linalg.solve(V, v))
            except np.linalg.LinAlgError:
                W = float(v @ np.linalg.pinv(V) @ v)
            df = R.shape[0]
            rec[f"W_{t}"] = W
            rec[f"p_{t}"] = float(stats.chi2.sf(W, df))
        rows.append(rec)
    return pd.DataFrame(rows)


def select_item_models(wald: pd.DataFrame, alpha: float = 0.05,
                       order=("DINA", "DINO", "ACDM", "LLM", "RRUM")) -> dict:
    """Pick, for each item, the reduced model with the largest p-value among those not
    rejected at ``alpha``; keep G-DINA when all are rejected (Ma et al. 2016's rule).
    With one attribute every model is equivalent, so items absent from the table stay G-DINA."""
    choice = {}
    for _, r in wald.iterrows():
        ps = {t: r[f"p_{t}"] for t in order if f"p_{t}" in r}
        ok = {t: p for t, p in ps.items() if p > alpha}
        choice[r["item"]] = max(ok, key=ok.get) if ok else "GDINA"
    return choice


# --------------------------------------------------- classification quality
def classification_reliability(model, X=None) -> dict:
    """Posterior-based accuracy and consistency (Johnson & Sinharay 2018; Wang et al. 2015).

    attribute accuracy_k    = mean_i max(p_ik, 1 - p_ik)
    attribute consistency_k = mean_i [p_ik^2 + (1 - p_ik)^2]
    pattern accuracy        = mean_i max_l P(alpha_l | x_i)
    pattern consistency     = mean_i sum_l P(alpha_l | x_i)^2
    """
    K = model.q.K
    acc = np.zeros(K)
    con = np.zeros(K)
    pacc = pcon = 0.0
    wsum = 0.0
    w = model._w if X is None else None
    for sl, post in model.iter_posteriors(X):
        ww = w[sl] if w is not None else np.ones(post.shape[0])
        marg = post @ model.profiles
        acc += ww @ np.maximum(marg, 1 - marg)
        con += ww @ (marg ** 2 + (1 - marg) ** 2)
        pacc += ww @ post.max(1)
        pcon += ww @ (post ** 2).sum(1)
        wsum += ww.sum()
    attr = pd.DataFrame({"attribute": model.q.attributes, "accuracy": acc / wsum,
                         "consistency": con / wsum})
    return {"attribute": attr, "pattern_accuracy": pacc / wsum, "pattern_consistency": pcon / wsum}
