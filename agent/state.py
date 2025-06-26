from typing import TypedDict, Annotated, List, Optional, Dict
from langchain_core.messages import BaseMessage


def add_messages(left: list, right: list) -> list:
    """Add messages to the state."""
    return left + right


class AgentState(TypedDict):
    original_idea: str
    parsed: Optional[Dict]
    embedding: Optional[List[float]]
    search_results: Optional[Dict]
    matches: Optional[List[Dict]]
    verdict: Optional[str]
    messages: Annotated[List[BaseMessage], add_messages]
    tool_invocation_count: Dict[str, int]
