"""Analyze agent - runs cycle and dead-code detection."""

import logging

from app.analysis import find_cycles, find_unreachable
from app.state import SynaptixState

logger = logging.getLogger(__name__)


def analyze(state: SynaptixState) -> dict:
    edges = state["dependency_edges"]
    entries = state["entry_points"]
    cycles = find_cycles(edges)
    dead = find_unreachable(edges, entries)
    if cycles:
        logger.warning("Detected %d cycle(s): %s", len(cycles), cycles)
    if dead:
        logger.info("Detected %d unreachable file(s)", len(dead))

    from app.callgraph import build_call_graph
    call_graph = build_call_graph(state["repo_path"], state["discovered_files"])
    logger.info(
        "Call graph: %d symbols, %d edges, %d unresolved",
        len(call_graph["symbols"]), len(call_graph["edges"]), len(call_graph["unresolved"]),
    )

    return {"cycles": cycles, "dead_files": dead, "call_graph": call_graph}
