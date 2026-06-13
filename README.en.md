# MAGATAMA (勾玉) - YATA fork with comP Bridge

[![CI](https://github.com/tsucky230/MAGATAMA/workflows/CI/badge.svg)](https://github.com/tsucky230/MAGATAMA/actions)
[![Coverage](https://codecov.io/gh/tsucky230/MAGATAMA/branch/main/graph/badge.svg)](https://codecov.io/gh/tsucky230/MAGATAMA)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🇯🇵 [日本語版 README](README.md)

**MAGATAMA** is a fork of [YATA (八咫)](https://github.com/nahisaho/YATA) (by nahisaho, MIT License)
that adds **direct integration with the [comP](https://github.com/tsucky230/comP) code indexer**.

MAGATAMA inherits the full MCP tool suite from YATA and adds a **comP Bridge (2 tools)** that imports
comP's `.comp/index.db` SQLite index into the knowledge graph — no re-parsing required.

## What is the comP Bridge?

[comP](https://github.com/tsucky230/comP) is a code indexer built as a VSCode extension + Rust daemon.
It stores analysis results in `<workspace>/.comp/index.db` (SQLite, WAL mode).

The MAGATAMA comP Bridge reads this SQLite database directly and converts it into the NetworkX
knowledge graph (inherited from YATA). This means **comP's pre-built index is immediately available
to all MAGATAMA tools** such as `search_entities`, `hybrid_search`, and `analyze_impact`.

```text
[comP Rust Daemon] ──writes──> .comp/index.db (SQLite, WAL mode)
                                    │ read-only connection
                                    ▼
                      [MAGATAMA CompIndexReader] ──converts──> NetworkXKnowledgeGraph
                                    │
                                    ▼
                 [MAGATAMA MCP Server (FastMCP)] ──MCP──> Claude Desktop / Cursor / Copilot
```

## ✨ Features

- 🔌 **comP Bridge**: Import comP `.comp/index.db` into the knowledge graph without re-parsing
- 🔍 **Code Analysis**: High-speed AST parsing via Tree-sitter (24 languages)
- 🕸️ **Knowledge Graph**: Entity-relationship graph powered by NetworkX
- 🔗 **Relationship Detection**: Automatic detection of CALLS/IMPORTS/INHERITS/CONTAINS
- 🤖 **MCP Compliant**: Full Model Context Protocol support (36 Tools, 3 Prompts, 1 Resource)
- 📚 **Framework Knowledge**: Built-in knowledge graphs for 47 frameworks (457K+ entities)
- 🔎 **Hybrid Search**: Keyword + semantic integrated search
- 🎯 **Pattern Detection**: Automatic detection of 10 design patterns
- 📝 **Documentation Generation**: Automatic JSDoc/docstring generation
- 📊 **Quality Analysis**: Cyclomatic complexity, coupling, and cohesion metrics
- 📈 **Evolution Tracking**: Code hotspot analysis from Git history
- 💾 **Persistence**: Save/load to JSON/SQLite
- 🔒 **Privacy**: Fully local execution (no external data transmission)
- 🔄 **Incremental Analysis**: Re-analyze only changed files

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/tsucky230/MAGATAMA.git
cd MAGATAMA

# Install dependencies with uv (recommended)
uv sync --all-packages
```

### Basic Usage

```bash
# Parse a file
magatama parse path/to/file.py

# Parse a directory
magatama parse path/to/project --pattern "**/*.py" --pattern "**/*.ts"

# Start MCP server (stdio mode)
magatama serve

# Start MCP server (SSE mode)
magatama serve --transport sse --port 8080

# Display server info
magatama info

# Search entities
magatama query "parse" --type function
```

### Using with comP

```bash
# 1. Index your project with comP (runs automatically via VSCode + comP extension)

# 2. Start MAGATAMA MCP server
magatama serve
```

Then from an MCP client (e.g., Claude Desktop):

```python
# Check the index without loading
get_external_graph_info(path="e:/dev/myproject")

# Load the index into the knowledge graph
read_external_graph(path="e:/dev/myproject")

# Use any MAGATAMA tool on the indexed code
search_entities(query="MyClass")
get_related_entities(entity_id="comp:myproject:n42")
analyze_impact(entity_id="comp:myproject:n42")
```

### Integration with AI Tools

#### GitHub Copilot (VS Code)

`.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "magatama", "serve"]
    }
  }
}
```

#### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "magatama", "serve"]
    }
  }
}
```

## 🔧 MCP Tools (36 Tools)

### 🔌 comP Bridge (2 Tools)

| Tool | Description |
|------|-------------|
| `read_external_graph` | Load a comP index into MAGATAMA's knowledge graph |
| `get_external_graph_info` | Inspect comP index stats without loading |

`read_external_graph` parameters:

| Parameter | Description |
| --------- | ----------- |
| `path` | Workspace root, `.comp` directory, or direct path to `.db` file |
| `mode` | `replace` (default): purge existing entries then load; `merge`: add on top |

### 📁 Core Tools (10 Tools)

| Tool | Description |
|------|-------------|
| `parse_file` | Parse a source file and extract entities |
| `parse_directory` | Batch-parse all files in a directory |
| `search_entities` | Search entities by name or type |
| `get_entity` | Get details for a specific entity |
| `get_related_entities` | Get adjacent nodes in the knowledge graph |
| `get_graph_stats` | Get knowledge graph statistics |
| `save_graph` | Save the knowledge graph to a JSON file |
| `load_graph` | Load a knowledge graph from a JSON file |
| `list_supported_languages` | List all 24 supported languages |
| `get_language_for_file` | Detect the language from a file extension |

### 🧠 Framework Knowledge Tools (7 Tools)

| Tool | Description |
|------|-------------|
| `list_frameworks` | List available framework knowledge graphs |
| `search_framework_docs` | Search entities within a framework |
| `search_all_frameworks` | Cross-framework search |
| `find_code_patterns` | Find common patterns across frameworks |
| `get_framework_entity_context` | Get detailed context for a framework entity |
| `framework_semantic_search_tool` | Semantic search within frameworks |
| `framework_find_by_pattern` | Pattern matching across all frameworks |

### 🔍 Search & Context Tools (4 Tools)

| Tool | Description |
|------|-------------|
| `semantic_search` | Semantic search on local code |
| `find_by_pattern` | Find entities by naming pattern |
| `get_code_context` | Get comprehensive context for an entity |
| `find_usage_examples` | Find usage examples for an entity |

### 📚 Documentation & Recommendation Tools (4 Tools)

| Tool | Description |
|------|-------------|
| `generate_documentation` | Auto-generate documentation for an entity |
| `recommend_code` | Suggest code snippets |
| `analyze_impact` | Analyze the blast radius of a change |
| `find_critical_paths` | Identify critical dependency paths |

### 🔎 Hybrid Search & Quality Tools (4 Tools)

| Tool | Description |
| ------ | ----------- |
| `hybrid_search` | Local + framework cross-search |
| `analyze_quality` | Code quality metrics analysis |
| `track_evolution` | Track code evolution from Git history |
| `find_hotspots` | Identify frequently-changed code |

### 🤖 AI Coding Assistance Tools (5 Tools)

| Tool | Description |
| ------ | ----------- |
| `get_coding_guidance` | Generate AI coding guidance |
| `detect_patterns` | Detect design patterns automatically |
| `check_api_compatibility` | Check API version compatibility |
| `navigate_code` | Navigate code relationships |
| `get_call_graph` | Get the call graph for a function |

## 💬 MCP Prompts (3 Prompts)

| Prompt | Description |
|--------|-------------|
| `analyze_codebase` | Analyze codebase structure and provide insights |
| `explain_entity` | Explain a specific code entity |
| `find_dependencies` | Analyze dependencies of an entity |

## 📚 MCP Resources

| URI | Description |
|-----|-------------|
| `magatama://graph/stats` | Knowledge graph statistics |

## 💻 CLI Commands

### parse — Source Code Analysis

```bash
magatama parse <PATH> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-p, --pattern` | File glob pattern (default: `**/*.py`) |
| `-e, --exclude` | Exclusion pattern |
| `-o, --output` | Output path for the knowledge graph |

### query — Entity Search

```bash
magatama query <QUERY> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-t, --type` | Filter by entity type (function, class, method, etc.) |
| `-n, --max-results` | Maximum results (default: 20) |
| `-g, --graph` | Graph file to load |
| `--json` | Output in JSON format |

### serve — Start MCP Server

```bash
magatama serve [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-t, --transport` | Transport: `stdio` or `sse` (default: stdio) |
| `-p, --port` | SSE port (default: 8080) |

## 🏗️ Supported Languages (24)

| Language | Extensions | Status |
|----------|------------|--------|
| Python | `.py` | ✅ |
| TypeScript | `.ts`, `.tsx` | ✅ |
| JavaScript | `.js`, `.jsx` | ✅ |
| Rust | `.rs` | ✅ |
| Go | `.go` | ✅ |
| Java | `.java` | ✅ |
| Kotlin | `.kt` | ✅ |
| Scala | `.scala` | ✅ |
| C | `.c`, `.h` | ✅ |
| C++ | `.cpp`, `.hpp` | ✅ |
| C# | `.cs` | ✅ |
| Swift | `.swift` | ✅ |
| Objective-C | `.m` | ✅ |
| PHP | `.php` | ✅ |
| Ruby | `.rb` | ✅ |
| Dart | `.dart` | ✅ |
| Elixir | `.ex`, `.exs` | ✅ |
| Haskell | `.hs` | ✅ |
| Julia | `.jl` | ✅ |
| Lua | `.lua` | ✅ |
| Groovy | `.groovy` | ✅ |
| SQL | `.sql` | ✅ |
| Zig | `.zig` | ✅ |
| YAML | `.yaml`, `.yml` | ✅ |

## 📚 Supported Frameworks (26)

### Python

| Framework | Category | Key Entities |
|-----------|----------|-------------|
| Django | Web Framework | Model, View, Template, Form, Middleware |
| Flask | Web Framework | Blueprint, Route, Extension |
| FastAPI | Web Framework | Router, Dependency, Pydantic Model |
| Pytest | Testing | Fixture, Marker, Plugin |
| NumPy | Data Science | ndarray, ufunc, dtype |
| Pandas | Data Science | DataFrame, Series, Index |
| SQLAlchemy | ORM | Model, Session, Query, Engine |
| LangChain | AI/LLM | Chain, Agent, Memory, Tool |
| Haystack | AI/NLP | Pipeline, Document Store, Retriever |
| Streamlit | Dashboard | App, Widget, Cache, Session |
| LangGraph | AI/Agent | Graph, Node, Edge, State |

### JavaScript / TypeScript

| Framework | Category | Key Entities |
|-----------|----------|-------------|
| React | UI Framework | Component, Hook, Context, Props |
| Vue.js | UI Framework | Component, Composition API, Directive |
| Angular | UI Framework | Component, Service, Module, Pipe |
| Next.js | Full-stack | Page, API Route, Middleware, Server Component |
| Express | Web Framework | Router, Middleware, Request, Response |
| NestJS | Web Framework | Controller, Service, Module, Guard |
| Jest | Testing | Test, Describe, Mock, Expect |
| Astro | Meta Framework | Component, Island, Integration |
| SolidJS | UI Framework | Signal, Effect, Component |
| Remix | Full-stack | Loader, Action, Route, Form |
| htmx | Hypermedia | Attribute, Swap, Trigger |
| Hono | Edge Runtime | Router, Middleware, Context |
| tRPC | Type-safe API | Router, Procedure, Query, Mutation |
| Qwik | Resumable | Component, Signal, QRL |
| Bun | Runtime | Server, File, Plugin |
| Expo | Mobile | App, Navigation, Component |

### Rust

| Framework | Category | Key Entities |
|-----------|----------|-------------|
| Actix-web | Web Framework | App, Route, Handler, Middleware |
| Tokio | Async Runtime | Runtime, Task, Channel, Stream |
| Serde | Serialization | Serialize, Deserialize, Attribute |
| Rocket | Web Framework | Route, Guard, Fairing, Responder |
| Axum | Web Framework | Router, Handler, Extension, State |
| Tauri | Desktop App | Command, Window, Plugin, State |

### Go

| Framework | Category | Key Entities |
|-----------|----------|-------------|
| Gin | Web Framework | Router, Handler, Middleware, Context |
| Echo | Web Framework | Router, Handler, Middleware, Context |
| Fiber | Web Framework | App, Route, Handler, Middleware |
| GORM | ORM | Model, DB, Query, Association |

### Other

| Framework | Language | Category |
|-----------|----------|----------|
| Phoenix | Elixir | Web Framework |
| Prisma | TypeScript | ORM |
| Drizzle | TypeScript | ORM |
| SwiftUI | Swift | Mobile |
| Jetpack Compose | Kotlin | Mobile |
| Spring Boot | Java | Web Framework |
| .NET Core | C# | Web Framework |
| Ruby on Rails | Ruby | Web Framework |
| Laravel | PHP | Web Framework |

## 🛠️ Development

### Setup

```bash
git clone https://github.com/tsucky230/MAGATAMA.git
cd MAGATAMA
uv sync --all-packages

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=magatama_core --cov=magatama_mcp

# Run linters
uv run ruff check .
uv run mypy packages/
```

### Project Structure

```text
MAGATAMA/
├── packages/
│   ├── magatama-core/              # Knowledge graph engine (library)
│   │   ├── src/magatama_core/
│   │   │   ├── domain/         # Domain layer (entities, value objects)
│   │   │   ├── application/    # Application layer (use cases)
│   │   │   └── infrastructure/ # Infrastructure (parsers, storage, comP Bridge)
│   │   └── tests/
│   └── magatama-mcp/               # MCP Server (application)
│       ├── src/magatama_mcp/
│       │   ├── server/         # MCP implementation (FastMCP)
│       │   └── cli/            # CLI implementation (Click)
│       └── tests/
├── steering/                   # Project memory
└── storage/specs/              # Design documents
```

### Architecture

Built on Clean Architecture:

- **Domain Layer**: Core entities, value objects, repository interfaces
- **Application Layer**: Use cases (ParseFileUseCase, LoadCompIndexUseCase, etc.)
- **Infrastructure Layer**: Parsers, NetworkXKnowledgeGraph, **CompIndexReader (comP Bridge)**
- **Interface Layer**: MCP server (FastMCP) and CLI (Click)

## 📊 Test Status

- **Tests**: 794 (694 magatama-core + 100 magatama-mcp)
- **E2E Tests**: 42 (18 integration + 24 security)
- **Coverage**: 76%
- **Languages**: 24 parsers
- **Framework graphs**: 47 (457K+ entities)

## 📜 License

MIT License

This project is a fork of [YATA](https://github.com/nahisaho/YATA)
(Copyright (c) 2025 nahisaho) under the MIT License, with comP Bridge added.
See [LICENSE](LICENSE) for full details.

## 🙏 Credits

- [YATA](https://github.com/nahisaho/YATA) by **nahisaho** — the foundation of this project
- [comP](https://github.com/tsucky230/comP) by **tsucky230** — VSCode code indexer
- [Model Context Protocol](https://modelcontextprotocol.io/) — Anthropic
- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) — AST parser
- [NetworkX](https://networkx.org/) — graph library
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP SDK

## 📖 Documentation

- [日本語 README](README.md)
- [AI Tools Setup Guide](docs/AI_TOOLS_SETUP.md)
- [Knowledge Database Update Guide](docs/KNOWLEDGE_UPDATE_GUIDE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [CHANGELOG](CHANGELOG.md)

---

**MAGATAMA** (勾玉) — one of the three imperial treasures of Japan, sibling to YATA (八咫鏡).
