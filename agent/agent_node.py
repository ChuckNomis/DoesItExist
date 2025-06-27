from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from .prompts import system_prompt
from .tool_registry import (
    parse_idea,
    embed_idea,
    patent_search,
    scholar_search,
    search_web,
    compare_similarity,
    summarize_results
)

# Initialize the model
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

# Bind tools to the LLM
tools = [
    parse_idea,
    embed_idea,
    patent_search,
    scholar_search,
    search_web,
    compare_similarity,
    summarize_results
]
llm_with_tools = llm.bind_tools(tools)


def agent_node(state):
    """
    Invokes the agent model to decide the next action and returns only the
    new message as an update.
    """
    # The graph framework will manage the message history. We just need to
    # prepare the messages for the LLM.
    messages = state["messages"]

    # Ensure the system prompt is the first message for the LLM.
    if not isinstance(messages[0], SystemMessage):
        messages_for_llm = [SystemMessage(content=system_prompt)] + messages
    else:
        messages_for_llm = messages

    # Invoke the model
    response = llm_with_tools.invoke(messages_for_llm)

    # Return only the new response. The graph will append this to the
    # 'messages' list in the state.
    return {"messages": [response]}
