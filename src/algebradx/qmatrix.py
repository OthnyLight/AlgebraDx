"""Q-matrix and attribute dictionary handling.

A Q-matrix is a J x K binary matrix: q[j, k] = 1 when item j requires attribute k.
An attribute dictionary gives each attribute a code, a short name and a definition,
plus optional prerequisite links that define an attribute hierarchy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


@dataclass
class QMatrix:
    """A validated Q-matrix.

    Parameters
    ----------
    q : array-like, shape (J, K)
        Binary item-by-attribute matrix.
    items : sequence of str
        Item identifiers (length J).
    attributes : sequence of str
        Attribute codes (length K).
    """

    q: np.ndarray
    items: list[str]
    attributes: list[str]
    attribute_names: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.q = np.asarray(self.q, dtype=int)
        self.items = [str(i) for i in self.items]
        self.attributes = [str(a) for a in self.attributes]
        if self.q.ndim != 2:
            raise ValueError("Q-matrix must be two-dimensional")
        J, K = self.q.shape
        if len(self.items) != J:
            raise ValueError(f"{J} rows in Q but {len(self.items)} item ids")
        if len(self.attributes) != K:
            raise ValueError(f"{K} columns in Q but {len(self.attributes)} attribute codes")
        if not np.isin(self.q, [0, 1]).all():
            raise ValueError("Q-matrix entries must be 0 or 1")
        empty = [self.items[j] for j in np.where(self.q.sum(1) == 0)[0]]
        if empty:
            raise ValueError(f"items with no required attribute: {empty}")
        if len(set(self.items)) != J:
            raise ValueError("duplicate item ids in Q-matrix")

    # ------------------------------------------------------------------ io
    @classmethod
    def from_csv(cls, path, item_col: str = "item", attributes: Sequence[str] | None = None,
                 dictionary: "AttributeDictionary | None" = None) -> "QMatrix":
        """Read a Q-matrix from CSV with an item column and one 0/1 column per attribute.

        Extra non-attribute columns (e.g. ``source``, ``note``) are ignored when
        ``attributes`` or ``dictionary`` is given; otherwise every column except
        ``item_col`` must be an attribute.
        """
        df = pd.read_csv(path, dtype={item_col: str}, comment="#")
        if attributes is None and dictionary is not None:
            attributes = dictionary.codes
        if attributes is None:
            attributes = [c for c in df.columns if c != item_col]
        missing = [a for a in attributes if a not in df.columns]
        if missing:
            raise ValueError(f"attribute columns missing from Q-matrix file: {missing}")
        names = dictionary.names if dictionary is not None else {}
        return cls(df[list(attributes)].fillna(0).astype(int).to_numpy(),
                   df[item_col].tolist(), list(attributes), names)

    def to_frame(self) -> pd.DataFrame:
        df = pd.DataFrame(self.q, columns=self.attributes)
        df.insert(0, "item", self.items)
        return df

    def to_csv(self, path):
        self.to_frame().to_csv(path, index=False)

    # ------------------------------------------------------------ helpers
    @property
    def J(self) -> int:
        return self.q.shape[0]

    @property
    def K(self) -> int:
        return self.q.shape[1]

    def subset(self, items: Iterable[str]) -> "QMatrix":
        idx = [self.items.index(i) for i in items]
        return QMatrix(self.q[idx], [self.items[i] for i in idx], self.attributes,
                       self.attribute_names)

    def coverage(self) -> pd.DataFrame:
        """Items measuring each attribute: total, single-attribute items, and a flag."""
        single = self.q[self.q.sum(1) == 1]
        out = pd.DataFrame({
            "attribute": self.attributes,
            "n_items": self.q.sum(0),
            "n_single_attribute_items": single.sum(0),
        })
        out["flag"] = np.where(out["n_items"] < 3, "fewer than 3 items",
                               np.where(out["n_single_attribute_items"] == 0,
                                        "no single-attribute item", ""))
        return out

    def is_complete(self) -> bool:
        """True when the Q-matrix contains an identity block (each attribute has at least
        one item that requires it alone). Completeness is required for every attribute profile
        to be distinguishable under the DINA model (Chiu, Douglas & Li 2009)."""
        single = self.q[self.q.sum(1) == 1]
        return bool((single.sum(0) >= 1).all())

    def identifiability_report(self) -> dict:
        """Check sufficient conditions for strict identifiability of restricted latent
        class models with a saturated structural model (Xu & Shang 2018):

        A. Q contains a K x K identity sub-matrix (complete);
        B. every attribute is required by at least three items;
        C. after removing one identity block, the remaining columns are pairwise distinct.
        """
        q = self.q
        K = self.K
        single_rows = [j for j in range(self.J) if q[j].sum() == 1]
        A = self.is_complete()
        B = bool((q.sum(0) >= 3).all())
        C = False
        if A:
            used = set()
            for k in range(K):
                for j in single_rows:
                    if q[j, k] == 1 and j not in used:
                        used.add(j)
                        break
            rest = np.delete(q, sorted(used), axis=0)
            cols = {tuple(rest[:, k]) for k in range(K)}
            C = len(cols) == K
        return {"complete_identity_block": A, "each_attribute_three_items": B,
                "distinct_columns_after_identity": C,
                "sufficient_conditions_met": bool(A and B and C)}


@dataclass
class AttributeDictionary:
    """Codes, names, definitions and (optional) prerequisite links for attributes."""

    table: pd.DataFrame

    REQUIRED = ("code", "name", "definition")

    def __post_init__(self):
        miss = [c for c in self.REQUIRED if c not in self.table.columns]
        if miss:
            raise ValueError(f"attribute dictionary is missing columns {miss}")
        if self.table["code"].duplicated().any():
            raise ValueError("duplicate attribute codes")
        if "prerequisites" not in self.table.columns:
            self.table["prerequisites"] = ""
        self.table["prerequisites"] = self.table["prerequisites"].fillna("").astype(str)

    @classmethod
    def from_csv(cls, path) -> "AttributeDictionary":
        return cls(pd.read_csv(path, dtype=str, comment="#").fillna(""))

    @property
    def codes(self) -> list[str]:
        return self.table["code"].tolist()

    @property
    def names(self) -> dict[str, str]:
        return dict(zip(self.table["code"], self.table["name"]))

    def hierarchy(self) -> list[tuple[str, str]]:
        """Prerequisite edges (pre, post): mastering ``post`` presumes ``pre``."""
        edges = []
        for code, pre in zip(self.table["code"], self.table["prerequisites"]):
            for p in [x.strip() for x in pre.replace(";", ",").split(",") if x.strip()]:
                if p not in self.codes:
                    raise ValueError(f"prerequisite {p!r} of {code!r} is not an attribute code")
                edges.append((p, code))
        return edges


def all_profiles(K: int) -> np.ndarray:
    """All 2^K attribute profiles as a (2^K, K) int8 array, ordered by binary value with
    attribute 1 as the most significant bit."""
    if K > 20:
        raise ValueError("K > 20 attributes is not supported (2^K profiles)")
    return np.array(list(product([0, 1], repeat=K)), dtype=np.int8)


def permissible_profiles(K: int, edges: Sequence[tuple[int, int]] = ()) -> np.ndarray:
    """Profiles consistent with prerequisite edges (pre, post) given as attribute indices:
    a profile with post = 1 must have pre = 1 (Leighton, Gierl & Hunka 2004)."""
    P = all_profiles(K)
    keep = np.ones(len(P), dtype=bool)
    for pre, post in edges:
        keep &= ~((P[:, post] == 1) & (P[:, pre] == 0))
    return P[keep]
