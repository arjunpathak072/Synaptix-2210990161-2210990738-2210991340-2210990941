"""Discovery agent - scans repo for Python files and identifies entry points."""

import ast
import logging
from pathlib import Path

from app.state import SynaptixState

logger = logging.getLogger(__name__)

EXCLUDE_DIRS: set[str] = {
    "venv",
    ".venv",
    "__pycache__",
    ".git",
    "node_modules",
    ".tox",
    ".eggs",
    "dist",
    "build",
    "tests",
}
ENTRY_FILENAMES: set[str] = {"main.py", "__main__.py", "app.py", "manage.py"}


def discover(state: SynaptixState) -> dict:
    """Scan the repository for .py files and detect entry points."""
    repo_path = Path(state["repo_path"])
    discovered: list[str] = []
    entry_points: list[str] = []

    for root_path in repo_path.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in root_path.parts):
            continue
        rel = str(root_path.relative_to(repo_path))
        discovered.append(rel)

        if root_path.name in ENTRY_FILENAMES or _has_main_guard(root_path):
            entry_points.append(rel)

    logger.info("Discovered %d Python files", len(discovered))
    logger.info(
        "Entry points: %s",
        entry_points or ["(none found, scanning all files)"],
    )

    if not entry_points:
        entry_points = list(discovered)

    return {"discovered_files": discovered, "entry_points": entry_points}


def _has_main_guard(filepath: Path) -> bool:
    try:
        tree = ast.parse(filepath.read_text(), filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"
        ):
            return True
    return False
