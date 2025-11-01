#!/usr/bin/env python3
"""
Retrieve English articles about Trump-Xi meetings from the last 3 days using NewsAPI.ai
with full text content, and save to CSV and Markdown files.

Uses NewsAPI.ai (Event Registry) with API key loaded from news-api/.env

Outputs:
- CSV:   showcase/trump_xi_meeting_fulltext.csv
- MD:    showcase/trump_xi_meeting_fulltext.md
"""

import csv
import datetime as dt
import os
import sys
from typing import Any, Dict, List
import time

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


def fetch_articles_newsapi_ai(
    api_key: str,
    *,
    days: int = 3,
    page_size: int = 100,
    max_articles: int = 200,
    sleep_sec: float = 0.2,
) -> List[Dict[str, Any]]:
    """
    Query NewsAPI.ai for English articles with Trump and Xi in title over the given
    number of days. Paginates until max_articles are collected or pages exhausted.
    Includes full body text.
    """
    date_start, date_end = _last_n_days_range(days)

    print(
        "Querying NewsAPI.ai for English articles with Trump and Xi in the TITLE "
        f"from {date_start} to {date_end}..."
    )

    url = "https://newsapi.ai/api/v1/article/getArticles"

    collected: List[Dict[str, Any]] = []
    filtered: List[Dict[str, Any]] = []
    page = 1
    page_size = max(1, min(page_size, 100))
    total_results_reported = None

    while True:
        payload = {
            "query": {
                "$query": {
                    "$and": [
                        {"keyword": "Trump", "keywordLoc": "title"},
                        {"keyword": "Xi", "keywordLoc": "title"},
                    ]
                },
                "$filter": {
                    "forceMaxDataTimeWindow": "31",
                    "dataType": ["news"],
                    "isDuplicateFilter": "skipDuplicates",
                    "lang": ["eng"],
                    "dateStart": date_start,
                    "dateEnd": date_end,
                }
            },
            "resultType": "articles",
            "articlesSortBy": "date",
            "articlesCount": page_size,
            "articlesPage": page,
            "includeArticleTitle": True,
            "includeArticleBasicInfo": True,
            "includeArticleBody": True,
            "includeArticleEventUri": False,
            "includeArticleLinks": False,
            "includeArticleExtractedDates": False,
            "includeArticleCategories": True,
            "includeArticleLocation": True,
            "includeArticleImage": True,
            "includeArticleVideos": False,
            "includeArticleSocialScore": False,
            "includeArticleSentiment": True,
            "includeArticleConcepts": False,
            "includeSourceTitle": True,
            "includeSourceDescription": False,
            "includeSourceLocation": True,
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
        articles_data = data.get("articles", {})
        if total_results_reported is None:
            print(f"Response keys: {list(data.keys())}")
            print(f"Articles data keys: {list(articles_data.keys())}")
            total_results_reported = int(articles_data.get("totalResults", 0) or 0)
            print(f"Total count from API: {total_results_reported}")

        results = articles_data.get("results", [])
        print(f"Page {page}: retrieved {len(results)} articles")

        for a in results:
            # normalize
            title = (a.get("title") or "").strip()
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

            src = a.get("source") or {}
            if isinstance(src, dict):
                source = src.get("title") or src.get("uri") or ""
            else:
                source = str(src)

            url2 = a.get("url") or ""
            published = a.get("dateTime") or a.get("date") or a.get("time") or ""
            body = (a.get("body") or "").strip()
            lang = a.get("lang") or ""
            sentiment = a.get("sentiment") or ""
            if isinstance(sentiment, (int, float)):
                sentiment = str(sentiment)

            row = {
                "title": title,
                "authors": authors,
                "source": source,
                "url": url2,
                "published": published,
                "language": lang,
                "sentiment": sentiment,
                "body": body,
            }
            collected.append(row)

            # Apply client-side filter incrementally so we can stop when target reached
            lang_lc = (lang or "").lower()
            title_lc = title.lower()
            if lang_lc in {"eng", "en"} and ("trump" in title_lc and "xi" in title_lc):
                filtered.append(row)

        # Stop if we've reached our desired filtered total
        if len(filtered) >= max_articles:
            break

        pages_total = int(articles_data.get("pages", 0) or 0)
        current_page = int(articles_data.get("page", page) or page)
        if pages_total and current_page >= pages_total:
            break

        page += 1
        time.sleep(sleep_sec)

    print(f"After client-side filtering (English + title contains Trump & Xi): {len(filtered)} articles")
    return filtered[:max_articles]


def save_csv(rows: List[Dict[str, Any]], path: str) -> None:
    """Save articles with full text to CSV file"""
    fieldnames = ["title", "authors", "source", "url", "published", "language", "sentiment", "body"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: (r.get(k) or "") for k in fieldnames})


def save_md(rows: List[Dict[str, Any]], path: str) -> None:
    """Save articles with full text to Markdown file"""
    lines: List[str] = []
    lines.append("# Trump–Xi Meeting Articles: Last 3 Days (English, Full Text)\n")
    lines.append("")
    if not rows:
        lines.append("No results returned from NewsAPI.ai for the selected window.")
    else:
        lines.append(f"Total articles: {len(rows)}\n")
        lines.append("")
        
        for i, r in enumerate(rows, 1):
            title = r.get("title") or "(no title)"
            source = r.get("source") or "?"
            url = r.get("url") or ""
            authors = r.get("authors") or ""
            published = r.get("published") or ""
            lang = r.get("language") or ""
            sentiment = r.get("sentiment") or ""
            body = r.get("body") or ""
            
            lines.append(f"## {i}. {title}\n")
            lines.append(f"**Source:** {source}  ")
            if authors:
                lines.append(f"**Authors:** {authors}  ")
            if published:
                lines.append(f"**Published:** {published}  ")
            if lang:
                lines.append(f"**Language:** {lang}  ")
            if sentiment:
                lines.append(f"**Sentiment:** {sentiment}  ")
            if url:
                lines.append(f"**URL:** [{url}]({url})  ")
            lines.append("")
            
            if body:
                lines.append("**Full Text:**\n")
                lines.append(body)
                lines.append("")
            
            lines.append("---\n")

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
        # Parse CLI options before fetching to allow tuning
        import argparse
        parser = argparse.ArgumentParser(description="Retrieve Trump–Xi articles (English, full text)")
        parser.add_argument(
            "--output-csv",
            dest="output_csv",
            default=os.path.join(SHOWCASE_DIR, "trump_xi_meeting_fulltext.csv"),
            help="Path to write CSV output",
        )
        parser.add_argument(
            "--output-md",
            dest="output_md",
            default=os.path.join(SHOWCASE_DIR, "trump_xi_meeting_fulltext.md"),
            help="Path to write Markdown output",
        )
        parser.add_argument(
            "--no-md",
            dest="no_md",
            action="store_true",
            help="Skip writing Markdown output",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=3,
            help="How many days back to search (default 3)",
        )
        parser.add_argument(
            "--page-size",
            type=int,
            default=100,
            help="Articles per page to request (max 100)",
        )
        parser.add_argument(
            "--max-articles",
            type=int,
            default=200,
            help="Maximum number of articles to collect",
        )
        args = parser.parse_args()

        articles = fetch_articles_newsapi_ai(
            api_key,
            days=args.days,
            page_size=args.page_size,
            max_articles=args.max_articles,
        )
    except Exception as e:
        sys.stderr.write(f"NewsAPI.ai error: {e}\n")
        articles = []

    # Use args parsed above

    csv_path = args.output_csv
    md_path = args.output_md

    # Ensure target directory exists
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    save_csv(articles, csv_path)
    if not args.no_md:
        os.makedirs(os.path.dirname(md_path), exist_ok=True)
        save_md(articles, md_path)

    print(f"\nSaved CSV: {csv_path}")
    if not args.no_md:
        print(f"Saved MD:  {md_path}")
    print(f"Total articles saved: {len(articles)}")
    
    # Show summary statistics
    if articles:
        print(f"\nLanguages: {set(a.get('language', '') for a in articles if a.get('language'))}")
        with_body = sum(1 for a in articles if a.get('body'))
        print(f"Articles with full text: {with_body}/{len(articles)}")


if __name__ == "__main__":
    main()
