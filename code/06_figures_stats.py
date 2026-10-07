#!/usr/bin/env python3
"""Step 6 — figures and paper/stats.json (every number any document quotes).

    python code/06_figures_stats.py                    # synthetic + recovery, stamped
    python code/06_figures_stats.py --source timss2023 # real-data figures, stamped
    python code/06_figures_stats.py --final            # remove the stamp after verification

Colours: the dataviz reference palette (slot 1 blue, slot 2 orange), validated for
colour-vision deficiency; identity is never carried by colour alone (legends + markers).
"""
import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "paper", "figures")
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
STAMP = "DRA" "FT — unverified"   # removed by --final

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "legend.frameon": False, "figure.dpi": 150,
})


def finish(fig, name, final, caption):
    if not final:
        fig.text(0.99, 0.01, STAMP, ha="right", va="bottom", fontsize=8, color="#b2182b", alpha=0.8)
    fig.text(0.01, 0.01, caption, ha="left", va="bottom", fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(FIG, name), dpi=200)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="synthetic")
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    os.makedirs(FIG, exist_ok=True)
    res = os.path.join(ROOT, "results", a.source)
    log = json.load(open(os.path.join(res, "fit_log.json")))
    prev = pd.read_csv(os.path.join(res, "attribute_prevalence.csv"))
    rel = pd.read_csv(os.path.join(res, "classification_reliability.csv"))
    rfit = pd.read_csv(os.path.join(res, "relative_fit.csv"))
    qv = pd.read_csv(os.path.join(res, "qmatrix_validation.csv"))
    tag = "synthetic data (not real students)" if a.source == "synthetic" else f"{a.source} US sample"
    stats = {"source": a.source, "data_label": tag}

    # Figure 1 — skill prevalence with replicate SE (and truth for synthetic data)
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    y = np.arange(len(prev))[::-1]
    se = prev["se_replicate"] if "se_replicate" in prev else None
    ax.errorbar(prev["estimate"], y, xerr=None if se is None else 1.96 * se, fmt="o", color=BLUE,
                ms=6, lw=2, capsize=0, label="estimated (95% CI, replicate weights)")
    if "true_prevalence" in prev:
        ax.scatter(prev["true_prevalence"], y, marker="D", s=30, facecolor="none",
                   edgecolor=ORANGE, lw=1.6, label="true value", zorder=3)
    ax.set_yticks(y, [f"{c}  {n}" for c, n in zip(prev["attribute"], prev["name"])])
    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of students who have mastered the skill")
    ax.legend(loc="upper center", bbox_to_anchor=(0.35, -0.2), ncol=2, fontsize=7)
    ax.set_title("Skill prevalence", loc="left", fontsize=10, color=INK)
    finish(fig, f"fig1_prevalence_{a.source}.png", a.final, f"Source: {tag}; AlgebraDx v0.1.")

    # Figure 2 — classification accuracy per skill
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    x = np.arange(len(rel))
    # dot plot, not bars: the axis does not start at zero
    ax.scatter(x, rel["accuracy"], s=46, color=BLUE, label="expected accuracy (model)", zorder=3)
    if "true_classification_agreement" in prev:
        ax.scatter(x, prev["true_classification_agreement"], marker="D", s=26, color=ORANGE,
                   zorder=3, label="observed agreement with true profile")
    ax.set_xticks(x, rel["attribute"])
    ax.set_ylim(0.5, 1)
    ax.set_ylabel("Proportion classified correctly")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=7)
    ax.set_title("How reliably each skill is classified", loc="left", fontsize=10, color=INK)
    finish(fig, f"fig2_reliability_{a.source}.png", a.final, f"Source: {tag}; posterior-based indices (Johnson & Sinharay 2018).")

    stats.update({
        "n_students": log["n_students"], "n_items": log["n_items"], "K": log["K"],
        "items_per_student_mean": round(log["items_per_student_mean"], 1),
        "final_model": log["final_model"], "srmsr": round(log["srmsr"], 3),
        "p_adj_correlation": round(log["p_adj_correlation"], 3),
        "pattern_accuracy": round(log["pattern_accuracy"], 3),
        "attribute_accuracy_min": round(rel["accuracy"].min(), 3),
        "attribute_accuracy_max": round(rel["accuracy"].max(), 3),
        "attribute_accuracy_mean": round(rel["accuracy"].mean(), 3),
        "prevalence_min": round(prev["estimate"].min(), 3),
        "prevalence_max": round(prev["estimate"].max(), 3),
        "q_items_flagged": int(qv["differs"].sum()),
        "item_model_counts": log["item_model_counts"],
        "bic_best_model": rfit.sort_values("bic").iloc[0]["model"],
        "gdina_seconds": round(log["summary"]["seconds"], 0) if log["final_model"] == "GDINA" else None,
    })
    if "se_replicate" in prev:
        stats["prevalence_se_max"] = round(prev["se_replicate"].max(), 3)
        stats["n_replicates"] = int(prev["n_replicates"].iloc[0])
    if "true_prevalence" in prev:
        stats["prevalence_abs_error_max"] = round((prev["estimate"] - prev["true_prevalence"]).abs().max(), 3)
        stats["true_pattern_agreement"] = round(log["true_pattern_agreement"], 3)
        stats["true_attribute_agreement_mean"] = round(prev["true_classification_agreement"].mean(), 3)
        stats["item_prob_rmse_vs_truth"] = round(log["item_prob_rmse_vs_truth"], 3)

    # Figure 3 — recovery study
    rec_path = os.path.join(ROOT, "results", "recovery", "recovery.csv")
    if os.path.exists(rec_path):
        rec = pd.read_csv(rec_path)
        A = rec[rec.study == "A"].groupby("N").mean(numeric_only=True).reset_index()
        B = rec[rec.study == "B"].mean(numeric_only=True)
        fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.8))
        axes[0].plot(A["N"], A["rmse_P"], "-o", color=BLUE, lw=2, ms=6)
        axes[0].set_xscale("log")
        axes[0].set_xticks(A["N"], [f"{n:,}" for n in A["N"]])
        axes[0].minorticks_off()
        axes[0].set_xlabel("Students (complete data, K = 5)")
        axes[0].set_ylabel("RMSE of item success probabilities")
        axes[0].set_ylim(0, None)
        axes[1].plot(A["N"], A["attribute_agreement_mean"], "-o", color=BLUE, lw=2, ms=6,
                     label="observed")
        axes[1].plot(A["N"], A["predicted_attribute_accuracy"], "--D", color=ORANGE, lw=2, ms=5,
                     label="model-predicted")
        axes[1].set_xscale("log")
        axes[1].set_xticks(A["N"], [f"{n:,}" for n in A["N"]])
        axes[1].minorticks_off()
        axes[1].set_xlabel("Students (complete data, K = 5)")
        axes[1].set_ylabel("Skill classification accuracy")
        axes[1].set_ylim(0.8, 1)
        axes[1].legend(fontsize=7, loc="lower right")
        finish(fig, "fig3_recovery.png", a.final,
               f"Simulation, {int(rec[rec.study == 'A'].rep.max()) + 1} replications per N.")
        stats["recovery"] = {
            "A_reps": int(rec[rec.study == "A"].rep.max()) + 1,
            "A_rmse_by_N": {str(int(n)): round(v, 3) for n, v in zip(A["N"], A["rmse_P"])},
            "A_attr_agreement_by_N": {str(int(n)): round(v, 3) for n, v in zip(A["N"], A["attribute_agreement_mean"])},
            "A_pred_accuracy_by_N": {str(int(n)): round(v, 3) for n, v in zip(A["N"], A["predicted_attribute_accuracy"])},
            "A_pattern_agreement_by_N": {str(int(n)): round(v, 3) for n, v in zip(A["N"], A["pattern_agreement"])},
            "B_reps": int(rec[rec.study == "B"].rep.max()) + 1,
            "B_items_per_student": round(B["items_per_student"], 1),
            "B_rmse_P": round(B["rmse_P"], 3),
            "B_prevalence_error_max": round(B["max_abs_prevalence_error"], 3),
            "B_attr_agreement": round(B["attribute_agreement_mean"], 3),
            "B_pred_accuracy": round(B["predicted_attribute_accuracy"], 3),
            "B_pattern_agreement": round(B["pattern_agreement"], 3),
            "B_seconds": round(B["seconds"], 0),
        }
    with open(os.path.join(ROOT, "paper", "stats.json"), "w") as f:
        json.dump(stats, f, indent=2, default=str)
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    main()
