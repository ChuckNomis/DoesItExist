import httpx
import asyncio
import json
from .embeddings import get_embedding
import logging
import os

# Set logging level to WARNING to suppress info logs
logging.basicConfig(level=logging.WARNING)


async def search_patent(query: str, num_results=5, state=None):
    """
    Searches PatentView for similar patents and returns top results with embeddings.
    Uses improved search strategy with multiple approaches and relevance sorting.
    """
    if state is None:
        state = {}
    invocation_count = state.get('tool_invocation_count', {})

    url = "https://search.patentsview.org/api/v1/patent/"

    # Extract key terms from the query for better searching
    # Remove common stop words and clean the query
    stop_words = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
                  'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
                  'to', 'was', 'will', 'with', 'using', 'device', 'system', 'method'}

    query_words = [word.lower().strip() for word in query.split()
                   if word.lower().strip() not in stop_words and len(word.strip()) > 2]

    # Create a multi-strategy search query
    # Strategy 1: Phrase search for the most important terms
    # Strategy 2: All words search for key terms
    # Strategy 3: Any words search as fallback

    search_strategies = []

    # Strategy 1: If we have 2-4 key words, try phrase search
    if 2 <= len(query_words) <= 4:
        key_phrase = " ".join(query_words[:3])  # Use first 3 words as phrase
        search_strategies.append({
            "_or": [
                {"_text_phrase": {"patent_title": key_phrase}},
                {"_text_phrase": {"patent_abstract": key_phrase}}
            ]
        })

    # Strategy 2: All key words must be present
    if len(query_words) >= 2:
        key_terms = " ".join(query_words[:5])  # Use up to 5 key words
        search_strategies.append({
            "_or": [
                {"_text_all": {"patent_title": key_terms}},
                {"_text_all": {"patent_abstract": key_terms}}
            ]
        })

    # Strategy 3: Any of the key words (but require at least 2 matches for better relevance)
    if len(query_words) >= 3:
        important_terms = " ".join(query_words[:6])  # Use up to 6 terms
        search_strategies.append({
            "_or": [
                {"_text_any": {"patent_title": important_terms}},
                {"_text_any": {"patent_abstract": important_terms}}
            ]
        })

    # Fallback: If no strategies work, use the original query
    if not search_strategies:
        search_strategies.append({
            "_or": [
                {"_text_any": {"patent_title": query}},
                {"_text_any": {"patent_abstract": query}}
            ]
        })

    # Fields to retrieve - using correct field names per official API documentation
    f = [
        "patent_id",         # Official API field name for patent number
        "patent_title",
        "patent_abstract",
        "patent_date",
        "inventors",
        "patent_num_times_cited_by_us_patents"  # For relevance scoring
    ]

    # Try each strategy in order of preference
    results = []
    headers = {
        "X-Api-Key": os.getenv("PATENTSVIEW_API_KEY")
    }

    for i, q_strategy in enumerate(search_strategies):
        try:
            # Sort by citation count (more cited = more relevant) and recent date
            s = [
                {"patent_num_times_cited_by_us_patents": "desc"},
                {"patent_date": "desc"}
            ]

            # Options for the query - get more results to filter better ones
            # Get 3x results to filter best ones
            o = {"size": min(num_results * 3, 50)}

            # Parameters for the POST request
            params = {
                "q": q_strategy,
                "f": f,
                "s": s,
                "o": o
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=params, headers=headers, timeout=20.0)
                response.raise_for_status()

            data = response.json()
            strategy_results = data.get("patents", [])

            if strategy_results:
                # Remove info logs for strategy results
                # logging.info(f"Strategy {i+1} found {len(strategy_results)} results")
                # logging.info(f"Strategy {i+1} returned no results")
                results = strategy_results
                break  # Use the first strategy that returns results
            else:
                # Remove info logs for strategy results
                # logging.info(f"Strategy {i+1} returned no results")
                continue

        except Exception as e:
            logging.warning(f"Strategy {i+1} failed: {e}")
            continue

    if not results:
        logging.warning("All search strategies failed or returned no results")
        return []

    # Filter and rank results based on relevance
    def calculate_relevance_score(patent):
        """Calculate a simple relevance score based on query terms in title/abstract"""
        title = (patent.get('patent_title') or '').lower()
        abstract = (patent.get('patent_abstract') or '').lower()

        # Count query word matches
        title_matches = sum(1 for word in query_words if word in title)
        abstract_matches = sum(1 for word in query_words if word in abstract)

        # Weight title matches higher than abstract matches
        score = (title_matches * 3) + (abstract_matches * 1)

        # Bonus for citation count (popular patents are more likely to be relevant)
        citations = patent.get('patent_num_times_cited_by_us_patents') or 0
        if isinstance(citations, (int, float)) and citations > 0:
            score += min(citations / 10, 5)  # Cap bonus at 5 points

        return score

    # Score and sort results
    scored_results = [(calculate_relevance_score(p), p) for p in results]
    scored_results.sort(key=lambda x: x[0], reverse=True)

    # Take the best results
    best_results = [p for score,
                    p in scored_results[:num_results] if score > 0]

    # If we don't have enough good results, take the top ones anyway
    if len(best_results) < num_results:
        best_results = [p for score, p in scored_results[:num_results]]

    async def format_and_embed(item):
        title = item.get('patent_title', 'No Title')
        snippet = item.get('patent_abstract', 'No Snippet')
        patent_id = item.get('patent_id', '')  # Using correct field name
        link = f"https://patents.google.com/patent/US{patent_id}/en" if patent_id else ""

        text_to_embed = f"{title} {snippet}"
        embedding = await get_embedding(text_to_embed)

        return {
            "title": title,
            "snippet": snippet,
            "link": link,
            "embedding": embedding
        }

    try:
        embedded_results = await asyncio.gather(*(format_and_embed(p) for p in best_results))
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

    # Add a warning log for potential spamming
    # Assuming 5 is a threshold for spamming
    if invocation_count.get('search_patent', 0) > 5:
        logging.warning(
            f"Potential spamming detected for tool 'search_patent' from IP: {get_remote_address(request)}")
