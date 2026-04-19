"""LangGraph workflow definition for Synaptix."""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.analyze import analyze
from app.agents.context_climber import climb
from app.agents.discovery import discover
from app.agents.relationship_resolver import resolve
from app.agents.semantic_indexer import index
from app.renderer import render
from app.state import SynaptixState


def build_graph() -> CompiledStateGraph:
    """Construct and compile the Synaptix agent graph."""
    g = StateGraph(SynaptixState)  # type: ignore[arg-type]

    g.add_node("discover", discover)
    g.add_node("climb", climb)
    g.add_node("analyze", analyze)
    g.add_node("index", index)
    g.add_node("resolve", resolve)
    g.add_node("render", render)

    g.add_edge(START, "discover")
    g.add_edge("discover", "climb")
    g.add_edge("climb", "analyze")
    g.add_edge("analyze", "index")
    g.add_edge("index", "resolve")
    g.add_edge("resolve", "render")
    g.add_edge("render", END)

    return g.compile()
