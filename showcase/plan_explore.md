# Plan for Exploring NewsAPI.ai

## Goal
Explore the NewsAPI.ai using the API key in `/workspaces/ai4news/news-api/.env` to search for news articles about Trump and Xi meeting in South Korea. The aim is to understand what metadata and content (full text, etc.) are available from the API before deciding on specific search strategies.

## Steps

1. **Review API Documentation**
   - Reference: [NewsAPI.ai Documentation](https://newsapi.ai/documentation?tab=introduction)
   - Confirm endpoint for article search and authentication method (likely header `X-API-Key`).

2. **Set Up Environment**
   - Ensure API key is present in `/workspaces/ai4news/news-api/.env`.
   - Use Python and `requests` (with `python-dotenv` for loading the key).

3. **Draft Minimal Search Script**
   - Search for articles with keywords: `Trump`, `Xi`, `South Korea`.
   - Use parameters for language (`en`), and limit results (e.g., 10 articles).
   - Print out available metadata and content fields for each article.

4. **Inspect API Response**
   - Identify available fields: headline, summary, full text, publication date, source, entities, sentiment, etc.
   - Note any limitations (e.g., partial text, missing fields).

5. **Document Findings**
   - Summarize what metadata and content are available.
   - List possible next steps for more targeted searches (e.g., by date, source, sentiment).

## Next Steps
- After initial exploration, decide on specific queries or filters to use for deeper analysis.
- Consider saving results to a file for further review.

---

**References:**
- API key location: `/workspaces/ai4news/news-api/.env`
- Usage notes: `/workspaces/ai4news/news-api/NEWSAPI_AI.md`
- API docs: https://newsapi.ai/documentation?tab=introduction
