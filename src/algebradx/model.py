"""Marginal maximum-likelihood estimation of diagnostic classification models by EM.

The likelihood handles three things large-scale assessments need:

* **missing by design** — TIMSS and PISA rotate items across booklets, so each student
  sees a fraction of the pool. A missing response contributes nothing to the likelihood
  (ignorable under random booklet assignment; Mislevy & Wu 1996).
* **sampling weights** — each student's likelihood contribution is multiplied by a
  survey weight (pseudo-maximum likelihood; Skinner 1989). Weights are rescaled to sum
  to the number of students so the log-likelihood keeps its usual scale.
* **large K** — the E-step runs over students in chunks so memory stays bounded at
  ``chunk_size x L`` doubles, where L = number of permissible profiles.
"""
from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.special import logsumexp

from .items import EPS, ItemModel, link
from .qmatrix import QMatrix, all_profiles, permissible_profiles
from .structural import StructuralModel


@dataclass
class FitHistory:
    loglik: list = field(default_factory=list)
    max_change: list = field(default_factory=list)


def _prepare_responses(X, q: QMatrix):
    if isinstance(X, pd.DataFrame):
        missing = [i for i in q.items if i not in X.columns]
        if missing:
            raise ValueError(f"{len(missing)} Q-matrix items not in the response data, e.g. {missing[:5]}")
        X = X[q.items].to_numpy(dtype=float)
    X = np.asarray(X, dtype=float)
    if X.shape[1] != q.J:
        raise ValueError(f"responses have {X.shape[1]} columns, Q-matrix has {q.J} items")
    obs = ~np.isnan(X)
    if not np.isin(X[obs], [0, 1]).all():
        raise ValueError("responses must be 0, 1 or missing (NaN); score items before fitting")
    return X


class DiagnosticModel:
    """A diagnostic classification model in the G-DINA family.

    Parameters
    ----------
    qmatrix : QMatrix
    model : str or mapping item -> str
        Item response function for every item (``"GDINA"``, ``"LCDM"``, ``"DINA"``, ``"DINO"``,
        ``"ACDM"``, ``"LLM"``, ``"RRUM"``, ``"GDINA_LOG"``), or a per-item mapping (items not
        in the mapping use ``"GDINA"``).
    structural : {"saturated", "loglinear1", "loglinear2"}
    hierarchy : sequence of (prerequisite_code, attribute_code) pairs, optional
        Restricts the permissible profiles.

    Examples
    --------
    >>> from algebradx import DiagnosticModel, simulate
    >>> sim = simulate.simulate_dataset(n_students=500, seed=1)
    >>> m = DiagnosticModel(sim.qmatrix, model="DINA").fit(sim.responses)
    """

    def __init__(self, qmatrix: QMatrix, model: str | Mapping[str, str] = "GDINA",
                 structural: str = "saturated", hierarchy: Sequence[tuple[str, str]] | None = None):
        self.q = qmatrix
        if isinstance(model, str):
            models = {i: model for i in qmatrix.items}
        else:
            models = {i: model.get(i, "GDINA") for i in qmatrix.items}
        self.item_models = [ItemModel(np.where(qmatrix.q[j])[0], models[it])
                            for j, it in enumerate(qmatrix.items)]
        self.hierarchy = list(hierarchy or [])
        idx_edges = [(qmatrix.attributes.index(a), qmatrix.attributes.index(b))
                     for a, b in self.hierarchy]
        self.profiles = (permissible_profiles(qmatrix.K, idx_edges) if idx_edges
                         else all_profiles(qmatrix.K))
        self.structural = StructuralModel(self.profiles, structural)
        self.group_idx = [it.group_index(self.profiles) for it in self.item_models]
        self.fitted = False
        self.history = FitHistory()

    # ---------------------------------------------------------------- shapes
    @property
    def L(self) -> int:
        return len(self.profiles)

    @property
    def n_item_params(self) -> int:
        return int(sum(it.n_params for it in self.item_models))

    @property
    def n_params(self) -> int:
        return self.n_item_params + self.structural.n_params

    def _prob_matrix(self) -> np.ndarray:
        """J x L matrix of success probabilities for every item and profile."""
        return np.vstack([it.P[g] for it, g in zip(self.item_models, self.group_idx)])

    # ---------------------------------------------------------------- E-step
    def _chunks(self, X, w, chunk_size):
        """Pre-split responses into (x1, x0, observed, weight) chunks once per fit."""
        out = []
        for s in range(0, X.shape[0], chunk_size):
            x = X[s:s + chunk_size]
            obs = ~np.isnan(x)
            x1 = np.where(obs, np.nan_to_num(x), 0.0)
            out.append((x1, obs.astype(float) - x1, obs.astype(float), w[s:s + chunk_size]))
        return out

    @staticmethod
    def _posterior_inplace(lj):
        """Turn log joint (n x L) into posteriors in place; return log marginal per row."""
        mx = lj.max(1)
        lj -= mx[:, None]
        np.exp(lj, out=lj)
        tot = lj.sum(1)
        lj /= tot[:, None]
        return mx + np.log(tot)

    def _estep(self, chunks):
        PL = np.clip(self._prob_matrix(), EPS, 1 - EPS)
        A, B = np.log(PL), np.log1p(-PL)
        log_pi = self.structural.log_pi
        J, L = PL.shape
        R = np.zeros((J, L))
        Nn = np.zeros((J, L))
        counts = np.zeros(L)
        ll = 0.0
        for x1, x0, obs, ww in chunks:
            lj = x1 @ A
            lj += x0 @ B
            lj += log_pi
            lse = self._posterior_inplace(lj)
            ll += float(ww @ lse)
            lj *= ww[:, None]
            R += x1.T @ lj
            Nn += obs.T @ lj
            counts += lj.sum(0)
        return ll, R, Nn, counts

    def _mstep(self, R, Nn, counts):
        for j, it in enumerate(self.item_models):
            g = self.group_idx[j]
            r = np.bincount(g, weights=R[j], minlength=it.n_groups)
            n = np.bincount(g, weights=Nn[j], minlength=it.n_groups)
            it.m_step(r, n)
        self.structural.m_step(counts)

    def _em_step(self, chunks):
        ll, R, Nn, counts = self._estep(chunks)
        self._mstep(R, Nn, counts)
        return ll

    # parameter vector used by the SQUAREM accelerator (Varadhan & Roland 2008)
    def _get_theta(self):
        parts = [link(it.P, "logit") for it in self.item_models]
        st = self.structural
        parts.append(st.log_pi if st.kind == "saturated" else st.gamma)
        return np.concatenate(parts)

    def _set_theta(self, theta):
        pos = 0
        for it in self.item_models:
            seg = theta[pos:pos + it.n_groups]
            pos += it.n_groups
            it.set_probabilities(1 / (1 + np.exp(-np.clip(seg, -30, 30))))
        rest = theta[pos:]
        st = self.structural
        if st.kind == "saturated":
            st.log_pi = rest - logsumexp(rest)
        else:
            st.gamma = rest.copy()
            eta = st.Z @ st.gamma
            st.log_pi = eta - logsumexp(eta)

    def _prob_state(self):
        return np.concatenate([it.P for it in self.item_models] + [self.structural.pi])

    # ------------------------------------------------------------------ fit
    def _init_items(self, rng=None):
        for it in self.item_models:
            groups = np.arange(it.n_groups)
            n_mastered = np.array([bin(g).count("1") for g in groups]) / max(it.Kj, 1)
            lo, hi = 0.2, 0.8
            if rng is not None:
                lo, hi = rng.uniform(0.1, 0.35), rng.uniform(0.65, 0.9)
            it.set_probabilities(lo + (hi - lo) * n_mastered)

    def fit(self, X, weights=None, max_iter: int = 2000, tol: float = 1e-5,
            chunk_size: int = 2000, n_starts: int = 1, random_state: int | None = 0,
            verbose: bool = False, warm_start: bool = False, normalize_weights: bool = True,
            accelerate: bool = True):
        """Fit the model by EM.

        Parameters
        ----------
        X : DataFrame (columns = Q-matrix item ids) or array, values 0/1/NaN
        weights : array of sampling weights, optional
        max_iter : maximum number of EM steps (an accelerated cycle counts as three)
        tol : convergence when one plain EM step changes no item probability and no profile
              probability by more than ``tol``
        n_starts : random starts; the solution with the largest log-likelihood is kept
        warm_start : start from the current parameters (used for replicate-weight refits)
        accelerate : use SQUAREM extrapolation (Varadhan & Roland 2008), with a fallback
              to the plain EM step whenever the extrapolated point lowers the likelihood
        """
        X = _prepare_responses(X, self.q)
        N = X.shape[0]
        w = np.ones(N) if weights is None else np.asarray(weights, dtype=float)
        if w.shape != (N,) or (w < 0).any() or not np.isfinite(w).all():
            raise ValueError("weights must be a non-negative finite vector, one per student")
        if normalize_weights:
            w = w * (N / w.sum())
        self._X, self._w, self._chunk = X, w, chunk_size
        chunks = self._chunks(X, w, chunk_size)

        rng = np.random.default_rng(random_state)
        best = None
        for start in range(max(n_starts, 1)):
            if not warm_start or start > 0:
                self._init_items(rng if start > 0 else None)
                self.structural.set_pi(np.full(self.L, 1.0 / self.L))
            hist = FitHistory()
            t0 = time.time()
            converged = False
            steps = 0
            while steps < max_iter:
                th0 = self._get_theta()
                ll0 = self._em_step(chunks)
                th1, p1 = self._get_theta(), self._prob_state()
                ll1 = self._em_step(chunks)
                th2, p2 = self._get_theta(), self._prob_state()
                steps += 2
                change = float(np.max(np.abs(p2 - p1)))
                hist.loglik += [ll0, ll1]
                hist.max_change.append(change)
                if verbose:
                    print(f"  step {steps:4d}  loglik {ll1:,.4f}  max change {change:.2e}")
                if change < tol:
                    converged = True
                    break
                if not accelerate:
                    continue
                r = th1 - th0
                v = th2 - th1 - r
                nv = np.linalg.norm(v)
                if nv == 0 or not np.isfinite(nv):
                    continue
                alpha = min(-1.0, -np.linalg.norm(r) / nv)
                alpha = max(alpha, -64.0)
                thp = th0 - 2 * alpha * r + alpha ** 2 * v
                self._set_theta(thp)
                llp = self._em_step(chunks)    # log-likelihood at the extrapolated point
                steps += 1
                if not np.isfinite(llp) or llp < ll1:
                    self._set_theta(th2)       # reject: back to the plain EM path
                else:
                    hist.loglik.append(llp)
            ll, R, Nn, counts = self._estep(chunks)
            hist.loglik.append(ll)
            state = dict(ll=ll, R=R, Nn=Nn, counts=counts, hist=hist, n_iter=steps,
                         converged=converged, seconds=time.time() - t0,
                         items=[(it.P.copy(), it.delta.copy()) for it in self.item_models],
                         log_pi=self.structural.log_pi.copy(),
                         gamma=(None if getattr(self.structural, "gamma", None) is None else self.structural.gamma.copy()))
            if best is None or ll > best["ll"]:
                best = state
        # restore best
        for it, (P, d) in zip(self.item_models, best["items"]):
            it.P, it.delta = P, d
        self.structural.log_pi = best["log_pi"]
        if best["gamma"] is not None:
            self.structural.gamma = best["gamma"]
        self.loglik = best["ll"]
        self._R, self._Nn, self._counts = best["R"], best["Nn"], best["counts"]
        self.history = best["hist"]
        self.n_iter, self.converged, self.seconds = best["n_iter"], best["converged"], best["seconds"]
        self.n_students = N
        self.fitted = True
        if not self.converged:
            warnings.warn(f"EM did not converge in {max_iter} steps "
                          f"(last max change {best['hist'].max_change[-1]:.2e})")
        self._cov = None
        return self

    # ---------------------------------------------------------- summaries
    @property
    def deviance(self) -> float:
        return -2 * self.loglik

    @property
    def aic(self) -> float:
        return self.deviance + 2 * self.n_params

    @property
    def bic(self) -> float:
        return self.deviance + np.log(self.n_students) * self.n_params

    def attribute_prevalence(self) -> pd.Series:
        return pd.Series(self.structural.attribute_prevalence(), index=self.q.attributes,
                         name="prevalence")

    def profile_distribution(self, top: int | None = None) -> pd.DataFrame:
        df = pd.DataFrame({"profile": ["".join(map(str, p)) for p in self.profiles],
                           "probability": self.structural.pi})
        df = df.sort_values("probability", ascending=False)
        return df.head(top) if top else df

    def item_parameters(self) -> pd.DataFrame:
        """One row per item x latent group: the success probability and its SE."""
        rows = []
        cov = self._cov if self._cov is not None else [None] * self.q.J
        for j, it in enumerate(self.item_models):
            names = [self.q.attributes[a] for a in it.attrs]
            se = np.sqrt(np.clip(np.diag(cov[j]), 0, None)) if cov[j] is not None else \
                np.full(it.n_groups, np.nan)
            for g in range(it.n_groups):
                bits = [(g >> (it.Kj - 1 - m)) & 1 for m in range(it.Kj)]
                rows.append({"item": self.q.items[j], "model": it.model,
                             "group": "".join(map(str, bits)),
                             "attributes": "+".join(names),
                             "P": it.P[g], "se": se[g]})
        return pd.DataFrame(rows)

    def guess_slip(self) -> pd.DataFrame:
        """P(correct | no required attribute) and 1 - P(correct | all required attributes)."""
        return pd.DataFrame({"item": self.q.items,
                             "model": [it.model for it in self.item_models],
                             "guess": [it.P[0] for it in self.item_models],
                             "slip": [1 - it.P[-1] for it in self.item_models],
                             "gdi": [self._item_gdi(j) for j in range(self.q.J)]})

    def _item_gdi(self, j):
        it = self.item_models[j]
        w = np.bincount(self.group_idx[j], weights=self.structural.pi, minlength=it.n_groups)
        pbar = w @ it.P
        return float(w @ (it.P - pbar) ** 2)

    def summary(self) -> dict:
        return {"n_students": self.n_students, "n_items": self.q.J, "K": self.q.K,
                "n_profiles": self.L, "structural": self.structural.kind,
                "item_models": pd.Series([it.model for it in self.item_models]).value_counts().to_dict(),
                "loglik": self.loglik, "n_params": self.n_params, "aic": self.aic, "bic": self.bic,
                "converged": self.converged, "iterations": self.n_iter, "seconds": round(self.seconds, 2)}

    # --------------------------------------------------------- posteriors
    def iter_posteriors(self, X=None, chunk_size: int | None = None):
        """Yield (row slice, posterior matrix chunk) for the fitted (or new) responses."""
        X = self._X if X is None else _prepare_responses(X, self.q)
        cs = chunk_size or getattr(self, "_chunk", 2000)
        PL = np.clip(self._prob_matrix(), EPS, 1 - EPS)
        A, B = np.log(PL), np.log1p(-PL)
        for s in range(0, X.shape[0], cs):
            x = X[s:s + cs]
            obs = ~np.isnan(x)
            x1 = np.where(obs, np.nan_to_num(x), 0.0)
            x0 = obs.astype(float) - x1
            lj = x1 @ A + x0 @ B + self.structural.log_pi
            self._posterior_inplace(lj)
            yield slice(s, s + len(x)), lj

    def score(self, X=None, ids=None, threshold: float = 0.5) -> pd.DataFrame:
        """Skill report for every student.

        Returns one row per student: posterior probability of mastering each attribute
        (``p_<code>``), the classification at ``threshold`` (``m_<code>``), the most likely
        (MAP) profile and its posterior probability.
        """
        out = []
        for sl, post in self.iter_posteriors(X):
            marg = post @ self.profiles
            mp = post.argmax(1)
            df = pd.DataFrame(marg, columns=[f"p_{a}" for a in self.q.attributes])
            for k, a in enumerate(self.q.attributes):
                df[f"m_{a}"] = (marg[:, k] >= threshold).astype(int)
            df["map_profile"] = ["".join(map(str, self.profiles[i])) for i in mp]
            df["map_probability"] = post[np.arange(len(mp)), mp]
            out.append(df)
        res = pd.concat(out, ignore_index=True)
        if ids is not None:
            res.insert(0, "id", list(ids))
        return res

    # ------------------------------------------------ standard errors
    def compute_standard_errors(self):
        """Item-wise empirical cross-product (XPD) standard errors for the success
        probabilities, with a sandwich correction for sampling weights.

        Item parameters are treated one item at a time, ignoring their covariance with the
        structural parameters (the ``itemwise`` approach in de la Torre 2011 and the R
        package GDINA). For survey-design standard errors use
        :func:`algebradx.survey.replicate_standard_errors`.
        """
        X, w = self._X, self._w
        J = self.q.J
        H = [np.zeros((it.n_params, it.n_params)) for it in self.item_models]
        G = [np.zeros((it.n_params, it.n_params)) for it in self.item_models]
        onehots = [np.eye(it.n_groups)[g] for it, g in zip(self.item_models, self.group_idx)]
        for sl, post in self.iter_posteriors():
            x = X[sl]
            ww = w[sl]
            for j, it in enumerate(self.item_models):
                obs = ~np.isnan(x[:, j])
                if not obs.any():
                    continue
                pg = post[obs] @ onehots[j]                     # n x groups
                xj = x[obs, j][:, None]
                sP = pg * (xj - it.P) / (it.P * (1 - it.P))     # score wrt P_g
                sd = sP @ it.jacobian()                          # score wrt delta
                wj = ww[obs][:, None]
                H[j] += (sd * wj).T @ sd
                G[j] += (sd * wj ** 2).T @ sd
        covs = []
        for j, it in enumerate(self.item_models):
            Hi = np.linalg.pinv(H[j])
            cov_delta = Hi @ G[j] @ Hi
            Jac = it.jacobian()
            covs.append(Jac @ cov_delta @ Jac.T)
        self._cov = covs
        self._cov_delta_H = H
        return self

    # ------------------------------------------------------- persistence
    def to_dict(self) -> dict:
        """Everything needed to score new students with this calibration."""
        if not self.fitted:
            raise ValueError("fit the model first")
        return {
            "format": "algebradx-calibration", "version": 1,
            "items": self.q.items, "attributes": self.q.attributes,
            "attribute_names": self.q.attribute_names,
            "q": self.q.q.tolist(), "hierarchy": self.hierarchy,
            "structural": self.structural.kind,
            "log_pi": self.structural.log_pi.tolist(),
            "gamma": (self.structural.gamma.tolist()
                      if getattr(self.structural, "gamma", None) is not None else None),
            "item_models": [{"item": i, "model": it.model, "P": it.P.tolist(),
                             "delta": it.delta.tolist()}
                            for i, it in zip(self.q.items, self.item_models)],
            "summary": self.summary(),
        }

    def save(self, path) -> None:
        import json
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=1)

    @classmethod
    def load(cls, path) -> "DiagnosticModel":
        """Load a saved calibration; the result can :meth:`score` new response data."""
        import json
        with open(path) as f:
            d = json.load(f)
        if d.get("format") != "algebradx-calibration":
            raise ValueError("not an algebradx calibration file")
        q = QMatrix(np.array(d["q"]), d["items"], d["attributes"], d.get("attribute_names", {}))
        m = cls(q, {im["item"]: im["model"] for im in d["item_models"]},
                structural=d["structural"], hierarchy=[tuple(e) for e in d["hierarchy"]])
        for it, im in zip(m.item_models, d["item_models"]):
            it.P = np.array(im["P"])
            it.delta = np.array(im["delta"])
        m.structural.log_pi = np.array(d["log_pi"])
        if d.get("gamma") is not None:
            m.structural.gamma = np.array(d["gamma"])
        m.fitted = True
        m._cov = None
        m._chunk = 2000
        m._X = None
        return m
