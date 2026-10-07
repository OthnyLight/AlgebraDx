"""Simulate responses from a diagnostic classification model, optionally with a
TIMSS-like rotated booklet design, sampling weights and jackknife zones.

Simulated data let the package be tested and demonstrated without any restricted file,
and they are what the parameter-recovery study in the paper uses.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .items import ItemModel
from .qmatrix import QMatrix


@dataclass
class SimulatedData:
    responses: pd.DataFrame
    alpha: np.ndarray
    qmatrix: QMatrix
    item_probs: list
    weights: np.ndarray
    jk_zone: np.ndarray
    jk_rep: np.ndarray
    booklet: np.ndarray
    true_pi: np.ndarray | None = None


def random_qmatrix(J: int, K: int, max_attrs: int = 3, seed: int | None = None,
                   prefix: str = "I", attr_prefix: str = "A") -> QMatrix:
    """A Q-matrix with two identity blocks followed by random items needing 1..max_attrs
    attributes — satisfies the Xu & Shang (2018) sufficient conditions."""
    rng = np.random.default_rng(seed)
    if J < 2 * K:
        raise ValueError("need at least 2K items")
    rows = [np.eye(K, dtype=int), np.eye(K, dtype=int)]
    for _ in range(J - 2 * K):
        k = rng.integers(1, min(max_attrs, K) + 1)
        r = np.zeros(K, dtype=int)
        r[rng.choice(K, size=k, replace=False)] = 1
        rows.append(r[None])
    q = np.vstack(rows)
    return QMatrix(q, [f"{prefix}{j + 1:03d}" for j in range(J)],
                   [f"{attr_prefix}{k + 1:02d}" for k in range(K)])


def correlated_profiles(n: int, K: int, rho: float = 0.5, prevalence=None, seed=None):
    """Draw attribute profiles by thresholding a multivariate normal (Chiu et al. 2009)."""
    rng = np.random.default_rng(seed)
    cov = np.full((K, K), rho) + (1 - rho) * np.eye(K)
    z = rng.multivariate_normal(np.zeros(K), cov, size=n)
    if prevalence is None:
        prevalence = np.linspace(0.75, 0.3, K)
    from scipy.stats import norm
    cut = norm.ppf(1 - np.asarray(prevalence))
    return (z > cut).astype(np.int8)


def generate_item_probs(q: QMatrix, model: str = "GDINA", guess=(0.1, 0.3), slip=(0.1, 0.3),
                        seed=None) -> list[np.ndarray]:
    """Monotone success probabilities per latent group.

    Group 0 (no required attribute) gets a guessing level, the all-attribute group gets
    1 - slip, and partial groups rise with the number of mastered attributes (with random
    interaction for GDINA)."""
    rng = np.random.default_rng(seed)
    out = []
    for j in range(q.J):
        Kj = int(q.q[j].sum())
        G = 2 ** Kj
        g = rng.uniform(*guess)
        s = rng.uniform(*slip)
        counts = np.array([bin(x).count("1") for x in range(G)])
        if model.upper() == "DINA":
            P = np.where(counts == Kj, 1 - s, g)
        elif model.upper() == "DINO":
            P = np.where(counts >= 1, 1 - s, g)
        else:
            frac = counts / Kj
            if Kj > 1:
                frac = np.clip(frac + rng.uniform(-0.1, 0.1, G) * (counts > 0) * (counts < Kj), 0, 1)
            P = g + (1 - s - g) * frac
        out.append(P.astype(float))
    return out


def simulate_dataset(n_students: int = 2000, J: int = 40, K: int = 5, model: str = "GDINA",
                     q: QMatrix | None = None, n_booklets: int = 1, rho: float = 0.5,
                     n_zones: int = 0, weight_cv: float = 0.0, seed: int | None = None,
                     item_probs=None, alpha=None) -> SimulatedData:
    """Simulate a dataset.

    n_booklets > 1 assigns items to booklets in a rotated design: items are split into
    ``n_booklets`` blocks and booklet b contains blocks b and b+1 (mod n_booklets), as in
    TIMSS's paired-block designs, so every pair of adjacent blocks is linked.
    n_zones > 0 adds jackknife zones (two schools' worth of students per zone, JKREP 0/1).
    weight_cv > 0 draws log-normal sampling weights with that coefficient of variation.
    """
    rng = np.random.default_rng(seed)
    if q is None:
        q = random_qmatrix(J, K, seed=rng.integers(1 << 31))
    if item_probs is None:
        item_probs = generate_item_probs(q, model, seed=rng.integers(1 << 31))
    if alpha is None:
        alpha = correlated_profiles(n_students, q.K, rho=rho, seed=rng.integers(1 << 31))
    N = len(alpha)
    X = np.empty((N, q.J))
    for j in range(q.J):
        attrs = np.where(q.q[j])[0]
        g = ItemModel(attrs, "GDINA").group_index(alpha)
        X[:, j] = rng.random(N) < item_probs[j][g]
    booklet = np.zeros(N, dtype=int)
    if n_booklets > 1:
        blocks = np.array_split(rng.permutation(q.J), n_booklets)
        booklet = rng.integers(0, n_booklets, N)
        for b in range(n_booklets):
            seen = np.concatenate([blocks[b], blocks[(b + 1) % n_booklets]])
            mask = np.ones(q.J, dtype=bool)
            mask[seen] = False
            X[np.ix_(booklet == b, mask)] = np.nan
    if weight_cv > 0:
        s2 = np.log(1 + weight_cv ** 2)
        w = rng.lognormal(-s2 / 2, np.sqrt(s2), N) * 100
    else:
        w = np.ones(N)
    if n_zones > 0:
        zone = rng.integers(1, n_zones + 1, N)
        rep = rng.integers(0, 2, N)
    else:
        zone = np.zeros(N, dtype=int)
        rep = np.zeros(N, dtype=int)
    df = pd.DataFrame(X, columns=q.items)
    # true profile distribution implied by alpha (empirical)
    return SimulatedData(df, alpha, q, item_probs, w, zone, rep, booklet)
