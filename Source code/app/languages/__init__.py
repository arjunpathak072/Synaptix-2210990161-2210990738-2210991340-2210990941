"""Language dispatcher for multi-language analysis.

Currently Python is the only fully-implemented language. JavaScript/TypeScript
extractors are stubs that will use tree-sitter when enabled (requires adding
tree-sitter-javascript / tree-sitter-typescript as dependencies).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from app.agents.context_climber import _extract_local_imports as _py_extract

# Map file extension -> logical language
_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}

SUPPORTED_EXTENSIONS: set[str] = set(_EXT_TO_LANG.keys())

# Extractor signature: (filepath, repo_root, known_files) -> (imports, dynamic)
Extractor = Callable[[Path, Path, set[str]], tuple[list[str], list[str]]]


def detect_language(path: Path) -> Optional[str]:
    return _EXT_TO_LANG.get(path.suffix.lower())


def get_import_extractor(language: str) -> Optional[Extractor]:
    if language == "python":
        return _py_extract
    # JS/TS support is opt-in; returning None here causes the file to be
    # discovered but not traced — future work will fill this in.
    return None
