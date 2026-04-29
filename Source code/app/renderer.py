"""Mermaid Renderer - converts labeled DAG to Mermaid.js flowchart."""

import json
import re
from collections import defaultdict
from pathlib import Path, PurePosixPath

from app.state import SynaptixState


def render(state: SynaptixState) -> dict[str, str]:
    """Render the dependency graph as a Mermaid flowchart and save to file."""
    repo_path = Path(state["repo_path"])
    edges: dict[str, list[str]] = state["dependency_edges"]
    labels: dict[str, str] = state.get("file_labels", {})
    cycles: list[list[str]] = state.get("cycles", [])
    dead: set[str] = set(state.get("dead_files", []))
    cycle_set: set[str] = {f for cyc in cycles for f in cyc}

    # Hide package __init__.py files from the rendered diagram (they clutter the
    # graph as hub nodes). They remain in analysis data (graph.json, cycles, etc.).
    def _visible(f: str) -> bool:
        return not f.endswith("__init__.py")

    visible_edges: dict[str, list[str]] = {
        src: [d for d in deps if _visible(d)]
        for src, deps in edges.items()
        if _visible(src)
    }

    all_files: set[str] = set(visible_edges.keys()) | {
        f for deps in visible_edges.values() for f in deps
    }
    node_ids: dict[str, str] = {f: f"n{i}" for i, f in enumerate(sorted(all_files))}

    # Group files by top-level directory for subgraphs
    groups: dict[str, list[str]] = defaultdict(list)
    for f in sorted(all_files):
        parent = str(PurePosixPath(f).parent)
        group = parent.split("/", 1)[0] if parent not in (".", "") else "(root)"
        groups[group].append(f)

    lines: list[str] = ["flowchart LR"]
    for group, files in sorted(groups.items()):
        safe_group = _sanitize_id(group)
        lines.append(f"    subgraph {safe_group}[{group}]")
        for f in files:
            nid = node_ids[f]
            label = labels.get(f, f)
            safe_label = f"{_sanitize(f)}<br/>{_sanitize(label)}"
            classes: list[str] = []
            if f in cycle_set:
                classes.append("cycle")
            if f in dead:
                classes.append("dead")
            suffix = ":::" + ",".join(classes) if classes else ""
            lines.append(f'        {nid}["{safe_label}"]{suffix}')
        lines.append("    end")

    for src, deps in sorted(visible_edges.items()):
        lines.extend(
            f"    {node_ids[src]} --> {node_ids[dep]}"
            for dep in sorted(deps)
            if src in node_ids and dep in node_ids
        )

    if cycle_set:
        lines.append("    classDef cycle fill:#ffdddd,stroke:#c00,stroke-width:2px;")
    if dead:
        lines.append("    classDef dead fill:#eeeeee,stroke:#999,stroke-dasharray:4 2,color:#666;")

    mermaid = "\n".join(lines)

    out_path = repo_path / "synaptix_output.md"
    out_path.write_text(
        f"# Synaptix - Repository Mental Map\n\n```mermaid\n{mermaid}\n```\n",
    )

    # Sidecar JSON for tooling (slash commands, diffing, etc.)
    (repo_path / ".synaptix_db").mkdir(parents=True, exist_ok=True)
    (repo_path / ".synaptix_db" / "graph.json").write_text(json.dumps({
        "edges": edges,
        "labels": labels,
        "cycles": cycles,
        "dead_files": sorted(dead),
        "call_graph": state.get("call_graph", {}),
    }, indent=2))

    return {"mermaid_output": mermaid, "output_file": str(out_path)}


def _sanitize(text: str) -> str:
    return re.sub(r'["\[\]{}()<>]', "", text)


def _sanitize_id(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", text) or "root"
