"""Slash command handler for chat. Returns a response string or None if not a slash command."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

HELP = (
    "**Available commands**\n"
    "- `/find <query>` — pure retrieval, no LLM\n"
    "- `/explain <path>` — walk through a specific file\n"
    "- `/trace <path>` — show module-level callers and callees\n"
    "- `/trace <symbol>` or `/trace file.py::symbol` — function-level call graph\n"
)


class _Retriever(Protocol):
    def query(self, q: str, n_results: int = 6) -> list[dict]: ...


def handle_slash(
    message: str,
    *,
    repo_path: str,
    retriever: _Retriever | None,
    edges: dict[str, list[str]],
    call_graph: dict | None = None,
) -> str | None:
    """Return response string if this is a slash command, else None."""
    msg = message.strip()
    if not msg.startswith("/"):
        return None

    parts = msg.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/find":
        return _find(arg, retriever)
    if cmd == "/explain":
        return _explain(arg, repo_path)
    if cmd == "/trace":
        # Symbol trace if arg contains :: or matches a call-graph symbol name
        if call_graph and ("::" in arg or _is_symbol(arg, call_graph)):
            return _trace_symbol(arg, call_graph)
        return _trace(arg, edges)
    return HELP


def _find(query: str, retriever: Any) -> str:
    if not query:
        return "Usage: `/find <query>`"
    if not retriever:
        return "No index available."
    results = retriever.query(query, n_results=8)
    if not results:
        return f"No results for `{query}`."
    lines = [f"**Retrieval results for** `{query}`:\n"]
    for r in results:
        m = r["metadata"]
        path = m.get("path", "?")
        sym = m.get("symbol_name", "")
        kind = m.get("symbol_kind", "file")
        s, e = m.get("start_line", 0), m.get("end_line", 0)
        if sym:
            lines.append(f"- `{path}` → {kind} **{sym}** (L{s + 1}–{e + 1})")
        else:
            lines.append(f"- `{path}`")
    return "\n".join(lines)


def _explain(path_arg: str, repo_path: str) -> str:
    if not path_arg:
        return "Usage: `/explain <path>`"
    full = Path(repo_path) / path_arg
    try:
        content = full.read_text()
    except (FileNotFoundError, UnicodeDecodeError):
        return f"Could not read `{path_arg}`."
    return (
        f"Please explain the following file step by step.\n\n"
        f"**File:** `{path_arg}`\n\n```python\n{content[:8000]}\n```"
    )


def _trace(path_arg: str, edges: dict[str, list[str]]) -> str:
    if not path_arg:
        return "Usage: `/trace <path>`"
    callees = sorted(edges.get(path_arg, []))
    callers = sorted(src for src, deps in edges.items() if path_arg in deps)
    if not callees and not callers:
        return f"`{path_arg}` has no recorded callers or callees."
    out = [f"**Trace for** `{path_arg}`:\n"]
    out.append("**Imported by (callers):**")
    out.extend(f"- `{c}`" for c in callers) if callers else out.append("- _(none)_")
    out.append("\n**Imports (callees):**")
    out.extend(f"- `{c}`" for c in callees) if callees else out.append("- _(none)_")
    return "\n".join(out)


def _is_symbol(name: str, call_graph: dict) -> bool:
    """Return True if `name` matches any symbol in the call graph."""
    for caller, callee in call_graph.get("edges", []):
        for sid in (caller, callee):
            if sid.split("::")[-1] == name or sid == name:
                return True
    return False


def _trace_symbol(arg: str, call_graph: dict) -> str:
    """Show callers/callees of a function or method in the call graph."""
    if not arg:
        return "Usage: `/trace <symbol>` or `/trace file.py::symbol`"

    edges = call_graph.get("edges", [])

    def matches(sid: str) -> bool:
        if "::" in arg:
            return sid == arg
        return sid.split("::")[-1] == arg

    callers = sorted({c for c, callee in edges if matches(callee)})
    callees = sorted({callee for c, callee in edges if matches(c)})

    if not callers and not callees:
        return f"Symbol `{arg}` has no recorded callers or callees in the call graph."

    out = [f"**Call-graph trace for** `{arg}`:\n"]
    out.append("**Callers:**")
    out.extend(f"- `{c}`" for c in callers) if callers else out.append("- _(none)_")
    out.append("\n**Callees:**")
    out.extend(f"- `{c}`" for c in callees) if callees else out.append("- _(none)_")
    return "\n".join(out)
