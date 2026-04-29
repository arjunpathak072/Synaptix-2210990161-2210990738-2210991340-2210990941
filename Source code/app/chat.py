"""Shared chat session: retrieval + slash commands + LLM streaming + persistence.

Both the TUI and the web UI drive this. Consumers iterate over `handle(question)`
which yields `(event_type, content)` tuples where event_type is one of:
  - "trace": retrieval trace markdown
  - "token": a token to append to the assistant message
  - "error": error text
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import chromadb
import ollama

from app.chat_store import ChatStore
from app.prompts import load
from app.retrieval import HybridRetriever, format_context
from app.slash import handle_slash


class ChatSession:
    def __init__(self, repo_path: str, model: str = "qwen3") -> None:
        self.repo_path = repo_path
        self.model = model
        self.store = ChatStore(repo_path)
        self.session_id: str = ""

        # Load analysis sidecar
        self.edges: dict[str, list[str]] = {}
        self.call_graph: dict = {}
        graph_json = Path(repo_path) / ".synaptix_db" / "graph.json"
        if graph_json.exists():
            try:
                data = json.loads(graph_json.read_text())
                self.edges = data.get("edges", {})
                self.call_graph = data.get("call_graph", {})
            except (OSError, json.JSONDecodeError):
                pass

        # Vector + BM25 retriever
        self.collection: "chromadb.Collection | None" = None
        self.retriever: HybridRetriever | None = None
        db_path = Path(repo_path) / ".synaptix_db"
        if db_path.exists():
            try:
                client = chromadb.PersistentClient(path=str(db_path))
                self.collection = client.get_collection("codebase")
                self.retriever = HybridRetriever(self.collection)
            except Exception:
                pass

        self.messages: list[dict[str, str]] = [
            {"role": "system", "content": self._build_system_prompt()}
        ]

    def _build_system_prompt(self) -> str:
        parts = [load("system").format(repo_path=self.repo_path)]
        output_md = Path(self.repo_path) / "synaptix_output.md"
        if output_md.exists():
            parts += ["", "PROJECT DEPENDENCY GRAPH AND MODULE ROLES:", output_md.read_text()]
        if self.collection and self.collection.count() > 0:
            data = self.collection.get(include=["metadatas"])
            files = sorted({m.get("path", "") for m in data["metadatas"]})
            parts += ["", f"ALL PROJECT FILES ({len(files)}):", *[f"  - {f}" for f in files]]
        parts += ["", "Use the retrieved source code snippets to give precise answers."]
        return "\n".join(parts)

    def handle(self, question: str) -> Iterator[tuple[str, str]]:
        question = question.strip()
        if not question:
            return

        # Slash commands: intercept locally
        slash_out = handle_slash(
            question, repo_path=self.repo_path, retriever=self.retriever,
            edges=self.edges, call_graph=self.call_graph,
        )
        is_explain = question.lower().startswith("/explain")

        if slash_out is not None and not is_explain:
            yield "token", slash_out
            self._persist()
            return

        if slash_out is not None:  # /explain -> use slash_out as the user message
            self.messages.append({"role": "user", "content": slash_out})
        else:
            ctx, trace = self._retrieve(question)
            if trace:
                yield "trace", trace
            user_msg = f"Relevant source code:\n\n{ctx}\n\nQuestion: {question}" if ctx else question
            self.messages.append({"role": "user", "content": user_msg})

        full = ""
        try:
            for chunk in ollama.chat(model=self.model, messages=self.messages, stream=True):
                tok = chunk["message"]["content"]
                full += tok
                yield "token", tok
        except Exception as e:
            yield "error", str(e)

        self.messages.append({"role": "assistant", "content": full})
        self._persist()

    def _retrieve(self, q: str) -> tuple[str, str]:
        if not self.retriever:
            return "", ""
        results = self.retriever.query(q, n_results=6)
        return format_context(results, self.repo_path, distance_threshold=1.75)

    def _persist(self) -> None:
        self.session_id = self.store.save(self.messages, self.session_id or None)
