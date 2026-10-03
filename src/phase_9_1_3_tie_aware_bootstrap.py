from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# PHASE 9.1.3 — TIE-AWARE FINAL TEST BOOTSTRAP
# ============================================================

RESULTS_DIR = Path("results/eligible")

INPUT_FILE = RESULTS_DIR / "final_test_router_predictions.csv"

OUTPUT_CI = (
    RESULTS_DIR /
    "canonical_bootstrap_confidence_intervals.csv"
)

OUTPUT_COMPARISONS = (
    RESULTS_DIR /
    "canonical_bootstrap_paired_comparisons.csv"
)

OUTPUT_RAW = (
    RESULTS_DIR /
    "canonical_bootstrap_raw.csv"
)

LOCKED_BUDGET = 0.15
N_BOOTSTRAP = 5000
SEED = 42


print("=" * 80)
print("PHASE 9.1.3 — TIE-AWARE PAIRED BOOTSTRAP")
print("=" * 80)


# ------------------------------------------------------------
# Load
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

n = len(df)
n_review = int(np.floor(LOCKED_BUDGET * n))

fn_mask = (
    (df["actual_30d"] == 1) &
    (df["predicted_30d"] == 0)
)

total_fn = int(fn_mask.sum())

print("\nDataset shape:", df.shape)
print("Low-risk patients:", n)
print("False negatives:", total_fn)
print("Review budget:", LOCKED_BUDGET)
print("Patients reviewed:", n_review)


# ============================================================
# Ranking functions
# ============================================================

def fn_indicator(frame):
    return (
        (frame["actual_30d"].to_numpy() == 1) &
        (frame["predicted_30d"].to_numpy() == 0)
    )


def deterministic_capture(frame, score_col, k):
    """
    Rank by score descending.

    bootstrap_order is used only as a deterministic secondary
    ordering when duplicate rows occur in a bootstrap sample.
    """

    ranked = frame.sort_values(
        [score_col, "bootstrap_order"],
        ascending=[False, True]
    )

    selected = ranked.head(k)

    captured = fn_indicator(selected).sum()

    return float(captured)


def probability_expected_capture(frame, k):
    """
    Tie-aware expected FN capture.

    All patients strictly above the probability cutoff are selected.

    If the cutoff falls inside a tie, calculate the EXPECTED number
    of false negatives selected uniformly at random from that tie.
    """

    score = "probability_score"

    values = frame[score].to_numpy()

    sorted_scores = np.sort(values)[::-1]

    cutoff = sorted_scores[k - 1]

    above = frame[frame[score] > cutoff]

    tied = frame[
        np.isclose(
            frame[score],
            cutoff,
            atol=1e-12,
            rtol=0
        )
    ]

    slots = k - len(above)

    above_fn = fn_indicator(above).sum()
    tied_fn = fn_indicator(tied).sum()

    if len(tied) == 0:
        return float(above_fn)

    expected_tied_fn = (
        slots * tied_fn / len(tied)
    )

    return float(
        above_fn + expected_tied_fn
    )


# ============================================================
# Original point estimates
# ============================================================

original = df.copy()
original["bootstrap_order"] = np.arange(len(original))

prob_fn = probability_expected_capture(
    original,
    n_review
)

router_fn = deterministic_capture(
    original,
    "fn_router_probability",
    n_review
)

dis_fn = deterministic_capture(
    original,
    "disagreement_score",
    n_review
)

random_fn = (
    n_review * total_fn / n
)


point_rows = []

for method, captured in [
    ("Probability", prob_fn),
    ("Rescue Router", router_fn),
    ("Disagreement", dis_fn),
    ("Random", random_fn),
]:

    point_rows.append({
        "method": method,
        "fn_captured": captured,
        "fn_capture_rate": captured / total_fn
    })

point_df = pd.DataFrame(point_rows)


print("\n" + "=" * 80)
print("CANONICAL POINT ESTIMATES")
print("=" * 80)

temp = point_df.copy()
temp["fn_capture_percent"] = (
    temp["fn_capture_rate"] * 100
)

print(
    temp[
        [
            "method",
            "fn_captured",
            "fn_capture_percent"
        ]
    ].to_string(index=False)
)


# ============================================================
# Bootstrap
# ============================================================

print("\n" + "=" * 80)
print(f"RUNNING {N_BOOTSTRAP} PAIRED BOOTSTRAP ITERATIONS")
print("=" * 80)

rng = np.random.default_rng(SEED)

records = []


for b in range(N_BOOTSTRAP):

    idx = rng.integers(
        0,
        n,
        size=n
    )

    boot = df.iloc[idx].copy()

    # Unique ordering for duplicate bootstrap rows
    boot["bootstrap_order"] = np.arange(n)

    boot_total_fn = int(
        fn_indicator(boot).sum()
    )

    if boot_total_fn == 0:
        continue

    boot_k = int(
        np.floor(
            LOCKED_BUDGET * len(boot)
        )
    )

    probability_captured = (
        probability_expected_capture(
            boot,
            boot_k
        )
    )

    router_captured = (
        deterministic_capture(
            boot,
            "fn_router_probability",
            boot_k
        )
    )

    disagreement_captured = (
        deterministic_capture(
            boot,
            "disagreement_score",
            boot_k
        )
    )

    # Exact analytical random expectation
    random_capture_rate = (
        boot_k / len(boot)
    )

    records.append({
        "iteration": b + 1,

        "Probability":
            probability_captured /
            boot_total_fn,

        "Rescue Router":
            router_captured /
            boot_total_fn,

        "Disagreement":
            disagreement_captured /
            boot_total_fn,

        "Random":
            random_capture_rate,
    })

    if (b + 1) % 500 == 0:
        print(
            f"Completed {b + 1}/{N_BOOTSTRAP}"
        )


raw = pd.DataFrame(records)


# ============================================================
# Confidence intervals
# ============================================================

print("\n" + "=" * 80)
print("BOOTSTRAP 95% CONFIDENCE INTERVALS")
print("=" * 80)

ci_rows = []

for method in [
    "Probability",
    "Rescue Router",
    "Disagreement",
    "Random"
]:

    values = raw[method].to_numpy()

    point = float(
        point_df.loc[
            point_df["method"] == method,
            "fn_capture_rate"
        ].iloc[0]
    )

    ci_rows.append({
        "method": method,
        "point_estimate": point,
        "bootstrap_mean": np.mean(values),
        "ci_lower": np.percentile(values, 2.5),
        "ci_upper": np.percentile(values, 97.5),
    })


ci = pd.DataFrame(ci_rows)

ci_print = ci.copy()

for c in [
    "point_estimate",
    "bootstrap_mean",
    "ci_lower",
    "ci_upper"
]:
    ci_print[c] *= 100

print(ci_print.to_string(index=False))


# ============================================================
# Paired comparisons
# ============================================================

print("\n" + "=" * 80)
print("PAIRED BOOTSTRAP COMPARISONS")
print("=" * 80)


comparisons = [
    ("Rescue Router", "Probability"),
    ("Rescue Router", "Disagreement"),
    ("Probability", "Disagreement"),
    ("Rescue Router", "Random"),
]


comparison_rows = []


for a, b in comparisons:

    diff = (
        raw[a].to_numpy() -
        raw[b].to_numpy()
    )

    # Two-sided bootstrap sign test style p-value
    p_lower = np.mean(diff <= 0)
    p_upper = np.mean(diff >= 0)

    p_value = min(
        1.0,
        2 * min(
            p_lower,
            p_upper
        )
    )

    comparison_rows.append({
        "comparison": f"{a} vs {b}",
        "mean_difference": np.mean(diff),
        "ci_lower": np.percentile(
            diff,
            2.5
        ),
        "ci_upper": np.percentile(
            diff,
            97.5
        ),
        "bootstrap_p_value": p_value,
        "probability_a_better":
            np.mean(diff > 0),
        "probability_equal":
            np.mean(
                np.isclose(
                    diff,
                    0,
                    atol=1e-12
                )
            ),
        "probability_a_worse":
            np.mean(diff < 0),
    })


comparison_df = pd.DataFrame(
    comparison_rows
)


comparison_print = comparison_df.copy()

for c in [
    "mean_difference",
    "ci_lower",
    "ci_upper",
    "probability_a_better",
    "probability_equal",
    "probability_a_worse",
]:
    comparison_print[c] *= 100


print(
    comparison_print.to_string(
        index=False
    )
)


# ============================================================
# Router lift over random
# ============================================================

print("\n" + "=" * 80)
print("RESCUE ROUTER VS RANDOM")
print("=" * 80)

router_random_diff = (
    raw["Rescue Router"] -
    raw["Random"]
)

router_lift = (
    raw["Rescue Router"] /
    raw["Random"]
)


point_router = float(
    point_df.loc[
        point_df["method"] ==
        "Rescue Router",
        "fn_capture_rate"
    ].iloc[0]
)

point_random = float(
    point_df.loc[
        point_df["method"] ==
        "Random",
        "fn_capture_rate"
    ].iloc[0]
)


print(
    f"Router point capture: "
    f"{point_router*100:.2f}%"
)

print(
    f"Random expectation: "
    f"{point_random*100:.2f}%"
)

print(
    f"Point difference: "
    f"{(point_router-point_random)*100:.2f} pp"
)

print(
    "Difference 95% CI: "
    f"[{np.percentile(router_random_diff,2.5)*100:.2f}, "
    f"{np.percentile(router_random_diff,97.5)*100:.2f}]"
)

p_router_random = min(
    1.0,
    2 * min(
        np.mean(
            router_random_diff <= 0
        ),
        np.mean(
            router_random_diff >= 0
        )
    )
)

print(
    "Bootstrap p-value:",
    p_router_random
)

print(
    "Probability router > random:",
    f"{np.mean(router_random_diff > 0)*100:.2f}%"
)

print(
    f"Point lift: "
    f"{point_router/point_random:.3f}x"
)

print(
    "Lift 95% CI: "
    f"[{np.percentile(router_lift,2.5):.3f}, "
    f"{np.percentile(router_lift,97.5):.3f}]"
)


# ============================================================
# Save
# ============================================================

ci.to_csv(
    OUTPUT_CI,
    index=False
)

comparison_df.to_csv(
    OUTPUT_COMPARISONS,
    index=False
)

raw.to_csv(
    OUTPUT_RAW,
    index=False
)


print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print(OUTPUT_CI)
print(OUTPUT_COMPARISONS)
print(OUTPUT_RAW)

print("\n" + "=" * 80)
print("PHASE 9.1.3 COMPLETE")
print("=" * 80)