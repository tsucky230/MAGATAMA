# YATA 設定ファイル設計書

**Project**: YATA (八咫)
**Document ID**: DES-YATA-006
**Version**: 1.0
**Created**: 2025-12-31
**Status**: Draft
**Author**: MUSUBI SDD

---

## 1. 概要

本文書は、YATA MCP Serverの設定管理方式を定義する。ローカルファイル、環境変数、CLI引数の3層構造で設定を管理する。

---

## 2. 設定の優先順位

```
CLI Arguments  (最高優先)
     ↓
Environment Variables
     ↓
Config File (~/.yata/config.toml)
     ↓
Default Values (最低優先)
```

---

## 3. 設定ファイル

### 3.1 ファイル配置

| OS | Path |
|----|------|
| Linux/macOS | `~/.yata/config.toml` |
| Windows | `%USERPROFILE%\.yata\config.toml` |

### 3.2 ディレクトリ構造

```
~/.yata/
├── config.toml          # 設定ファイル
├── db.sqlite            # メインDB
├── cache/               # キャッシュディレクトリ
│   └── repos/           # クローンしたリポジトリ
└── logs/                # ログファイル
    └── yata.log
```

### 3.3 設定ファイルスキーマ

```toml
# ~/.yata/config.toml
# YATA Configuration File

#==============================================================================
# General Settings
#==============================================================================
[general]
# ログレベル: DEBUG, INFO, WARNING, ERROR
log_level = "INFO"

# ログ出力先: "console", "file", "both"
log_output = "console"

# ログファイルパス（log_output = "file" or "both" の場合）
log_file = "~/.yata/logs/yata.log"

# JSONフォーマットログ出力
log_json = false

#==============================================================================
# Storage Settings
#==============================================================================
[storage]
# SQLite データベースパス
db_path = "~/.yata/db.sqlite"

# キャッシュディレクトリ
cache_dir = "~/.yata/cache"

# グラフキャッシュサイズ（LRU、ライブラリ数）
graph_cache_size = 10

# 最大ライブラリ数
max_libraries = 100

#==============================================================================
# Parser Settings
#==============================================================================
[parser]
# パースタイムアウト（秒）
timeout = 30

# 最大ファイルサイズ（MB）
max_file_size = 10

# 除外パターン（glob）
exclude_patterns = [
    "**/node_modules/**",
    "**/.git/**",
    "**/dist/**",
    "**/build/**",
    "**/__pycache__/**",
    "**/.venv/**",
    "**/venv/**",
]

# 言語別設定
[parser.python]
enabled = true
extensions = [".py", ".pyi"]

[parser.typescript]
enabled = true
extensions = [".ts", ".tsx"]

[parser.javascript]
enabled = true
extensions = [".js", ".jsx", ".mjs"]

[parser.rust]
enabled = true
extensions = [".rs"]

[parser.go]
enabled = true
extensions = [".go"]

#==============================================================================
# MCP Server Settings
#==============================================================================
[mcp]
# デフォルトトランスポート: "stdio", "sse"
transport = "stdio"

# SSEポート（transport = "sse" の場合）
sse_port = 8080

# SSEホスト
sse_host = "127.0.0.1"

# リクエストタイムアウト（秒）
request_timeout = 30

# 最大応答トークン数
max_response_tokens = 8000

#==============================================================================
# GitHub Settings
#==============================================================================
[github]
# GitHub Personal Access Token（環境変数 GITHUB_TOKEN を推奨）
# token = "ghp_xxxxxxxxxxxxxxxxxxxx"

# クローン時のデフォルト深度
clone_depth = 1

# キャッシュ有効期限（時間）
cache_ttl = 24

# レートリミット時の待機（秒）
rate_limit_wait = 60

#==============================================================================
# Performance Settings
#==============================================================================
[performance]
# インデックス並列度
indexing_workers = 4

# クエリ並列度
query_workers = 2

# バッチサイズ（エンティティ数）
batch_size = 1000

#==============================================================================
# GraphRAG Settings
#==============================================================================
[graphrag]
# コミュニティ検出有効化
enabled = true

# Louvainアルゴリズム解像度
resolution = 1.0

# 最小コミュニティサイズ
min_community_size = 3
```

---

## 4. 環境変数

### 4.1 環境変数一覧

| 環境変数 | 設定項目 | デフォルト |
|----------|----------|------------|
| `YATA_LOG_LEVEL` | general.log_level | INFO |
| `YATA_LOG_OUTPUT` | general.log_output | console |
| `YATA_LOG_FILE` | general.log_file | ~/.yata/logs/yata.log |
| `YATA_LOG_JSON` | general.log_json | false |
| `YATA_DB_PATH` | storage.db_path | ~/.yata/db.sqlite |
| `YATA_CACHE_DIR` | storage.cache_dir | ~/.yata/cache |
| `YATA_GRAPH_CACHE_SIZE` | storage.graph_cache_size | 10 |
| `YATA_PARSER_TIMEOUT` | parser.timeout | 30 |
| `YATA_MAX_FILE_SIZE` | parser.max_file_size | 10 |
| `YATA_MCP_TRANSPORT` | mcp.transport | stdio |
| `YATA_MCP_PORT` | mcp.sse_port | 8080 |
| `YATA_MCP_HOST` | mcp.sse_host | 127.0.0.1 |
| `GITHUB_TOKEN` | github.token | (none) |
| `YATA_CLONE_DEPTH` | github.clone_depth | 1 |

### 4.2 環境変数の命名規則

```
YATA_<SECTION>_<KEY>
```

- セクション名とキー名はアンダースコアで連結
- すべて大文字

---

## 5. CLI引数

### 5.1 グローバルオプション

```bash
yata [OPTIONS] COMMAND [ARGS]...

Options:
  --config PATH        設定ファイルパス [default: ~/.yata/config.toml]
  --log-level LEVEL    ログレベル [DEBUG|INFO|WARNING|ERROR]
  --log-json           JSON形式でログ出力
  -v, --verbose        詳細出力（--log-level DEBUG と同等）
  -q, --quiet          最小出力（--log-level ERROR と同等）
  --version            バージョン表示
  --help               ヘルプ表示
```

### 5.2 コマンド別オプション

```bash
# index コマンド
yata index <PATH> [OPTIONS]
  --name TEXT          ライブラリ名
  --version TEXT       バージョン文字列
  --tag TEXT           Gitタグ（GitHub URL時）
  --branch TEXT        Gitブランチ（GitHub URL時）
  --token TEXT         GitHub Token（環境変数 GITHUB_TOKEN を上書き）
  --timeout INT        パースタイムアウト秒

# serve コマンド
yata serve [OPTIONS]
  --transport TEXT     トランスポート [stdio|sse]
  --port INT           SSEポート
  --host TEXT          SSEホスト

# query コマンド
yata query <QUERY> [OPTIONS]
  --library TEXT       対象ライブラリID
  --format TEXT        出力形式 [json|text|table]
  --max-results INT    最大結果数

# watch コマンド
yata watch <PATH> [OPTIONS]
  --debounce INT       デバウンス秒数
```

---

## 6. Python実装

### 6.1 設定モデル

```python
# src/yata/config.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import os
import tomllib

@dataclass
class GeneralConfig:
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_output: Literal["console", "file", "both"] = "console"
    log_file: Path = field(default_factory=lambda: Path.home() / ".yata/logs/yata.log")
    log_json: bool = False

@dataclass
class StorageConfig:
    db_path: Path = field(default_factory=lambda: Path.home() / ".yata/db.sqlite")
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".yata/cache")
    graph_cache_size: int = 10
    max_libraries: int = 100

@dataclass
class ParserLanguageConfig:
    enabled: bool = True
    extensions: list[str] = field(default_factory=list)

@dataclass
class ParserConfig:
    timeout: int = 30
    max_file_size: int = 10  # MB
    exclude_patterns: list[str] = field(default_factory=lambda: [
        "**/node_modules/**",
        "**/.git/**",
        "**/dist/**",
        "**/build/**",
        "**/__pycache__/**",
    ])
    python: ParserLanguageConfig = field(default_factory=lambda: ParserLanguageConfig(extensions=[".py", ".pyi"]))
    typescript: ParserLanguageConfig = field(default_factory=lambda: ParserLanguageConfig(extensions=[".ts", ".tsx"]))
    javascript: ParserLanguageConfig = field(default_factory=lambda: ParserLanguageConfig(extensions=[".js", ".jsx", ".mjs"]))
    rust: ParserLanguageConfig = field(default_factory=lambda: ParserLanguageConfig(extensions=[".rs"]))
    go: ParserLanguageConfig = field(default_factory=lambda: ParserLanguageConfig(extensions=[".go"]))

@dataclass
class MCPConfig:
    transport: Literal["stdio", "sse"] = "stdio"
    sse_port: int = 8080
    sse_host: str = "127.0.0.1"
    request_timeout: int = 30
    max_response_tokens: int = 8000

@dataclass
class GitHubConfig:
    token: str | None = None
    clone_depth: int = 1
    cache_ttl: int = 24  # hours
    rate_limit_wait: int = 60  # seconds

@dataclass
class PerformanceConfig:
    indexing_workers: int = 4
    query_workers: int = 2
    batch_size: int = 1000

@dataclass
class GraphRAGConfig:
    enabled: bool = True
    resolution: float = 1.0
    min_community_size: int = 3

@dataclass
class YataConfig:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    parser: ParserConfig = field(default_factory=ParserConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    graphrag: GraphRAGConfig = field(default_factory=GraphRAGConfig)
```

### 6.2 設定ローダー

```python
# src/yata/config.py (continued)
from typing import Any

def load_config(
    config_path: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> YataConfig:
    """
    Load configuration with priority:
    1. CLI arguments (cli_overrides)
    2. Environment variables
    3. Config file
    4. Defaults
    """
    config = YataConfig()
    
    # Load from file
    if config_path is None:
        config_path = Path.home() / ".yata" / "config.toml"
    
    if config_path.exists():
        with open(config_path, "rb") as f:
            file_config = tomllib.load(f)
        config = _merge_config(config, file_config)
    
    # Override with environment variables
    config = _apply_env_vars(config)
    
    # Override with CLI arguments
    if cli_overrides:
        config = _apply_cli_overrides(config, cli_overrides)
    
    # Ensure directories exist
    _ensure_directories(config)
    
    return config

def _apply_env_vars(config: YataConfig) -> YataConfig:
    """Apply environment variable overrides"""
    env_mapping = {
        "YATA_LOG_LEVEL": ("general", "log_level"),
        "YATA_LOG_OUTPUT": ("general", "log_output"),
        "YATA_LOG_JSON": ("general", "log_json", _parse_bool),
        "YATA_DB_PATH": ("storage", "db_path", Path),
        "YATA_CACHE_DIR": ("storage", "cache_dir", Path),
        "YATA_GRAPH_CACHE_SIZE": ("storage", "graph_cache_size", int),
        "YATA_PARSER_TIMEOUT": ("parser", "timeout", int),
        "YATA_MAX_FILE_SIZE": ("parser", "max_file_size", int),
        "YATA_MCP_TRANSPORT": ("mcp", "transport"),
        "YATA_MCP_PORT": ("mcp", "sse_port", int),
        "YATA_MCP_HOST": ("mcp", "sse_host"),
        "GITHUB_TOKEN": ("github", "token"),
        "YATA_CLONE_DEPTH": ("github", "clone_depth", int),
    }
    
    for env_var, mapping in env_mapping.items():
        value = os.environ.get(env_var)
        if value is not None:
            section, key = mapping[0], mapping[1]
            converter = mapping[2] if len(mapping) > 2 else str
            setattr(getattr(config, section), key, converter(value))
    
    return config

def _parse_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes", "on")

def _ensure_directories(config: YataConfig) -> None:
    """Ensure required directories exist"""
    config.storage.db_path.parent.mkdir(parents=True, exist_ok=True)
    config.storage.cache_dir.mkdir(parents=True, exist_ok=True)
    if config.general.log_output in ("file", "both"):
        config.general.log_file.parent.mkdir(parents=True, exist_ok=True)
```

### 6.3 CLI統合（click）

```python
# src/yata/cli/commands.py
import click
from pathlib import Path
from yata.config import load_config, YataConfig

@click.group()
@click.option("--config", type=click.Path(path_type=Path), help="Config file path")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]))
@click.option("--log-json", is_flag=True, help="Output logs in JSON format")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("-q", "--quiet", is_flag=True, help="Enable quiet mode")
@click.pass_context
def cli(ctx, config, log_level, log_json, verbose, quiet):
    """YATA - Yet Another Tool for AI Coding Assistance"""
    cli_overrides = {}
    
    if log_level:
        cli_overrides["general.log_level"] = log_level
    elif verbose:
        cli_overrides["general.log_level"] = "DEBUG"
    elif quiet:
        cli_overrides["general.log_level"] = "ERROR"
    
    if log_json:
        cli_overrides["general.log_json"] = True
    
    ctx.obj = load_config(config_path=config, cli_overrides=cli_overrides)

@cli.command()
@click.argument("path")
@click.option("--name", help="Library name")
@click.option("--version", help="Version string")
@click.option("--token", help="GitHub token", envvar="GITHUB_TOKEN")
@click.pass_obj
def index(config: YataConfig, path, name, version, token):
    """Index a library from local path or GitHub URL"""
    if token:
        config.github.token = token
    # ... implementation
```

---

## 7. 初期設定ウィザード

```bash
$ yata init

YATA 初期設定
============

設定ファイルの場所: ~/.yata/config.toml

[1/4] ログレベルを選択してください:
  1. DEBUG (詳細)
  2. INFO (標準) [デフォルト]
  3. WARNING (警告のみ)
  4. ERROR (エラーのみ)
> 2

[2/4] データベースの場所:
  [デフォルト: ~/.yata/db.sqlite]
> 

[3/4] GitHub Token を設定しますか？ (公開リポジトリのみなら不要)
  [y/N]
> n

[4/4] 有効にする言語を選択してください (カンマ区切り):
  python, typescript, javascript, rust, go
  [デフォルト: すべて]
> python,typescript

設定を保存しました: ~/.yata/config.toml
```

---

## 8. 要件トレーサビリティ

| 設計要素 | 要件ID | 説明 |
|----------|--------|------|
| ログ設定 | REQ-NFR-009 | 構造化ログ出力 |
| パーサー設定 | REQ-LANG-001〜005 | 言語サポート |
| GitHub設定 | REQ-KGC-007 | GitHubリポジトリ取得 |
| パフォーマンス設定 | REQ-NFR-001〜003 | パフォーマンス要件 |

---

## 9. 変更履歴

| バージョン | 日付 | 著者 | 変更内容 |
|------------|------|------|----------|
| 1.0 | 2025-12-31 | MUSUBI SDD | 初版作成 |

---

*Generated by MUSUBI SDD - Design Phase (Configuration)*
