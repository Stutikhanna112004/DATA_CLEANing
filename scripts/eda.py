"""
Data Vortex - Round 1: EDA chart + summary generator.
Reads data/processed/*.csv, writes reports/figures/*.png and reports/eda_summary.json.

Run: python scripts/eda.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROC_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
FIG_DIR = Path(__file__).resolve().parent.parent / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["figure.dpi"] = 110
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3


def savefig(name):
    plt.tight_layout()
    plt.savefig(FIG_DIR / name)
    plt.close()


def main():
    users = pd.read_csv(PROC_DIR / "Social_Engine_Users_clean.csv")
    posts = pd.read_csv(PROC_DIR / "Social_Engine_Posts_clean.csv", parse_dates=["timestamp_parsed"])

    summary = {}

    # 1. Platform distribution
    plat_counts = posts["platform"].value_counts(dropna=True)
    plt.figure(figsize=(6, 4))
    plat_counts.plot(kind="bar", color="#3b82f6")
    plt.title("Posts by Platform")
    plt.ylabel("Post count")
    savefig("01_platform_distribution.png")
    summary["platform_distribution"] = plat_counts.to_dict()

    # 2. Posting volume over time
    posts["month"] = posts["timestamp_parsed"].dt.to_period("M").astype(str)
    monthly = posts.groupby("month").size().sort_index()
    plt.figure(figsize=(8, 4))
    monthly.plot(kind="line", marker="o", color="#10b981")
    plt.title("Posting Volume Over Time")
    plt.ylabel("Post count")
    plt.xticks(rotation=45, ha="right")
    savefig("02_posting_volume_over_time.png")
    summary["monthly_post_counts"] = monthly.to_dict()

    # 3. Follower count distribution
    plt.figure(figsize=(6, 4))
    users["follower_count"].plot(kind="hist", bins=30, color="#f59e0b")
    plt.title("Follower Count Distribution")
    plt.xlabel("follower_count")
    savefig("03_follower_count_distribution.png")
    summary["follower_count_stats"] = users["follower_count"].describe().to_dict()

    # 4. Engagement metric distributions
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, col, color in zip(axes, ["likes", "shares", "comments"], ["#ef4444", "#8b5cf6", "#06b6d4"]):
        posts[col].dropna().plot(kind="hist", bins=30, ax=ax, color=color)
        ax.set_title(col)
    plt.suptitle("Engagement Metric Distributions")
    savefig("04_engagement_distributions.png")
    summary["engagement_stats"] = {
        col: posts[col].describe().to_dict() for col in ["likes", "shares", "comments"]
    }

    # 5. Engagement correlation
    corr = posts[["likes", "shares", "comments"]].corr()
    plt.figure(figsize=(4, 4))
    plt.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    plt.xticks(range(3), corr.columns, rotation=45)
    plt.yticks(range(3), corr.columns)
    for i in range(3):
        for j in range(3):
            plt.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center")
    plt.title("Engagement Metric Correlation")
    plt.colorbar()
    savefig("05_engagement_correlation.png")
    summary["engagement_correlation"] = corr.to_dict()

    # 6. Top user locations
    top_locations = users["location"].value_counts().head(15)
    plt.figure(figsize=(7, 5))
    top_locations.plot(kind="barh", color="#6366f1")
    plt.title("Top 15 User Locations")
    plt.gca().invert_yaxis()
    savefig("06_top_locations.png")
    summary["top_locations"] = top_locations.to_dict()

    # 7. Language distribution
    lang_counts = users["language"].value_counts()
    plt.figure(figsize=(6, 4))
    lang_counts.plot(kind="bar", color="#14b8a6")
    plt.title("User Language Distribution")
    savefig("07_language_distribution.png")
    summary["language_distribution"] = lang_counts.to_dict()

    # 8. Missingness overview
    miss = posts[["platform", "text_content", "likes"]].isnull().mean().sort_values(ascending=False)
    plt.figure(figsize=(5, 4))
    (miss * 100).plot(kind="bar", color="#dc2626")
    plt.title("Missingness by Column (%)")
    plt.ylabel("% missing")
    savefig("08_missingness_overview.png")
    summary["missingness_pct"] = (miss * 100).to_dict()

    # 9. Missingness independence check (pairwise correlation of missingness indicators)
    miss_ind = posts[["platform", "text_content", "likes"]].isnull().astype(int)
    miss_corr = miss_ind.corr()
    summary["missingness_indicator_correlation"] = miss_corr.to_dict()
    plt.figure(figsize=(4, 4))
    plt.imshow(miss_corr, cmap="coolwarm", vmin=-1, vmax=1)
    plt.xticks(range(3), miss_corr.columns, rotation=45)
    plt.yticks(range(3), miss_corr.columns)
    for i in range(3):
        for j in range(3):
            plt.text(j, i, f"{miss_corr.iloc[i, j]:.2f}", ha="center", va="center")
    plt.title("Missingness Independence Check")
    plt.colorbar()
    savefig("09_missingness_independence.png")

    with open(Path(__file__).resolve().parent.parent / "reports" / "eda_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("EDA complete. Figures written to reports/figures/, summary to reports/eda_summary.json")


if __name__ == "__main__":
    main()
