# YATA エラーコード設計書

**Project**: YATA (八咫)
**Document ID**: DES-YATA-005
**Version**: 1.0
**Created**: 2025-12-31
**Status**: Draft
**Author**: MUSUBI SDD

---

## 1. 概要

本文書は、YATA MCP Serverのエラーコード体系を定義する。MCP仕様に準拠しつつ、YATA固有のエラーを識別可能にする。

---

## 2. エラーコード体系

### 2.1 コード範囲

| 範囲 | カテゴリ | 説明 |
|------|----------|------|
| -32700 ~ -32600 | JSON-RPC | 標準JSON-RPCエラー |
| -32099 ~ -32000 | MCP Reserved | MCP仕様予約 |
| 1000 ~ 1999 | YATA Library | ライブラリ関連エラー |
| 2000 ~ 2999 | YATA Parser | パーサー関連エラー |
| 3000 ~ 3999 | YATA Storage | ストレージ関連エラー |
| 4000 ~ 4999 | YATA GitHub | GitHub連携エラー |
| 5000 ~ 5999 | YATA Query | クエリ関連エラー |

---

## 3. JSON-RPC標準エラー

| Code | Name | Description |
|------|------|-------------|
| -32700 | ParseError | JSON解析エラー |
| -32600 | InvalidRequest | 無効なリクエスト |
| -32601 | MethodNotFound | メソッド未定義 |
| -32602 | InvalidParams | 無効なパラメータ |
| -32603 | InternalError | 内部エラー |

---

## 4. YATAエラーコード詳細

### 4.1 Library Errors (1000-1999)

| Code | Name | Message | Cause | Resolution |
|------|------|---------|-------|------------|
| 1001 | LIBRARY_NOT_FOUND | Library not found: {library_id} | 指定されたライブラリIDが存在しない | `list_libraries`で有効なIDを確認 |
| 1002 | LIBRARY_ALREADY_EXISTS | Library already exists: {name} | 同名のライブラリが既に登録済み | 既存ライブラリを更新するか別名を使用 |
| 1003 | LIBRARY_INDEX_FAILED | Failed to index library: {reason} | インデックス作成に失敗 | ソースパスと権限を確認 |
| 1004 | LIBRARY_VERSION_NOT_FOUND | Version not found: {version} | 指定バージョンが存在しない | 有効なバージョンを指定 |
| 1005 | LIBRARY_INVALID_PATH | Invalid library path: {path} | パスが無効または存在しない | パスの存在と形式を確認 |

### 4.2 Parser Errors (2000-2999)

| Code | Name | Message | Cause | Resolution |
|------|------|---------|-------|------------|
| 2001 | PARSER_LANGUAGE_NOT_SUPPORTED | Language not supported: {lang} | サポート外の言語 | サポート言語: Python, TypeScript, JavaScript, Rust, Go |
| 2002 | PARSER_SYNTAX_ERROR | Syntax error in {file}:{line} | ソースコードの構文エラー | ソースコードを修正 |
| 2003 | PARSER_FILE_TOO_LARGE | File too large: {size}MB (max: 10MB) | ファイルサイズ超過 | ファイルを分割 |
| 2004 | PARSER_ENCODING_ERROR | Encoding error: {file} | 文字エンコーディングエラー | UTF-8エンコーディングを使用 |
| 2005 | PARSER_TIMEOUT | Parser timeout: {file} | パース処理タイムアウト | 複雑なファイルを分割 |

### 4.3 Storage Errors (3000-3999)

| Code | Name | Message | Cause | Resolution |
|------|------|---------|-------|------------|
| 3001 | STORAGE_CONNECTION_FAILED | Failed to connect to storage | DBファイルアクセス不可 | DB パスと権限を確認 |
| 3002 | STORAGE_WRITE_FAILED | Failed to write to storage | 書き込み失敗 | ディスク容量と権限を確認 |
| 3003 | STORAGE_READ_FAILED | Failed to read from storage | 読み込み失敗 | DBファイルの整合性を確認 |
| 3004 | STORAGE_INTEGRITY_ERROR | Storage integrity error | データ整合性エラー | DBファイルを再構築 |
| 3005 | STORAGE_MIGRATION_FAILED | Migration failed: {version} | スキーママイグレーション失敗 | バックアップから復元 |

### 4.4 GitHub Errors (4000-4999)

| Code | Name | Message | Cause | Resolution |
|------|------|---------|-------|------------|
| 4001 | GITHUB_INVALID_URL | Invalid GitHub URL: {url} | GitHub URL形式エラー | `https://github.com/owner/repo` 形式を使用 |
| 4002 | GITHUB_REPO_NOT_FOUND | Repository not found: {repo} | リポジトリが存在しないまたはプライベート | URL確認、認証トークン設定 |
| 4003 | GITHUB_RATE_LIMITED | GitHub API rate limited | APIレートリミット到達 | 認証トークン設定、または待機 |
| 4004 | GITHUB_AUTH_FAILED | GitHub authentication failed | 認証失敗 | トークンの有効性を確認 |
| 4005 | GITHUB_CLONE_FAILED | Failed to clone: {reason} | クローン失敗 | ネットワークとURLを確認 |
| 4006 | GITHUB_REF_NOT_FOUND | Ref not found: {ref} | ブランチ/タグが存在しない | 有効なref名を確認 |

### 4.5 Query Errors (5000-5999)

| Code | Name | Message | Cause | Resolution |
|------|------|---------|-------|------------|
| 5001 | QUERY_INVALID_SYNTAX | Invalid query syntax | クエリ構文エラー | クエリ形式を確認 |
| 5002 | QUERY_ENTITY_NOT_FOUND | Entity not found: {entity_id} | エンティティが存在しない | 有効なエンティティIDを使用 |
| 5003 | QUERY_TIMEOUT | Query timeout | クエリタイムアウト | クエリを簡略化 |
| 5004 | QUERY_TOO_MANY_RESULTS | Too many results: {count} | 結果数超過 | フィルタを追加 |
| 5005 | QUERY_DEPTH_EXCEEDED | Max depth exceeded: {depth} | 探索深度超過 | 深度パラメータを調整 |

---

## 5. エラーレスポンス形式

### 5.1 MCP Error Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": 1001,
    "message": "Library not found: lib-invalid-id",
    "data": {
      "error_id": "yata-err-20251231-abc123",
      "library_id": "lib-invalid-id",
      "suggestion": "Use list_libraries to get valid library IDs",
      "docs_url": "https://github.com/nahisaho/YATA/docs/errors#1001"
    }
  }
}
```

### 5.2 Error Data フィールド

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| error_id | string | Yes | 一意のエラー識別子（ログ相関用） |
| suggestion | string | No | 解決のヒント |
| docs_url | string | No | ドキュメントリンク |
| *context* | varies | No | エラー固有の追加情報 |

---

## 6. Python実装

### 6.1 エラークラス定義

```python
# src/yata/core/errors.py
from enum import IntEnum
from dataclasses import dataclass
from typing import Any
import uuid
from datetime import datetime

class YataErrorCode(IntEnum):
    """YATA Error Codes"""
    # Library Errors (1000-1999)
    LIBRARY_NOT_FOUND = 1001
    LIBRARY_ALREADY_EXISTS = 1002
    LIBRARY_INDEX_FAILED = 1003
    LIBRARY_VERSION_NOT_FOUND = 1004
    LIBRARY_INVALID_PATH = 1005
    
    # Parser Errors (2000-2999)
    PARSER_LANGUAGE_NOT_SUPPORTED = 2001
    PARSER_SYNTAX_ERROR = 2002
    PARSER_FILE_TOO_LARGE = 2003
    PARSER_ENCODING_ERROR = 2004
    PARSER_TIMEOUT = 2005
    
    # Storage Errors (3000-3999)
    STORAGE_CONNECTION_FAILED = 3001
    STORAGE_WRITE_FAILED = 3002
    STORAGE_READ_FAILED = 3003
    STORAGE_INTEGRITY_ERROR = 3004
    STORAGE_MIGRATION_FAILED = 3005
    
    # GitHub Errors (4000-4999)
    GITHUB_INVALID_URL = 4001
    GITHUB_REPO_NOT_FOUND = 4002
    GITHUB_RATE_LIMITED = 4003
    GITHUB_AUTH_FAILED = 4004
    GITHUB_CLONE_FAILED = 4005
    GITHUB_REF_NOT_FOUND = 4006
    
    # Query Errors (5000-5999)
    QUERY_INVALID_SYNTAX = 5001
    QUERY_ENTITY_NOT_FOUND = 5002
    QUERY_TIMEOUT = 5003
    QUERY_TOO_MANY_RESULTS = 5004
    QUERY_DEPTH_EXCEEDED = 5005


@dataclass
class YataError(Exception):
    """Base YATA Error"""
    code: YataErrorCode
    message: str
    data: dict[str, Any] | None = None
    
    def __post_init__(self):
        self.error_id = self._generate_error_id()
    
    def _generate_error_id(self) -> str:
        date = datetime.now().strftime("%Y%m%d")
        short_uuid = uuid.uuid4().hex[:6]
        return f"yata-err-{date}-{short_uuid}"
    
    def to_mcp_error(self) -> dict:
        """Convert to MCP error response format"""
        return {
            "code": int(self.code),
            "message": self.message,
            "data": {
                "error_id": self.error_id,
                **(self.data or {})
            }
        }


# Convenience factory functions
def library_not_found(library_id: str) -> YataError:
    return YataError(
        code=YataErrorCode.LIBRARY_NOT_FOUND,
        message=f"Library not found: {library_id}",
        data={
            "library_id": library_id,
            "suggestion": "Use list_libraries to get valid library IDs"
        }
    )

def parser_language_not_supported(lang: str) -> YataError:
    return YataError(
        code=YataErrorCode.PARSER_LANGUAGE_NOT_SUPPORTED,
        message=f"Language not supported: {lang}",
        data={
            "language": lang,
            "supported": ["python", "typescript", "javascript", "rust", "go"]
        }
    )

def github_rate_limited(reset_at: str) -> YataError:
    return YataError(
        code=YataErrorCode.GITHUB_RATE_LIMITED,
        message="GitHub API rate limited",
        data={
            "reset_at": reset_at,
            "suggestion": "Set GITHUB_TOKEN environment variable for higher limits"
        }
    )
```

### 6.2 MCP Tool でのエラーハンドリング

```python
# src/yata/mcp/tools.py
from mcp.server.fastmcp import FastMCP
from mcp.types import McpError
from yata.core.errors import YataError, YataErrorCode

mcp = FastMCP("yata")

@mcp.tool()
async def resolve_library(query: str) -> dict:
    """Resolve library by name or query"""
    try:
        result = await library_service.resolve(query)
        if not result:
            raise YataError(
                code=YataErrorCode.LIBRARY_NOT_FOUND,
                message=f"No library found for query: {query}",
                data={"query": query}
            )
        return result
    except YataError as e:
        raise McpError(e.code, e.message, e.to_mcp_error()["data"])
    except Exception as e:
        raise McpError(-32603, f"Internal error: {str(e)}")
```

---

## 7. ログ統合

### 7.1 エラーログフォーマット

```python
import structlog

logger = structlog.get_logger()

def log_error(error: YataError):
    logger.error(
        "yata_error",
        error_id=error.error_id,
        error_code=error.code,
        error_name=error.code.name,
        message=error.message,
        data=error.data,
    )
```

### 7.2 ログ出力例

```json
{
  "timestamp": "2025-12-31T12:34:56.789Z",
  "level": "error",
  "event": "yata_error",
  "error_id": "yata-err-20251231-abc123",
  "error_code": 1001,
  "error_name": "LIBRARY_NOT_FOUND",
  "message": "Library not found: lib-invalid-id",
  "data": {
    "library_id": "lib-invalid-id",
    "suggestion": "Use list_libraries to get valid library IDs"
  }
}
```

---

## 8. 要件トレーサビリティ

| 設計要素 | 要件ID | 説明 |
|----------|--------|------|
| エラーコード体系 | REQ-MCP-008 | MCPエラー応答形式 |
| エラーログ出力 | REQ-NFR-009 | 構造化ログ出力 |
| エラーハンドリング | REQ-NFR-004 | エラー時の継続処理 |

---

## 9. 変更履歴

| バージョン | 日付 | 著者 | 変更内容 |
|------------|------|------|----------|
| 1.0 | 2025-12-31 | MUSUBI SDD | 初版作成 |

---

*Generated by MUSUBI SDD - Design Phase (Error Codes)*
