"""Graph analysis: SCC-based cycle detection and reachability."""

from __future__ import annotations


def find_cycles(edges: dict[str, list[str]]) -> list[list[str]]:
    """Return non-trivial strongly-connected components (cycles) using Tarjan's algorithm.

    Includes single-node self-loops (where a node imports itself).
    """
    index_counter = [0]
    stack: list[str] = []
    lowlink: dict[str, int] = {}
    index: dict[str, int] = {}
    on_stack: set[str] = set()
    result: list[list[str]] = []

    nodes = set(edges.keys()) | {d for deps in edges.values() for d in deps}

    def strongconnect(v: str) -> None:
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)

        for w in edges.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            component: list[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                component.append(w)
                if w == v:
                    break
            # Keep only real cycles: SCC size > 1, or a self-loop
            if len(component) > 1 or v in edges.get(v, []):
                result.append(sorted(component))

    for node in sorted(nodes):
        if node not in index:
            strongconnect(node)

    return result


def find_unreachable(
    edges: dict[str, list[str]], entry_points: list[str]
) -> list[str]:
    """Return files not reachable from any entry point."""
    nodes = set(edges.keys()) | {d for deps in edges.values() for d in deps}
    reachable: set[str] = set()
    stack = list(entry_points)
    while stack:
        n = stack.pop()
        if n in reachable:
            continue
        reachable.add(n)
        stack.extend(edges.get(n, []))
    return sorted(nodes - reachable)
