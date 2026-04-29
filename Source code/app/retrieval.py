"""Hybrid retrieval: vector search + BM25 with reciprocal rank fusion."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _tokenize(text: str) -> list[str]:
    # Split camelCase / snake_case into component words too
    words = _TOKEN_RE.findall(text)
    out: list[str] = []
    for w in words:
        out.append(w.lower())
        # split snake_case
        for part in w.split("_"):
            if part and part.lower() != w.lower():
                out.append(part.lower())
        # split camelCase
        for part in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", w):
            if part and part.lower() != w.lower():
                out.append(part.lower())
    return out


class HybridRetriever:
    """Combines Chroma vector search with BM25 over symbol/path tokens."""

    def __init__(self, collection: Any) -> None:
        self.collection = collection
        self._bm25: BM25Okapi | None = None
        self._ids: list[str] = []
        self._docs: list[str] = []
        self._metas: list[dict] = []
        self._build_bm25()

    def _build_bm25(self) -> None:
        if not self.collection or self.collection.count() == 0:
            return
        data = self.collection.get(include=["documents", "metadatas"])
        self._ids = data["ids"]
        self._docs = data["documents"]
        self._metas = data["metadatas"]
        corpus = [
            _tokenize(
                f"{m.get('path', '')} {m.get('symbol_name', '')} {m.get('symbol_kind', '')} {d[:2000]}"
            )
            for d, m in zip(self._docs, self._metas, strict=False)
        ]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def query(self, question: str, n_results: int = 6) -> list[dict]:
        """Return fused top-n results with {id, document, metadata, distance}.

        BM25 re-ranks vector hits; it does not introduce new docs. This keeps
        trivial queries ("hi") from surfacing spurious keyword matches and
        guarantees every returned hit has a real vector distance.
        """
        if not self.collection or self.collection.count() == 0:
            return []

        # Vector search (over-fetch for fusion)
        k = max(n_results * 3, 20)
        vec = self.collection.query(
            query_texts=[question],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        vec_ids = vec["ids"][0]
        vec_dist = {i: d for i, d in zip(vec_ids, vec["distances"][0], strict=False)}
        vec_doc = dict(zip(vec_ids, vec["documents"][0], strict=False))
        vec_meta = dict(zip(vec_ids, vec["metadatas"][0], strict=False))
        vec_id_set = set(vec_ids)

        # BM25 search — used only to re-rank within vec_id_set
        bm_ids: list[str] = []
        if self._bm25:
            scores = self._bm25.get_scores(_tokenize(question))
            ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
            bm_ids = [self._ids[i] for i in ranked if scores[i] > 0 and self._ids[i] in vec_id_set]

        # Reciprocal Rank Fusion over intersection
        rrf_k = 60
        fused: dict[str, float] = {}
        for rank, doc_id in enumerate(vec_ids):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (rrf_k + rank)
        for rank, doc_id in enumerate(bm_ids):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (rrf_k + rank)

        top = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:n_results]
        return [
            {
                "id": doc_id,
                "document": vec_doc[doc_id],
                "metadata": vec_meta[doc_id],
                "distance": vec_dist[doc_id],
            }
            for doc_id, _score in top
        ]


def format_context(
    results: list[dict], repo_path: str, distance_threshold: float | None = None
) -> tuple[str, str]:
    """Return (context_block, trace_markdown) for a list of hybrid results."""
    chunks: list[str] = []
    trace_lines: list[str] = []
    seen: set[str] = set()
    for r in results:
        meta, doc, dist = r["metadata"], r["document"], r["distance"]
        if distance_threshold is not None and dist == dist and dist > distance_threshold:
            continue
        path = meta.get("path", "unknown")
        sym = meta.get("symbol_name", "")
        kind = meta.get("symbol_kind", "file")
        start, end = meta.get("start_line", 0), meta.get("end_line", 0)
        key = f"{path}::{sym}" if sym else path
        if key in seen:
            continue
        seen.add(key)

        full_path = Path(repo_path) / path
        try:
            lines = full_path.read_text().splitlines()
            source = "\n".join(lines[start : end + 1])
        except (FileNotFoundError, UnicodeDecodeError):
            source = doc[:3000]

        header = f"--- {path}"
        if sym:
            header += f" | {kind} `{sym}` (L{start + 1}-{end + 1})"
        chunks.append(f"{header} ---\n{source}")

        loc = f"`{path}` → {kind} **{sym}** (L{start + 1}–{end + 1})" if sym else f"`{path}`"
        dist_str = f"{dist:.4f}" if dist == dist else "n/a"
        trace_lines.append(f"- {loc}  · distance: `{dist_str}`")
    return "\n\n".join(chunks), "\n".join(trace_lines)
