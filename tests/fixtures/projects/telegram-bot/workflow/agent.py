"""LangGraph workflow — NOT LangChain. Bug4 fixture: detector must recognize this."""

from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages


class State:
    messages: list


def build_workflow() -> StateGraph:
    graph = StateGraph(State)
    graph.add_node("classify", lambda s: s)
    graph.add_node("respond", lambda s: s)
    graph.add_edge("classify", "respond")
    graph.set_entry_point("classify")
    graph.set_finish_point("respond")
    return graph.compile()
