import httpx
import asyncio
import os
from .embeddings import get_embedding


async def _search_lens_api(query: str, search_type: str, num_results=5):
    """
    Generic search function for the Lens.org API.
    Can search for 'patent' or 'scholar'.
    """
    if search_type not in ['patent', 'scholar']:
        raise ValueError("search_type must be 'patent' or 'scholar'")

    # According to the API documentation, there are separate resources for patent and scholar.
    url = f"https://api.lens.org/{search_type}/search"
    token = os.environ.get("LENS_API_KEY")
    if not token:
        return f"Error: LENS_API_KEY is not set in the environment."

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": {"match_phrase": {"text": query}},
        "size": num_results,
        "include": ["lens_id", "title", "abstract", "url", "publication_type", "authors", "source_urls"]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=20.0)
            response.raise_for_status()

        results = response.json().get("data", [])

        async def format_and_embed(item):
            title = item.get('title', 'No Title')

            if search_type == 'patent':
                snippet = item.get('abstract', 'No Abstract')
                link = f"https://www.lens.org/lens/patent/{item.get('lens_id')}"
            else:  # scholar
                # For scholarly articles, abstract might be inside a nested structure
                abstract_obj = item.get('abstract')
                if isinstance(abstract_obj, dict):
                    snippet = abstract_obj.get('text', 'No Abstract')
                else:
                    snippet = abstract_obj or 'No abstract available'

                # Link can be a direct url or constructed
                source_urls = item.get('source_urls', [])
                link = next((su.get('url') for su in source_urls if su.get('url')),
                            f"https://www.lens.org/lens/scholar/{item.get('lens_id')}")

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
        return f"An HTTP error occurred while searching Lens.org: {e.response.text}"
    except Exception as e:
        return f"An unexpected error occurred while searching Lens.org: {e}"


async def search_lens_patents(query: str, num_results=5):
    """Searches Lens.org for patents."""
    return await _search_lens_api(query, 'patent', num_results)


async def search_lens_academic(query: str, num_results=5):
    """Searches Lens.org for scholarly articles."""
    return await _search_lens_api(query, 'scholar', num_results)
