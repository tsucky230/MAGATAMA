# MAGATAMA Troubleshooting Guide

A compilation of common issues and solutions.

---

## About MAGATAMA / YATA

**MAGATAMA (勾玉)** is a fork of [YATA (八咫)](https://github.com/nahisaho/YATA) that adds the comP Bridge feature.
The lineage below describes the origin and background of YATA, the upstream project this fork is based on.

**YATA (八咫)** was born as a system to enhance [MUSUBI](https://github.com/nahisaho/musubi) (Ultimate Specification Driven Development).

YATA is the **second MCP Server** following [CodeGraph MCP Server](https://github.com/nahisaho/CodeGraphMCPServer). While CodeGraph MCP Server specializes in building knowledge graphs for codebases, YATA provides more advanced AI coding support features including framework knowledge graphs, design pattern detection, and code quality analysis.

YATA implements features that surpass [Context7](https://context7.com/). See [YATA vs Context7](YATA_vs_Context7.md) for details.

| Project | Role |
|---------|------|
| [MUSUBI](https://github.com/nahisaho/musubi) | Ultimate Specification Driven Development Framework |
| [CodeGraph MCP Server](https://github.com/nahisaho/CodeGraphMCPServer) | Codebase Knowledge Graph MCP Server (1st) |
| [YATA](https://github.com/nahisaho/YATA) | AI Coding Support MCP Server (2nd, upstream of this fork) |
| **MAGATAMA** | YATA fork + comP Bridge (this project) |
| [Context7](https://context7.com/) | Library Documentation MCP Server (Comparison target) |

---

## Table of Contents

- [Installation Issues](#installation-issues)
- [MCP Server Issues](#mcp-server-issues)
- [Analysis Issues](#analysis-issues)
- [Performance Issues](#performance-issues)
- [AI Tool Integration Issues](#ai-tool-integration-issues)
- [Error Message Reference](#error-message-reference)

---

## Installation Issues

### `uv` command not found

**Symptom:**

```
bash: uv: command not found
```

**Solution:**

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart shell, or
source ~/.bashrc  # or ~/.zshrc
```

### Dependency Installation Error

**Symptom:**

```
Error: Could not find tree-sitter-python
```

**Solution:**

```bash
# Clear cache and reinstall
uv cache clean
uv sync --all-packages --reinstall
```

### Python Version Error

**Symptom:**

```
Requires Python 3.11+
```

**Solution:**

```bash
# Install Python 3.11+
# macOS
brew install python@3.12

# Ubuntu
sudo apt install python3.12

# Use specific version with uv
uv python install 3.12
```

---

## MCP Server Issues

### Server Won't Start

**Symptom:**

```
Error: Failed to start server
```

**Check the following:**

1. Check if port is in use (for SSE mode):

```bash
lsof -i :8080
# If in use, specify different port
magatama serve --transport sse --port 8081
```

2. Check if dependencies are correctly installed:

```bash
uv run python -c "import fastmcp; print(fastmcp.__version__)"
```

### Hangs in stdio Mode

**Symptom:**

Prompt doesn't return after starting server.

**Explanation:**

This is normal behavior. In stdio mode, the server communicates with MCP clients via standard I/O.

**Verification method:**

```bash
# Verify operation in another terminal
echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{}}' | magatama serve | head -1
```

### Cannot Connect in SSE Mode

**Symptom:**

```
Connection refused: localhost:8080
```

**Solution:**

1. Check if server is running:

```bash
curl http://localhost:8080/health
```

2. Check firewall settings
3. Verify correct port is specified

---

## Analysis Issues

### Files Not Recognized

**Symptom:**

```
No files matched pattern
```

**Solution:**

1. Check patterns:

```bash
# Default pattern
magatama parse ./src --pattern "**/*.py"

# Multiple patterns
magatama parse ./src --pattern "**/*.py" --pattern "**/*.ts"
```

2. Try with absolute path:

```bash
magatama parse /absolute/path/to/project
```

### Parsing Files with Syntax Errors

**Symptom:**

```
Parse error in file.py
```

**Explanation:**

MAGATAMA attempts to parse files even with syntax errors. Parts with errors are ignored, and only parseable parts are processed.

**Solution:**

1. Fix syntax errors in the file
2. Or exclude the file:

```bash
magatama parse ./src --exclude "**/broken_file.py"
```

### Encoding Error

**Symptom:**

```
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

**Solution:**

1. Re-save the file in UTF-8
2. Exclude binary files:

```bash
magatama parse ./src --exclude "**/*.bin" --exclude "**/*.exe"
```

---

## Performance Issues

### Slow on Large Projects

**Symptom:**

Parsing takes several minutes or more.

**Optimization methods:**

1. Exclude unnecessary directories:

```bash
magatama parse ./src \
  --exclude "**/node_modules/**" \
  --exclude "**/.git/**" \
  --exclude "**/dist/**" \
  --exclude "**/build/**" \
  --exclude "**/__pycache__/**"
```

2. Narrow file patterns:

```bash
# Specific extensions only
magatama parse ./src --pattern "**/*.py" --pattern "**/*.ts"
```

3. Save and reuse graph:

```bash
# Initial parsing
magatama parse ./src --output graph.json

# Load graph afterwards
magatama query "search_term" --graph graph.json
```

### High Memory Usage

**Symptom:**

Memory usage exceeds 500MB.

**Solutions:**

1. Split analysis targets:

```bash
# Parse by subdirectory
magatama parse ./src/module1 --output module1.json
magatama parse ./src/module2 --output module2.json
```

2. Add exclude patterns to narrow scope

### Slow Queries

**Symptom:**

Search takes more than 1 second.

**Optimization methods:**

1. Specify concrete search conditions:

```bash
# Specify type
magatama query "process" --type function

# Limit results
magatama query "process" --max-results 10
```

---

## AI Tool Integration Issues

### Tools Not Appearing in Claude Desktop

**Verification steps:**

1. Check if JSON in config file is valid:

```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq .
```

2. Completely restart Claude Desktop
3. Run command directly to verify:

```bash
uv run --directory /path/to/magatama magatama serve
```

### Not Recognized in VS Code Copilot

**Verification steps:**

1. Check `.vscode/mcp.json` configuration
2. Restart VS Code
3. Disable → Enable Copilot extension

### Connection Error in Cursor

**Verification steps:**

1. Check `.cursor/mcp.json` configuration
2. Restart Cursor
3. Check error logs in Developer Tools (F12)

---

## Error Message Reference

### `EntityNotFoundError: Entity not found: xxx`

**Cause:** Entity with specified ID doesn't exist.

**Solution:** Verify entity name or run parsing again.

### `EntityAlreadyExistsError: Entity already exists: xxx`

**Cause:** Attempted to add entity with duplicate ID.

**Solution:** Clear graph and re-parse:

```bash
magatama parse ./src --output graph.json  # Overwrite
```

### `ParserNotFoundError: No parser for extension: .xxx`

**Cause:** Unsupported file extension.

**Solution:** Parse only files with supported extensions:
- Python: `.py`
- TypeScript: `.ts`, `.tsx`
- JavaScript: `.js`, `.jsx`
- Rust: `.rs`
- Go: `.go`
- And 19 more languages

### `ConfigurationError: Invalid configuration`

**Cause:** Invalid configuration file format.

**Solution:** Validate JSON format.

### `TimeoutError: Operation timed out`

**Cause:** Operation timed out.

**Solution:** Narrow analysis scope or add exclude patterns.

---

## Debug Methods

### Enable Verbose Logging

```bash
# Set log level via environment variable
export MAGATAMA_LOG_LEVEL=DEBUG
magatama parse ./src
```

### Debug MCP Communication

```bash
# Use MCP Inspector
npx @anthropic/mcp-inspector magatama serve
```

### Profiling

```bash
# Run benchmark
magatama benchmark ./src --json > benchmark.json
```

---

## Support

If the issue isn't resolved:

1. Report on [GitHub Issues](https://github.com/tsucky230/MAGATAMA/issues)
2. Include the following information:
   - OS and version
   - Python version
   - MAGATAMA version (`magatama info`)
   - Full error message
   - Steps to reproduce
