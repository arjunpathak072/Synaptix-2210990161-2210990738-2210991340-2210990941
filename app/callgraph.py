"""Function-level call graph via tree-sitter.

Two-phase design:

1. `extract_calls_from_file`: per-file, walks AST to find every call site inside a
   function/method and emits (caller_qualified, callee_simple_name) tuples.

2. `build_call_graph`: cross-file resolution — maps each simple callee name to a
   concrete `file::symbol` ID using import context and same-file symbol tables.
   Unresolved names (builtins, third-party, dynamic) are dropped.
"""

from __future__ import annotations

import ast
from pathlib import Path

from app.treesitter import _parser, extract_symbols_from_file


def extract_calls_from_file(path: Path) -> list[tuple[str, str]]:
    """Return list of (caller_qualified_name, callee_simple_name) tuples."""
    try:
        source = path.read_bytes()
    except (FileNotFoundError, PermissionError):
        return []
    tree = _parser.parse(source)

    calls: list[tuple[str, str]] = []

    def walk(node, enclosing: str | None, class_name: str | None) -> None:
        t = node.type
        if t == "function_definition":
            name_node = node.child_by_field_name("name")
            fname = name_node.text.decode() if name_node else "<anon>"
            qualified = f"{class_name}.{fname}" if class_name else fname
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    walk(child, qualified, None)
            return

        if t == "class_definition":
            cls_node = node.child_by_field_name("name")
            cname = cls_node.text.decode() if cls_node else "<anon>"
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    walk(child, enclosing, cname)
            return

        if t == "call" and enclosing is not None:
            func_node = node.child_by_field_name("function")
            callee = _callee_name(func_node)
            if callee:
                calls.append((enclosing, callee))

        for child in node.children:
            walk(child, enclosing, class_name)

    for child in tree.root_node.children:
        walk(child, None, None)

    return calls


def _callee_name(func_node) -> str | None:
    """Extract simple callee name from a call's function expression."""
    if func_node is None:
        return None
    t = func_node.type
    if t == "identifier":
        return func_node.text.decode()
    if t == "attribute":
        attr = func_node.child_by_field_name("attribute")
        if attr:
            return attr.text.decode()
    return None


def build_call_graph(repo_path: str, files: list[str]) -> dict:
    """Build a symbol-level call graph.

    Returns dict with:
      - symbols: list[file::qualified]
      - edges:   list[(caller_id, callee_id)]
      - unresolved: list[(caller_id, callee_name)]
    """
    root = Path(repo_path)

    # Symbol table: simple_name -> [file::qualified]
    by_simple: dict[str, list[str]] = {}
    # file -> set of qualified names defined there
    file_defs: dict[str, set[str]] = {}

    for rel in files:
        for sym in extract_symbols_from_file(root / rel):
            qualified = f"{sym.parent_class}.{sym.name}" if sym.parent_class else sym.name
            full = f"{rel}::{qualified}"
            by_simple.setdefault(sym.name, []).append(full)
            if sym.parent_class:
                by_simple.setdefault(qualified, []).append(full)
            file_defs.setdefault(rel, set()).add(qualified)

    # Per-file imports: name -> file::qualified
    imports_by_file: dict[str, dict[str, str]] = {
        rel: _imported_names(root / rel, files) for rel in files
    }

    edges: list[tuple[str, str]] = []
    unresolved: list[tuple[str, str]] = []

    for rel in files:
        calls = extract_calls_from_file(root / rel)
        local_defs = file_defs.get(rel, set())
        local_simple = {q.split(".")[-1]: q for q in local_defs}
        imports = imports_by_file.get(rel, {})

        for caller, callee in calls:
            caller_id = f"{rel}::{caller}"
            resolved = _resolve_callee(
                callee, rel, local_simple, imports, by_simple,
            )
            if resolved:
                edges.append((caller_id, resolved))
            else:
                unresolved.append((caller_id, callee))

    return {
        "symbols": sorted({s for sids in by_simple.values() for s in sids}),
        "edges": edges,
        "unresolved": unresolved,
    }


def _resolve_callee(
    name: str,
    rel: str,
    local_simple: dict[str, str],
    imports: dict[str, str],
    by_simple: dict[str, list[str]],
) -> str | None:
    """Resolve a simple callee name to file::qualified, or None."""
    # Prefer same-file
    if name in local_simple:
        return f"{rel}::{local_simple[name]}"
    # Imported symbol
    if name in imports:
        return imports[name]
    # Globally unique across repo
    candidates = by_simple.get(name, [])
    if len(candidates) == 1:
        return candidates[0]
    return None


def _imported_names(filepath: Path, files: list[str]) -> dict[str, str]:
    """Map imported local name -> file::symbol using Python AST.

    Handles `from module import name [as alias]` where module resolves to a repo file.
    """
    try:
        tree = ast.parse(filepath.read_text(), filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return {}

    result: dict[str, str] = {}
    file_set = set(files)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        parts = node.module.split(".")
        candidates = [
            str(Path(*parts)) + ".py",
            str(Path(*parts, "__init__.py")),
        ]
        target: str | None = next(
            (str(Path(c)) for c in candidates if str(Path(c)) in file_set), None
        )
        if not target:
            continue
        for alias in node.names:
            local = alias.asname or alias.name
            result[local] = f"{target}::{alias.name}"
    return result
