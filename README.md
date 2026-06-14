# MAGATAMA (勾玉) — give your AI a *map* of a huge codebase

[![CI](https://github.com/tsucky230/MAGATAMA/workflows/CI/badge.svg)](https://github.com/tsucky230/MAGATAMA/actions)
[![Coverage](https://codecov.io/gh/tsucky230/MAGATAMA/branch/main/graph/badge.svg)](https://codecov.io/gh/tsucky230/MAGATAMA)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🇯🇵 [日本語版 README](README_jp.md)

---

## 🗺️ MAGATAMA in 30 seconds

Picture someone arriving in an unfamiliar city. Nobody walks every single
street end-to-end to find their way — they look at a **map** and learn only
the roads they need.

When people give an LLM (Claude, Copilot, …) a large codebase, they usually
make it **read all the source**. That's like walking every street: it burns
time — which here means tokens, which means cost.

This is where pairing with its **sibling tool
[comP](https://github.com/tsucky230/comP) (a VSCode extension)** pays off.
MAGATAMA works on its own, but combined with comP the benefit doubles. Their
roles split like this:

- **comP** is the **surveyor** that walks your code and builds a **map (index)**.
- **MAGATAMA** is the **guide** that reads that map and hands the LLM *only the
  block it needs right now*.

So the LLM grasps the structure — functions, classes, dependencies — without
reading the full source. Measured on this very repo, a project overview took
about **1/500 of the tokens** (full data in [OVERVIEW.md](OVERVIEW.md)).

> **In one line:** MAGATAMA is an **MCP server** that turns code into a
> "knowledge graph (map)" and feeds an AI maximum context for minimum tokens.
> It is a fork of [YATA (八咫)](https://github.com/nahisaho/YATA) plus direct
> integration with the [comP](https://github.com/tsucky230/comP) code indexer.

---

## 💡 What you can actually do (3 signature scenes)

### Scene 1: Grasp an unfamiliar giant repo in 5 minutes

> "What does this repo do, how is it structured, where do I start reading?"

Instead of opening every file, the LLM reads only the **stats, top modules and
exported symbols** from comP's map and returns an overview. We did exactly this
on MAGATAMA itself — see [OVERVIEW.md](OVERVIEW.md).

### Scene 2: Know what breaks if you change a function

> "If I touch `save_graph`, what's affected?"

`analyze_impact` / `get_call_graph` walk the map and return the **blast radius**.
The structure graph replaces the manual grep-and-eyeball loop.

### Scene 3: Write idiomatic framework code

> "What's the right way to do dependency injection in FastAPI?"

MAGATAMA ships **built-in knowledge graphs for 47 frameworks**, so
`hybrid_search` cross-searches your code *and* the official idioms (from YATA).

---

## 🧩 How comP and MAGATAMA fit together

```text
[comP (VSCode extension + Rust daemon)]
        │ analyzes the workspace and writes the map
        ▼
   .comp/index.db  (SQLite, WAL mode)   ← the city map
        │
        ├─→ comP MCP ……………… query the map directly (file summary, one symbol — lightweight)
        │
        └─→ MAGATAMA Bridge … import the map into a knowledge graph, analyze (36 tools)
                  │
                  ▼
        Claude Desktop / Cursor / Copilot / Claude Code
```

- **comP** = builds the map and answers cheap lookups (`get_file_summary`, `get_symbol`).
- **MAGATAMA** = analyzes the whole map (`search_entities`, `analyze_impact`, `hybrid_search`).

---

## 🚀 Setup (with worked examples)

Goal: **① index code with comP → ② install MAGATAMA → ③ register it as an MCP
server in your AI tool → ④ verify.**

### Step 1. Install comP as a VSCode extension and start indexing

1. Install the comP extension (`tsucky230.comp-vscode`) in VSCode
   (see the [comP repo](https://github.com/tsucky230/comP) for the VSIX/steps).
2. Open your project folder in VSCode.
3. comP analyzes the workspace automatically and writes the map to
   **`<project>/.comp/index.db`** (SQLite, WAL mode). Only the first pass is
   slow; afterwards it updates incrementally on change.

> Check: you should see a `.comp/` folder containing `index.db`.

To connect comP itself to an AI as an MCP server, add this to `.mcp.json`
(real example from this repo):

```json
{
  "mcpServers": {
    "comp": {
      "command": "c:\\Users\\<you>\\.vscode\\extensions\\tsucky230.comp-vscode-0.8.1\\daemon\\target\\release\\comp-daemon-win.exe",
      "args": [],
      "env": {
        "COMP_WORKSPACE_ROOT": "e:\\dev\\MAGATAMA",
        "RUST_LOG": "info"
      }
    }
  }
}
```

> Point `COMP_WORKSPACE_ROOT` at the folder you want indexed, and replace the
> version in the path (`0.8.1`) with the extension version you installed.

### Step 2. Install MAGATAMA

```bash
# From source (this repo)
git clone https://github.com/tsucky230/MAGATAMA.git
cd MAGATAMA
uv sync --all-packages       # no uv yet? https://astral.sh/uv

# Or from PyPI
pip install magatama
```

Verify:

```bash
magatama info        # shows the version and tool count (36) if OK
```

### Step 3. Register it as an MCP server

#### Claude Desktop (Windows)

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\path\\to\\MAGATAMA", "magatama", "serve"]
    }
  }
}
```

#### GitHub Copilot / VS Code

`.vscode/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}", "magatama", "serve"]
    }
  }
}
```

With the PyPI install you can use `"command": "magatama", "args": ["serve"]`.
For Cursor / Continue and SSE mode, see the
[AI Tools Setup Guide](docs/AI_TOOLS_SETUP.md).

### Step 4. Connect and use it

Restart your AI tool and ask, in chat:

```text
Call get_external_graph_info(path="e:/dev/myproject") to check comP's map.
If it looks good, read_external_graph it and give me an overview of the project.
```

The LLM imports comP's map into MAGATAMA and overviews the project without
reading the full source.

---

## 🎬 Try it: prompt → sample output

What it feels like in practice (typed into your AI tool's chat).

### Example A: project overview

**Prompt**

```text
read_external_graph(path="e:/dev/MAGATAMA"), then use get_graph_stats to
summarize the size and structure of this project.
```

**Sample output (real data)**

```text
✓ Imported (203 files / 3,829 symbols)
- Languages: Python 123 / Markdown 38 / JSON 36 / YAML 1
- Largest module: framework_usecase.py (133 symbols)
- Layout: packages/magatama-core (engine) + packages/magatama-mcp (MCP+CLI)
→ Clean Architecture (domain → application → infrastructure → interface)
```

### Example B: impact analysis

**Prompt**

```text
search_entities(query="save_graph") to find the target, then analyze_impact
to tell me the blast radius of changing this function.
```

**Sample output**

```text
Target: _handle_save_graph (mcp_server.py:442)
Possibly affected: the `save` command (cli/main.py), parse --output save path
→ When changing it, check the tests on these two paths.
```

### Example C: framework idioms (from YATA)

**Prompt**

```text
hybrid_search(query="FastAPI dependency injection") to cross-search the
official idiom and where my code does it.
```

**Sample output**

```text
[Framework] FastAPI: declare Depends() as a function parameter (Router/Dependency)
[Local]    (no match) → you're not using DI yet. Candidate: the routes layer
```

> Want to try it from the CLI only? Persist the map to JSON and reuse it:
>
> ```bash
> magatama parse ./src -o graph.json
> magatama stats --graph graph.json
> magatama query "UseCase" --type class --graph graph.json
> ```

---

## 🔧 MCP Tools (36)

The LLM autonomously picks **only the tools it needs** from these.

<details>
<summary><b>🔌 comP Bridge (2) — import the map</b></summary>

| Tool | Description |
|------|-------------|
| `read_external_graph` | Load a comP index into the knowledge graph (`mode=replace`/`merge`) |
| `get_external_graph_info` | Inspect comP index stats without loading (freshness check) |

</details>

<details>
<summary><b>📁 Core (10) — parse & search</b></summary>

| Tool | Description |
|------|-------------|
| `parse_file` / `parse_directory` | Parse source and extract entities |
| `search_entities` / `get_entity` | Search by name/type / get details |
| `get_related_entities` | Adjacent nodes (related entities) |
| `get_graph_stats` | Graph statistics |
| `save_graph` / `load_graph` | Save/load to JSON |
| `list_supported_languages` / `get_language_for_file` | List 24 languages / detect |

</details>

<details>
<summary><b>🧠 Framework knowledge (7) — built-in maps for 47 frameworks</b></summary>

`list_frameworks` / `search_framework_docs` / `search_all_frameworks` /
`find_code_patterns` / `get_framework_entity_context` /
`framework_semantic_search_tool` / `framework_find_by_pattern`

</details>

<details>
<summary><b>🔍 Search & context (4) / 📚 Docs & recommendation (4)</b></summary>

`semantic_search` / `find_by_pattern` / `get_code_context` /
`find_usage_examples` · `generate_documentation` / `recommend_code` /
`analyze_impact` / `find_critical_paths`

</details>

<details>
<summary><b>🔎 Hybrid search & quality (4) / 🤖 AI assistance (5)</b></summary>

`hybrid_search` / `analyze_quality` / `track_evolution` / `find_hotspots` ·
`get_coding_guidance` / `detect_patterns` / `check_api_compatibility` /
`navigate_code` / `get_call_graph`

</details>

**MCP Prompts**: `analyze_codebase` / `explain_entity` / `find_dependencies`
**MCP Resources**: `magatama://graph/stats`

---

## 💻 CLI commands (for humans at the terminal)

| Command | What it does | Example |
|---------|--------------|---------|
| `parse` | Build a knowledge graph (`-o` to save) | `magatama parse ./src -o graph.json` |
| `query` | Search entities | `magatama query "User" -t class -g graph.json` |
| `stats` | Show statistics | `magatama stats -g graph.json` |
| `serve` | Start the MCP server | `magatama serve` / `--transport sse --port 8080` |
| `watch` | Watch & auto-update (`-o` auto-saves) | `magatama watch ./src -o graph.json` |
| `validate` | Check graph integrity (`--repair`) | `magatama validate -g graph.json --repair` |
| `info` | Server info & tool list | `magatama info` |

> Note: `parse`/`query`/`stats` are **stateless across processes**. Use
> `parse -o` to write the map to JSON, then load it with `--graph` in
> `query`/`stats`. For AI integration, the long-running `serve` process holds
> the graph and the LLM calls the tools instead.

---

## 🏗️ Languages & frameworks

- **24 languages**: Python, TypeScript/JS, Rust, Go, Java, Kotlin, Scala,
  C/C++, C#, Swift, Objective-C, PHP, Ruby, Dart, Elixir, Haskell, Julia, Lua,
  Groovy, SQL, Zig, YAML
- **47 frameworks** (457K+ entities): Django/Flask/FastAPI, React/Vue/Angular/
  Next.js, Actix/Axum/Tauri, Gin/Echo, Phoenix, Spring Boot, Rails, Laravel,
  SwiftUI, Jetpack Compose, and more

---

## 🛠️ Development

```bash
uv sync --all-packages
uv run pytest                         # tests (794)
uv run pytest --cov=magatama_core --cov=magatama_mcp
uv run ruff check . && uv run mypy packages/
```

```text
MAGATAMA/
├── packages/
│   ├── magatama-core/   # Knowledge graph engine (library)
│   └── magatama-mcp/    # MCP server + CLI (the `magatama` command)
├── steering/            # Project memory & rules
└── storage/specs/       # Design docs (requirements, C4, ADRs)
```

Built on **Clean Architecture**. Details & measurements in [OVERVIEW.md](OVERVIEW.md).

---

## 📜 License / Credits

MIT License. This project forks
[YATA](https://github.com/nahisaho/YATA) (Copyright (c) 2025 nahisaho) under
the MIT License and adds the comP Bridge.

- [YATA](https://github.com/nahisaho/YATA) by **nahisaho** — the foundation
- [comP](https://github.com/tsucky230/comP) by **tsucky230** — code indexer
- [Model Context Protocol](https://modelcontextprotocol.io/) / Tree-sitter / NetworkX / FastMCP

---

## 📖 Documentation

- [Project overview + token measurement (OVERVIEW.md)](OVERVIEW.md)
- [AI Tools Setup Guide](docs/AI_TOOLS_SETUP.md)
- [Knowledge Database Update Guide](docs/KNOWLEDGE_UPDATE_GUIDE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [日本語 README](README_jp.md) / [CHANGELOG](CHANGELOG.md)

---

## 📛 About the name

**YATA (八咫)** is an old word for "very large", reflecting the goal of handling
vast codebases and framework knowledge whole. **MAGATAMA (勾玉)** is "a small
stone that condenses great power" — extracting the essence from that vastness
and delivering it densely to the LLM. Like the magatama, one of Japan's three
imperial treasures.
