from langgraph.graph import StateGraph, START, END
from .agent_node import agent_node, tools
from .state import AgentState
from langchain_core.messages import ToolMessage
import asyncio
from typing import List
import inspect

# Create a tool map for easy lookup
tool_map = {tool.name: tool for tool in tools}


async def tool_executor(state: AgentState):
    """
    Executes tools and returns a dictionary of updates to the state, following
    the correct LangGraph pattern.
    """
    tool_calls = state["messages"][-1].tool_calls

    # This dictionary will hold all the updates to be returned.
    updates = {}

    # This list will hold the new tool messages to be added to the history.
    tool_messages = []

    # We need a copy of the invocation count to update it safely.
    invocation_count = state.get('tool_invocation_count', {}).copy()

    for tool_call in tool_calls:
        tool_name = tool_call["name"]

        if invocation_count.get(tool_name, 0) > 0:
            error_message = f"Error: Tool '{tool_name}' has already been called."
            tool_messages.append(ToolMessage(
                content=error_message, tool_call_id=tool_call["id"]))
            continue

        tool_to_call = tool_map[tool_name]

        # The tool is invoked with the full state, as it's state-aware.
        output_dict = await tool_to_call.ainvoke({"state": state})

        if not isinstance(output_dict, dict):
            raise ValueError(f"Tool {tool_name} did not return a dictionary.")

        # Collate the updates from the tool's output.
        updates.update(output_dict)

        tool_messages.append(
            ToolMessage(
                content=f"Successfully executed tool '{tool_name}'.",
                tool_call_id=tool_call["id"],
            )
        )
        invocation_count[tool_name] = invocation_count.get(tool_name, 0) + 1

    # The 'messages' update should only contain the *new* tool messages.
    updates["messages"] = tool_messages

    # The 'tool_invocation_count' update contains the new counts.
    updates["tool_invocation_count"] = invocation_count

    # Return the dictionary of updates. The graph will merge this into the state.
    return updates


def should_continue(state: AgentState):
    """
    Determines the next step in the graph. If a verdict has been generated,
    the graph ends. Otherwise, it routes to the tool executor if the agent
    has requested a tool call.
    """
    if state.get("verdict"):
        return END

    messages = state.get("messages", [])
    if not messages or not messages[-1].tool_calls:
        return END

    return "tool_executor"


def should_continue_after_tools(state: AgentState):
    """
    Determines the next step after the tool executor has run.
    If a verdict is in the state, the process ends.
    Otherwise, it goes back to the agent.
    """
    if state.get("verdict"):
        return "end"
    return "agent"


def build_graph():
    """
    Builds the execution graph for the agent.
    """
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tool_executor", tool_executor)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tool_executor": "tool_executor",
            "end": END,
        },
    )

    # After the tool executor runs, we check if we're done.
    graph.add_conditional_edges(
        "tool_executor",
        should_continue_after_tools,
        {
            "agent": "agent",
            "end": END,
        },
    )

    # Compile the graph into a runnable application
    app = graph.compile()
    return app
