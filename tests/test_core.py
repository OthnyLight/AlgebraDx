"""Unit and recovery tests. Run with ``pytest`` (or ``python tests/run_tests.py``)."""
import os
import tempfile

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logsumexp

from algebradx import DiagnosticModel, QMatrix, AttributeDictionary, permissible_profiles
from algebradx import fit as F
from algebradx import qvalidation as QV
from algebradx import report as RP
from algebradx import simulate as S
from algebradx import survey as SV
from algebradx.cli import main as cli_main
from algebradx.items import ItemModel, design_matrix


def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    raise AssertionError(f"{exc.__name__} not raised")


# ------------------------------------------------------------------ Q-matrix
def test_qmatrix_validation():
    raises(ValueError, QMatrix, [[1, 0], [0, 0]], ["a", "b"], ["A1", "A2"])     # empty row
    raises(ValueError, QMatrix, [[1, 2]], ["a"], ["A1", "A2"])                  # non-binary
    raises(ValueError, QMatrix, [[1, 0], [0, 1]], ["a", "a"], ["A1", "A2"])     # duplicate ids
    q = QMatrix([[1, 0], [0, 1], [1, 1]], ["a", "b", "c"], ["A1", "A2"])
    assert q.is_complete()
    rep = q.identifiability_report()
    assert rep["complete_identity_block"] and not rep["each_attribute_three_items"]


def test_hierarchy_profiles():
    P = permissible_profiles(3, [(0, 1), (1, 2)])          # linear chain A1 -> A2 -> A3
    assert len(P) == 4
    assert {tuple(p) for p in P} == {(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1)}


def test_attribute_dictionary(tmp_path=None):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "a.csv")
    pd.DataFrame({"code": ["A1", "A2"], "name": ["x", "y"], "definition": ["", ""],
                  "prerequisites": ["", "A1"]}).to_csv(path, index=False)
    ad = AttributeDictionary.from_csv(path)
    assert ad.hierarchy() == [("A1", "A2")]


# --------------------------------------------------------------- item models
def test_design_shapes():
    for kind, cols in [("saturated", 8), ("main", 4), ("dina", 2), ("dino", 2)]:
        D, labels = design_matrix(3, kind)
        assert D.shape == (8, cols) and len(labels) == cols


def test_numeric_mstep_recovers_additive_models():
    rng = np.random.default_rng(0)
    for model in ("ACDM", "LLM", "RRUM"):
        it = ItemModel([0, 1, 2], model)
        true = np.array({"ACDM": [0.15, 0.2, 0.25, 0.3], "LLM": [-1.5, 1.0, 1.2, 0.8],
                         "RRUM": [np.log(0.1), 0.7, 0.9, 0.6]}[model])
        P = it._from_delta(true)
        n = rng.integers(200, 400, it.n_groups).astype(float)
        it.m_step(P * n, n)                          # exact expected counts
        assert np.allclose(it.P, P, atol=1e-4), (model, it.P, P)


# --------------------------------------------------------------- estimation
def test_em_reaches_direct_mle():
    """EM must reach the same maximum as direct numerical optimisation of the marginal
    likelihood (tiny saturated G-DINA problem, K = 2)."""
    q = QMatrix([[1, 0], [0, 1], [1, 1], [1, 0], [0, 1], [1, 1]], list("abcdef"), ["A1", "A2"])
    sim = S.simulate_dataset(n_students=800, q=q, seed=4)
    m = DiagnosticModel(q, "GDINA", structural="saturated").fit(sim.responses, tol=1e-8, max_iter=5000)
    X = sim.responses.to_numpy()
    prof = m.profiles
    gidx = m.group_idx
    sizes = [it.n_groups for it in m.item_models]

    def negll(theta):
        pos, PL = 0, []
        for g, s in zip(gidx, sizes):
            PL.append(expit(theta[pos:pos + s])[g]); pos += s
        PL = np.vstack(PL)
        lp = np.concatenate([[0.0], theta[pos:]]); lp -= logsumexp(lp)
        lj = X @ np.log(PL) + (1 - X) @ np.log(1 - PL) + lp
        return -logsumexp(lj, axis=1).sum()

    th0 = np.concatenate([np.log(it.P / (1 - it.P)) for it in m.item_models] +
                         [m.structural.log_pi[1:] - m.structural.log_pi[0]])
    res = minimize(negll, th0 + 0.05, method="BFGS", options={"gtol": 1e-6, "maxiter": 5000})
    assert abs(-res.fun - m.loglik) < 1e-3, (-res.fun, m.loglik)


def test_dina_recovery():
    sim = S.simulate_dataset(n_students=4000, J=30, K=4, model="DINA", seed=1)
    m = DiagnosticModel(sim.qmatrix, "DINA").fit(sim.responses)
    gs = m.guess_slip()
    true_g = np.array([p[0] for p in sim.item_probs])
    true_s = np.array([1 - p[-1] for p in sim.item_probs])
    assert np.abs(gs["guess"] - true_g).mean() < 0.02
    assert np.abs(gs["slip"] - true_s).mean() < 0.02
    assert np.abs(m.attribute_prevalence().values - sim.alpha.mean(0)).max() < 0.03


def test_gdina_equals_lcdm_and_nesting():
    sim = S.simulate_dataset(n_students=2000, J=24, K=3, seed=2)
    g = DiagnosticModel(sim.qmatrix, "GDINA").fit(sim.responses, tol=1e-7)
    l = DiagnosticModel(sim.qmatrix, "LCDM").fit(sim.responses, tol=1e-7)
    d = DiagnosticModel(sim.qmatrix, "DINA").fit(sim.responses, tol=1e-7)
    assert abs(g.loglik - l.loglik) < 1e-2
    assert d.loglik <= g.loglik + 1e-6
    assert F.likelihood_ratio(d, g)["df"] == g.n_params - d.n_params


def test_booklet_design_recovery():
    sim = S.simulate_dataset(n_students=6000, J=42, K=5, n_booklets=6, seed=3)
    assert sim.responses.isna().mean().mean() > 0.5
    m = DiagnosticModel(sim.qmatrix, "GDINA", structural="loglinear2").fit(sim.responses, tol=1e-5)
    assert m.converged
    err = np.mean([np.abs(it.P - p).mean() for it, p in zip(m.item_models, sim.item_probs)])
    assert err < 0.06, err


def test_weights_equal_replicated_rows():
    """Integer weights must give exactly the fit obtained by repeating rows."""
    sim = S.simulate_dataset(n_students=400, J=15, K=3, seed=5)
    w = np.random.default_rng(5).integers(1, 4, 400)
    a = DiagnosticModel(sim.qmatrix).fit(sim.responses, weights=w, normalize_weights=False, tol=1e-8)
    rep = sim.responses.loc[sim.responses.index.repeat(w)].reset_index(drop=True)
    b = DiagnosticModel(sim.qmatrix).fit(rep, tol=1e-8)
    assert abs(a.loglik - b.loglik) < 1e-4
    assert max(np.abs(x.P - y.P).max() for x, y in zip(a.item_models, b.item_models)) < 1e-4


def test_hierarchy_model_zeroes_impermissible():
    q = S.random_qmatrix(18, 3, seed=1)
    alpha = S.correlated_profiles(3000, 3, rho=0.6, seed=2)
    alpha[:, 1] *= alpha[:, 0]                       # enforce A01 -> A02
    sim = S.simulate_dataset(q=q, alpha=alpha, seed=3)
    m = DiagnosticModel(q, "GDINA", hierarchy=[("A01", "A02")]).fit(sim.responses)
    assert m.L == 6
    assert not ((m.profiles[:, 1] == 1) & (m.profiles[:, 0] == 0)).any()
    assert np.abs(m.attribute_prevalence().values - alpha.mean(0)).max() < 0.04


def test_loglinear_structural():
    sim = S.simulate_dataset(n_students=3000, J=30, K=4, rho=0.0, seed=8)
    m = DiagnosticModel(sim.qmatrix, "GDINA", structural="loglinear1").fit(sim.responses)
    assert m.structural.n_params == 4
    assert np.abs(m.attribute_prevalence().values - sim.alpha.mean(0)).max() < 0.04


# -------------------------------------------------------- fit & inference
def test_wald_tests_detect_true_model():
    sim = S.simulate_dataset(n_students=4000, J=30, K=4, model="DINA", seed=9)
    m = DiagnosticModel(sim.qmatrix, "GDINA").fit(sim.responses, tol=1e-6).compute_standard_errors()
    w = F.wald_item_tests(m)
    assert (w["p_DINA"] > 0.01).mean() > 0.8           # true model rarely rejected
    assert (w["p_DINO"] < 0.05).mean() > 0.8           # wrong model usually rejected
    choice = F.select_item_models(w)
    assert sum(v == "DINA" for v in choice.values()) / len(choice) > 0.6


def test_absolute_fit_and_reliability():
    sim = S.simulate_dataset(n_students=2000, J=24, K=3, n_booklets=3, seed=10)
    m = DiagnosticModel(sim.qmatrix).fit(sim.responses)
    af = F.absolute_fit(m)
    assert 0 <= af["srmsr"] < 0.05
    assert af["p_adj_correlation"] > 0.01               # a correct model should fit
    rel = F.classification_reliability(m)
    acc = rel["attribute"]["accuracy"]
    assert ((acc >= 0.5) & (acc <= 1)).all()
    assert 0 < rel["pattern_accuracy"] <= 1


def test_gdi_finds_misspecified_entries():
    sim = S.simulate_dataset(n_students=4000, J=24, K=4, seed=12)
    q_bad = sim.qmatrix.q.copy()
    wrong = [10, 14, 20]
    for j in wrong:                                     # drop one required attribute or add one
        k = np.where(q_bad[j])[0]
        if len(k) > 1:
            q_bad[j, k[0]] = 0
        else:
            q_bad[j, (k[0] + 1) % 4] = 1
    qb = QMatrix(q_bad, sim.qmatrix.items, sim.qmatrix.attributes)
    m = DiagnosticModel(qb).fit(sim.responses)
    sugg, mesa = QV.gdi_validation(m)
    flagged = set(sugg.loc[sugg["differs"], "item"])
    assert {sim.qmatrix.items[j] for j in wrong} & flagged, flagged
    # flagged suggestions for the wrong items should restore the true q-vector
    for j in wrong:
        it = sim.qmatrix.items[j]
        if it in flagged:
            truth = "+".join(np.array(sim.qmatrix.attributes)[sim.qmatrix.q[j] == 1])
            assert sugg.set_index("item").loc[it, "suggested_q"] == truth


def test_standard_errors_are_reasonable():
    """Model-based SEs should be close to the spread of estimates across replications."""
    q = S.random_qmatrix(16, 2, seed=1)
    probs = S.generate_item_probs(q, seed=2)
    est, ses = [], []
    for r in range(25):
        sim = S.simulate_dataset(n_students=1000, q=q, item_probs=probs, seed=100 + r)
        m = DiagnosticModel(q, "DINA").fit(sim.responses, tol=1e-7).compute_standard_errors()
        est.append(m.item_models[0].P)
        ses.append(np.sqrt(np.diag(m._cov[0])))
    ratio = np.mean(ses, 0) / np.std(est, 0, ddof=1)
    assert np.all((ratio > 0.6) & (ratio < 1.6)), ratio


# --------------------------------------------------------------- survey
def test_timss_replicate_weights():
    w = np.ones(8)
    zone = np.array([1, 1, 1, 1, 2, 2, 2, 2])
    rep = np.array([0, 1, 0, 1, 0, 1, 0, 1])
    R, f = SV.timss_replicate_weights(w, zone, rep, "full")
    assert R.shape == (8, 4) and f == 0.5
    assert np.allclose(R.sum(0), 8)
    R1, f1 = SV.timss_replicate_weights(w, zone, rep, "half")
    assert R1.shape == (8, 2) and f1 == 1.0


def test_replicate_se_runs():
    sim = S.simulate_dataset(n_students=600, J=12, K=2, n_zones=6, weight_cv=0.3, seed=6)
    m = DiagnosticModel(sim.qmatrix, "DINA").fit(sim.responses, weights=sim.weights)
    R, f = SV.timss_replicate_weights(sim.weights, sim.jk_zone, sim.jk_rep)
    out = SV.replicate_standard_errors(m, R, f, max_iter=100)
    assert (out["se"] > 0).all() and (out["se"] < 0.2).all()
    assert np.allclose(out.set_index("statistic").loc["prevalence:A01", "estimate"],
                       m.attribute_prevalence()["A01"])


# ----------------------------------------------------- persistence & report
def test_save_load_and_score_new_students():
    sim = S.simulate_dataset(n_students=800, J=18, K=3, seed=7)
    m = DiagnosticModel(sim.qmatrix).fit(sim.responses)
    path = os.path.join(tempfile.mkdtemp(), "cal.json")
    m.save(path)
    m2 = DiagnosticModel.load(path)
    a, b = m.score(), m2.score(sim.responses)
    assert np.allclose(a.filter(regex="^p_").values, b.filter(regex="^p_").values)
    acc = (b.filter(regex="^m_").values == sim.alpha).mean()
    assert acc > 0.8, acc


def test_report_helpers():
    st = RP.mastery_status([0.1, 0.5, 0.9])
    assert list(st) == ["not yet", "uncertain", "mastered"]
    scores = pd.DataFrame({"p_A1": [0.1, 0.5, 0.9], "p_A2": [0.95, 0.9, 0.05]})
    g = RP.group_summary(scores, ["A1", "A2"])
    tot = g[["share_mastered", "share_uncertain", "share_not_yet"]].sum(1)
    assert np.allclose(tot, 1)
    assert "<table>" in RP.html_report(scores, ["A1", "A2"])


def test_cli_roundtrip():
    d = tempfile.mkdtemp()
    cli_main(["simulate", "--n", "500", "--items", "15", "--attributes", "3", "--out", d])
    out = os.path.join(d, "res")
    cli_main(["fit", "--responses", os.path.join(d, "responses.csv"), "--qmatrix",
              os.path.join(d, "qmatrix.csv"), "--id", "id", "--weight", "weight", "--out", out])
    for f in ("calibration.json", "student_scores.csv", "summary.json", "report.html"):
        assert os.path.exists(os.path.join(out, f)), f
    cli_main(["score", "--calibration", os.path.join(out, "calibration.json"), "--responses",
              os.path.join(d, "responses.csv"), "--id", "id", "--out", os.path.join(d, "s.csv")])
    assert len(pd.read_csv(os.path.join(d, "s.csv"))) == 500


# ------------------------------------------------------------- scoring rules
def test_timss_scoring_rules():
    from algebradx import datasets as DS
    mc = DS.score_timss_mc([1, 2, 9, 6, np.nan, 7], key=2)
    assert np.allclose(mc[:3], [0, 1, 0]) and np.isnan(mc[3]) and np.isnan(mc[4]) and np.isnan(mc[5])
    cr1 = DS.score_timss_cr([10, 11, 70, 79, 99, 96, np.nan], max_points=1)
    assert np.allclose(cr1[:5], [1, 1, 0, 0, 0]) and np.isnan(cr1[5]) and np.isnan(cr1[6])
    cr2 = DS.score_timss_cr([20, 10, 70, 99], max_points=2)
    assert np.allclose(cr2, [1, 0, 0, 0])
    cr2b = DS.score_timss_cr([20, 10, 70], max_points=2, partial="one")
    assert np.allclose(cr2b, [1, 1, 0])
    assert DS.already_scored([0, 1, np.nan, 2]) and not DS.already_scored([1, 3, 4])


def test_pisa_scoring_rules():
    from algebradx import datasets as DS
    s = DS.score_pisa([0, 1, 9, 7, 8, np.nan])
    assert np.allclose(s[:3], [0, 1, 0]) and np.isnan(s[3:]).all()
    s2 = DS.score_pisa([0, 1, 2, 9])
    assert np.allclose(s2, [0, 0, 1, 0])


# ------------------------------------------------------------- SPSS reader
def _write_sav(path, cols, compress=True):
    """Write a minimal numeric+string SPSS file (test helper)."""
    import struct
    names = list(cols)
    widths = [0 if not isinstance(cols[n][0], str) else 8 for n in names]
    n = len(cols[names[0]])
    out = bytearray()
    hdr = b"$FL2" + b"@(#) test".ljust(60) + struct.pack("<iiiii", 2, len(names), 1 if compress else 0, 0, n)
    hdr += struct.pack("<d", 100.0) + b"01 Jan 26" + b"00:00:00" + b"".ljust(64) + b"\0\0\0"
    out += hdr
    for nm, w in zip(names, widths):
        out += struct.pack("<iiiiii", 2, w, 0, 0, 0, 0) + nm[:8].upper().encode().ljust(8)
    # value labels for the first numeric variable
    out += struct.pack("<ii", 3, 1) + struct.pack("<d", 9.0) + bytes([7]) + b"Omitted"
    out += struct.pack("<iii", 4, 1, 1)
    long = "\t".join(f"{nm[:8].upper()}={nm}" for nm in names).encode()
    out += struct.pack("<iiii", 7, 13, 1, len(long)) + long
    out += struct.pack("<ii", 999, 0)
    slots = []
    for i in range(n):
        for nm, w in zip(names, widths):
            v = cols[nm][i]
            slots.append(("s", v.encode().ljust(8)) if w else ("n", v))
    if not compress:
        for kind, v in slots:
            out += v if kind == "s" else struct.pack("<d", -np.finfo(float).max if np.isnan(v) else v)
    else:
        for k in range(0, len(slots), 8):
            chunk = slots[k:k + 8]
            cmds, data = bytearray(), bytearray()
            for kind, v in chunk:
                if kind == "s":
                    cmds.append(253); data += v
                elif np.isnan(v):
                    cmds.append(255)
                elif float(v).is_integer() and -99 <= v <= 150:
                    cmds.append(int(v + 100))
                else:
                    cmds.append(253); data += struct.pack("<d", v)
            cmds += bytes(8 - len(cmds))
            out += cmds + data
    open(path, "wb").write(bytes(out))


def test_sav_reader_roundtrip():
    from algebradx.sav import read_sav
    d = tempfile.mkdtemp()
    cols = {"IDSTUD": [1.0, 2.0, 3.0], "LongItemName1": [1.0, np.nan, 9.0],
            "TOTWGT": [12.5, 3.25, 1e6], "CNT": ["USA", "CAN", "USA"]}
    for comp in (True, False):
        p = os.path.join(d, f"t{comp}.sav")
        _write_sav(p, cols, compress=comp)
        df, meta = read_sav(p)
        assert list(df.columns) == list(cols)
        assert np.allclose(df["TOTWGT"], cols["TOTWGT"]) and np.isnan(df["LongItemName1"][1])
        assert df["CNT"].tolist() == cols["CNT"]
        assert meta.value_labels["IDSTUD"] == {9.0: "Omitted"}
        us, _ = read_sav(p, usecols=["IDSTUD"], row_filter=("CNT", "USA"))
        assert us["IDSTUD"].tolist() == [1.0, 3.0] and list(us.columns) == ["IDSTUD"]
