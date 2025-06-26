from utils.similarity import calculate_cosine_similarity
from services.embeddings import get_embedding
from services.search_lens import search_lens_academic, search_lens_patents
from services.search_web import get_web_search_results
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add the project root to the system path
sys.path.append(str(Path(__file__).parent.parent))


# Import async services
# from services.search_products import search_products_on_website # This was a mock

# Initialize the async model
llm = ChatOpenAI(model="gpt-4o", temperature=0)


class ParsedIdea(BaseModel):
    """Structured representation of a parsed idea."""
    summary: str = Field(...,
                         description="A concise summary of the invention idea.")
    keywords: list[str] = Field(
        ..., description="A list of keywords relevant to the invention idea.")


@tool
async def parse_idea(state: dict) -> dict:
    """
    Parses the user's invention idea to extract a summary and keywords.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert at understanding invention ideas. Your task is to parse the user's idea into a structured format. Extract a concise summary and a list of relevant keywords."),
        ("human", "Here is the invention idea:\n\n{idea}")
    ])
    structured_llm = llm.with_structured_output(ParsedIdea)
    chain = prompt | structured_llm
    result = await chain.ainvoke({"idea": state['original_idea']})
    return {"parsed": result.dict()}


@tool
async def embed_idea(state: dict) -> dict:
    """
    Generates an embedding for the parsed idea.
    """
    summary = state.get("parsed", {}).get("summary")
    if not summary:
        return {"embedding": None}
    embedding = await get_embedding(summary)
    return {"embedding": embedding}


@tool
async def search_patents(state: dict) -> dict:
    """
    Searches for patents based on the parsed idea using the Lens.org API.
    """
    # Temporarily disabled due to API key permissions.
    current_results = state.get("search_results", {})
    current_results["patents"] = "Patent search is disabled. Please ensure you have an active Patent API subscription on Lens.org."
    return {"search_results": current_results}


@tool
async def search_academic(state: dict) -> dict:
    """Searches academic papers."""
    # Temporarily disabled due to API key permissions.
    current_results = state.get("search_results", {})
    current_results["academic"] = "Scholarly search is disabled. Please ensure your Lens.org API key is approved for scholarly search."
    return {"search_results": current_results}


@tool
async def search_web(state: dict) -> dict:
    """
    Searches the web for information related to the parsed idea.
    """
    summary = state.get("parsed", {}).get("summary")
    if not summary:
        return {"search_results": {"web": "No summary to search."}}
    results = await get_web_search_results(summary)
    current_results = state.get("search_results", {})
    current_results["web"] = results
    return {"search_results": current_results}


@tool
async def compare_similarity(state: dict) -> dict:
    """
    Compares the similarity between the user's idea and the search results.
    """
    idea_embedding = state.get("embedding")
    if not idea_embedding:
        return {"matches": []}

    search_results = state.get("search_results", {})
    all_matches = []
    SIMILARITY_THRESHOLD = 0.5

    for source, results in search_results.items():
        if not isinstance(results, list):
            continue
        for result in results:
            result_embedding = result.get('embedding')
            if result_embedding:
                similarity = calculate_cosine_similarity(
                    idea_embedding, result_embedding)
                if similarity > SIMILARITY_THRESHOLD:
                    all_matches.append({
                        "type": source,
                        "details": result,
                        "similarity": similarity
                    })

    sorted_matches = sorted(
        all_matches, key=lambda x: x['similarity'], reverse=True)
    return {"matches": sorted_matches}


@tool
async def summarize_results(state: dict) -> dict:
    """
    Summarizes the findings and provides a final verdict based on a structured output spec.
    """
    original_idea = state.get("original_idea", "No original idea provided.")
    matches = state.get("matches", [])

    if not matches:
        return {"verdict": "Verdict: Likely original\n\nNo similar inventions, products, or academic papers were found. The idea appears to be unique based on the conducted search."}

    # Format the top 5 matches for the prompt
    formatted_matches = ""
    for match in matches[:5]:
        match_type = match.get('type', 'N/A').capitalize()
        details = match.get('details', {})
        similarity = match.get('similarity', 0.0)

        title = details.get('title') or details.get('name', 'No Title')
        link = details.get('url') or details.get('link', '#')
        snippet = details.get('snippet') or details.get(
            'abstract') or details.get('description', 'No snippet available.')

        formatted_matches += f"- Source Type: {match_type}\n"
        formatted_matches += f"  - Title: {title}\n"
        formatted_matches += f"  - Link: {link}\n"
        formatted_matches += f"  - Similarity Score: {similarity:.2f}\n"
        formatted_matches += f"  - Snippet: {snippet}\n\n"

    prompt_text = f"""
    You are an expert invention analyst. Your task is to provide a structured summary and verdict based on the user's idea and the search results provided.

    **User's Original Idea:**
    {original_idea}

    **Top Search Results (sorted by relevance):**
    {formatted_matches}

    **Instructions:**
    Based on the information above, please generate a final report with the following structure:

    1.  **Verdict:** Start with a clear verdict. Choose one of the following:
        - "Verdict: Likely original"
        - "Verdict: Possibly overlapping with existing inventions"
        - "Verdict: Clearly already existing"

    2.  **Summary:** Below the verdict, provide a concise summary explaining your reasoning.

    3.  **Top 5 Findings:** List the top 5 most relevant findings that support your verdict. For each finding, provide:
        - The title or name.
        - A short explanation of why it's relevant.
        - The source type (e.g., Patent, Web Page, Academic Paper).
        - A link to the source.

    Format the findings as a clear, bulleted list. Keep the explanations brief but informative.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert invention analyst following a strict output format."),
        ("human", prompt_text)
    ])

    chain = prompt | llm
    response = await chain.ainvoke({})

    return {"verdict": response.content}
