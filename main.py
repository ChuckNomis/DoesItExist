import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables from .env file before importing modules that depend on them
load_dotenv()

from agent.graph import build_graph

MAX_IDEA_LENGTH = 2000
HIGH_RISK_PATTERNS = [
    "ignore previous",
    "ignore the above",
    "ignore instructions",
    "system prompt",
    "disregard previous",
    "act as",
    "you are now",
    "forget the above",
]
PROMPT_BLOCK_MESSAGE = (
    "We cannot analyze that request. Please describe an invention idea instead."
)


def is_high_risk_prompt(text: str) -> bool:
    lowered = text.lower()
    if any(pattern in lowered for pattern in HIGH_RISK_PATTERNS):
        return True
    if "ignore" in lowered and ("directions" in lowered or "instructions" in lowered):
        return True
    if "tell me what the capital" in lowered or "tell me the capital" in lowered:
        return True
    return False

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="DoesItExist?",
    description="An AI agent that checks if an invention idea already exists.",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount the static files directory
static_files_path = os.path.join(os.path.dirname(__file__), "frontend/static")
app.mount("/static", StaticFiles(directory=static_files_path), name="static")

# Build the LangGraph agent
graph = build_graph()


class IdeaRequest(BaseModel):
    idea: str


@app.post("/check")
@limiter.limit("5/minute")
async def check_idea(request: Request, idea_request: IdeaRequest):
    """
    Accepts an invention idea and returns the agent's verdict.
    """
    user_idea = (idea_request.idea or "").strip()
    if not user_idea:
        raise HTTPException(
            status_code=400, detail="Idea cannot be empty.")
    if len(user_idea) > MAX_IDEA_LENGTH:
        raise HTTPException(
            status_code=400, detail="Idea is too long.")

    if is_high_risk_prompt(user_idea):
        raise HTTPException(
            status_code=400,
            detail=PROMPT_BLOCK_MESSAGE,
        )

    spotlighted_idea = (
        "<<<USER_IDEA>>>\n"
        f"{user_idea}\n"
        "<<<END_USER_IDEA>>>"
    )

    initial_state = {
        "messages": [
            HumanMessage(
                content=f"Here is my invention idea:\n{spotlighted_idea}"
            )
        ],
        "original_idea": user_idea,
        "tool_invocation_count": {},
    }

    # Setting a recursion limit to prevent infinite loops
    config = {"recursion_limit": 15}

    final_state = await graph.ainvoke(initial_state, config=config)

    # Extract the final verdict from the agent's state
    summary = final_state.get(
        "verdict", "The agent did not produce a final summary.")

    return {"summary": summary}


@app.get("/")
async def read_index(request: Request):
    """
    Serves the main HTML page.
    """
    index_path = os.path.join(os.path.dirname(__file__), "frontend/index.html")
    return FileResponse(index_path)
