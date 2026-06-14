# MAGATAMA Showcase & Project Overview

> 🇯🇵 日本語版: [OVERVIEW_jp.md](OVERVIEW_jp.md)
> For the underlying idea, see [README.md](README.md).

---

## 🗺️ Why this document — what "handing over a map" means

Picture someone who has to read a huge amount of source code in a short time:
onboarding, an inherited legacy system, a first OSS contribution… There's
**no time to open and read every file**. What you want is a **map** of "what is
where".

- **comP** builds the map (analyzes code into `.comp/index.db`), and
- **MAGATAMA** (or comP MCP) pulls **only the block the LLM needs right now**
  out of that map and hands it over.

This document shows, **with plenty of "prompt → sample output" pairs**, what you
can actually do with that map. At the end, we **measure the token cost** of
working with the map versus without it.

> 📌 **Notation**
> - 🟢 **Measured** … real data from actually running comP / MAGATAMA.
> - 🔵 **Format illustration** … a representative example of a tool's response
>   format. The numbers are illustrative and vary by environment.

---

# Part 1 ｜ Using comP's map to grasp MAGATAMA itself 🟢

> 🟢 **Measured**: read the comP index (**203 files / 3,829 symbols**) from
> Claude Code via MCP and produced the following *without reading the source*.

## 1. In one line

An **MCP server** that turns a codebase into a "knowledge graph" and feeds AI
coding tools (Claude Desktop, Copilot, …) maximum context for minimum tokens.
A fork of YATA, plus re-parse-free import of comP's index.

## 2. The problem & value

Making an LLM understand code usually wastes tokens by feeding it full files.
MAGATAMA **compresses code into structure (entities + relationships)** and hands
over only search, impact analysis and call graphs. Fully local, no data leaves.

## 3. Big picture

```text
[comP Daemon] ─→ .comp/index.db (SQLite)
                       │ read-only connection
source ─Tree-sitter→ [MAGATAMA] ─→ NetworkX knowledge graph + 47-framework knowledge
                       │
                       ▼
       MCP Server (FastMCP / 36 tools) · CLI (Click)
                       │
                       ▼
          Claude Desktop / Cursor / Copilot
```

Designed on **Clean Architecture** (domain → application → infrastructure → interface).

## 4. Directory layout

| Path | Role |
|---|---|
| `packages/magatama-core/` | Knowledge graph engine (library): 24-language parsers, NetworkX graph, comP Bridge |
| `packages/magatama-mcp/` | MCP server + CLI (the `magatama` command) |
| `knowledge_graphs/` | Pre-built graphs for 47 frameworks (36 JSON files) |
| `storage/specs/` | Design docs (requirements, C4, ADRs) |
| `steering/` | Project rules & memory |
| `docs/` | User guides (JP/EN, 38 Markdown files) |

## 5. Tech stack

- **Language mix (measured by comP)**: Python 123 / Markdown 38 / JSON 36 / unknown 5 / YAML 1
- **Parsing**: `tree-sitter` + 23 language parsers (Python/TS/Rust/Go/Java/C#…)
- **Graph**: `networkx` / **validation**: `pydantic` / **logging**: `structlog`
- **MCP**: `mcp>=1.0` / **CLI**: `click`+`rich` / **SSE**: `uvicorn`+`httpx` / **watch**: `watchdog`
- **Layout**: uv monorepo (`magatama-core` lib + `magatama` app), Python 3.11+, MIT

## 6. How to use

```bash
magatama parse ./src -o graph.json        # parse → save the knowledge graph
magatama stats --graph graph.json         # show statistics
magatama query "UseCase" --type class --graph graph.json
magatama serve                            # start the MCP server (for AI tools)
```

## 7. Status

- **Maturity**: `Development Status :: 3 - Alpha` (pyproject classifiers)
- **Tests**: 794, coverage 76% (README). CLI tests verified locally.
- **Known limits / to confirm**: comP index dependency-edge count is `0`
  (to confirm). Index is slightly stale with a deleted file lingering →
  re-indexing should resolve it.

## 8. What to read next

1. `README.md` — the entry point to all features and the design philosophy
2. `packages/magatama-core/src/magatama_core/application/usecases/comp_usecase.py` — the comP Bridge core
3. `packages/magatama-core/src/magatama_core/infrastructure/storage/comp_index_reader.py` — SQLite → graph
4. `packages/magatama-mcp/src/magatama_mcp/server/mcp_server.py` — where the 36 tools register
5. `packages/magatama-core/src/magatama_core/application/usecases/framework_usecase.py` — largest module (133 symbols)

---

# Part 2 ｜ Showcase: prompt → sample output

Prompts you can **paste straight** into your AI tool's chat (Claude Desktop /
Copilot / Claude Code), grouped by capability, with the shape of the response.

## 🅰️ Overview a project with comP's map

### A-1. "Explain this repo in 5 minutes"

**Prompt**

```text
Check comP's map freshness with get_external_graph_info(path="e:/dev/myproject").
If fine, read_external_graph(path="e:/dev/myproject"), then use get_graph_stats
and search_entities to summarize "purpose, structure, key modules, where to start
reading" in 10 lines or fewer.
```

🟢 **Measured** (summary produced against MAGATAMA itself)

```text
✓ Map imported: 203 files / 3,829 symbols
- Purpose : an MCP server that graph-ifies code and feeds AI minimal-token context
- Structure: two packages — magatama-core (engine) + magatama-mcp (MCP+CLI)
- Languages: Python 123 / Markdown 38 / JSON 36
- Largest module: framework_usecase.py (133 symbols)
- Design  : Clean Architecture (domain→application→infrastructure→interface)
- Entry   : start from comp_usecase.py (the comP Bridge core)
```

### A-2. "Which files are 'heavy'?" (hotspot candidates)

**Prompt**

```text
From list_indexed_files, list the top 5 files by symbol count and explain each
file's role in one line.
```

🟢 **Measured** (from comP's Top Files by Symbol Count)

```text
1. framework_usecase.py            133  framework-knowledge use cases
2. docs/KNOWLEDGE_UPDATE_GUIDE.md   92  knowledge-DB update guide
3. sqlite_storage.py                68  SQLite persistence
4. test_framework_usecase.py        81  tests for the above
5. steering/product.ja.md           68  product direction notes
```

---

## 🅱️ What YATA already gives you (framework knowledge, cross-search, analysis)

MAGATAMA inherits all 36 YATA tools. Here are the signature ones as
prompt + sample output.

### B-1. Look up framework idioms — `search_framework_docs`

**Prompt**

```text
Show the supported frameworks with list_frameworks. Then use
search_framework_docs(framework="fastapi", query="dependency") to show the key
entities around FastAPI dependency injection.
```

🔵 **Format illustration**

```text
[frameworks] 47: fastapi, django, flask, react, vue, axum, gin, phoenix, ...
[fastapi / "dependency"]
  - Depends            (function)  declared on a route parameter to inject a dep
  - Dependency         (concept)   a reusable dependency provider
  - Security           (function)  authorized dependency (OAuth2, etc.)
```

### B-2. Your code × the official idiom at once — `hybrid_search`

**Prompt**

```text
hybrid_search(query="retry with backoff"): show both the official framework
idiom and where my code already does it.
```

🔵 **Format illustration**

```text
[Local]     util/http.py:42  request_with_retry()  ← already has exponential backoff
[Framework] tenacity: @retry(wait=wait_exponential())  the canonical idiom
→ Aligning your custom impl with tenacity will ease maintenance.
```

### B-3. Blast radius of a change — `analyze_impact` / `get_call_graph`

**Prompt**

```text
Find the target with search_entities(query="save_graph"), then analyze_impact for
the blast radius of changing it, and get_call_graph for the call relationships.
```

🔵 **Format illustration** (target 🟢 real: `_handle_save_graph`)

```text
[impact] _handle_save_graph (mcp_server.py:442)
  ← called by: the save command (cli/main.py), parse --output save path
  → depends on: NetworkXKnowledgeGraph.save(), entities.count()
[call graph]
  save (CLI) ──► call_tool("save_graph") ──► _handle_save_graph ──► graph.save()
→ When changing it, test both the CLI save and parse --output paths.
```

### B-4. Design-pattern detection — `detect_patterns`

**Prompt**

```text
Use detect_patterns to list the design patterns in this codebase, with one
representative location each.
```

🔵 **Format illustration**

```text
- Repository    : domain/repositories/*  (persistence abstraction)
- Use Case      : application/usecases/*  (business logic)
- Strategy      : infrastructure/parsers/* (per-language parser switching)
- Adapter       : comp_index_reader.py     (SQLite → graph)
```

### B-5. Quality metrics — `analyze_quality` / `find_hotspots`

**Prompt**

```text
Use analyze_quality for complexity/coupling concerns and find_hotspots for the
files that change most often in Git history.
```

🔵 **Format illustration**

```text
[quality] high complexity: framework_usecase.py (multi-purpose → split candidate)
[hotspots] recently most-changed: cli/main.py, mcp_server.py
→ ripple points for spec changes; focus your reviews here.
```

### B-6. Auto documentation — `generate_documentation`

**Prompt**

```text
generate_documentation(entity="LoadCompIndexUseCase"): draft a docstring for this
core class.
```

🔵 **Format illustration**

```text
LoadCompIndexUseCase — use case that imports comP's index.db into the graph.
  load(path, mode="replace"|"merge") -> import result (counts, removed, metadata)
  related: CompIndexReader (reads), NetworkXKnowledgeGraph (stores)
```

> These outputs are possible **because the map (index) lets the LLM skip the full
> source**. Without the map, getting the same answers means re-reading the source
> every time — which is exactly the next token comparison.

---

# Part 3 ｜ Measured token cost: with the map vs without 🟢

We measured "the tokens an LLM needs to produce the Part 1 overview" **with**
comP's map versus **without** it (reading all source).

## Method

- Target: Python source under `packages/magatama-core/src` and
  `packages/magatama-mcp/src` (excluding tests / `__pycache__`) — **64 files**.
- Tokenizer: `tiktoken` `cl100k_base` as a proxy (Claude's exact tokenizer is
  not public, so these are **estimates** for trend comparison).
- Script: `scripts/measure_overview_tokens.py` (reproducible).
  Command: `uv run --with tiktoken python scripts/measure_overview_tokens.py`
  (falls back to a chars/4 estimate when `tiktoken` is absent).

## A. With the map (read comP's structured summary)

| Data read | Tokens |
|---|---:|
| The summary actually used for the overview (stats + languages + top files) | **289** |
| Full comP index export (all 203 files' symbol listing) | 50,515 |

## B. Without the map (read all source)

| Data read | Chars | Tokens |
|---|---:|---:|
| Full text of 64 source files | 730,411 | **145,978** |

## Result

| Approach | Tokens | Reduction vs B | Ratio |
|---|---:|---:|---:|
| **B. Read all source** | 145,978 | — | baseline |
| A. Full comP index export | 50,515 | **−65.4%** | 2.9× less |
| **A. comP summary (used for the overview)** | **289** | **−99.8%** | **~505× less** |

---

## 🎁 Bottom line — why it's a great deal

- **Fast**: no waiting for the LLM to read every file — just the right block.
- **Cheap**: an overview costs **~1/500 of the tokens**; helps both API billing
  and context budget.
- **Broad**: cross-search 24 languages + 47 frameworks' idioms (36 YATA tools).
- **Safe**: fully local — your code never leaves the machine.
- **Easy**: install comP in VSCode and open the folder; the map auto-updates.
  Then just ask your AI.

> The map removes the "where do I even start?" paralysis in front of a mountain
> of code. Try **Steps 1–4** in [README.md](README.md) in about 10 minutes.

> Note: token counts use `cl100k_base` as a proxy; absolute values vary by model.
> What matters is the order-of-magnitude gap (hundreds vs ~150k tokens), which is
> a stable trend.
