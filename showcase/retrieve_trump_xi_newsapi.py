#!/usr/bin/env python3
"""
Retrieve articles about Trump and Xi from the last 3 days using NewsAPI.ai
and save to CSV, then generate a brief Markdown summary file in the showcase folder.

Uses NewsAPI.ai (Event Registry) with API key loaded from news-api/.env

Outputs:
- CSV:   showcase/trump_xi_last3days_newsapi.csv
- MD:    showcase/trump_xi_last3days_newsapi.md
"""

import csv
import datetime as dt
import os
import sys
from typing import Any, Dict, List

import requests

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None


SHOWCASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SHOWCASE_DIR, os.pardir))
ENV_PATH = os.path.join(REPO_ROOT, "news-api", ".env")


def _load_api_key() -> str:
    """Load NewsAPI.ai API key from news-api/.env"""
    if load_dotenv:
        try:
            load_dotenv(ENV_PATH)
        except Exception:
            pass
    
    key = os.getenv("NEWSAPI_AI_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "Missing NEWSAPI_AI_API_KEY. Add it to news-api/.env or your environment."
        )
    return key


def _date_str(d: dt.date) -> str:
    """Format date as YYYY-MM-DD for NewsAPI.ai"""
    return d.strftime("%Y-%m-%d")


def _last_n_days_range(n_days: int = 3) -> tuple[str, str]:
    """Get date range for last N days"""
    today = dt.datetime.now(dt.UTC).date()
    start = today - dt.timedelta(days=max(0, n_days))
    return _date_str(start), _date_str(today)


def fetch_articles_newsapi_ai(api_key: str, count: int = 100) -> List[Dict[str, Any]]:
    """
    Query NewsAPI.ai (Event Registry) for articles mentioning both Trump and Xi
    within the last 3 days, English language, sorted by date.
    
    Based on NewsAPI.ai documentation: https://newsapi.ai/documentation
    """
    date_start, date_end = _last_n_days_range(3)
    
    print(f"Querying NewsAPI.ai for articles from {date_start} to {date_end}...")

    url = "https://newsapi.ai/api/v1/article/getArticles"

    # Build query according to NewsAPI.ai documentation
    payload = {
        "query": {
            "$query": {
                "$and": [
                    {"keyword": "Trump", "keywordLoc": "body"},
                    {"keyword": "Xi", "keywordLoc": "body"},
                ]
            },
            "$filter": {
                "forceMaxDataTimeWindow": "31",
                "dataType": ["news", "blog"],
                "isDuplicateFilter": "skipDuplicates"
            }
        },
        "resultType": "articles",
        "articlesSortBy": "date",
        "articlesCount": max(1, min(count, 100)),
        "articlesPage": 1,
        "includeArticleTitle": True,
        "includeArticleBasicInfo": True,
        "includeArticleBody": False,
        "includeArticleEventUri": False,
        "includeArticleLinks": False,
        "includeArticleExtractedDates": False,
        "includeArticleCategories": False,
        "includeArticleLocation": False,
        "includeArticleImage": False,
        "includeArticleVideos": False,
        "includeArticleSocialScore": False,
        "includeArticleSentiment": False,
        "includeArticleConcepts": False,
        "includeSourceTitle": True,
        "includeSourceDescription": False,
        "includeSourceLocation": False,
        "includeSourceRanking": False,
        "includeConceptLabel": False,
        "includeConceptImage": False,
        "includeConceptSynonyms": False,
        "apiKey": api_key,
    }

    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
    except requests.HTTPError as e:
        sys.stderr.write(f"HTTP error {r.status_code}: {r.text}\n")
        raise e

    data = r.json()
    
    # Debug: print response structure
    print(f"Response keys: {list(data.keys())}")
    
    # NewsAPI.ai structure: { "articles": { "results": [ ... ] } }
    articles_data = data.get("articles", {})
    print(f"Articles data keys: {list(articles_data.keys())}")
    print(f"Total count from API: {articles_data.get('totalResults', 0)}")
    
    articles = articles_data.get("results", [])
    print(f"Retrieved {len(articles)} articles")

    normalized: List[Dict[str, Any]] = []
    for a in articles:
        title = (a.get("title") or "").strip()
        
        # Authors may be a list of author objects
        authors_raw = a.get("authors") or []
        if isinstance(authors_raw, list):
            authors = ", ".join(
                [
                    (str(auth.get("name") if isinstance(auth, dict) else auth) or "").strip()
                    for auth in authors_raw
                    if auth is not None
                ]
            )
        else:
            authors = str(authors_raw).strip()

        # Source information
        src = a.get("source") or {}
        if isinstance(src, dict):
            source = src.get("title") or src.get("uri") or ""
        else:
            source = str(src)

        url = a.get("url") or ""
        
        # Date/time fields
        published = a.get("dateTime") or a.get("date") or a.get("time") or ""

        normalized.append(
            {
                "title": title,
                "authors": authors,
                "source": source,
                "url": url,
                "published": published,
            }
        )

    return normalized


def save_csv(rows: List[Dict[str, Any]], path: str) -> None:
    """Save articles to CSV file"""
    fieldnames = ["title", "authors", "source", "url", "published"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: (r.get(k) or "") for k in fieldnames})


def save_md(rows: List[Dict[str, Any]], path: str) -> None:
    """Save articles summary to Markdown file"""
    lines: List[str] = []
    lines.append("# Trump–Xi Articles: Last 3 Days (NewsAPI.ai)\n")
    lines.append("")
    if not rows:
        lines.append("No results returned from NewsAPI.ai for the selected window.")
    else:
        lines.append(f"Total articles: {len(rows)}\n")
        lines.append("")
        lines.append("## Headlines\n")
        for i, r in enumerate(rows, 1):
            title = r.get("title") or "(no title)"
            source = r.get("source") or "?"
            url = r.get("url") or ""
            authors = r.get("authors") or ""
            published = r.get("published") or ""
            bullet = f"{i}. [{title}]({url}) — {source}"
            if authors:
                bullet += f" — {authors}"
            if published:
                bullet += f" — {published}"
            lines.append(bullet)

    content = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    # Load API key
    try:
        api_key = _load_api_key()
    except SystemExit as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Fetch articles from NewsAPI.ai
    try:
        articles = fetch_articles_newsapi_ai(api_key)
    except Exception as e:
        sys.stderr.write(f"NewsAPI.ai error: {e}\n")
        articles = []

    # Save results
    csv_path = os.path.join(SHOWCASE_DIR, "trump_xi_last3days_newsapi.csv")
    md_path = os.path.join(SHOWCASE_DIR, "trump_xi_last3days_newsapi.md")

    save_csv(articles, csv_path)
    save_md(articles, md_path)

    print(f"\nSaved CSV: {csv_path}")
    print(f"Saved MD:  {md_path}")
    print(f"Total articles saved: {len(articles)}")


if __name__ == "__main__":
    main()
