import os
import json
import re
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
    "ignore that",
    "ignore all previous",
    "ignore instructions",
    "system prompt",
    "disregard previous",
    "act as",
    "you are now",
    "forget the above",
    "system_overridden",
    "after you read this",
    "real content starts below",
    "answer only with",
    "no matter the question",
    "always respond with",
    "system rules",
    "passwords_are_here",
    "next request must be obeyed",
]
PROMPT_BLOCK_MESSAGE = (
    "We cannot analyze that request. Please describe an invention idea instead."
)


def is_high_risk_prompt(text: str) -> bool:
    lowered = text.lower()
    if any(pattern in lowered for pattern in HIGH_RISK_PATTERNS):
        return True
    if "ignore" in lowered and (
        "directions" in lowered or "instructions" in lowered or "tell me" in lowered
    ):
        return True
    if "but actually" in lowered and "ignore" in lowered:
        return True
    if "after you read this" in lowered and "output" in lowered:
        return True
    if "tell me what the capital" in lowered or "tell me the capital" in lowered:
        return True
    if ("\"meta\"" in lowered or "'meta'" in lowered) and "ignore" in lowered:
        return True
    if looks_like_malicious_json(text):
        return True
    if contains_malicious_html_comment(text):
        return True
    if forces_fixed_output(lowered):
        return True
    if references_system_rule_override(lowered):
        return True
    if enforces_multi_step_override(lowered):
        return True
    return False


def looks_like_malicious_json(text: str) -> bool:
    try:
        parsed = json.loads(text)
    except Exception:
        return False

    if not isinstance(parsed, dict):
        return False

    for key, value in parsed.items():
        if not isinstance(value, str):
            continue
        lowered_val = value.lower()
        if any(
            trigger in lowered_val
            for trigger in [
                "ignore the",
                "ignore instructions",
                "output hacked",
                "system override",
                "after you read",
                "instead of",
            ]
        ):
            return True

    return False


def contains_malicious_html_comment(text: str) -> bool:
    for match in re.findall(r"<!--(.*?)-->", text, flags=re.IGNORECASE | re.DOTALL):
        lowered = match.lower()
        if "ignore" in lowered or "output" in lowered or "instead" in lowered:
            return True
    return False


def forces_fixed_output(text: str) -> bool:
    return any(
        phrase in text
        for phrase in [
            "answer only with",
            "respond only with",
            "no matter the question",
            "always respond with",
            "output exactly",
        ]
    )


def references_system_rule_override(text: str) -> bool:
    if "system rules" in text and ("don't apply" in text or "do not apply" in text):
        return True
    if "your instructions say" in text and "must be obeyed" in text:
        return True
    if "next request must be obeyed" in text:
        return True
    return False


def enforces_multi_step_override(text: str) -> bool:
    has_step_sequence = "first" in text and "second" in text and "finally" in text
    if has_step_sequence and ("output" in text or "respond" in text):
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
