from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agent.graph import build_graph
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables from .env file
load_dotenv()

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
    initial_state = {
        "messages": [HumanMessage(content=f"Here is my invention idea: {idea_request.idea}")],
        "original_idea": idea_request.idea,
        "tool_invocation_count": {},
    }

    # Setting a recursion limit to prevent infinite loops
    config = {"recursion_limit": 10}

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
