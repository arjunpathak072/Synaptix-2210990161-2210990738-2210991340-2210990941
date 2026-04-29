# Synaptix

**Synaptix: Autonomous Multi-Agent Framework for Semantic Codebase Navigation and Architectural Mapping**

An agentic AI system that autonomously builds a "Mental Map" of any Python repository. You point it at a codebase, and it discovers all Python files and entry points, traces import dependencies using AST parsing, extracts every function, class, and method using Tree-sitter, uses a local LLM (Ollama/qwen3) to semantically label each module, and outputs an interactive Mermaid.js dependency flowchart.

## Team Details

| Roll No | Name |
|---|---|
| 2210991340 | Arjun Pathak |
| 2210990738 | Rohan Kapoor |
| 2210990161 | Arnav Gupta |
| 2210990941 | Vanshaj Gupta |

**Mentor:** Dr. Rajat Takkar

**Department:** Computer Science and Engineering, Chitkara University, Punjab

## Project Title

**Synaptix** — Autonomous Multi-Agent Framework for Semantic Codebase Navigation and Architectural Mapping

## Type

Copyright

## Current Status

Completed. The system is fully functional with the following capabilities:
- Multi-agent pipeline for repository analysis (Discovery → Context Climbing → Semantic Indexing → Relationship Resolution → Mermaid Rendering)
- Interactive Chat TUI with symbol-level RAG retrieval
- Web UI for visual exploration (split-screen: Mermaid diagram + chat)
- Built with LangGraph, Ollama/qwen3, ChromaDB, Tree-sitter

## Repository Structure

```
├── IPR Submission Proof/    # Copyright forms and submission proof
├── Report and PPT/          # Project report and presentation
├── Source code/              # Complete source code
│   ├── app/                 # Main application package
│   ├── pyproject.toml       # Project configuration
│   ├── uv.lock              # Dependency lock file
│   ├── synaptix_output.md   # Sample output
│   └── LICENSE              # Apache 2.0 License
└── README.md                # This file
```

## Tech Stack

- **Python & LangGraph** — Stateful multi-agent orchestration
- **Ollama/qwen3** — Local LLM (zero-cost, offline inference)
- **ChromaDB** — Privacy-first local vector storage
- **Tree-sitter** — Symbol-level code indexing (functions, classes, methods)
- **Python ast** — Import tracing & entry point detection
- **Textual** — Terminal chat TUI
- **Flask** — Web UI backend with SSE streaming

## Setup & Usage

```bash
# Navigate to source code
cd "Source code"

# Pull the LLM model
ollama pull qwen3

# Install Synaptix
pip install -e .

# Analyze a Python repository
python -m app --path /path/to/python/repo

# Analyze and launch interactive chat
python -m app --path /path/to/python/repo --chat

# Analyze and launch web UI
python -m app --path /path/to/python/repo --web
```
