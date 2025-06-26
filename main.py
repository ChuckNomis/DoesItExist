from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agent.graph import build_graph
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- DEBUGGING ---
print("--- ENVIRONMENT DEBUG ---")
print(f"Loaded OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")
print(f"Loaded TAVILY_API_KEY: {os.getenv('TAVILY_API_KEY')}")
print(f"Loaded LENS_API_KEY: {os.getenv('LENS_API_KEY')}")
print("-------------------------")

app = FastAPI(
    title="Invention Checker Agent",
    description="An AI agent that checks if an invention idea already exists.",
    version="0.1.0",
)

# Mount the static files directory
static_files_path = os.path.join(os.path.dirname(__file__), "frontend/static")
app.mount("/static", StaticFiles(directory=static_files_path), name="static")

# Build the LangGraph agent
graph = build_graph()


class IdeaRequest(BaseModel):
    idea: str


@app.post("/check")
async def check_idea(request: IdeaRequest):
    """
    Accepts an invention idea and returns the agent's verdict.
    """
    initial_state = {
        "messages": [HumanMessage(content=f"Here is my invention idea: {request.idea}")],
        "original_idea": request.idea,
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
async def read_index():
    """
    Serves the main HTML page.
    """
    index_path = os.path.join(os.path.dirname(__file__), "frontend/index.html")
    return FileResponse(index_path)
