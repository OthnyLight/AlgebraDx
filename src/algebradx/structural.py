"""Structural (attribute-profile) models.

The structural model gives the population probability pi_l of each permissible attribute
profile alpha_l.

* ``saturated``  — one free probability per permissible profile (L - 1 parameters).
* ``loglinear1`` — log pi_l = gamma_0 + sum_k gamma_k alpha_lk  (attributes independent).
* ``loglinear2`` — adds all pairwise terms gamma_kk' alpha_lk alpha_lk' (Xu & von Davier
  2008; Henson & Templin 2005). With K = 12 this is 78 parameters instead of 4095.

A prerequisite hierarchy restricts which profiles are permissible; it combines with any of
the three forms.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
from scipy.special import logsumexp


class StructuralModel:
    def __init__(self, profiles: np.ndarray, kind: str = "saturated", ridge: float = 1e-6):
        kind = kind.lower()
        if kind not in ("saturated", "loglinear1", "loglinear2"):
            raise ValueError("structural model must be 'saturated', 'loglinear1' or 'loglinear2'")
        self.kind = kind
        self.profiles = profiles
        self.L, self.K = profiles.shape
        self.ridge = ridge
        if kind == "saturated":
            self.Z = None
        else:
            cols = [profiles[:, k].astype(float) for k in range(self.K)]
            if kind == "loglinear2":
                cols += [(profiles[:, a] * profiles[:, b]).astype(float)
                         for a, b in combinations(range(self.K), 2)]
            Z = np.column_stack(cols)
            # drop columns that are constant or duplicate earlier ones (happens under a hierarchy)
            keep, seen = [], set()
            for c in range(Z.shape[1]):
                key = Z[:, c].tobytes()
                if Z[:, c].std() == 0 or key in seen:
                    continue
                seen.add(key)
                keep.append(c)
            self.Z = Z[:, keep]
            self.gamma = np.zeros(self.Z.shape[1])
        self.log_pi = np.full(self.L, -np.log(self.L))

    @property
    def pi(self) -> np.ndarray:
        return np.exp(self.log_pi)

    @property
    def n_params(self) -> int:
        return self.L - 1 if self.kind == "saturated" else self.Z.shape[1]

    def set_pi(self, pi):
        pi = np.maximum(np.asarray(pi, dtype=float), 1e-300)
        pi = pi / pi.sum()
        if self.kind == "saturated":
            self.log_pi = np.log(pi)
        else:
            self.m_step(pi * 1000.0)

    def m_step(self, counts: np.ndarray, newton_steps: int = 25) -> None:
        """Update from expected profile counts."""
        C = counts.sum()
        if self.kind == "saturated":
            pi = np.maximum(counts / C, 1e-300)
            self.log_pi = np.log(pi / pi.sum())
            return
        Z, g = self.Z, self.gamma
        for _ in range(newton_steps):
            eta = Z @ g
            lp = eta - logsumexp(eta)
            p = np.exp(lp)
            grad = Z.T @ (counts - C * p) - self.ridge * C * g
            Zc = Z - p @ Z
            H = C * (Zc.T * p) @ Zc + self.ridge * C * np.eye(len(g))
            step = np.linalg.solve(H, grad)
            # backtracking on the concave objective
            obj = counts @ lp - 0.5 * self.ridge * C * g @ g
            t = 1.0
            while t > 1e-6:
                gn = g + t * step
                en = Z @ gn
                lpn = en - logsumexp(en)
                if counts @ lpn - 0.5 * self.ridge * C * gn @ gn >= obj - 1e-12:
                    break
                t /= 2
            g = gn
            if np.max(np.abs(t * step)) < 1e-8:
                break
        self.gamma = g
        eta = Z @ g
        self.log_pi = eta - logsumexp(eta)

    def attribute_prevalence(self) -> np.ndarray:
        return self.pi @ self.profiles
