"""Context Climber agent - traces import dependencies via AST parsing."""

import ast
import logging
from collections import deque
from pathlib import Path

from app.state import SynaptixState

logger = logging.getLogger(__name__)


def climb(state: SynaptixState) -> dict:
    """Trace import dependencies from entry points and build a dependency DAG."""
    repo_path = Path(state["repo_path"])
    discovered: set[str] = set(state["discovered_files"])
    entry_points: list[str] = state["entry_points"]

    edges: dict[str, list[str]] = {}
    dynamic: dict[str, list[str]] = {}
    visited: set[str] = set()
    queue: deque[str] = deque(entry_points)

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        imports, dyn_mods = _extract_local_imports(
            repo_path / current,
            repo_path,
            discovered,
        )
        imports = _add_parent_inits(imports, discovered)
        if imports:
            edges[current] = imports
        else:
            edges.setdefault(current, [])
        if dyn_mods:
            dynamic[current] = sorted(set(dyn_mods))
        for imp in imports:
            if imp not in visited:
                queue.append(imp)

    for rel in discovered:
        if rel not in visited and rel not in edges:
            edges.setdefault(rel, [])

    total_edges = sum(len(v) for v in edges.values())
    logger.info(
        "Traced %d dependency edges across %d files (%d with dynamic imports)",
        total_edges, len(edges), len(dynamic),
    )
    return {"dependency_edges": edges, "dynamic_imports": dynamic}


def _extract_local_imports(
    filepath: Path,
    repo_root: Path,
    known_files: set[str],
) -> tuple[list[str], list[str]]:
    """Return (static_import_paths, dynamic_module_names)."""
    try:
        tree = ast.parse(filepath.read_text(), filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return [], []

    file_dir = filepath.parent
    imports: list[str] = []
    dynamic: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:  # relative import
                base = file_dir
                for _ in range(node.level - 1):
                    base = base.parent
                module = node.module or ""
                _resolve_relative(base, module, repo_root, known_files, imports)
                for alias in node.names:
                    sub = f"{module}.{alias.name}" if module else alias.name
                    _resolve_relative(base, sub, repo_root, known_files, imports)
            elif node.module:
                _resolve_and_add(node.module, repo_root, file_dir, known_files, imports)
                for alias in node.names:
                    _resolve_and_add(
                        f"{node.module}.{alias.name}", repo_root, file_dir, known_files, imports,
                    )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                _resolve_and_add(alias.name, repo_root, file_dir, known_files, imports)
        elif isinstance(node, ast.Call):
            mod = _dynamic_import_target(node)
            if mod:
                dynamic.append(mod)
                _resolve_and_add(mod, repo_root, file_dir, known_files, imports)

    return sorted(set(imports)), dynamic


def _dynamic_import_target(call: ast.Call) -> str | None:
    """Return module name if this is importlib.import_module('x') or __import__('x')."""
    if not call.args or not isinstance(call.args[0], ast.Constant):
        return None
    if not isinstance(call.args[0].value, str):
        return None
    func = call.func
    if isinstance(func, ast.Name) and func.id == "__import__":
        return call.args[0].value
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "import_module"
        and isinstance(func.value, ast.Name)
        and func.value.id == "importlib"
    ):
        return call.args[0].value
    return None


def _resolve_relative(
    base: Path,
    module: str,
    repo_root: Path,
    known_files: set[str],
    out: list[str],
) -> None:
    """Resolve a relative import to a known file path."""
    parts = module.split(".") if module else []
    target = base.joinpath(*parts) if parts else base
    for candidate in (target.with_suffix(".py"), target / "__init__.py"):
        try:
            rel = str(candidate.relative_to(repo_root))
        except ValueError:
            continue
        if rel in known_files:
            out.append(rel)
            return


def _resolve_and_add(
    module: str,
    repo_root: Path,
    file_dir: Path,
    known_files: set[str],
    out: list[str],
) -> None:
    """Resolve a module name to a known file path and append it to out."""
    parts = module.split(".")
    candidates = [
        str(Path(*parts)) + ".py",
        str(Path(*parts, "__init__.py")),
    ]

    rel_from_root = file_dir.relative_to(repo_root)
    if str(rel_from_root) != ".":
        candidates += [
            str(rel_from_root / Path(*parts)) + ".py",
            str(rel_from_root / Path(*parts, "__init__.py")),
        ]

    for candidate in candidates:
        normalized = str(Path(candidate))
        if normalized in known_files:
            out.append(normalized)
            return


def _add_parent_inits(imports: list[str], known_files: set[str]) -> list[str]:
    """For each imported file, also include any ancestor __init__.py files that exist."""
    out = set(imports)
    for rel in imports:
        parts = Path(rel).parts
        for i in range(1, len(parts)):
            init = str(Path(*parts[:i], "__init__.py"))
            if init in known_files:
                out.add(init)
    return sorted(out)
