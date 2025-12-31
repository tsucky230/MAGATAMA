# YATA C4 Deployment Diagram

**Project**: YATA (八咫)
**Document ID**: DES-YATA-008
**Version**: 1.0
**Created**: 2025-12-31
**Status**: Draft
**Author**: MUSUBI SDD

---

## 1. 概要

本文書は、YATA MCP Serverのデプロイメント構成を定義する。ローカル環境での実行を前提とし、各AIコーディングツールとの連携方法を示す。

---

## 2. デプロイメント概要図

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Developer Workstation                                   │
│                              (macOS / Linux / Windows)                               │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           AI Coding Tools                                    │   │
│  │                                                                              │   │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │   │
│  │  │              │   │              │   │              │   │              │ │   │
│  │  │    Claude    │   │   GitHub     │   │    Cursor    │   │   Windsurf   │ │   │
│  │  │   Desktop    │   │   Copilot    │   │              │   │              │ │   │
│  │  │              │   │              │   │              │   │              │ │   │
│  │  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘ │   │
│  │         │                  │                  │                  │         │   │
│  │         │ MCP (stdio)      │ MCP (stdio)      │ MCP (stdio)      │ MCP     │   │
│  │         │                  │                  │                  │         │   │
│  └─────────┼──────────────────┼──────────────────┼──────────────────┼─────────┘   │
│            │                  │                  │                  │             │
│            └──────────────────┴─────────┬────────┴──────────────────┘             │
│                                         │                                         │
│                                         ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                              YATA MCP Server                                 │  │
│  │                              (Python Process)                                │  │
│  │                                                                              │  │
│  │  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐            │  │
│  │  │  MCP Server    │    │  CLI App       │    │  Knowledge     │            │  │
│  │  │  (mcp ^1.0.0)  │    │  (click)       │    │  Graph Engine  │            │  │
│  │  │                │    │                │    │  (networkx)    │            │  │
│  │  └────────────────┘    └────────────────┘    └────────────────┘            │  │
│  │                                                                              │  │
│  └────────────────────────────────────────┬─────────────────────────────────────┘  │
│                                           │                                        │
│                                           ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                              Local Storage                                   │  │
│  │                                                                              │  │
│  │  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐            │  │
│  │  │  ~/.yata/      │    │  ~/.yata/      │    │  ~/.yata/      │            │  │
│  │  │  db.sqlite     │    │  cache/repos/  │    │  config.toml   │            │  │
│  │  │                │    │                │    │                │            │  │
│  │  │  [SQLite DB]   │    │  [Git Clones]  │    │  [Settings]    │            │  │
│  │  └────────────────┘    └────────────────┘    └────────────────┘            │  │
│  │                                                                              │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         │ HTTPS (optional)
                                         ▼
                            ┌────────────────────────┐
                            │       GitHub.com       │
                            │                        │
                            │  - Repository Clone    │
                            │  - API (metadata)      │
                            │                        │
                            └────────────────────────┘
```

---

## 3. AIツール別設定

### 3.1 Claude Desktop

**設定ファイル**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "yata": {
      "command": "python",
      "args": ["-m", "yata", "serve"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

**代替（uv使用）**:
```json
{
  "mcpServers": {
    "yata": {
      "command": "uv",
      "args": ["run", "--with", "yata", "yata", "serve"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### 3.2 GitHub Copilot (VS Code)

**設定ファイル**: `.vscode/mcp.json`

```json
{
  "servers": {
    "yata": {
      "command": "python",
      "args": ["-m", "yata", "serve"],
      "env": {
        "GITHUB_TOKEN": "${env:GITHUB_TOKEN}"
      }
    }
  }
}
```

### 3.3 Cursor

**設定ファイル**: `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "yata": {
      "command": "python",
      "args": ["-m", "yata", "serve"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### 3.4 Windsurf

**設定ファイル**: `~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "yata": {
      "command": "python",
      "args": ["-m", "yata", "serve"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

---

## 4. トランスポート構成

### 4.1 stdio トランスポート（デフォルト）

```
┌──────────────────┐         ┌──────────────────┐
│   AI Tool        │         │   YATA Server    │
│   (Parent)       │         │   (Child)        │
│                  │         │                  │
│  ┌────────────┐  │  stdin  │  ┌────────────┐  │
│  │ MCP Client │──┼────────>│──│ MCP Server │  │
│  │            │  │         │  │            │  │
│  │            │<─┼─────────│<─│            │  │
│  └────────────┘  │  stdout │  └────────────┘  │
│                  │         │                  │
└──────────────────┘         └──────────────────┘
```

**起動コマンド**:
```bash
python -m yata serve
# or
yata serve
```

### 4.2 SSE トランスポート（HTTP）

```
┌──────────────────┐                    ┌──────────────────┐
│   AI Tool        │                    │   YATA Server    │
│   (Client)       │                    │   (HTTP Server)  │
│                  │                    │                  │
│  ┌────────────┐  │  HTTP POST         │  ┌────────────┐  │
│  │ MCP Client │──┼───────────────────>│──│ MCP Server │  │
│  │            │  │ /mcp/v1/messages   │  │            │  │
│  │            │<─┼───────────────────<│<─│            │  │
│  └────────────┘  │  SSE Stream        │  └────────────┘  │
│                  │                    │                  │
└──────────────────┘                    └──────────────────┘
                           │
                    http://127.0.0.1:8080
```

**起動コマンド**:
```bash
yata serve --transport sse --port 8080
```

**クライアント設定（SSE）**:
```json
{
  "mcpServers": {
    "yata": {
      "url": "http://127.0.0.1:8080/mcp/v1/sse"
    }
  }
}
```

---

## 5. インストール方法

### 5.1 pip インストール

```bash
# PyPIから（公開後）
pip install yata

# GitHubから
pip install git+https://github.com/nahisaho/YATA.git

# 開発インストール
git clone https://github.com/nahisaho/YATA.git
cd YATA
pip install -e ".[dev]"
```

### 5.2 uv インストール

```bash
# uvx で直接実行
uvx yata serve

# プロジェクトに追加
uv add yata
```

### 5.3 Docker（将来対応）

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install .

ENTRYPOINT ["python", "-m", "yata", "serve"]
```

```bash
# ビルド & 実行
docker build -t yata .
docker run -v ~/.yata:/root/.yata yata
```

---

## 6. ディレクトリ構造

### 6.1 インストール後のファイル配置

```
~/.yata/                          # YATA_HOME
├── config.toml                   # 設定ファイル
├── db.sqlite                     # メインDB
├── cache/                        # キャッシュ
│   └── repos/                    # クローンしたリポジトリ
│       ├── psf_requests/         # github.com/psf/requests
│       ├── tiangolo_fastapi/     # github.com/tiangolo/fastapi
│       └── ...
└── logs/                         # ログファイル
    └── yata.log

~/Library/Application Support/Claude/   # macOS
├── claude_desktop_config.json          # Claude Desktop設定

~/.vscode/                        # VS Code (User)
└── mcp.json                      # GitHub Copilot設定

.vscode/                          # プロジェクト
└── mcp.json                      # プロジェクト固有設定
```

### 6.2 環境変数

| 変数 | 説明 | デフォルト |
|------|------|------------|
| `YATA_HOME` | YATAホームディレクトリ | `~/.yata` |
| `GITHUB_TOKEN` | GitHub Personal Access Token | (none) |
| `YATA_LOG_LEVEL` | ログレベル | `INFO` |

---

## 7. ネットワーク構成

### 7.1 ファイアウォール設定

| 方向 | ポート | プロトコル | 用途 |
|------|--------|-----------|------|
| Outbound | 443 | HTTPS | GitHub API/Clone |
| Inbound | 8080 | HTTP | SSE Transport (Optional) |

### 7.2 プロキシ設定

```bash
# 環境変数
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1

# または config.toml
[network]
proxy = "http://proxy.example.com:8080"
no_proxy = ["localhost", "127.0.0.1"]
```

---

## 8. セキュリティ考慮事項

### 8.1 認証情報の保護

```
┌─────────────────────────────────────────────────────────────┐
│                    認証情報の流れ                            │
│                                                              │
│  環境変数 ($GITHUB_TOKEN)                                   │
│       │                                                      │
│       ▼                                                      │
│  AI Tool Config (claude_desktop_config.json)                │
│       │                                                      │
│       │ プロセス起動時に渡される                            │
│       ▼                                                      │
│  YATA Server (メモリ内のみ)                                  │
│       │                                                      │
│       │ 使用時のみ                                          │
│       ▼                                                      │
│  GitHub API 呼び出し                                         │
│                                                              │
│  ❌ ファイルに保存しない                                     │
│  ❌ ログに出力しない                                         │
│  ❌ エラーメッセージに含めない                               │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 ローカル実行の保証

- データは `~/.yata/` 内にのみ保存
- テレメトリ/使用状況データの外部送信なし
- GitHub 連携は明示的なコマンド実行時のみ

---

## 9. 要件トレーサビリティ

| 設計要素 | 要件ID | 説明 |
|----------|--------|------|
| stdio/SSE Transport | REQ-MCP-001 | MCPプロトコル準拠 |
| GitHub Token | REQ-KGC-007 | GitHub認証サポート |
| Local Storage | REQ-NFR-007 | ローカル実行 |
| 設定ファイル | DES-YATA-006 | 設定管理 |

---

## 10. 変更履歴

| バージョン | 日付 | 著者 | 変更内容 |
|------------|------|------|----------|
| 1.0 | 2025-12-31 | MUSUBI SDD | 初版作成 |

---

*Generated by MUSUBI SDD - Design Phase (Deployment)*
