# Trump-Xi News Retrieval Scripts and Data

This directory contains multiple scripts for retrieving news articles about Trump and Xi using different approaches and filters.

## Scripts

### 1. `retrieve_trump_xi.py` (Original - Multi-fallback)
- **Primary source:** NewsAPI.ai
- **Fallbacks:** NewsAPI.org → Google News RSS
- **Language:** All languages
- **Content:** Basic metadata only (no full text)
- **Outputs:**
  - `trump_xi_last3days.csv` (43K)
  - `trump_xi_last3days.md` (44K)

### 2. `retrieve_trump_xi_newsapi.py` (NewsAPI.ai only)
- **Source:** NewsAPI.ai exclusively (no fallbacks)
- **Language:** All languages
- **Content:** Basic metadata only (no full text)
- **Query:** Articles mentioning both "Trump" AND "Xi"
- **Outputs:**
  - `trump_xi_last3days_newsapi.csv` (23K)
  - `trump_xi_last3days_newsapi.md` (25K)
- **Results:** 100 articles from 92,890 total matches

### 3. `retrieve_trump_xi_fulltext.py` (English + Full Text) ⭐ **RECOMMENDED**
- **Source:** NewsAPI.ai exclusively
- **Language:** **English only**
- **Content:** **Full article body text included**
- **Query:** Articles mentioning "Trump" AND "Xi" AND ("meeting" OR "meet" OR "summit")
- **Outputs:**
  - `trump_xi_meeting_fulltext.csv` (228K)
  - `trump_xi_meeting_fulltext.md` (238K)
- **Results:** 50 articles from 35,634 total matches
- **Features:**
  - All articles in English (language: eng)
  - Full body text (average 4,400 characters per article)
  - Sentiment analysis included
  - Focus on meeting/summit-related content
  - 45/50 articles mention "meeting"
  - 47/50 articles mention "meet"
  - 26/50 articles mention "summit"

## CSV Structure

### Basic metadata (scripts 1 & 2):
```
title, authors, source, url, published
```

### Full text version (script 3):
```
title, authors, source, url, published, language, sentiment, body
```

## Usage

### Run the full text English version (recommended):
```bash
cd /workspaces/ai4news/showcase
python retrieve_trump_xi_fulltext.py
```

### Run the NewsAPI.ai only version:
```bash
cd /workspaces/ai4news/showcase
python retrieve_trump_xi_newsapi.py
```

### Run the original multi-fallback version:
```bash
cd /workspaces/ai4news/showcase
python retrieve_trump_xi.py
```

## Requirements

Install dependencies:
```bash
pip install -r requirements.txt
```

Required packages:
- `requests>=2.31.0`
- `python-dotenv>=1.0.1`

## API Key Setup

The scripts require a NewsAPI.ai API key stored in `/workspaces/ai4news/news-api/.env`:

```
NEWSAPI_AI_API_KEY=your_key_here
```

## Date Range

All scripts retrieve articles from the **last 3 days** by default.

## Generated on
November 1, 2025
