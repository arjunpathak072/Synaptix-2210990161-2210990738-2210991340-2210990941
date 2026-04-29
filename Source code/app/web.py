"""Flask-based Code Wiki: split-screen Mermaid diagram + chat."""

import json
from pathlib import Path

from flask import Flask, Response, render_template, request, stream_with_context

from app.chat import ChatSession

app = Flask(__name__)

_repo_path: str = ""
_session: ChatSession | None = None


def init(repo_path: str) -> None:
    global _repo_path, _session
    _repo_path = repo_path
    _session = ChatSession(repo_path)


def _load_mermaid() -> str:
    output_md = Path(_repo_path) / "synaptix_output.md"
    if not output_md.exists():
        return "graph TD\n    A[No diagram yet — run the pipeline first]"
    text = output_md.read_text()
    start = text.find("```mermaid")
    end = text.find("```", start + 10)
    if start == -1:
        return "graph TD\n    A[Could not parse diagram]"
    return text[start + 10 : end].strip()


@app.route("/")
def index():
    return render_template("index.html", repo_path=_repo_path, mermaid_code=_load_mermaid())


@app.route("/chat", methods=["POST"])
def chat():
    question = request.json.get("message", "").strip()
    if not question or _session is None:
        return Response(
            "data: " + json.dumps({"type": "error", "content": "Empty message"}) + "\n\n",
            content_type="text/event-stream",
        )

    def generate():
        for etype, content in _session.handle(question):
            yield f"data: {json.dumps({'type': etype, 'content': content})}\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream")


def run_web(repo_path: str, port: int = 5000) -> None:
    init(repo_path)
    print(f"\n🧠 Synaptix Explorer: http://localhost:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
