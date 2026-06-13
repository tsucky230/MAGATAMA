# ADR-001: Clean Architecture採用

**Project**: YATA (八咫)
**ADR ID**: ADR-001
**Status**: Accepted
**Date**: 2025-12-31
**Deciders**: MUSUBI SDD
**Related Requirements**: REQ-NFR-008 (言語追加の拡張性)

---

## Context

YATAは、プログラミング言語・フレームワークの知識グラフを構築し、MCPプロトコルを通じてAIコーディングツールにコンテキストを提供するシステムです。

以下の特性を持つアーキテクチャが求められます：

1. **多言語サポート**: Python, TypeScript, JavaScript, Rust, Goの5言語をサポートし、将来的に他の言語も追加可能
2. **プロトコル独立性**: MCP以外のプロトコル（REST API、gRPC等）への対応可能性
3. **ストレージ柔軟性**: SQLiteをプライマリとしつつ、他のDBへの移行可能性
4. **テスト容易性**: Article III (Test-First Imperative) の遵守

## Decision

**Clean Architecture**を採用し、以下の4層構造でシステムを設計する。

```
┌─────────────────────────────────────────┐
│   Interface Layer (MCP/CLI)             │ ← Entry points
├─────────────────────────────────────────┤
│   Application Layer (Services)          │ ← Use Cases
├─────────────────────────────────────────┤
│   Infrastructure Layer (Storage/Parser) │ ← I/O & External
├─────────────────────────────────────────┤
│   Domain Layer (Core)                   │ ← Pure logic
└─────────────────────────────────────────┘

Dependency Direction: ↓ (outer → inner)
```

### Layer Responsibilities

| Layer | 責務 | 依存先 | 例 |
|-------|------|--------|-----|
| **Interface** | 外部との通信、入出力 | Application | MCP Server, CLI |
| **Application** | ユースケース実装 | Domain, (Ports) | LibraryService, QueryService |
| **Infrastructure** | 外部システム連携 | Application (Ports) | SQLiteStorage, TreeSitterParser |
| **Domain** | ビジネスロジック | なし | Entity, Relation, KnowledgeGraph |

### Dependency Inversion

Application層はInfrastructure層に直接依存せず、**Ports（インターフェース）** を定義し、Infrastructure層がそれを実装する。

```python
# application/ports.py (Application層)
class StoragePort(Protocol):
    def save_graph(self, library_id: str, graph: KnowledgeGraph) -> None: ...
    def load_graph(self, library_id: str) -> KnowledgeGraph: ...

# infrastructure/storage/sqlite.py (Infrastructure層)
class SQLiteStorage(StoragePort):
    def save_graph(self, library_id: str, graph: KnowledgeGraph) -> None:
        # SQLite固有の実装
        ...
```

## Consequences

### Positive

1. **テスト容易性向上**: Domain層は外部依存なしでユニットテスト可能
2. **拡張性確保**: 新しい言語パーサー、ストレージ、プロトコルの追加が容易
3. **関心の分離**: 各層の責務が明確で、変更の影響範囲が限定的
4. **Article III準拠**: モック/スタブによるテストファーストが容易

### Negative

1. **初期実装コスト**: レイヤー分離のためのボイラープレートコードが必要
2. **学習コスト**: 開発者がClean Architectureを理解する必要がある
3. **過度な抽象化リスク**: 小規模機能でも層を跨ぐ必要がある

### Mitigations

| リスク | 対策 |
|--------|------|
| 初期実装コスト | テンプレート/コードジェネレーターの活用 |
| 学習コスト | 明確なドキュメントとコード例の提供 |
| 過度な抽象化 | シンプルな機能はファサードパターンで簡略化 |

## Alternatives Considered

### Alternative 1: レイヤードアーキテクチャ（従来型）

```
Presentation → Business → Data Access
```

**不採用理由**: 
- ビジネス層がデータアクセス層に依存し、テストが困難
- 新しいデータソース追加時にビジネス層の変更が必要

### Alternative 2: ヘキサゴナルアーキテクチャ

**不採用理由**: 
- Clean Architectureと本質的に同じ
- Clean Architectureの方がドキュメントが豊富

### Alternative 3: モノリシック（層分離なし）

**不採用理由**:
- Article IX（実サービス統合テスト）との両立が困難
- 将来の拡張性に問題

## Implementation

### Directory Structure

```
src/magatama/
├── core/                  # Domain Layer
│   ├── entities.py
│   ├── relations.py
│   ├── graph.py
│   └── indexer.py
├── application/           # Application Layer
│   ├── library_service.py
│   ├── query_service.py
│   ├── index_service.py
│   └── ports.py           # Port definitions
├── infrastructure/        # Infrastructure Layer
│   ├── storage/
│   │   └── sqlite.py
│   └── parsers/
│       ├── base.py
│       └── python.py
└── mcp/                   # Interface Layer
    ├── server.py
    ├── tools.py
    ├── resources.py
    └── prompts.py
```

### Dependency Injection

```python
# main.py or server.py
def create_app() -> MCPApp:
    # Infrastructure
    storage = SQLiteStorage(db_path="~/.magatama/db.sqlite")
    parser_registry = ParserRegistry()
    parser_registry.register(PythonParser())
    parser_registry.register(TypeScriptParser())
    
    # Application (inject infrastructure via ports)
    library_service = LibraryService(storage=storage)
    query_service = QueryService(storage=storage)
    index_service = IndexService(
        storage=storage,
        parser_registry=parser_registry
    )
    
    # Interface
    return MCPApp(
        library_service=library_service,
        query_service=query_service,
        index_service=index_service
    )
```

## References

- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- YATA steering/structure.ja.md

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-31 | MUSUBI SDD | Initial version |
