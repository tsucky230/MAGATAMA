# MAGATAMA (勾玉) — know where a code change reaches

> [日本語で読む](README_jp.md)

You have found the function to change. The hard part is knowing what else depends on it, which past decision shaped it, and where to check after the edit.

**comP indexes the code. MAGATAMA turns that graph into a change review you can act on.** Give it a file path and it returns the indexed symbols, callers and other dependents, the files they live in, and the dependency edge behind each result. When comP history is available, you can also ask which earlier work discussed that code.

## See the change before making it

Imagine changing a function in a shared library. A search for its name can miss calls through another module. Reading every file takes time and still leaves you to assemble the relationships yourself.

| Step | What you get |
| --- | --- |
| comP indexes the repository | A local map of files, symbols, and dependencies |
| MAGATAMA analyzes the file | A list of potentially affected code, grouped by file, with a reason for each link |
| You review the result | A focused set of places to inspect and tests to choose |

For example, a fixture with a main application and an additional library root produces this result:

~~~text
Changed file: E:/dev/shared/src/app.py
Changed symbol: main
Affected: src/app.py :: main
Reason: src/app.py :: main calls the changed symbol
~~~

The result is a **review starting point**, not a promise that every runtime effect has been found. If a path is ambiguous, the index has no dependency edges or has skipped edges, or it contains duplicate file entries, MAGATAMA reports the risk as **unknown** instead of calling the change safe.

## Why use both?

comP already provides relevant code retrieval, an impact graph, and session recall. Use it directly when you need to locate or read a symbol. MAGATAMA adds a file-level change view over comP's graph, attaches past discussion to code entities, and can leave patrol notes for the next session.

| Your question | Start with |
| --- | --- |
| “Which function should I read?” | comP run_pipeline or get_context |
| “If I edit these files, which indexed callers should I inspect?” | MAGATAMA analyze_change_scope |
| “Why was this file changed before?” | MAGATAMA get_entity_history, after loading comP history |
| “What changed since the last patrol?” | MAGATAMA patrol, then comP session_recall |

A comP index is required for the bridge features. comP's conversation recording is a beta feature and is **off by default**; history questions require records already present in .comp/session-memory.json or .comp/history/. The Claude Stop hook in this repository is for development of MAGATAMA and is not installed by the PyPI package.

## Try it on your repository

1. [Install and start comP](https://github.com/tsucky230/comP#installation--setup-3-steps) in VS Code. Open your project and confirm that it has .comp/index.db. comP's **Setup Agents** command can connect comP itself to your assistant.
2. Run MAGATAMA from a checkout that contains this change. `analyze_change_scope` is not yet part of the published PyPI release; a fresh clone of the default branch will have it after this change lands there:

~~~bash
git clone https://github.com/tsucky230/MAGATAMA.git
cd MAGATAMA
uv sync --all-packages --dev
uv run magatama info
~~~

3. Register MAGATAMA as an MCP server in your assistant. For a client that uses .mcp.json, the entry is:

~~~json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", "<path-to-MAGATAMA-checkout>", "magatama", "serve"]
    }
  }
}
~~~

Restart the assistant after adding the server. See the [AI tools setup guide](docs/AI_TOOLS_SETUP.md) for client-specific configuration.

4. Ask the assistant to use the actual path to your project:

~~~text
Check get_external_graph_info(path="<your-project>").
Then run analyze_change_scope(path="<your-project>",
files=["src/the-file-you-plan-to-change.py"]).
Show the affected files and the dependency reason for each one.
If risk is unknown, explain what index data needs checking.
~~~

The main workspace uses relative paths. On comP builds that index additional roots, those files use absolute paths. Use the full path when two roots contain the same file name.

## What the numbers do and do not show

An earlier [reproducible overview experiment](OVERVIEW.md) on this repository compared **145,978 estimated input tokens** for reading a selected set of source files with **289 tokens** for a compact comP map summary used to orient the reader. That measures one overview task on an older snapshot. It does not measure impact accuracy, total development cost, or a universal saving for every repository.

For change reviews, the useful result is concrete: the affected paths and the graph edges behind them. Check those against code and tests before editing. MAGATAMA's high/medium/low score is a heuristic over indexed relationships.

## More ways to use the graph

- **Review a PR:** compare its changed files with analyze_change_scope results and inspect affected callers that the diff did not touch.
- **Plan a shared-library update:** follow dependency edges into consumers across roots when the comP index contains those roots.
- **Resume work:** combine get_entity_history with comP session_recall to recover earlier decisions tied to a file.
- **Check overnight changes:** run magatama patrol periodically and read its notes in comP history.

The first three are workflows you can try now where the required index and history exist. Automated test selection and PR annotations are ideas for later work, not current features.

## Reference and development

- [Japanese README](README_jp.md)
- [Web introduction](docs/index.html)
- [comP integration contract and findings](docs/COMP_INTEGRATION.md)
- [AI tools setup](docs/AI_TOOLS_SETUP.md)
- [Technical overview and measurement method](OVERVIEW.md)
- [Changelog](CHANGELOG.md)
- [comP](https://github.com/tsucky230/comP)

From source, use uv sync --all-packages --dev and uv run pytest. The codebase targets Python 3.11 and newer and is based on [YATA](https://github.com/nahisaho/YATA). MAGATAMA is MIT licensed. Issues and contributions are welcome in the [repository](https://github.com/tsucky230/MAGATAMA).
