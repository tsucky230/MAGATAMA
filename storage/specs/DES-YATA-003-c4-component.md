# YATA C4 Component Diagram

**Project**: YATA (八咫)
**Document ID**: DES-YATA-003
**Version**: 1.0
**Created**: 2025-12-31
**Status**: Draft
**Author**: MUSUBI SDD

---

## 1. 概要

本文書は、YATAシステムの主要コンテナ内のコンポーネント構成を定義する。Clean Architectureの各レイヤー内部の詳細設計を示す。

---

## 2. MCP Server コンポーネント図

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              MCP Server Container                                    │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                              server.py                                       │   │
│  │                                                                              │   │
│  │  ┌─────────────┐                                                            │   │
│  │  │   MCPApp    │  Entry point: initialize MCP server                        │   │
│  │  └──────┬──────┘                                                            │   │
│  │         │                                                                    │   │
│  │         │ registers                                                          │   │
│  │         ▼                                                                    │   │
│  │  ┌──────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                         MCP Components                                │   │   │
│  │  │                                                                       │   │   │
│  │  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │   │   │
│  │  │  │  tools.py       │  │  resources.py   │  │  prompts.py     │      │   │   │
│  │  │  │                 │  │                 │  │                 │      │   │   │
│  │  │  │  [Component]    │  │  [Component]    │  │  [Component]    │      │   │   │
│  │  │  │                 │  │                 │  │                 │      │   │   │
│  │  │  │  14 MCP Tools   │  │  3 Resources    │  │  4 Prompts      │      │   │   │
│  │  │  │                 │  │                 │  │                 │      │   │   │
│  │  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘      │   │   │
│  │  │           │                    │                    │               │   │   │
│  │  └───────────┼────────────────────┼────────────────────┼───────────────┘   │   │
│  │              │                    │                    │                   │   │
│  └──────────────┼────────────────────┼────────────────────┼───────────────────┘   │
│                 │                    │                    │                       │
│                 │ calls              │ calls              │ returns               │
│                 ▼                    ▼                    ▼                       │
│          ┌─────────────────────────────────────────────────────────────┐         │
│          │                  Application Services                        │         │
│          └─────────────────────────────────────────────────────────────┘         │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 MCP Tools コンポーネント詳細

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 tools.py                                             │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │ Library Discovery Tools                                                        │  │
│  │                                                                                │  │
│  │  ┌────────────────────┐    ┌────────────────────┐                            │  │
│  │  │ resolve_library    │    │ list_libraries     │                            │  │
│  │  │                    │    │                    │                            │  │
│  │  │ Input:             │    │ Input: -           │                            │  │
│  │  │  - query: str      │    │                    │                            │  │
│  │  │  - library_name?   │    │ Output:            │                            │  │
│  │  │                    │    │  - libraries[]     │                            │  │
│  │  │ Output:            │    │                    │                            │  │
│  │  │  - library_id      │    │ Uses:              │                            │  │
│  │  │  - candidates[]    │    │  LibraryService    │                            │  │
│  │  │                    │    │                    │                            │  │
│  │  │ Uses:              │    └────────────────────┘                            │  │
│  │  │  LibraryService    │                                                      │  │
│  │  └────────────────────┘                                                      │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │ Documentation Tools                                                            │  │
│  │                                                                                │  │
│  │  ┌────────────────────┐    ┌────────────────────┐                            │  │
│  │  │ query_docs         │    │ get_api_reference  │                            │  │
│  │  │                    │    │                    │                            │  │
│  │  │ Input:             │    │ Input:             │                            │  │
│  │  │  - library_id      │    │  - library_id      │                            │  │
│  │  │  - query: str      │    │  - entity_name     │                            │  │
│  │  │  - version?        │    │                    │                            │  │
│  │  │  - max_tokens?     │    │ Output:            │                            │  │
│  │  │    (default: 8000) │    │  - signature       │                            │  │
│  │  │                    │    │  - docstring       │                            │  │
│  │  │ Output:            │    │  - examples        │                            │  │
│  │  │  - docs[]          │    │                    │                            │  │
│  │  │  - code_examples[] │    │ Uses:              │                            │  │
│  │  │                    │    │  QueryService      │                            │  │
│  │  │ Uses:              │    └────────────────────┘                            │  │
│  │  │  QueryService      │                                                      │  │
│  │  └────────────────────┘                                                      │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │ Code Structure Tools                                                           │  │
│  │                                                                                │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │  │
│  │  │query_code_       │  │find_dependencies │  │ find_callers     │            │  │
│  │  │structure         │  │                  │  │                  │            │  │
│  │  │                  │  │ Input:           │  │ Input:           │            │  │
│  │  │ Input:           │  │  - entity_id     │  │  - entity_id     │            │  │
│  │  │  - library_id    │  │  - depth?        │  │                  │            │  │
│  │  │  - query         │  │    (default: 3)  │  │ Output:          │            │  │
│  │  │                  │  │                  │  │  - callers[]     │            │  │
│  │  │ Output:          │  │ Output:          │  │                  │            │  │
│  │  │  - structure     │  │  - dependencies[]│  │ Uses:            │            │  │
│  │  │  - signature     │  │                  │  │  QueryService    │            │  │
│  │  │  - dependencies  │  │ Uses:            │  └──────────────────┘            │  │
│  │  │                  │  │  QueryService    │                                  │  │
│  │  │ Uses:            │  └──────────────────┘  ┌──────────────────┐            │  │
│  │  │  QueryService    │                        │find_              │            │  │
│  │  └──────────────────┘                        │implementations   │            │  │
│  │                                              │                  │            │  │
│  │                                              │ Input:           │            │  │
│  │                                              │  - interface_id  │            │  │
│  │                                              │                  │            │  │
│  │                                              │ Output:          │            │  │
│  │                                              │  - impls[]       │            │  │
│  │                                              │                  │            │  │
│  │                                              │ Uses:            │            │  │
│  │                                              │  QueryService    │            │  │
│  │                                              └──────────────────┘            │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │ GraphRAG Tools                                                                 │  │
│  │                                                                                │  │
│  │  ┌────────────────────┐    ┌────────────────────┐                            │  │
│  │  │ global_search      │    │ local_search       │                            │  │
│  │  │                    │    │                    │                            │  │
│  │  │ Input:             │    │ Input:             │                            │  │
│  │  │  - query: str      │    │  - query: str      │                            │  │
│  │  │  - max_results?    │    │  - entity_id       │                            │  │
│  │  │    (default: 10)   │    │  - max_results?    │                            │  │
│  │  │                    │    │                    │                            │  │
│  │  │ Output:            │    │ Output:            │                            │  │
│  │  │  - results[]       │    │  - results[]       │                            │  │
│  │  │                    │    │                    │                            │  │
│  │  │ Uses:              │    │ Uses:              │                            │  │
│  │  │  QueryService      │    │  QueryService      │                            │  │
│  │  └────────────────────┘    └────────────────────┘                            │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │ Management Tools                                                               │  │
│  │                                                                                │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │  │
│  │  │ index_library    │  │ update_library   │  │ remove_library   │            │  │
│  │  │                  │  │                  │  │                  │            │  │
│  │  │ Input:           │  │ Input:           │  │ Input:           │            │  │
│  │  │  - path          │  │  - library_id    │  │  - library_id    │            │  │
│  │  │  - name          │  │  - incremental?  │  │                  │            │  │
│  │  │  - version?      │  │                  │  │ Output:          │            │  │
│  │  │  - token?        │  │ Output:          │  │  - success       │            │  │
│  │  │                  │  │  - updated_count │  │                  │            │  │
│  │  │ Output:          │  │                  │  │ Uses:            │            │  │
│  │  │  - library_id    │  │ Uses:            │  │  LibraryService  │            │  │
│  │  │  - stats         │  │  IndexService    │  └──────────────────┘            │  │
│  │  │                  │  └──────────────────┘                                  │  │
│  │  │ Uses:            │                        ┌──────────────────┐            │  │
│  │  │  IndexService    │                        │ get_stats        │            │  │
│  │  └──────────────────┘                        │                  │            │  │
│  │                                              │ Input:           │            │  │
│  │                                              │  - library_id?   │            │  │
│  │                                              │                  │            │  │
│  │                                              │ Output:          │            │  │
│  │                                              │  - stats         │            │  │
│  │                                              │                  │            │  │
│  │                                              │ Uses:            │            │  │
│  │                                              │  LibraryService  │            │  │
│  │                                              └──────────────────┘            │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Knowledge Graph Engine コンポーネント図

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          Knowledge Graph Engine (Domain Layer)                       │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                              entities.py                                       │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                              Entity (Base)                               │  │  │
│  │  │                                                                          │  │  │
│  │  │  Attributes:                                                             │  │  │
│  │  │    - id: str (UUID)                                                      │  │  │
│  │  │    - name: str                                                           │  │  │
│  │  │    - kind: EntityKind                                                    │  │  │
│  │  │    - file_path: str                                                      │  │  │
│  │  │    - line_start: int                                                     │  │  │
│  │  │    - line_end: int                                                       │  │  │
│  │  │    - docstring: str | None                                               │  │  │
│  │  │    - metadata: dict                                                      │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │         ▲           ▲           ▲           ▲           ▲                     │  │
│  │         │           │           │           │           │                     │  │
│  │  ┌──────┴───┐ ┌─────┴────┐ ┌────┴─────┐ ┌───┴────┐ ┌────┴────┐               │  │
│  │  │  Class   │ │ Function │ │  Method  │ │ TypeDef│ │ Module  │               │  │
│  │  │          │ │          │ │          │ │        │ │         │               │  │
│  │  │ + bases  │ │ + params │ │ + params │ │ + type │ │ +exports│               │  │
│  │  │ +methods │ │ + returns│ │ + returns│ │        │ │         │               │  │
│  │  │ +attrs   │ │ +decorat │ │ +decorat │ │        │ │         │               │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘ └─────────┘               │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                              relations.py                                      │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                           Relation (Base)                                │  │  │
│  │  │                                                                          │  │  │
│  │  │  Attributes:                                                             │  │  │
│  │  │    - source_id: str                                                      │  │  │
│  │  │    - target_id: str                                                      │  │  │
│  │  │    - kind: RelationKind                                                  │  │  │
│  │  │    - metadata: dict                                                      │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │         ▲           ▲           ▲           ▲           ▲                     │  │
│  │         │           │           │           │           │                     │  │
│  │  ┌──────┴───┐ ┌─────┴────┐ ┌────┴─────┐ ┌───┴────┐ ┌────┴────┐               │  │
│  │  │ Inherits │ │  Calls   │ │ Depends  │ │Implemen│ │TypeRef  │               │  │
│  │  │          │ │          │ │          │ │   ts   │ │         │               │  │
│  │  │ Class →  │ │ Func →   │ │ Module → │ │Class → │ │ Func →  │               │  │
│  │  │ Class    │ │ Func     │ │ Module   │ │ Iface  │ │ Type    │               │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘ └─────────┘               │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                                graph.py                                        │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                         KnowledgeGraph                                   │  │  │
│  │  │                                                                          │  │  │
│  │  │  Dependencies:                                                           │  │  │
│  │  │    - networkx.DiGraph                                                    │  │  │
│  │  │                                                                          │  │  │
│  │  │  Methods:                                                                │  │  │
│  │  │    + add_entity(entity: Entity) -> str                                   │  │  │
│  │  │    + add_relation(relation: Relation) -> None                            │  │  │
│  │  │    + get_entity(entity_id: str) -> Entity | None                         │  │  │
│  │  │    + find_entities(query: str, kind: EntityKind?) -> list[Entity]        │  │  │
│  │  │    + get_dependencies(entity_id: str, depth: int) -> list[Entity]        │  │  │
│  │  │    + get_callers(entity_id: str) -> list[Entity]                         │  │  │
│  │  │    + get_implementations(interface_id: str) -> list[Entity]              │  │  │
│  │  │    + traverse(start_id: str, relation_kinds: list) -> Generator          │  │  │
│  │  │    + get_community(entity_id: str) -> Community                          │  │  │
│  │  │    + detect_communities() -> list[Community]                             │  │  │
│  │  │    + to_dict() -> dict                                                   │  │  │
│  │  │    + from_dict(data: dict) -> KnowledgeGraph                             │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                               indexer.py                                       │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                            Indexer                                       │  │  │
│  │  │                                                                          │  │  │
│  │  │  Dependencies:                                                           │  │  │
│  │  │    - ParserPort (interface)                                              │  │  │
│  │  │    - KnowledgeGraph                                                      │  │  │
│  │  │                                                                          │  │  │
│  │  │  Methods:                                                                │  │  │
│  │  │    + index_file(file_path: str) -> list[Entity]                          │  │  │
│  │  │    + index_directory(dir_path: str) -> KnowledgeGraph                    │  │  │
│  │  │    + extract_entities(ast: AST) -> list[Entity]                          │  │  │
│  │  │    + extract_relations(entities: list[Entity]) -> list[Relation]         │  │  │
│  │  │    + build_graph(entities, relations) -> KnowledgeGraph                  │  │  │
│  │  │    + update_incremental(changed_files: list[str]) -> KnowledgeGraph      │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Infrastructure Layer コンポーネント図

### 4.1 Parser Adapter

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                               Parser Adapter                                         │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                               base.py                                          │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                      ParserPort (Protocol)                               │  │  │
│  │  │                                                                          │  │  │
│  │  │  Abstract Methods:                                                       │  │  │
│  │  │    + parse(source: str) -> AST                                           │  │  │
│  │  │    + get_language() -> str                                               │  │  │
│  │  │    + get_file_extensions() -> list[str]                                  │  │  │
│  │  │    + extract_classes(ast: AST) -> list[ClassNode]                        │  │  │
│  │  │    + extract_functions(ast: AST) -> list[FunctionNode]                   │  │  │
│  │  │    + extract_imports(ast: AST) -> list[ImportNode]                       │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │         ▲           ▲           ▲           ▲           ▲                     │  │
│  │         │           │           │           │           │                     │  │
│  │  ┌──────┴───┐ ┌─────┴────┐ ┌────┴─────┐ ┌───┴────┐ ┌────┴────┐               │  │
│  │  │ Python   │ │TypeScript│ │JavaScript│ │  Rust  │ │   Go    │               │  │
│  │  │ Parser   │ │  Parser  │ │  Parser  │ │ Parser │ │ Parser  │               │  │
│  │  │          │ │          │ │          │ │        │ │         │               │  │
│  │  │ tree-    │ │ tree-    │ │ tree-    │ │ tree-  │ │ tree-   │               │  │
│  │  │ sitter-  │ │ sitter-  │ │ sitter-  │ │ sitter-│ │ sitter- │               │  │
│  │  │ python   │ │typescript│ │javascript│ │ rust   │ │ go      │               │  │
│  │  │          │ │          │ │          │ │        │ │         │               │  │
│  │  │ .py      │ │ .ts,.tsx │ │ .js,.jsx │ │ .rs    │ │ .go     │               │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘ └─────────┘               │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                            registry.py                                         │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                         ParserRegistry                                   │  │  │
│  │  │                                                                          │  │  │
│  │  │  Methods:                                                                │  │  │
│  │  │    + register(parser: ParserPort) -> None                                │  │  │
│  │  │    + get_parser(extension: str) -> ParserPort | None                     │  │  │
│  │  │    + get_parser_by_language(language: str) -> ParserPort | None          │  │  │
│  │  │    + list_supported_languages() -> list[str]                             │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Storage Adapter

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Storage Adapter                                         │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                               ports.py                                         │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                      StoragePort (Protocol)                              │  │  │
│  │  │                                                                          │  │  │
│  │  │  Abstract Methods:                                                       │  │  │
│  │  │    + save_graph(library_id: str, graph: KnowledgeGraph) -> None          │  │  │
│  │  │    + load_graph(library_id: str, version: str?) -> KnowledgeGraph        │  │  │
│  │  │    + delete_graph(library_id: str, version: str?) -> None                │  │  │
│  │  │    + list_libraries() -> list[LibraryInfo]                               │  │  │
│  │  │    + get_library(library_id: str) -> LibraryInfo | None                  │  │  │
│  │  │    + save_metadata(library_id: str, metadata: dict) -> None              │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                               sqlite.py                                        │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                       SQLiteStorage                                      │  │  │
│  │  │                                                                          │  │  │
│  │  │  Implements: StoragePort                                                 │  │  │
│  │  │                                                                          │  │  │
│  │  │  Attributes:                                                             │  │  │
│  │  │    - db_path: str (default: ~/.yata/db.sqlite)                           │  │  │
│  │  │    - connection: sqlite3.Connection                                      │  │  │
│  │  │                                                                          │  │  │
│  │  │  Tables:                                                                 │  │  │
│  │  │    - libraries (id, name, version, path, created_at, metadata)           │  │  │
│  │  │    - entities (id, library_id, kind, name, file_path, data)              │  │  │
│  │  │    - relations (id, library_id, source_id, target_id, kind)              │  │  │
│  │  │    - communities (id, library_id, name, entities, summary)               │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                                cache.py                                        │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                          GraphCache                                      │  │  │
│  │  │                                                                          │  │  │
│  │  │  Attributes:                                                             │  │  │
│  │  │    - max_size: int (default: 10)                                         │  │  │
│  │  │    - cache: OrderedDict[str, KnowledgeGraph]                             │  │  │
│  │  │                                                                          │  │  │
│  │  │  Methods:                                                                │  │  │
│  │  │    + get(library_id: str) -> KnowledgeGraph | None                       │  │  │
│  │  │    + put(library_id: str, graph: KnowledgeGraph) -> None                 │  │  │
│  │  │    + invalidate(library_id: str) -> None                                 │  │  │
│  │  │    + clear() -> None                                                     │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 GitHub Adapter

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                               GitHub Adapter                                         │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                               github.py                                        │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                        GitHubClient                                      │  │  │
│  │  │                                                                          │  │  │
│  │  │  Attributes:                                                             │  │  │
│  │  │    - token: str | None (from GITHUB_TOKEN env)                           │  │  │
│  │  │    - http_client: httpx.AsyncClient                                      │  │  │
│  │  │    - rate_limit_remaining: int                                           │  │  │
│  │  │    - cache_dir: str (default: ~/.yata/repos/)                            │  │  │
│  │  │                                                                          │  │  │
│  │  │  Methods:                                                                │  │  │
│  │  │    + clone_repo(url: str, ref: str?) -> str                              │  │  │
│  │  │    + fetch_file(owner: str, repo: str, path: str) -> str                 │  │  │
│  │  │    + get_repo_info(owner: str, repo: str) -> RepoInfo                    │  │  │
│  │  │    + list_files(owner: str, repo: str, path: str) -> list[str]           │  │  │
│  │  │    + is_cached(url: str, ref: str?) -> bool                              │  │  │
│  │  │    + _handle_rate_limit() -> None                                        │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                       MetadataExtractor                                  │  │  │
│  │  │                                                                          │  │  │
│  │  │  Methods:                                                                │  │  │
│  │  │    + extract_from_package_json(content: str) -> LibraryMetadata          │  │  │
│  │  │    + extract_from_pyproject_toml(content: str) -> LibraryMetadata        │  │  │
│  │  │    + extract_from_cargo_toml(content: str) -> LibraryMetadata            │  │  │
│  │  │    + extract_from_go_mod(content: str) -> LibraryMetadata                │  │  │
│  │  │    + extract_from_readme(content: str) -> str                            │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Application Layer コンポーネント詳細

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Application Layer                                       │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                          library_service.py                                    │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                        LibraryService                                    │  │  │
│  │  │                                                                          │  │  │
│  │  │  Dependencies:                                                           │  │  │
│  │  │    - storage: StoragePort                                                │  │  │
│  │  │    - cache: GraphCache                                                   │  │  │
│  │  │                                                                          │  │  │
│  │  │  Methods:                                                                │  │  │
│  │  │    + resolve_library(query: str) -> list[LibraryMatch]                   │  │  │
│  │  │    + list_libraries() -> list[LibraryInfo]                               │  │  │
│  │  │    + get_library(library_id: str) -> LibraryInfo                         │  │  │
│  │  │    + remove_library(library_id: str) -> bool                             │  │  │
│  │  │    + get_stats(library_id: str?) -> Stats                                │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                           query_service.py                                     │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                         QueryService                                     │  │  │
│  │  │                                                                          │  │  │
│  │  │  Dependencies:                                                           │  │  │
│  │  │    - storage: StoragePort                                                │  │  │
│  │  │    - cache: GraphCache                                                   │  │  │
│  │  │    - graph_engine: KnowledgeGraph                                        │  │  │
│  │  │                                                                          │  │  │
│  │  │  Methods:                                                                │  │  │
│  │  │    + query_docs(library_id, query, version, max_tokens) -> DocsResult    │  │  │
│  │  │    + query_code_structure(library_id, query) -> StructureResult          │  │  │
│  │  │    + find_dependencies(entity_id, depth) -> list[Entity]                 │  │  │
│  │  │    + find_callers(entity_id) -> list[Entity]                             │  │  │
│  │  │    + find_implementations(interface_id) -> list[Entity]                  │  │  │
│  │  │    + global_search(query, max_results) -> list[SearchResult]             │  │  │
│  │  │    + local_search(query, entity_id, max_results) -> list[SearchResult]   │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                           index_service.py                                     │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                         IndexService                                     │  │  │
│  │  │                                                                          │  │  │
│  │  │  Dependencies:                                                           │  │  │
│  │  │    - storage: StoragePort                                                │  │  │
│  │  │    - parser_registry: ParserRegistry                                     │  │  │
│  │  │    - github_client: GitHubClient                                         │  │  │
│  │  │    - indexer: Indexer                                                    │  │  │
│  │  │                                                                          │  │  │
│  │  │  Methods:                                                                │  │  │
│  │  │    + index_library(path, name, version, token?) -> IndexResult           │  │  │
│  │  │    + index_from_github(url, version, token?) -> IndexResult              │  │  │
│  │  │    + update_library(library_id, incremental) -> IndexResult              │  │  │
│  │  │    + watch_path(path, callback) -> WatchHandle                           │  │  │
│  │  │    + _detect_language(file_path) -> str                                  │  │  │
│  │  │    + _extract_metadata(path) -> LibraryMetadata                          │  │  │
│  │  │                                                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                              ports.py                                          │  │
│  │                                                                                │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │  │
│  │  │   StoragePort    │  │   ParserPort     │  │  GitHubPort      │            │  │
│  │  │   (Protocol)     │  │   (Protocol)     │  │  (Protocol)      │            │  │
│  │  │                  │  │                  │  │                  │            │  │
│  │  │  Dependency      │  │  Dependency      │  │  Dependency      │            │  │
│  │  │  Inversion       │  │  Inversion       │  │  Inversion       │            │  │
│  │  │  Principle       │  │  Principle       │  │  Principle       │            │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘            │  │
│  │                                                                                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. 要件トレーサビリティ

| 要件ID | コンポーネント | 説明 |
|--------|----------------|------|
| REQ-KGC-001 | Indexer, ParserPort | ソースコード解析 |
| REQ-KGC-002 | Indexer.extract_relations | 関係性抽出 |
| REQ-KGC-003 | KnowledgeGraph, SQLiteStorage | グラフストレージ |
| REQ-KGC-004 | (future) DocParser | ドキュメント統合 |
| REQ-KGC-005 | SQLiteStorage | バージョン管理 |
| REQ-KGC-006 | KnowledgeGraph.detect_communities | コミュニティ検出 |
| REQ-KGC-007 | GitHubClient | GitHubリポジトリ取得 |
| REQ-KGC-008 | MetadataExtractor | メタデータ抽出 |
| REQ-MCP-001 | MCPApp, server.py | MCPプロトコル準拠 |
| REQ-MCP-002 | resolve_library tool | ライブラリ検索 |
| REQ-MCP-003 | query_docs tool | ドキュメントクエリ |
| REQ-MCP-004 | query_code_structure tool | コード構造クエリ |
| REQ-MCP-005 | find_* tools | グラフ探索 |
| REQ-MCP-006 | resources.py | MCPリソース |
| REQ-MCP-007 | prompts.py | MCPプロンプト |
| REQ-MCP-008 | (全tools) | エラー応答形式 |
| REQ-CLI-001〜006 | CLI commands | CLIインターフェース |
| REQ-LANG-001〜005 | Language Parsers | 言語サポート |

---

## 7. 変更履歴

| バージョン | 日付 | 著者 | 変更内容 |
|------------|------|------|----------|
| 1.0 | 2025-12-31 | MUSUBI SDD | 初版作成 |

---

*Generated by MUSUBI SDD - Design Phase (C4 Component)*
