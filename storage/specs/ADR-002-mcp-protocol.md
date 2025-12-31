# ADR-002: MCP Python SDK採用

**Project**: YATA (八咫)
**ADR ID**: ADR-002
**Status**: Accepted
**Date**: 2025-12-31
**Deciders**: MUSUBI SDD
**Related Requirements**: REQ-MCP-001〜008

---

## Context

YATAは、AIコーディングツール（GitHub Copilot、Claude、Cursor、Cline等）に対して知識グラフベースのコンテキストを提供するMCPサーバーです。

MCPプロトコルの実装方法として、以下の選択肢があります：

1. **公式MCP Python SDK** (mcp ^1.0.0)
2. **公式MCP TypeScript SDK**
3. **プロトコル仕様からのスクラッチ実装**
4. **サードパーティライブラリ**

## Decision

**公式MCP Python SDK (mcp ^1.0.0)** を採用する。

### 理由

1. **Anthropic公式**: プロトコル策定者が提供する公式実装
2. **Python採用済み**: CodeGraphMCPServerとの技術的一貫性（REQ-KGC参照）
3. **エコシステム**: Tree-sitter, NetworkX等のPythonライブラリとの親和性
4. **成熟度**: 1.0.0リリース済みで安定

### SDK構成

```
mcp (Python SDK)
├── Server class          # MCPサーバー基盤
├── @server.tool()       # ツール定義デコレータ
├── @server.resource()   # リソース定義デコレータ
├── @server.prompt()     # プロンプト定義デコレータ
├── stdio transport      # ローカル通信
└── sse transport        # HTTP通信
```

## Implementation

### Server Initialization

```python
from mcp import Server
from mcp.transports import stdio, sse

# サーバー作成
server = Server(name="yata", version="1.0.0")

# ツール登録
@server.tool()
async def resolve_library(query: str, library_name: str | None = None) -> dict:
    """ライブラリ名からIDを解決"""
    result = await library_service.resolve_library(query)
    return {"library_id": result.id, "candidates": result.candidates}

@server.tool()
async def query_docs(
    library_id: str,
    query: str,
    version: str | None = None,
    max_tokens: int = 8000
) -> dict:
    """ドキュメント検索"""
    result = await query_service.query_docs(library_id, query, version, max_tokens)
    return {"docs": result.docs, "code_examples": result.examples}

# リソース登録
@server.resource("yata://libraries")
async def list_libraries() -> dict:
    """登録済みライブラリ一覧"""
    libraries = await library_service.list_libraries()
    return {"libraries": [lib.to_dict() for lib in libraries]}

@server.resource("yata://entities/{entity_id}")
async def get_entity(entity_id: str) -> dict:
    """エンティティ詳細"""
    entity = await query_service.get_entity(entity_id)
    return entity.to_dict()

# プロンプト登録
@server.prompt("implement_with_library")
async def implement_with_library(library_id: str, task: str) -> str:
    """ライブラリを使った実装ガイドプロンプト"""
    context = await query_service.get_implementation_context(library_id, task)
    return f"""
以下のライブラリを使用して、タスクを実装してください。

## ライブラリ情報
{context.library_info}

## 関連API
{context.relevant_apis}

## コード例
{context.code_examples}

## タスク
{task}
"""
```

### Transport Configuration

```python
# stdio (ローカル実行: Claude Desktop, Cursor等)
async def run_stdio():
    async with stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)

# SSE (HTTP経由: リモート接続)
async def run_sse(port: int = 8080):
    async with sse.sse_server(port=port) as (read_stream, write_stream):
        await server.run(read_stream, write_stream)
```

### Error Handling (REQ-MCP-008)

```python
from mcp.errors import MCPError

@server.tool()
async def query_docs(library_id: str, query: str) -> dict:
    try:
        result = await query_service.query_docs(library_id, query)
        return result.to_dict()
    except LibraryNotFoundError as e:
        raise MCPError(
            code=-32602,  # Invalid params
            message=f"Library not found: {library_id}",
            data={"library_id": library_id, "suggestion": "Use resolve_library first"}
        )
    except QueryTimeoutError as e:
        raise MCPError(
            code=-32001,  # Application error
            message="Query timeout",
            data={"timeout_ms": e.timeout_ms, "query": query}
        )
```

### MCP Error Codes

| Code | Name | Description |
|------|------|-------------|
| -32700 | Parse Error | JSON解析エラー |
| -32600 | Invalid Request | 無効なリクエスト |
| -32601 | Method Not Found | メソッド未定義 |
| -32602 | Invalid Params | 無効なパラメータ |
| -32603 | Internal Error | 内部エラー |
| -32001〜-32099 | Application Error | アプリケーション固有エラー |

## Consequences

### Positive

1. **プロトコル準拠保証**: 公式SDKによる仕様準拠
2. **保守性**: Anthropicによる継続的メンテナンス
3. **開発効率**: デコレータベースの宣言的API定義
4. **テスト容易性**: SDK提供のテストユーティリティ

### Negative

1. **SDK依存**: SDKの破壊的変更の影響を受ける
2. **抽象化コスト**: SDK内部の挙動理解が必要な場合がある
3. **Python限定**: TypeScript実装への移行時は別SDK必要

### Mitigations

| リスク | 対策 |
|--------|------|
| SDK破壊的変更 | バージョン固定 (`mcp ^1.0.0`)、統合テストで検知 |
| 抽象化コスト | SDK内部コードリーディング、Anthropicドキュメント参照 |

## Tool/Resource/Prompt Mapping

### Tools (14種)

| Tool | 説明 | REQ |
|------|------|-----|
| `resolve_library` | ライブラリID解決 | REQ-MCP-002 |
| `list_libraries` | ライブラリ一覧 | REQ-MCP-002 |
| `query_docs` | ドキュメント検索 | REQ-MCP-003 |
| `get_api_reference` | API詳細 | REQ-MCP-003 |
| `query_code_structure` | コード構造 | REQ-MCP-004 |
| `find_dependencies` | 依存関係 | REQ-MCP-005 |
| `find_callers` | 呼び出し元 | REQ-MCP-005 |
| `find_implementations` | 実装クラス | REQ-MCP-005 |
| `global_search` | グローバル検索 | REQ-KGC-006 |
| `local_search` | ローカル検索 | REQ-KGC-006 |
| `index_library` | インデックス作成 | REQ-CLI-001 |
| `update_library` | ライブラリ更新 | REQ-CLI-001 |
| `remove_library` | ライブラリ削除 | - |
| `get_stats` | 統計情報 | REQ-CLI-004 |

### Resources (3種)

| Resource URI | 説明 | REQ |
|--------------|------|-----|
| `yata://libraries` | ライブラリ一覧 | REQ-MCP-006 |
| `yata://entities/{id}` | エンティティ詳細 | REQ-MCP-006 |
| `yata://stats` | 統計情報 | REQ-MCP-006 |

### Prompts (4種)

| Prompt | 説明 | REQ |
|--------|------|-----|
| `implement_with_library` | 実装ガイド | REQ-MCP-007 |
| `explain_api` | API説明 | REQ-MCP-007 |
| `migrate_version` | バージョン移行 | REQ-MCP-007 |
| `best_practices` | ベストプラクティス | REQ-MCP-007 |

## References

- [MCP Official Documentation](https://modelcontextprotocol.io/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-31 | MUSUBI SDD | Initial version |
