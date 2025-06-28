import httpx
import asyncio
from .embeddings import get_embedding
import logging
import os

# Set logging level to WARNING to suppress info logs
logging.basicConfig(level=logging.WARNING)


async def search_scholar(query: str, num_results=5):
    """
    Searches Semantic Scholar for similar papers and returns top results with embeddings.
    """
    url = "https://api.semanticscholar.org/graph/v1/paper/search"

    params = {
        "query": query,
        "limit": num_results,
        "fields": "title,abstract,year,authors,url,citationCount"
    }

    headers = {
        "x-api-key": os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=20.0)
            response.raise_for_status()

        data = response.json()
        results = data.get("data", [])
        if not results:
            return []

        async def format_and_embed(item):
            title = item.get('title', 'No Title')
            snippet = item.get('abstract', 'No Snippet')
            link = item.get('url', '')

            text_to_embed = f"{title} {snippet}"
            embedding = await get_embedding(text_to_embed)

            return {
                "title": title,
                "snippet": snippet,
                "link": link,
                "authors": [author['name'] for author in item.get('authors', [])],
                "year": item.get('year'),
                "citationCount": item.get('citationCount'),
                "embedding": embedding
            }

        embedded_results = await asyncio.gather(*(format_and_embed(p) for p in results))
        return embedded_results

    except httpx.HTTPStatusError as e:
        logging.error(
            "An HTTP error occurred while searching Semantic Scholar.")
        logging.error(f"Status code: {e.response.status_code}")
        logging.error(f"Response body: {e.response.text}")
        logging.error(f"Response headers: {e.response.headers}")
        return []
    except Exception as e:
        logging.error(
            f"An unexpected error occurred while searching Semantic Scholar: {e}")
        return []
