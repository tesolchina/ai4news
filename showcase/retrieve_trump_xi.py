#!/usr/bin/env python3
"""
Retrieve articles about the Trump–Xi meeting from the last 3 days and save to CSV,
then generate a brief Markdown summary file in the showcase folder.

Defaults to using NewsAPI.ai (Event Registry) with API key loaded from news-api/.env
via python-dotenv. If the provider responds with an error, the script will surface
the HTTP error message for troubleshooting.

Outputs:
- CSV:   showcase/trump_xi_last3days.csv
- MD:    showcase/trump_xi_last3days.md
"""

import csv
import datetime as dt
import os
import sys
from typing import Any, Dict, List
import urllib.parse
import xml.etree.ElementTree as ET

import requests

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None


SHOWCASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SHOWCASE_DIR, os.pardir))
ENV_PATH = os.path.join(REPO_ROOT, "news-api", ".env")
ENV_ALT_PATHS = [
    os.path.join(REPO_ROOT, "jour3105", ".env"),
]


def _load_api_key() -> str:
    # Load env file explicitly from news-api/.env if python-dotenv is available
    if load_dotenv:
        try:
            load_dotenv(ENV_PATH)
        except Exception:
            # fallback: try default discovery
            try:
                load_dotenv()
            except Exception:
                pass
        # also try alternate env files, if present
        for p in ENV_ALT_PATHS:
            if os.path.exists(p):
                try:
                    load_dotenv(p)
                except Exception:
                    pass
    key = os.getenv("NEWSAPI_AI_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "Missing NEWSAPI_AI_API_KEY. Add it to news-api/.env or your environment."
        )
    return key


def _date_str(d: dt.date) -> str:
    # NewsAPI.ai typically accepts YYYY-MM-DD for dateStart/dateEnd
    return d.strftime("%Y-%m-%d")


def _last_n_days_range(n_days: int = 3) -> tuple[str, str]:
    today = dt.datetime.now(dt.UTC).date()
    start = today - dt.timedelta(days=max(0, n_days))
    return _date_str(start), _date_str(today)


def fetch_articles_newsapi_ai(api_key: str, count: int = 100) -> List[Dict[str, Any]]:
    """
    Query NewsAPI.ai (Event Registry) for articles mentioning both Trump and Xi
    within the last 3 days, English language, sorted by date.

    Note: Endpoint/JSON format are based on common Event Registry usage patterns.
    Adjust if your plan_explore confirms different fields.
    """
    date_start, date_end = _last_n_days_range(3)

    url = "https://newsapi.ai/api/v1/article/getArticles"

    # Build a query that matches both keywords; keywordLoc 'title' biases for titles.
    payload = {
        "query": {
            "$query": {
                "$and": [
                    {"keyword": "Trump", "keywordLoc": "title"},
                    {"keyword": "Xi", "keywordLoc": "title"},
                ]
            },
            "lang": "eng",
            "dateStart": date_start,
            "dateEnd": date_end,
        },
        "resultType": "articles",
        "articles": {
            "page": 1,
            "count": max(1, min(count, 200)),
            "sortBy": "date",
            "sortByAsc": False,
        },
    }

    headers = {
        "Accept": "application/json",
        # Many implementations accept this header; if your account expects a query param,
        # switch to passing apiKey in the params instead.
        "X-API-Key": api_key,
    }

    # Some deployments require apiKey as a query param; include it redundantly for compatibility.
    params = {"apiKey": api_key}

    r = requests.post(url, json=payload, headers=headers, params=params, timeout=60)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        # Provide server response text to aid debugging without exposing secrets
        sys.stderr.write(f"HTTP error {r.status_code}: {r.text}\n")
        raise e

    data = r.json()

    # Typical structure: { "articles": { "results": [ ... ] } }
    articles = (
        (data or {}).get("articles", {})
        .get("results", [])
    )

    normalized: List[Dict[str, Any]] = []
    for a in articles:
        title = (a.get("title") or "").strip()
        # Authors may be a list of strings or objects; be defensive
        authors_raw = a.get("authors") or a.get("author")
        if isinstance(authors_raw, list):
            authors = ", ".join(
                [
                    (str(x.get("name") if isinstance(x, dict) else x) or "").strip()
                    for x in authors_raw
                    if x is not None
                ]
            )
        else:
            authors = (authors_raw or "").strip()

        # Source may be object or string
        src = a.get("source") or a.get("sourceUri") or a.get("dataSource")
        if isinstance(src, dict):
            source = src.get("title") or src.get("name") or src.get("uri") or ""
        else:
            source = src or ""

        url = a.get("url") or a.get("link") or ""
        published = a.get("dateTime") or a.get("date") or a.get("publishedAt") or ""

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


def fetch_articles_newsapi_org(api_key: str, count: int = 100) -> List[Dict[str, Any]]:
    """
    Fallback provider: NewsAPI.org everything endpoint with date filter.
    Requires NEWSAPI_API_KEY set (e.g., in jour3105/.env or user env).
    """
    date_start, _date_end = _last_n_days_range(3)
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "Trump AND Xi",
        "from": date_start,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": max(1, min(count, 100)),
        "apiKey": api_key,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    articles = data.get("articles", [])
    out: List[Dict[str, Any]] = []
    for a in articles:
        src = (a.get("source") or {}).get("name") or ""
        out.append(
            {
                "title": (a.get("title") or "").strip(),
                "authors": (a.get("author") or "").strip(),
                "source": src,
                "url": a.get("url") or "",
                "published": a.get("publishedAt") or "",
            }
        )
    return out


def fetch_articles_google_news_rss(count: int = 100) -> List[Dict[str, Any]]:
    """
    Public fallback: Google News RSS for the last 3 days, no API key required.
    Query uses `when:3d` to limit to a 3-day window.
    """
    # Build query and feed URL
    q = urllib.parse.quote("Trump Xi when:3d")
    feed_url = (
        "https://news.google.com/rss/search?q="
        f"{q}&hl=en-US&gl=US&ceid=US:en"
    )

    r = requests.get(feed_url, timeout=30)
    r.raise_for_status()

    # Parse RSS XML
    root = ET.fromstring(r.content)
    items = root.findall(".//item")

    results: List[Dict[str, Any]] = []
    for it in items[: max(1, min(count, 100))]:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub_date = (it.findtext("pubDate") or "").strip()
        source_el = it.find("source")
        source = source_el.text.strip() if source_el is not None and source_el.text else "Google News"

        results.append(
            {
                "title": title,
                "authors": "",
                "source": source,
                "url": link,
                "published": pub_date,
            }
        )

    return results


def save_csv(rows: List[Dict[str, Any]], path: str) -> None:
    fieldnames = ["title", "authors", "source", "url", "published"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: (r.get(k) or "") for k in fieldnames})


def save_md(rows: List[Dict[str, Any]], path: str) -> None:
    lines: List[str] = []
    lines.append("# Trump–Xi meeting: last 3 days\n")
    lines.append("")
    if not rows:
        lines.append("No results returned from the API for the selected window.")
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
    articles: List[Dict[str, Any]] = []

    # Try primary: NewsAPI.ai (Event Registry) if key present
    api_key = os.getenv("NEWSAPI_AI_API_KEY", "").strip()
    if not api_key:
        try:
            api_key = _load_api_key()
        except SystemExit:
            api_key = ""

    if api_key:
        try:
            articles = fetch_articles_newsapi_ai(api_key)
        except Exception as e:
            sys.stderr.write(f"Primary provider error: {e}\n")

    # Fallback 1: NewsAPI.org if key present and still empty
    if not articles:
        fallback_key = os.getenv("NEWSAPI_API_KEY", "").strip()
        if fallback_key:
            try:
                print("Trying NewsAPI.org fallback...")
                articles = fetch_articles_newsapi_org(fallback_key)
            except Exception as e:
                sys.stderr.write(f"NewsAPI.org fallback error: {e}\n")

    # Fallback 2: Google News RSS (no key required)
    if not articles:
        try:
            print("Trying Google News RSS fallback (no API key)...")
            articles = fetch_articles_google_news_rss()
        except Exception as e:
            sys.stderr.write(f"Google News RSS fallback error: {e}\n")

    csv_path = os.path.join(SHOWCASE_DIR, "trump_xi_last3days.csv")
    md_path = os.path.join(SHOWCASE_DIR, "trump_xi_last3days.md")

    save_csv(articles, csv_path)
    save_md(articles, md_path)

    print(f"Saved CSV: {csv_path}")
    print(f"Saved MD:  {md_path}")


if __name__ == "__main__":
    main()
