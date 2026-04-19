"""Semantic Indexer agent - vectorizes code at symbol granularity using tree-sitter."""

import contextlib
import logging
from pathlib import Path

import chromadb
from rich.progress import Progress

from app.state import SynaptixState
from app.treesitter import extract_symbols_from_file, get_symbol_chunk

logger = logging.getLogger(__name__)


def index(state: SynaptixState) -> dict[str, str]:
    """Index discovered files into ChromaDB at symbol-level granularity."""
    repo_path = Path(state["repo_path"])
    discovered: list[str] = state["discovered_files"]
    entry_points: set[str] = set(state["entry_points"])

    db_path = repo_path / ".synaptix_db"
    client = chromadb.PersistentClient(path=str(db_path))

    with contextlib.suppress(Exception):
        client.delete_collection("codebase")
    collection = client.get_or_create_collection("codebase")

    docs: list[str] = []
    ids: list[str] = []
    metas: list[dict] = []

    with Progress() as progress:
        task = progress.add_task("Indexing symbols", total=len(discovered))
        for rel in discovered:
            full_path = repo_path / rel
            symbols = extract_symbols_from_file(full_path)

            if not symbols:
                # Fallback: index the whole file if tree-sitter finds no symbols
                try:
                    content = full_path.read_text()
                except (UnicodeDecodeError, FileNotFoundError):
                    progress.advance(task)
                    continue
                if not content.strip():
                    progress.advance(task)
                    continue
                docs.append(content[:8000])
                ids.append(rel)
                metas.append({
                    "path": rel,
                    "is_entry": rel in entry_points,
                    "symbol_name": "",
                    "symbol_kind": "file",
                    "start_line": 0,
                    "end_line": content.count("\n"),
                })
                progress.advance(task)
                continue

            for sym in symbols:
                chunk = get_symbol_chunk(full_path, sym)
                if not chunk.strip():
                    continue
                qualified = f"{sym.parent_class}.{sym.name}" if sym.parent_class else sym.name
                doc_id = f"{rel}::{qualified}"
                # Prefix the chunk with context for better embedding similarity
                doc_text = f"{sym.kind} {qualified} in {rel}\n\n{chunk}"

                docs.append(doc_text)
                ids.append(doc_id)
                metas.append({
                    "path": rel,
                    "is_entry": rel in entry_points,
                    "symbol_name": qualified,
                    "symbol_kind": sym.kind,
                    "start_line": sym.start_line,
                    "end_line": sym.end_line,
                })
            progress.advance(task)

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metas)

    logger.info("Indexed %d symbol chunks into ChromaDB", len(docs))
    return {}
