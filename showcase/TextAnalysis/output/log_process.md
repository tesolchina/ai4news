# What we did (plain-language summary)

This short note explains what we analyzed, how we did it, and how to read the results. No technical background needed.

## What is this about?
We looked at news coverage around the Trump–Xi meeting. The goal was to quickly understand:
- How much coverage there was over time, and which outlets published the most
- What kinds of headlines appeared (grouped into a few common themes)
- Which words and short phrases are most prominent in the full articles

## What we used
- Input data: a spreadsheet of articles called `trump_xi_meeting_fulltext_dedup.csv` (titles, dates, sources, and full text)
- Meeting date considered: 2025-10-30
- Number of headline themes (clusters): 5

## What we produced (open these files)
- basic_stats.png — A three-part picture showing:
  1) Articles per day (with a vertical line marking the meeting date)
  2) Top news sources by number of articles
  3) Counts of stories before, on, and after the meeting
- title_clusters.png — A bar chart showing the size of each headline theme. Themes are labeled by the most important words found in their titles.
- titles_with_clusters.csv — A spreadsheet with every article and the theme it was assigned to.
- fulltext_wordcloud.png — A word cloud from the article texts, highlighting important words and short phrases. We filtered out generic words (like “year”) and single-letter tokens (like “S”, “U”) to keep it readable.

All files are here: this same folder (`showcase/TextAnalysis/output`).

## Quick facts (from the dataset we analyzed)
- Total articles: 1,657
- Unique sources: 614
- Date range (published): 2025-10-30T02:22:28Z to 2025-11-01T02:28:39Z (UTC)

## Search criteria (how the articles were gathered)
Based on the retrieval scripts and notes in `showcase/README_trump_xi_files.md`:
- Source: NewsAPI.ai (Event Registry)
- Time window: last 3 days (rolling)
- Language: English only
- Keywords: articles mentioning both “Trump” AND “Xi”; for the full‑text set we focused on meeting context (e.g., “meeting” OR “meet” OR “summit”) where possible
- Content: Full article text included when available; duplicates were removed before analysis

## How to read the visuals
- basic_stats.png: 
  - Left: Spikes show days with more articles. The red dashed line marks the meeting date, so you can compare activity before/after.
  - Middle: Which outlets most frequently covered the story.
  - Right: How many articles were published before, on, and after the meeting.
- title_clusters.png:
  - Bars show how many headlines fell into each theme. The theme labels are built from the most characteristic words found in those headlines.
- fulltext_wordcloud.png:
  - Bigger words/phrases appeared more often across all articles. We included phrases and removed unhelpful words and single letters.

## What to keep in mind
- Automated grouping (themes) is a quick way to get the big picture, but labels are shorthand. They’re not manually curated.
- Word clouds reflect frequency, not importance or accuracy. They are best for a fast feel of common language.
- The input data drives the results. Missing or duplicated articles would affect the pictures.

## If you want changes
Tell us if you’d like any of these tweaks:
- More or fewer headline themes
- Add/remove specific words from the word cloud
- Focus on a narrower time window or specific outlets
- Export an easy-to-read summary spreadsheet

## Who to ask
If anything is unclear or you want a slightly different view, let us know what decision you’re trying to make, and we’ll tailor the visuals accordingly.
