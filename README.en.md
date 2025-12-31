# YATA (八咫) - AI Coding Support MCP Server

[![CI](https://github.com/nahisaho/YATA/workflows/CI/badge.svg)](https://github.com/nahisaho/YATA/actions)
[![Coverage](https://codecov.io/gh/nahisaho/YATA/branch/main/graph/badge.svg)](https://codecov.io/gh/nahisaho/YATA)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**YATA** (八咫 - yata) is a Knowledge Graph MCP Server for AI coding support.

By analyzing library source code and building a knowledge graph, it provides accurate context to AI tools such as Claude Desktop, GitHub Copilot, and Cursor.

> 🇯🇵 [日本語版 README](README.md)

## ✨ Features

- 🔍 **Code Analysis**: High-speed AST parsing via Tree-sitter (24 languages supported)
- 🕸️ **Knowledge Graph**: Entity-relationship graph powered by NetworkX
- 🔗 **Relationship Detection**: Automatic detection of CALLS/IMPORTS/INHERITS/CONTAINS relationships
- 🤖 **MCP Compliant**: Full Model Context Protocol support (32 Tools, 3 Prompts, 1 Resource)
- 📚 **Framework Knowledge**: Built-in knowledge graphs for 47 frameworks
- 🔎 **Hybrid Search**: Keyword + Semantic integrated search
- 📝 **Documentation Generation**: Automatic JSDoc/docstring generation
- 🎯 **Pattern Detection**: Automatic detection of 10 design patterns
- 🔄 **Compatibility Check**: API version compatibility analysis
- 📈 **Quality Analysis**: Cyclomatic complexity, coupling, and cohesion metrics
- 📊 **Evolution Tracking**: Code hotspot analysis from Git history
- 💾 **Persistence**: Save/load to JSON/SQLite
- 🔒 **Privacy**: Fully local execution (no external data transmission)

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/nahisaho/YATA.git
cd yata

# Install dependencies with uv (recommended)
uv sync --all-packages
```

### Basic Usage

```bash
# Parse a file
yata parse path/to/file.py

# Parse a directory
yata parse path/to/project --pattern "**/*.py" --pattern "**/*.ts"

# Start MCP server (stdio mode)
yata serve

# Start MCP server (SSE mode)
yata serve --transport sse --port 8080

# Display server info
yata info

# Search entities
yata query "parse" --type function

# Display statistics
yata stats --graph graph.json

# Validate graph integrity
yata validate --graph graph.json --repair

# Watch directory
yata watch ./src --output graph.json

# Run performance benchmark
yata benchmark ./src

# Bulk update knowledge database (47 frameworks)
python scripts/update_knowledge_db.py

# Update specific frameworks only
python scripts/update_knowledge_db.py --frameworks react django fastapi
```

### Integration with AI Tools

#### GitHub Copilot (VS Code)

`.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "yata": {
      "command": "uv",
      "args": ["run", "yata", "serve"]
    }
  }
}
```

#### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "yata": {
      "command": "uv",
      "args": ["run", "yata", "serve"]
    }
  }
}
```

## 🔧 MCP Tools (32 Tools)

### 📁 Basic Tools

| Tool | Description |
|------|-------------|
| `parse_file` | Parse a source file and extract entities |
| `parse_directory` | Batch parse files in a directory |
| `search_entities` | Search entities by name or type |
| `get_entity` | Get details of a specific entity |
| `get_related_entities` | Get related entities |
| `get_graph_stats` | Get knowledge graph statistics |
| `save_graph` | Save knowledge graph to JSON file |
| `load_graph` | Load knowledge graph from JSON file |

### 🧠 Framework Knowledge Graph Tools

| Tool | Description |
|------|-------------|
| `register_framework` | Register a framework knowledge graph |
| `search_framework` | Search entities within a framework |
| `get_framework_entity` | Get framework entity details |
| `list_frameworks` | List registered frameworks |
| `get_framework_stats` | Get framework statistics |
| `get_usage_examples` | Get framework usage examples |
| `get_framework_structure` | Get framework structure |

### 📚 Documentation Generation Tools (Phase 1)

| Tool | Description |
|------|-------------|
| `generate_documentation` | Auto-generate entity documentation (JSDoc/docstring format) |
| `recommend_code` | Get code recommendations from knowledge graph (similar code, pattern suggestions) |
| `analyze_impact` | Dependency impact analysis (identify change impact scope) |

### 🔍 Hybrid Search & Quality Analysis Tools (Phase 2)

| Tool | Description |
|------|-------------|
| `hybrid_search` | Integrated keyword + semantic search |
| `analyze_quality` | Code quality metrics analysis (cyclomatic complexity, coupling, cohesion) |
| `track_evolution` | Analyze code change frequency and hotspots from Git history |
| `find_hotspots` | Identify frequently changed files and functions |

### 🤖 AI Coding Support Tools (Phase 3)

| Tool | Description |
|------|-------------|
| `get_coding_guidance` | Generate AI coding guidance (framework recommended code) |
| `detect_patterns` | Auto-detect design patterns (Singleton, Factory, etc. - 10 patterns) |
| `check_api_compatibility` | API version compatibility check (Django, FastAPI, React supported) |
| `navigate_code` | Interactive code navigation (relationship exploration) |
| `get_call_graph` | Get function call graph |

## 💬 MCP Prompts

| Prompt | Description |
|--------|-------------|
| `analyze_codebase` | Analyze codebase structure and provide insights |
| `explain_entity` | Explain a specific code entity |
| `find_dependencies` | Analyze entity dependencies |

## 📚 MCP Resources

| URI | Description |
|-----|-------------|
| `yata://graph/stats` | Knowledge graph statistics |

## 💻 CLI Command Details

### parse - Source Code Analysis

```bash
yata parse <PATH> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-p, --pattern` | Target file pattern (default: `**/*.py`) |
| `-e, --exclude` | Exclusion pattern |
| `-o, --output` | Knowledge graph save path |

### query - Entity Search

```bash
yata query <QUERY> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-t, --type` | Filter by entity type (function, class, method, etc.) |
| `-n, --max-results` | Maximum number of results (default: 20) |
| `-g, --graph` | Graph file path to load |
| `--json` | Output in JSON format |

### stats - Display Statistics

```bash
yata stats [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-g, --graph` | Graph file path to load |
| `--json` | Output in JSON format |

### validate - Integrity Validation

```bash
yata validate [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-g, --graph` | Graph file to validate |
| `-r, --repair` | Auto-repair issues |
| `--json` | Output in JSON format |

### watch - File Monitoring

```bash
yata watch <DIRECTORY> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-p, --pattern` | Watch pattern |
| `-e, --exclude` | Exclusion pattern |
| `-d, --debounce` | Debounce delay in seconds (default: 1.0) |
| `-o, --output` | Auto-save path for graph |

### benchmark - Performance Measurement

```bash
yata benchmark <DIRECTORY> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-p, --pattern` | Target file pattern |
| `--json` | Output in JSON format |

### serve - Start MCP Server

```bash
yata serve [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-t, --transport` | Transport: `stdio` or `sse` (default: stdio) |
| `-p, --port` | Port for SSE (default: 8080) |

## 🏗️ Supported Languages (24 Languages)

| Language | Extension | Status |
|----------|-----------|--------|
| Python | `.py` | ✅ Supported |
| TypeScript | `.ts`, `.tsx` | ✅ Supported |
| JavaScript | `.js`, `.jsx` | ✅ Supported |
| Rust | `.rs` | ✅ Supported |
| Go | `.go` | ✅ Supported |
| Java | `.java` | ✅ Supported |
| Kotlin | `.kt` | ✅ Supported |
| Scala | `.scala` | ✅ Supported |
| C | `.c`, `.h` | ✅ Supported |
| C++ | `.cpp`, `.hpp` | ✅ Supported |
| C# | `.cs` | ✅ Supported |
| Swift | `.swift` | ✅ Supported |
| Objective-C | `.m` | ✅ Supported |
| PHP | `.php` | ✅ Supported |
| Ruby | `.rb` | ✅ Supported |
| Dart | `.dart` | ✅ Supported |
| Elixir | `.ex`, `.exs` | ✅ Supported |
| Haskell | `.hs` | ✅ Supported |
| Julia | `.jl` | ✅ Supported |
| Lua | `.lua` | ✅ Supported |
| Groovy | `.groovy` | ✅ Supported |
| SQL | `.sql` | ✅ Supported |
| Zig | `.zig` | ✅ Supported |
| YAML | `.yaml`, `.yml` | ✅ Supported |

## 📚 Supported Frameworks (47 Frameworks)

YATA provides pre-learned knowledge graphs of major framework structures.

### Python

| Framework | Category | Key Entities |
|-----------|----------|--------------|
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
|-----------|----------|--------------|
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
|-----------|----------|--------------|
| Actix-web | Web Framework | App, Route, Handler, Middleware |
| Tokio | Async Runtime | Runtime, Task, Channel, Stream |
| Serde | Serialization | Serialize, Deserialize, Attribute |
| Rocket | Web Framework | Route, Guard, Fairing, Responder |
| Axum | Web Framework | Router, Handler, Extension, State |
| Tauri | Desktop App | Command, Window, Plugin, State |

### Go

| Framework | Category | Key Entities |
|-----------|----------|--------------|
| Gin | Web Framework | Router, Handler, Middleware, Context |
| Echo | Web Framework | Router, Handler, Middleware, Context |
| Fiber | Web Framework | App, Route, Handler, Middleware |
| GORM | ORM | Model, DB, Query, Association |

### Elixir

| Framework | Category | Key Entities |
|-----------|----------|--------------|
| Phoenix | Web Framework | Controller, LiveView, Channel, Router |

### Database/ORM

| Framework | Language | Key Entities |
|-----------|----------|--------------|
| Prisma | TypeScript | Schema, Client, Query, Migration |
| Drizzle | TypeScript | Schema, Query, Migration, Relation |

### Mobile

| Framework | Language | Key Entities |
|-----------|----------|--------------|
| SwiftUI | Swift | View, State, Binding, Environment |
| Jetpack Compose | Kotlin | Composable, State, Modifier, Theme |

### Others

| Framework | Language | Category |
|-----------|----------|----------|
| Spring Boot | Java | Web Framework |
| .NET Core | C# | Web Framework |
| Ruby on Rails | Ruby | Web Framework |
| Laravel | PHP | Web Framework |

## 🎯 Detectable Design Patterns (10 Patterns)

| Pattern | Category | Detection Criteria |
|---------|----------|-------------------|
| Singleton | Creational | `getInstance`, `__new__`, static instance |
| Factory Method | Creational | `create*`, `build*`, `make*` methods |
| Builder | Creational | `set*`, `with*`, `build` chain |
| Adapter | Structural | `adapt`, `wrap`, interface conversion |
| Decorator | Structural | `@decorator`, wrapper functions |
| Facade | Structural | Unified interface for multiple services |
| Observer | Behavioral | `subscribe`, `notify`, `on*` events |
| Strategy | Behavioral | `execute`, `handle`, strategy interface |
| Command | Behavioral | `execute`, `undo`, command objects |
| Template Method | Behavioral | Abstract method + concrete implementation |

## 🔗 Automatic Relationship Detection

YATA automatically detects the following relationships:

| Relationship Type | Description |
|-------------------|-------------|
| `CALLS` | Function/method call relationships |
| `IMPORTS` | Module import relationships |
| `CONTAINS` | Module→Class→Method containment relationships |
| `INHERITS` | Class inheritance relationships |
| `DEPENDS_ON` | Dependencies (packages, inter-module) |
| `IMPLEMENTS` | Interface implementation relationships |

## 🛠️ Development

### Setup

```bash
# Clone the repository
git clone https://github.com/nahisaho/YATA.git
cd yata

# Install dependencies with uv
uv sync --all-packages

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=yata_core --cov=yata_mcp

# Run linter
uv run ruff check .
uv run mypy packages/
```

### Project Structure

```
yata/
├── packages/
│   ├── yata-core/          # Knowledge graph engine (library)
│   │   ├── src/yata_core/
│   │   │   ├── domain/     # Domain layer (entities, value objects)
│   │   │   ├── application/ # Application layer (use cases)
│   │   │   └── infrastructure/ # Infrastructure layer (parsers, storage)
│   │   └── tests/
│   └── yata-mcp/           # MCP Server (application)
│       ├── src/yata_mcp/
│       │   ├── server/     # MCP implementation (FastMCP)
│       │   └── cli/        # CLI implementation (Click)
│       └── tests/
├── steering/               # MUSUBI SDD project memory
└── storage/specs/          # Design documents
```

### Architecture

YATA is designed based on Clean Architecture:

- **Domain Layer**: Core entities (FunctionEntity, ClassEntity, etc.), value objects (EntityId, Location), repository interfaces
- **Application Layer**: Use cases (ParseFileUseCase, ParseDirectoryUseCase)
- **Infrastructure Layer**: Implementations (PythonParser, TypeScriptParser, NetworkXKnowledgeGraph)
- **Interface Layer**: MCP server and CLI

## 📊 Test Status

- **Test Count**: 592+
- **Coverage**: 82%+
- **Coverage Threshold**: 80% or higher
- **Supported Language Parsers**: 24
- **Framework Knowledge Graphs**: 47

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/) - Anthropic
- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) - AST Parser
- [NetworkX](https://networkx.org/) - Graph Library
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP SDK

## 📖 Documentation

- [AI Tools Setup Guide](docs/en/AI_TOOLS_SETUP.md) - Claude, Copilot, Cursor configuration
- [Knowledge Database Update Guide](docs/en/KNOWLEDGE_UPDATE_GUIDE.md) - How to update framework knowledge
- [Troubleshooting](docs/en/TROUBLESHOOTING.md) - Common issues and solutions
- [YATA vs Context7](docs/en/YATA_vs_Context7.md) - Detailed comparison with Context7
- [CHANGELOG](CHANGELOG.md) - Change history

---

**YATA** - Like the Yata no Kagami, reflecting the truth of code 🪞
