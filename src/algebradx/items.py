"""Item response functions for diagnostic classification models.

Every model in the G-DINA family (de la Torre 2011) is written as

    f(P_j(alpha*)) = D_j delta_j

where alpha* is the reduced attribute vector of the K_j* attributes item j requires,
P_j(alpha*) is the probability of a correct response for latent group alpha*, D_j is a
design matrix over the 2^K_j* latent groups and f is a link function (identity, logit
or log). The models below are special cases:

========  ==========  ========  ==========================================================
model     design      link      reference
========  ==========  ========  ==========================================================
GDINA     saturated   identity  de la Torre (2011)
LCDM      saturated   logit     Henson, Templin & Willse (2009); log-linear CDM
GDINA_log saturated   log       de la Torre (2011)
DINA      all-or-none identity  Junker & Sijtsma (2001)
DINO      any         identity  Templin & Henson (2006)
ACDM      main        identity  de la Torre (2011)
LLM       main        logit     Maris (1999)
RRUM      main        log       Hartz (2002)
========  ==========  ========  ==========================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
from scipy.optimize import minimize

EPS = 1e-4

MODELS = {
    "GDINA": ("saturated", "identity"),
    "LCDM": ("saturated", "logit"),
    "GDINA_LOG": ("saturated", "log"),
    "DINA": ("dina", "identity"),
    "DINO": ("dino", "identity"),
    "ACDM": ("main", "identity"),
    "LLM": ("main", "logit"),
    "RRUM": ("main", "log"),
}


def group_patterns(Kj: int) -> np.ndarray:
    """The 2^Kj reduced latent groups, attribute 1 as most significant bit."""
    idx = np.arange(2 ** Kj)
    return ((idx[:, None] >> np.arange(Kj - 1, -1, -1)) & 1).astype(float)


def saturated_terms(Kj: int) -> list[tuple[int, ...]]:
    """Intercept, main effects, then interactions in increasing order."""
    terms: list[tuple[int, ...]] = [()]
    for order in range(1, Kj + 1):
        terms += list(combinations(range(Kj), order))
    return terms


def design_matrix(Kj: int, kind: str) -> tuple[np.ndarray, list[str]]:
    A = group_patterns(Kj)
    one = np.ones((len(A), 1))
    if kind == "saturated":
        terms = saturated_terms(Kj)
        D = np.column_stack([A[:, list(t)].prod(1) if t else one[:, 0] for t in terms])
        labels = ["d0" if not t else "d" + "".join(str(i + 1) for i in t) for t in terms]
        return D, labels
    if kind == "main":
        return np.hstack([one, A]), ["d0"] + [f"d{i + 1}" for i in range(Kj)]
    if kind == "dina":
        return np.hstack([one, A.prod(1, keepdims=True)]), ["d0", "d_all"]
    if kind == "dino":
        return np.hstack([one, 1 - (1 - A).prod(1, keepdims=True)]), ["d0", "d_any"]
    raise ValueError(f"unknown design {kind!r}")


def link(p, kind):
    p = np.clip(p, EPS, 1 - EPS)
    if kind == "identity":
        return p
    if kind == "logit":
        return np.log(p / (1 - p))
    if kind == "log":
        return np.log(p)
    raise ValueError(kind)


def inv_link(eta, kind):
    if kind == "identity":
        return eta
    if kind == "logit":
        return 1.0 / (1.0 + np.exp(-eta))
    if kind == "log":
        return np.exp(eta)
    raise ValueError(kind)


def dp_deta(p, kind):
    if kind == "identity":
        return np.ones_like(p)
    if kind == "logit":
        return p * (1 - p)
    if kind == "log":
        return p
    raise ValueError(kind)


@dataclass
class ItemModel:
    """One item's response function.

    Attributes
    ----------
    attrs : indices of the attributes the item requires (from the Q-matrix row)
    model : one of :data:`MODELS`
    P     : success probability for each of the 2^K_j* latent groups
    delta : parameters on the link scale (length = number of design columns)
    """

    attrs: np.ndarray
    model: str = "GDINA"

    def __post_init__(self):
        self.model = self.model.upper()
        if self.model not in MODELS:
            raise ValueError(f"unknown item model {self.model!r}; choose from {list(MODELS)}")
        self.attrs = np.asarray(self.attrs, dtype=int)
        self.Kj = len(self.attrs)
        # with one required attribute every model is saturated (two latent groups)
        self.design_kind, self.link_kind = MODELS[self.model]
        self.D, self.labels = design_matrix(self.Kj, self.design_kind)
        self.n_groups = 2 ** self.Kj
        self.P = np.linspace(0.2, 0.8, self.n_groups) if self.n_groups > 1 else np.array([0.5])
        self.delta = self._project(self.P)

    @property
    def n_params(self) -> int:
        return self.D.shape[1]

    # ------------------------------------------------------------ helpers
    def _project(self, P):
        """Least-squares projection of group probabilities onto the design (link scale)."""
        eta = link(P, self.link_kind)
        delta, *_ = np.linalg.lstsq(self.D, eta, rcond=None)
        return delta

    def _from_delta(self, delta):
        return np.clip(inv_link(self.D @ delta, self.link_kind), EPS, 1 - EPS)

    def set_probabilities(self, P):
        P = np.clip(np.asarray(P, dtype=float), EPS, 1 - EPS)
        self.delta = self._project(P)
        self.P = self._from_delta(self.delta)

    def group_index(self, profiles: np.ndarray) -> np.ndarray:
        """Map full attribute profiles (L x K) to this item's latent group index."""
        sub = profiles[:, self.attrs].astype(np.int64)
        weights = 1 << np.arange(self.Kj - 1, -1, -1)
        return sub @ weights

    # ------------------------------------------------------------ M-step
    def m_step(self, r: np.ndarray, n: np.ndarray) -> None:
        """Maximise sum_g r_g log P_g + (n_g - r_g) log(1 - P_g) over this item's model.

        r, n : expected numbers of correct responses and of responses per latent group.
        """
        n = np.maximum(n, 1e-10)
        if self.n_params == self.n_groups:  # saturated (any link), or any model with K_j* = 1
            self.P = np.clip(r / n, EPS, 1 - EPS)
            self.delta = self._project(self.P)
            return
        if self.design_kind in ("dina", "dino") and self.link_kind == "identity":
            top = self.D[:, 1] == 1
            p0 = np.clip(r[~top].sum() / n[~top].sum(), EPS, 1 - EPS)
            p1 = np.clip(r[top].sum() / n[top].sum(), EPS, 1 - EPS)
            self.P = np.where(top, p1, p0)
            self.delta = np.array([p0, p1 - p0])
            return
        self._numeric_m_step(r, n)

    def _numeric_m_step(self, r, n):
        D, lk = self.D, self.link_kind

        def nll(delta):
            p = np.clip(inv_link(D @ delta, lk), EPS, 1 - EPS)
            val = -(r * np.log(p) + (n - r) * np.log(1 - p)).sum()
            gp = -(r / p - (n - r) / (1 - p))
            return val, D.T @ (gp * dp_deta(p, lk))

        start = self.delta
        if lk == "logit":
            res = minimize(nll, start, jac=True, method="L-BFGS-B")
        else:
            hi = 1 - EPS if lk == "identity" else np.log(1 - EPS)
            lo = EPS if lk == "identity" else np.log(EPS)
            cons = [{"type": "ineq", "fun": lambda d: D @ d - lo, "jac": lambda d: D},
                    {"type": "ineq", "fun": lambda d: hi - D @ d, "jac": lambda d: -D}]
            # make the start feasible
            eta = np.clip(D @ start, lo + 1e-6, hi - 1e-6)
            start, *_ = np.linalg.lstsq(D, eta, rcond=None)
            res = minimize(nll, start, jac=True, method="SLSQP", constraints=cons,
                           options={"maxiter": 200, "ftol": 1e-10})
        self.delta = res.x
        self.P = self._from_delta(self.delta)

    # ------------------------------------------------------------ inference
    def jacobian(self) -> np.ndarray:
        """dP/d delta (n_groups x n_params) at the current estimate."""
        return dp_deta(self.P, self.link_kind)[:, None] * self.D

    def describe(self) -> dict:
        return {"model": self.model, "link": self.link_kind, "design": self.design_kind,
                "labels": self.labels, "delta": self.delta.tolist(), "P": self.P.tolist()}
