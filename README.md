# MAGATAMA (勾玉) — give your AI a *map* of a huge codebase

[![CI](https://github.com/tsucky230/MAGATAMA/workflows/CI/badge.svg)](https://github.com/tsucky230/MAGATAMA/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🇯🇵 [日本語版 README](README_jp.md)

---

## 🗺️ MAGATAMA in 30 seconds

Nobody arriving in an unfamiliar city walks every street to learn their way
around. They look at a **map** and learn only the roads they need.

Yet when people hand an LLM (Claude, Copilot, …) a large codebase, they
usually make it **read all the source**. That's the same as walking every
street: time — which here means tokens, which means cost — goes up in smoke.

That's where the sibling tool **[comP](https://github.com/tsucky230/comP)**
(a VSCode extension) comes in, splitting the work:

- **comP** = the **surveyor** that walks the code and builds the **map (index)**
- **MAGATAMA** = the **guide** that reads the map and hands the LLM **only the
  block it needs right now**

Measured on this very repo, grasping a project overview took about
**1/500 of the tokens** (full data: [OVERVIEW.md](OVERVIEW.md)).

> **In one line**: an MCP server that turns code into a "knowledge graph
> (map)" and feeds an AI **maximum context for minimum tokens**. A fork of
> [YATA (八咫)](https://github.com/nahisaho/YATA) plus a direct
> [comP](https://github.com/tsucky230/comP) integration bridge.

---

## 📊 Where it actually pays off, and where it doesn't

The payoff depends on what you're doing. Here's the honest breakdown.

| Use case | Typical savings | Why |
| --- | --- | --- |
| **Overview of a huge repo** | **~1/500** (measured) | Reading everything is replaced by reading "stats + top modules + exported symbols" |
| **Change impact analysis** | **Large** | `analyze_impact` returns the blast radius **already scored `risk=high/medium/low`** — the tokens the LLM would spend aggregating and interpreting disappear entirely |
| **Writing idiomatic framework code** | **Large (indirect)** | `hybrid_search` cross-searches a knowledge graph for 47 frameworks. Kills the **hallucinate a nonexistent API → implement → fail → redo** loop |
| **Session handoff** | **Large** | `generate_handoff` auto-generates a handoff doc within a token budget — no more re-explaining context |
| **One-off questions on a small repo** | Small | Connecting comP directly is enough (see the comparison table below) |
| **Work unrelated to code** | None | Out of scope |

### Two effects the numbers don't capture

**① Failed-retry loops disappear**
The hidden cost of a cheap model is the "implement on a wrong assumption →
fail → redo" loop. MAGATAMA attacks it from two directions:

```
Direction 1 (prevents structural misunderstanding):
  analyze_impact surfaces the blast radius already risk-scored
  → rework caused by "a call site nobody noticed" disappears

Direction 2 (prevents knowledge hallucination):
  hybrid_search shows the official idiom next to your own code
  → rework caused by "a plausible but nonexistent API" disappears
```

**② Offloading judgment (helps cheaper models the most)**
Connecting comP directly gets you "a list of related nodes" — **interpretation
is left to the LLM**. A strong model can interpret that fine; a cheap model
gets it wrong. MAGATAMA does the interpretation (risk scoring, aggregation,
quality analysis) **with deterministic code before handing it over**, so
**less of the outcome depends on the model's judgment** — which widens what a
cheap model can safely handle.

---

## 💡 What you can actually do (5 signature scenes)

### Scene 1: Grasp an unfamiliar giant repo in 5 minutes

> "What does this repo do, and where do I start reading?"

Instead of opening every file, the LLM reads only the map's **stats, top
modules, and exported symbols** and returns an overview. We did exactly this
on MAGATAMA itself — see [OVERVIEW.md](OVERVIEW.md).

### Scene 2: Know what breaks if you change a function

> "If I touch `save_graph`, what's affected?"

`analyze_impact` / `get_call_graph` walk the map and return the **blast
radius, already risk-scored**. No more grep-and-eyeball loops.

### Scene 3: Write code that follows a framework's conventions

> "What's the right way to do dependency injection in FastAPI?"

MAGATAMA ships **built-in knowledge graphs for 47 frameworks** (from YATA), so
`hybrid_search` cross-searches the official idiom and your own code.

### Scene 4: "Which past request touched this file again?"

> "I want to rework auth — what did past sessions ask about it?"

comP records your AI conversations under `.comp/`. MAGATAMA's
`read_external_sessions` puts those **conversation records on the same graph
as your code**, wiring each record to the files and symbols it mentioned
(DISCUSSED edges). From then on, `get_related_entities` on a file also returns
the past requests that touched it. **The conversation memory and the code map
become one map.**

### Scene 5: Hand over "what changed while you were away" automatically

> "Someone on the team changed something last night. What's affected?"

Keep `magatama patrol` running and it periodically re-reads comP's map,
**detects the diff since the last pass** (added/changed/removed symbols),
attaches impact and quality analysis to each change, and **writes the
findings into comP's conversation history**. When the next chat starts and
the AI calls `session_recall`, it already knows what changed and where it
hurts.

```bash
magatama patrol . --interval 600   # patrol every 10 minutes
magatama patrol . --once           # single pass (cron / CI)
```

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
        └─→ MAGATAMA Bridge … import the map into a knowledge graph, analyze (39 tools)
                  │
                  ▼
      Claude Desktop / Claude Code / Cursor / Copilot
```

### "Isn't connecting comP directly enough?"

**For one-off lookups — yes, it is.** MAGATAMA's value starts *after* the
lookup.

| | comP directly | With MAGATAMA |
|---|---|---|
| **Impact analysis** | Returns the list of connected nodes (interpretation left to the LLM) | Scores it against thresholds and returns `risk=high/medium/low` — saving the tokens the LLM would spend aggregating |
| **Conversation memory** | `session_recall` = a flat list with substring filter | Conversation records become graph nodes next to your code; "past requests that touched this file" is one graph query away |
| **Where it runs** | Needs the VSCode extension's daemon | Reads index.db directly, so it works in CI/cron with no editor (`patrol`) |
| **Cross-project** | One daemon = one workspace | Load multiple projects' maps into one graph and query across them |
| **Knowledge** | Your code only | Built-in knowledge graphs for 47 frameworks, cross-searchable |

In one line: **comP draws the map; MAGATAMA is the analyst and note-taker
working on top of it.**

---

## 🤖 Getting the most out of it with Claude

### Pattern ①: Start every new session from a handoff

Chain session end and session start with these two lines:

```markdown
# At the end of a session:
Run generate_handoff to turn today's decisions and open issues into a handoff doc

# At the start of the next session:
Restore the previous handoff with session_recall before starting work
```

`generate_handoff` **auto-summarizes to fit a token budget** and writes it
into comP's history, so the next session's `session_recall` reliably picks it
up. No more hand-written handoff notes.

### Pattern ②: Feed cheap models "pre-judged" data

This pays off most in a tiered setup — a strong model for design, a cheap
model for implementation:

```markdown
# Strong model (design session):
Attach the analyze_impact results and the handoff, and write an implementation step list

# Cheap model (implementation session):
Implement strictly within the handoff and the risk=low impact list.
If you need to touch a file outside the list, stop and report instead of implementing
```

The cheap model only ever sees **material that's already judged and scoped**.
It structurally removes the room to go astray.

### Pattern ③: Give the reviewer objective data

In a review session (a separate conversation from implementation):

```markdown
Review this diff against the results of analyze_impact / analyze_quality /
find_hotspots. Prioritize flagging any risk=high blast-radius spot that
hasn't been touched
```

The LLM's "gut-feel review" becomes a two-stage process: mechanical
graph-derived detection, then LLM interpretation.

### Pattern ④: Make review asynchronous with patrol

Run `magatama patrol` on a Raspberry Pi or in CI, and **diff detection and
impact analysis are already done by the time anyone opens a chat**. The
first session of the day can start from "judging," not "investigating."

### Pattern ⑤: A template for reading an unfamiliar OSS repo

```markdown
Check the map's freshness with get_external_graph_info(path="...").
If it looks good, read_external_graph → get_graph_stats for the big picture,
then find_critical_paths for the order to read things in
```

---

## 📝 Rolling this into CLAUDE.md (prompt library)

Installing MAGATAMA without updating the AI's own rules of engagement leaves
most of the value on the table. Feed Claude the prompts below to rewrite
CLAUDE.md around MAGATAMA.

### Prompt ①: initial rollout (add MUST/NEVER rules)

```markdown
Add the following rules to CLAUDE.md as MUST/NEVER:

MUST:
- At session start, restore the handoff and patrol notes via session_recall
- For a whole-codebase overview, use read_external_graph + get_graph_stats first
- Before changing existing code, run analyze_impact and list any risk=high blast radius
- Before using a framework API, confirm the official idiom with hybrid_search
- Run generate_handoff before ending a session

NEVER:
- Read the full source of a project that's already graphed
- Change an existing function's signature without going through analyze_impact
- Use a framework API that hasn't been confirmed with hybrid_search

Attach one reason per rule, and flag any conflict with existing rules.
```

### Prompt ②: prevent a repeat of a hallucinated-API incident (learn from a violation)

```markdown
You just implemented something using a FastAPI API that doesn't exist, and it
failed. Checking with hybrid_search first would have caught it.
State the root cause in one line, and propose a one-line addition to the
NEVER section of CLAUDE.md to prevent the same kind of incident.
```

### Prompt ③: wire it into a 3-stage workflow

```markdown
My dev flow is design → implement → review. Write a draft "MAGATAMA usage by
stage" section for CLAUDE.md specifying which MAGATAMA tool
(read_external_graph / analyze_impact / hybrid_search / generate_handoff /
analyze_quality / find_hotspots / session_recall) to use at each stage and in
what order. Optimize for minimum tokens above all else.
```

### Prompt ④: pin down the division of memory responsibilities (vs. comP / Claude memory)

```markdown
Add this line to CLAUDE.md:
"Memory has three sources of truth: code structure and impact analysis live
in MAGATAMA (the graph), session records live in comP (.comp/), and
person/preference facts live in Claude's memory. Never duplicate the same
fact across layers."
```

> 💡 CLAUDE.md is meant to grow "one line per failure." The fastest loop is
> violation → root cause → add a rule.

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
magatama info        # shows the version and tool count (39) if OK
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

## 🔧 MCP Tools (39)

The LLM autonomously picks **only the tools it needs** from these.

**🔌 comP Bridge (5) — import the map and the memory**

| Tool | Description |
|------|-------------|
| `read_external_graph` | Load a comP index into the knowledge graph (`mode=replace`/`merge`) |
| `read_external_sessions` | Import comP conversation history as SESSION nodes, wired to the files/symbols they mention (DISCUSSED edges) |
| `get_entity_history` | For a file/symbol: past session records that discussed it (newest first) + current impact analysis, in one call |
| `generate_handoff` | Build a handoff Markdown (recent sessions + git state, token-budgeted); full text under `.magatama/handoffs/`, one-line summary into comP history |
| `get_external_graph_info` | Inspect comP index stats without loading (freshness check) |

**📁 Core (10) — parse & search**

`parse_file` / `parse_directory` / `search_entities` / `get_entity` / `get_related_entities` / `get_graph_stats` / `save_graph` / `load_graph` / `list_supported_languages` / `get_language_for_file`

**🧠 Framework knowledge (7) — built-in maps for 47 frameworks**

`list_frameworks` / `search_framework_docs` / `search_all_frameworks` / `find_code_patterns` / `get_framework_entity_context` / `framework_semantic_search_tool` / `framework_find_by_pattern`

**🔍 Search & context (4) / 📚 Docs & recommendation (4)**

`semantic_search` / `find_by_pattern` / `get_code_context` / `find_usage_examples` · `generate_documentation` / `recommend_code` / `analyze_impact` / `find_critical_paths`

**🔎 Hybrid search & quality (4) / 🤖 AI assistance (5)**

`hybrid_search` / `analyze_quality` / `track_evolution` / `find_hotspots` · `get_coding_guidance` / `detect_patterns` / `check_api_compatibility` / `navigate_code` / `get_call_graph`

**MCP Prompts**: `analyze_codebase` / `explain_entity` / `find_dependencies` **MCP Resources**: `magatama://graph/stats`

---

## 💻 CLI commands (for humans at the terminal)

| Command | What it does | Example |
|---------|--------------|---------|
| `parse` | Build a knowledge graph (`-o` to save) | `magatama parse ./src -o graph.json` |
| `query` | Search entities | `magatama query "User" -t class -g graph.json` |
| `stats` | Show statistics | `magatama stats -g graph.json` |
| `serve` | Start the MCP server | `magatama serve` / `--transport sse --port 8080` |
| `watch` | Watch & auto-update (`-o` auto-saves) | `magatama watch ./src -o graph.json` |
| `patrol` | Patrol comP's map periodically; note diffs + impact analysis into comP's history | `magatama patrol . --interval 600` |
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
uv run pytest                         # tests (918)
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
[YATA](https://github.com/nahisaho/YATA) (Copyright (c) 2025 nahisaho, MIT
License) and adds the comP Bridge.

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

## 💖 Support This Project

MAGATAMA is free and open-source. If you find it valuable, consider supporting development:

- ☕ **[GitHub Sponsors](https://github.com/sponsors/tsucky230)** — Support ongoing development
- 💖 **Star this repository** — Help others discover MAGATAMA

---

## 📛 About the name

**YATA (八咫)** is an old word for "very large", reflecting the goal of handling
vast codebases and framework knowledge whole. **MAGATAMA (勾玉)** is "a small
stone that condenses great power" — extracting the essence from that vastness
and delivering it densely to the LLM. Like the magatama, one of Japan's three
imperial treasures.
