#!/usr/bin/env python3
"""
Analyze Trump–Xi meeting coverage dataset and generate visuals.

Inputs
- CSV file with columns: title, authors, source, url, published, language, sentiment, body

Outputs (saved under output_dir)
- basic_stats.png: multi-panel basic stats visualization
- title_clusters.png: bar chart of clustered titles
- titles_with_clusters.csv: original rows with assigned cluster label
- fulltext_wordcloud.png: word cloud generated from full article texts

Usage
  python analyze_texts.py \
    --csv /workspaces/ai4news/showcase/TextAnalysis/trump_xi_meeting_fulltext_dedup.csv \
    --output-dir /workspaces/ai4news/showcase/TextAnalysis/output \
    --meeting-date 2025-10-30 \
    --clusters 5

Notes
- Meeting date default is set to 2025-10-30 based on dataset context. Override with --meeting-date if needed.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, date
from typing import List, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud, STOPWORDS


def ensure_output_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def parse_meeting_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid date format for --meeting-date: {value}. Use YYYY-MM-DD.") from e


def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "published" not in df.columns:
        raise ValueError("CSV must contain a 'published' column with ISO datetime strings.")
    # Parse published time; coerce errors to NaT
    df["published_dt"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
    df["date"] = df["published_dt"].dt.date
    return df


def plot_basic_stats(df: pd.DataFrame, meeting: date, out_path: str) -> None:
    sns.set_theme(style="whitegrid")

    # Articles per day
    daily_counts = (
        df.dropna(subset=["date"]).groupby("date").size().rename("articles").reset_index()
    )

    # Top sources
    source_counts = (
        df["source"].fillna("Unknown").value_counts().head(10).rename_axis("source").reset_index(name="count")
    )

    # Before / On / After
    def classify_row(d: date | float) -> str:
        if pd.isna(d):
            return "unknown"
        if d < meeting:
            return "before"
        if d == meeting:
            return "on"
        return "after"

    timing = df["date"].apply(classify_row).value_counts().reindex(["before", "on", "after", "unknown"]).fillna(0)

    # Plot
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # 1) Articles per day
    axes[0].plot(daily_counts["date"], daily_counts["articles"], marker="o")
    axes[0].axvline(pd.Timestamp(meeting), color="red", linestyle="--", label=f"Meeting {meeting}")
    axes[0].set_title("Articles per day")
    axes[0].set_xlabel("Date")
    axes[0].set_ylabel("Articles")
    axes[0].legend()
    fig.autofmt_xdate(rotation=30)

    # 2) Top sources
    sns.barplot(data=source_counts, x="count", y="source", ax=axes[1], palette="Blues_d")
    axes[1].set_title("Top sources (Top 10)")
    axes[1].set_xlabel("Articles")
    axes[1].set_ylabel("")

    # 3) Timing classification
    sns.barplot(x=timing.index, y=timing.values, ax=axes[2], palette=["#999", "#f99", "#9f9", "#ccc"])
    axes[2].set_title("Timing relative to meeting")
    axes[2].set_xlabel("")
    axes[2].set_ylabel("Articles")

    plt.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def cluster_titles(df: pd.DataFrame, k: int) -> Tuple[pd.DataFrame, List[str]]:
    titles = df["title"].fillna("")
    # Vectorize titles
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=5000)
    X = vectorizer.fit_transform(titles)

    # KMeans clustering
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    # Derive human-readable cluster names from top terms per centroid
    feature_names = vectorizer.get_feature_names_out()
    cluster_names: List[str] = []
    order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
    for i in range(k):
        top_terms = [feature_names[ind] for ind in order_centroids[i, :5]]
        cluster_names.append(
            ", ".join(top_terms[:3])  # concise label of top 3 terms
        )

    df_out = df.copy()
    df_out["title_cluster_id"] = labels
    df_out["title_cluster_name"] = [cluster_names[i] for i in labels]
    return df_out, cluster_names


def plot_title_clusters(df_with_clusters: pd.DataFrame, cluster_names: List[str], out_path: str) -> None:
    sns.set_theme(style="whitegrid")
    counts = df_with_clusters["title_cluster_name"].value_counts().rename_axis("cluster").reset_index(name="count")
    # Preserve original order by cluster id if possible
    order = cluster_names
    # Some clusters may share same name if top terms overlap; sort by counts if names duplicate
    counts["cluster"] = pd.Categorical(counts["cluster"], categories=order, ordered=True)
    counts = counts.sort_values(["cluster", "count"], ascending=[True, False])

    plt.figure(figsize=(10, 6))
    sns.barplot(data=counts, x="count", y="cluster", palette="viridis")
    plt.title("Title clusters (by top TF-IDF terms)")
    plt.xlabel("Articles")
    plt.ylabel("Cluster label (top terms)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def generate_fulltext_wordcloud(df: pd.DataFrame, out_path: str) -> None:
    texts = df["body"].dropna().astype(str)
    if texts.empty:
        # Fallback to titles if bodies are missing
        texts = df["title"].dropna().astype(str)

    # Build a richer set of stopwords and filters
    stopwords = set(STOPWORDS)
    stopwords.update({
        # Generic reporting verbs/terms
        "said", "says", "will", "would", "could", "also", "according",
        # Generic nouns/time words
        "year", "years", "month", "months", "day", "days", "week", "weeks",
        "today", "yesterday", "tomorrow", "time",
        # News boilerplate
        "new", "news", "breaking", "update", "live", "report",
        # Wire sources and common agencies
        "ap", "associated", "press", "reuters", "afp", "bbc", "cnn",
        # Domain-specific names we don't want dominating
        "trump", "xi", "jinping", "biden", "president", "china", "chinese",
        "u.s", "us", "united", "states", "america", "american",
        "south", "korea", "japan", "apec",
    })

    # Join all texts
    text_blob = "\n".join(texts.tolist())

    # Configure WordCloud to:
    # - include phrases via collocations=True (common bigrams)
    # - drop single-letter tokens using regexp that requires >=2 letters
    # - ignore numbers-only tokens by requiring alphabetic start
    wc = WordCloud(
        width=1600,
        height=900,
        background_color="white",
        stopwords=stopwords,
        max_words=500,
        collocations=True,              # allow meaningful phrases (bigrams)
        collocation_threshold=30,       # default; tweak if too many phrases/noise
        regexp=r"(?u)\b[a-zA-Z][a-zA-Z][a-zA-Z'-]*\b",  # >=2 letters; keep words/phrases parts
    )

    wc.generate(text_blob)
    wc.to_file(out_path)


def main():
    parser = argparse.ArgumentParser(description="Analyze CSV and generate visuals for Trump–Xi meeting coverage.")
    parser.add_argument("--csv", required=True, help="Path to input CSV file")
    parser.add_argument("--output-dir", required=True, help="Directory to write outputs")
    parser.add_argument("--meeting-date", type=parse_meeting_date, default=date(2025, 10, 30),
                        help="Meeting date in YYYY-MM-DD (default: 2025-10-30)")
    parser.add_argument("--clusters", type=int, default=5, help="Number of title clusters (default: 5)")

    args = parser.parse_args()

    ensure_output_dir(args.output_dir)
    df = load_data(args.csv)

    # 1) Basic stats
    basic_stats_path = os.path.join(args.output_dir, "basic_stats.png")
    plot_basic_stats(df, args.meeting_date, basic_stats_path)

    # 2) Title categorization
    df_clusters, cluster_names = cluster_titles(df, args.clusters)
    titles_csv_path = os.path.join(args.output_dir, "titles_with_clusters.csv")
    df_clusters.to_csv(titles_csv_path, index=False)
    clusters_plot_path = os.path.join(args.output_dir, "title_clusters.png")
    plot_title_clusters(df_clusters, cluster_names, clusters_plot_path)

    # 3) Word cloud of full text
    wordcloud_path = os.path.join(args.output_dir, "fulltext_wordcloud.png")
    generate_fulltext_wordcloud(df, wordcloud_path)

    # Drop a tiny README
    readme_path = os.path.join(args.output_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(
            "# TextAnalysis outputs\n\n"
            "This folder contains artifacts generated by `analyze_texts.py`.\n\n"
            "- `basic_stats.png`: Articles per day, top sources, and counts before/on/after the meeting.\n"
            "- `titles_with_clusters.csv`: Original rows with a `title_cluster_id` and `title_cluster_name`.\n"
            "- `title_clusters.png`: Bar chart of title cluster sizes with labels derived from top TF-IDF terms.\n"
            "- `fulltext_wordcloud.png`: Word cloud built from `body` texts (or titles if body missing).\n\n"
            f"Parameters used: meeting_date={args.meeting_date}, clusters={args.clusters}\n"
        )

    print("Outputs written to:", args.output_dir)


if __name__ == "__main__":
    main()
