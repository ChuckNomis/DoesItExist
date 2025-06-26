import asyncio
from langchain_tavily import TavilySearch
from .embeddings import get_embedding


async def get_web_search_results(query: str, max_results=10):
    """
    Uses Tavily to perform an async web search and embeds the results.
    """
    search = TavilySearch(max_results=max_results)
    try:
        # TavilySearch returns a dictionary with a 'results' key
        response = await search.ainvoke({"query": query})
        results = response.get("results", [])

        async def format_and_embed(result):
            # Each result is a dictionary, extract content for embedding
            text_to_embed = result.get('content', '')
            if not text_to_embed:
                return None

            embedding = await get_embedding(text_to_embed)
            return {
                "title": result.get('title', 'No Title'),
                "snippet": result.get('content', ''),
                "link": result.get('url', '#'),
                "embedding": embedding
            }

        # Filter out None results from formatting
        embedded_results = filter(None, await asyncio.gather(*(format_and_embed(r) for r in results)))
        return list(embedded_results)
    except Exception as e:
        # Handle cases where the search might fail
        print(f"An error occurred during web search: {e}")
        return []
