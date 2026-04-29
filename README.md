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

## Future Roadmap

Planned enhancements to evolve **Synaptix** into a professional-grade architectural intelligence tool:

### 1. Multi-Language Support
Extend Tree-sitter integration beyond Python to support **TypeScript, Go, and Rust**, enabling architectural mapping of polyglot microservice environments.

### 2. Incremental Indexing (Git-Aware)
Implement delta-updates via Git-hook integration to re-index only modified files, significantly reducing compute overhead for large-scale enterprise repositories.

### 3. Graph-Walk RAG
Evolution of the retrieval system to traverse the **Mermaid-defined relationships**. Instead of basic vector similarity, the agent will "walk the graph" to retrieve callers, callees, and dependencies for deeper context.

### 4. IDE Integration (VS Code / JetBrains)
Packaging the Web UI and interactive chat as a native IDE extension, allowing developers to visualize the codebase "Mental Map" directly alongside their source code.

### 5. Autonomous Refactoring Agents
Leveraging the structural map to propose and execute refactoring tasks, such as decoupling highly entangled modules or automatically generating unit test stubs based on function signatures.

### 6. CI/CD Architectural Guardrails
Headless CLI mode for GitHub Actions/GitLab CI to automatically detect and flag circular dependencies or architectural pattern violations during the Pull Request process.
