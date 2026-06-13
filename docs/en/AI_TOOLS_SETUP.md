# AI Tools Setup Guide

This guide explains how to integrate the MAGATAMA MCP Server with various AI coding tools.
(MAGATAMA is a fork of [YATA](https://github.com/nahisaho/YATA); the CLI command is `magatama`.)

## Table of Contents

- [Claude Desktop](#claude-desktop)
- [GitHub Copilot (VS Code)](#github-copilot-vs-code)
- [Cursor](#cursor)
- [Continue](#continue)
- [Verification Methods](#verification-methods)
- [General Troubleshooting](#general-troubleshooting)

---

## Claude Desktop

### macOS

1. Open the configuration file:

```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

2. Add the following configuration:

```json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/MAGATAMA", "magatama", "serve"],
      "env": {}
    }
  }
}
```

> **Note**: Replace `/path/to/MAGATAMA` with your actual MAGATAMA installation path.

### Windows

1. Open the configuration file:

```
%APPDATA%\Claude\claude_desktop_config.json
```

2. Add the following configuration:

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

### Linux

1. Open the configuration file:

```bash
code ~/.config/Claude/claude_desktop_config.json
```

2. Use the same format as macOS.

### Global Installation (PyPI)

```json
{
  "mcpServers": {
    "magatama": {
      "command": "magatama",
      "args": ["serve"]
    }
  }
}
```

---

## GitHub Copilot (VS Code)

### Project Local Configuration

1. Create `.vscode/mcp.json` at the project root:

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

### Global Configuration

Add to VS Code `settings.json`:

```json
{
  "github.copilot.chat.experimental.mcpServers": {
    "magatama": {
      "command": "magatama",
      "args": ["serve"]
    }
  }
}
```

### Using SSE Mode

Convenient for development verification:

```json
{
  "mcpServers": {
    "magatama": {
      "type": "sse",
      "url": "http://localhost:8080"
    }
  }
}
```

Start the server in a separate terminal:

```bash
magatama serve --transport sse --port 8080
```

---

## Cursor

### Configuration

1. Open Settings (⌘,)
2. Find the "MCP Servers" section
3. Add the following:

```json
{
  "mcpServers": {
    "magatama": {
      "command": "magatama",
      "args": ["serve"]
    }
  }
}
```

Or create `.cursor/mcp.json` at the project root:

```json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", ".", "magatama", "serve"]
    }
  }
}
```

---

## Continue

### VS Code Extension Configuration

`.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "magatama",
      "command": "magatama",
      "args": ["serve"]
    }
  ]
}
```

---

## Verification Methods

### Server Startup Test

```bash
# Basic operation check
magatama serve --help

# Display server information
magatama info
```

### Testing with MCP Inspector

```bash
# Test server with MCP Inspector
npx @anthropic/mcp-inspector magatama serve
```

Open http://localhost:5173 in your browser to interactively test tools.

### Verification Checklist

- [ ] `magatama info` displays version and tool list
- [ ] `magatama parse <file>` can parse files
- [ ] AI tool can connect to MCP server
- [ ] MAGATAMA tools are available in AI tool

---

## General Troubleshooting

### Server Won't Start

**Cause 1: uv not found**

```bash
# Check uv installation
which uv

# If not installed
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Cause 2: MAGATAMA not installed**

```bash
# For development version
cd /path/to/MAGATAMA
uv sync --all-packages
```

### Cannot Connect from AI Tool

**Check the following:**

1. Verify path is correct
2. Run command directly to verify operation
3. Confirm JSON in configuration file is valid

**Debug method:**

```bash
# Run command directly
uv run --directory /path/to/MAGATAMA magatama serve

# Check error logs
magatama serve 2>&1 | head -50
```

### "Unknown tool" Error

If the AI tool doesn't recognize MAGATAMA tools:

1. Restart the AI tool
2. Reload MCP server configuration
3. Check tool list with `magatama info`

### Slow Performance

**For large projects:**

1. Set exclude patterns:

```bash
magatama parse ./src --exclude "**/node_modules/**" --exclude "**/.git/**"
```

2. Save and reuse graph:

```bash
magatama parse ./src --output graph.json
magatama query "ClassName" --graph graph.json
```

### Out of Memory

**Solutions:**

1. Narrow the analysis scope
2. Exclude unnecessary files
3. Use SQLite storage (planned for future support)

---

## FAQ

### Q: Which languages are supported?

A: Python, TypeScript/TSX, JavaScript/JSX, Rust, Go, and 19 more languages (24 total) are supported.

### Q: Is private code sent externally?

A: No. MAGATAMA runs completely locally and does not send code or data externally.

### Q: Can I handle multiple projects simultaneously?

A: Yes. You can configure MCP server separately for each project. You can also analyze multiple directories together.

### Q: Where is graph data saved?

A: By default, it's kept in memory. You can save to JSON file with the `--output` option.

---

For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
