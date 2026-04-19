"""Relationship Resolver agent - uses LLM to semantically label each module."""

import hashlib
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from langchain_ollama import ChatOllama
from rich.progress import Progress

from app.prompts import load
from app.state import SynaptixState

logger = logging.getLogger(__name__)

_MAX_WORKERS = 4
_CACHE_FILE = "labels.json"


def resolve(state: SynaptixState) -> dict[str, dict[str, str]]:
    """Label each module's role using LLM (cached, parallel) or filename fallback."""
    repo_path = Path(state["repo_path"])
    edges: dict[str, list[str]] = state["dependency_edges"]
    all_files = sorted(set(edges.keys()) | {f for d in edges.values() for f in d})

    cache_path = repo_path / ".synaptix_db" / _CACHE_FILE
    cache: dict[str, dict[str, str]] = _load_cache(cache_path)

    llm: ChatOllama | None = None
    try:
        llm = ChatOllama(model="qwen3", temperature=0)
        llm.invoke("test")
    except (ConnectionError, RuntimeError, OSError) as e:
        logger.warning("Ollama unavailable (%s), using filename labels", e)
        llm = None

    labels: dict[str, str] = {}
    pending: list[tuple[str, str, str]] = []  # (rel, digest, code)

    for rel in all_files:
        try:
            content = (repo_path / rel).read_text()
        except (OSError, UnicodeDecodeError):
            labels[rel] = _fallback_label(rel)
            continue
        digest = hashlib.sha256(content.encode()).hexdigest()
        if rel in cache and cache[rel].get("hash") == digest:
            labels[rel] = cache[rel]["label"]
        elif llm:
            pending.append((rel, digest, content[:4000]))
        else:
            labels[rel] = _fallback_label(rel)

    if pending and llm:
        prompt_tmpl = load("label")
        with Progress() as progress:
            task = progress.add_task("Labeling modules", total=len(pending))
            with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
                futures = {
                    pool.submit(_label_one, llm, prompt_tmpl, rel, code): (rel, digest)
                    for rel, digest, code in pending
                }
                for fut in as_completed(futures):
                    rel, digest = futures[fut]
                    label = fut.result() or _fallback_label(rel)
                    labels[rel] = label
                    cache[rel] = {"hash": digest, "label": label}
                    progress.advance(task)

    _save_cache(cache_path, cache)
    source = "Ollama/qwen3" if llm else "filename fallback"
    logger.info("Labeled %d files via %s (%d cached)",
                len(labels), source, len(all_files) - len(pending))
    return {"file_labels": labels}


def _label_one(llm: ChatOllama, tmpl: str, rel: str, code: str) -> str:
    try:
        resp = llm.invoke(tmpl.format(path=rel, code=code))
        if isinstance(resp.content, str):
            return _clean_label(resp.content)
    except (OSError, RuntimeError) as e:
        logger.debug("LLM failed for %s: %s", rel, e)
    return ""


def _load_cache(path: Path) -> dict[str, dict[str, str]]:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(path: Path, cache: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2))


def _clean_label(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text.strip("\"'").strip()


def _fallback_label(rel: str) -> str:
    path = Path(rel)
    if path.name == "__init__.py":
        return "Package init"
    if path.name == "__main__.py":
        return "CLI entry point"
    return path.stem.replace("_", " ").title()
