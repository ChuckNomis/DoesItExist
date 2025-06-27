import httpx
import asyncio
import json
from .embeddings import get_embedding
import logging
import os

logging.basicConfig(level=logging.INFO)


async def search_patent(query: str, num_results=5):
    """
    Searches PatentView for similar patents and returns top results with embeddings.
    """
    url = "https://search.patentsview.org/api/v1/patent/"

    # Query for patents where the title or abstract contains any of the query words
    q = {
        "_or": [
            {"_text_any": {"patent_title": query}},
            {"_text_any": {"patent_abstract": query}}
        ]
    }

    # Fields to retrieve
    f = [
        "patent_number",
        "patent_title",
        "patent_abstract",
        "patent_date",
        "inventors"
    ]

    # Options for the query, including the number of results
    o = {"size": num_results}

    # Parameters for the POST request
    params = {
        "q": q,
        "f": f,
        "o": o
    }

    headers = {
        "X-Api-Key": os.getenv("PATENTSVIEW_API_KEY")
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=params, headers=headers, timeout=20.0)
            response.raise_for_status()

        data = response.json()
        results = data.get("patents", [])
        if not results:
            return []

        async def format_and_embed(item):
            title = item.get('patent_title', 'No Title')
            snippet = item.get('patent_abstract', 'No Snippet')
            pn = item.get('patent_number', '')
            link = f"https://patents.google.com/patent/US{pn}/en" if pn else ""

            text_to_embed = f"{title} {snippet}"
            embedding = await get_embedding(text_to_embed)

            return {
                "title": title,
                "snippet": snippet,
                "link": link,
                "embedding": embedding
            }

        embedded_results = await asyncio.gather(*(format_and_embed(p) for p in results))
        return embedded_results

    except httpx.HTTPStatusError as e:
        logging.error("An HTTP error occurred while searching PatentView.")
        logging.error(f"Status code: {e.response.status_code}")
        logging.error(f"Response body: {e.response.text}")
        logging.error(f"Response headers: {e.response.headers}")
        return []
    except Exception as e:
        logging.error(
            f"An unexpected error occurred while searching PatentView: {e}")
        return []
