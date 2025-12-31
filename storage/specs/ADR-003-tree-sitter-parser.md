# ADR-003: Tree-sitterによるAST解析

**Project**: YATA (八咫)
**ADR ID**: ADR-003
**Status**: Accepted
**Date**: 2025-12-31
**Deciders**: MUSUBI SDD
**Related Requirements**: REQ-KGC-001, REQ-LANG-001〜005

---

## Context

YATAは、プログラミング言語のソースコードからエンティティ（クラス、関数、メソッド等）と関係性（継承、呼び出し等）を抽出し、知識グラフを構築する必要があります。

ソースコード解析の方法として、以下の選択肢があります：

1. **Tree-sitter**: 増分パーサージェネレーター
2. **Language Server Protocol (LSP)**: 言語サーバー連携
3. **正規表現ベース**: パターンマッチング
4. **言語固有AST**: ast (Python), TypeScript Compiler API等

### 要件

- 5言語サポート: Python, TypeScript, JavaScript, Rust, Go
- 高速解析: 100,000行/30秒以下 (REQ-NFR-001)
- エラー耐性: 構文エラーがあっても部分解析可能
- 拡張性: 新しい言語の追加が容易 (REQ-NFR-008)

## Decision

**Tree-sitter** を採用する。

### 理由

| 基準 | Tree-sitter | LSP | 正規表現 | 言語固有AST |
|------|-------------|-----|----------|-------------|
| **多言語サポート** | ◎ 40+言語 | ○ 言語サーバー依存 | × 言語ごとに複雑 | × 言語ごとに別実装 |
| **パフォーマンス** | ◎ 増分パース | △ プロセス間通信 | ○ 高速 | ○ 言語依存 |
| **エラー耐性** | ◎ 部分解析可能 | ○ 言語サーバー依存 | × 困難 | △ 言語依存 |
| **拡張性** | ◎ グラマー追加のみ | △ サーバー追加必要 | × 大規模改修 | × 別実装必要 |
| **依存関係** | ○ 軽量 | × 各言語サーバー | ◎ なし | △ 言語ランタイム |

### Tree-sitterの特徴

1. **増分パーシング**: 変更部分のみ再解析で高速
2. **エラーリカバリ**: 構文エラーがあっても有効な部分のASTを生成
3. **統一的なAPI**: 全言語で同じインターフェース
4. **C言語ベース**: Pythonバインディングで高速に利用可能

## Implementation

### Parser Interface (Ports)

```python
# application/ports.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class ASTNode:
    """AST Node representation"""
    type: str
    text: str
    start_point: tuple[int, int]  # (row, col)
    end_point: tuple[int, int]
    children: list["ASTNode"]

class ParserPort(Protocol):
    """Parser interface for dependency inversion"""
    
    def parse(self, source: str) -> ASTNode:
        """Parse source code and return AST root"""
        ...
    
    def get_language(self) -> str:
        """Return language identifier"""
        ...
    
    def get_file_extensions(self) -> list[str]:
        """Return supported file extensions"""
        ...
    
    def extract_classes(self, ast: ASTNode) -> list["ClassNode"]:
        """Extract class definitions from AST"""
        ...
    
    def extract_functions(self, ast: ASTNode) -> list["FunctionNode"]:
        """Extract function definitions from AST"""
        ...
    
    def extract_imports(self, ast: ASTNode) -> list["ImportNode"]:
        """Extract import statements from AST"""
        ...
```

### Base Parser Implementation

```python
# infrastructure/parsers/base.py
import tree_sitter
from tree_sitter import Language, Parser

class TreeSitterParser:
    """Base class for Tree-sitter based parsers"""
    
    def __init__(self, language: Language):
        self.parser = Parser()
        self.parser.set_language(language)
    
    def parse(self, source: str) -> ASTNode:
        tree = self.parser.parse(bytes(source, "utf-8"))
        return self._convert_node(tree.root_node)
    
    def _convert_node(self, node: tree_sitter.Node) -> ASTNode:
        return ASTNode(
            type=node.type,
            text=node.text.decode("utf-8") if node.text else "",
            start_point=(node.start_point[0], node.start_point[1]),
            end_point=(node.end_point[0], node.end_point[1]),
            children=[self._convert_node(child) for child in node.children]
        )
    
    def query(self, ast: ASTNode, query_string: str) -> list[ASTNode]:
        """Execute Tree-sitter query on AST"""
        # Tree-sitter query language for pattern matching
        ...
```

### Language-Specific Parsers

#### Python Parser

```python
# infrastructure/parsers/python.py
from tree_sitter_python import language as python_language

class PythonParser(TreeSitterParser, ParserPort):
    """Python source code parser"""
    
    def __init__(self):
        super().__init__(Language(python_language()))
    
    def get_language(self) -> str:
        return "python"
    
    def get_file_extensions(self) -> list[str]:
        return [".py", ".pyi"]
    
    def extract_classes(self, ast: ASTNode) -> list[ClassNode]:
        """Extract Python class definitions"""
        query = """
        (class_definition
            name: (identifier) @class_name
            superclasses: (argument_list)? @bases
            body: (block) @body
        ) @class
        """
        matches = self.query(ast, query)
        return [self._parse_class(match) for match in matches]
    
    def extract_functions(self, ast: ASTNode) -> list[FunctionNode]:
        """Extract Python function definitions"""
        query = """
        (function_definition
            name: (identifier) @func_name
            parameters: (parameters) @params
            return_type: (type)? @return_type
            body: (block) @body
        ) @function
        """
        matches = self.query(ast, query)
        return [self._parse_function(match) for match in matches]
    
    def _parse_class(self, match: dict) -> ClassNode:
        # Parse class definition with:
        # - Base classes (inheritance)
        # - Methods
        # - Attributes
        # - Decorators
        # - Type hints
        ...
```

#### TypeScript Parser

```python
# infrastructure/parsers/typescript.py
from tree_sitter_typescript import language as ts_language

class TypeScriptParser(TreeSitterParser, ParserPort):
    """TypeScript source code parser"""
    
    def __init__(self):
        super().__init__(Language(ts_language()))
    
    def get_language(self) -> str:
        return "typescript"
    
    def get_file_extensions(self) -> list[str]:
        return [".ts", ".tsx", ".mts", ".cts"]
    
    def extract_classes(self, ast: ASTNode) -> list[ClassNode]:
        """Extract TypeScript class definitions"""
        query = """
        (class_declaration
            name: (type_identifier) @class_name
            type_parameters: (type_parameters)? @generics
            (class_heritage)? @heritage
            body: (class_body) @body
        ) @class
        """
        ...
    
    def extract_interfaces(self, ast: ASTNode) -> list[InterfaceNode]:
        """Extract TypeScript interface definitions"""
        query = """
        (interface_declaration
            name: (type_identifier) @interface_name
            type_parameters: (type_parameters)? @generics
            body: (interface_body) @body
        ) @interface
        """
        ...
```

### Parser Registry

```python
# infrastructure/parsers/registry.py
class ParserRegistry:
    """Registry for language parsers"""
    
    def __init__(self):
        self._parsers: dict[str, ParserPort] = {}
        self._extension_map: dict[str, str] = {}
    
    def register(self, parser: ParserPort) -> None:
        language = parser.get_language()
        self._parsers[language] = parser
        for ext in parser.get_file_extensions():
            self._extension_map[ext] = language
    
    def get_parser(self, extension: str) -> ParserPort | None:
        language = self._extension_map.get(extension)
        if language:
            return self._parsers.get(language)
        return None
    
    def get_parser_by_language(self, language: str) -> ParserPort | None:
        return self._parsers.get(language)
    
    def list_supported_languages(self) -> list[str]:
        return list(self._parsers.keys())

# Default registry initialization
def create_default_registry() -> ParserRegistry:
    registry = ParserRegistry()
    registry.register(PythonParser())
    registry.register(TypeScriptParser())
    registry.register(JavaScriptParser())
    registry.register(RustParser())
    registry.register(GoParser())
    return registry
```

### Entity Extraction Flow

```
Source Code (.py)
       │
       ▼
┌─────────────────┐
│  Tree-sitter    │
│  Parser         │
└────────┬────────┘
         │ AST
         ▼
┌─────────────────┐
│  PythonParser   │
│  extract_*      │
└────────┬────────┘
         │ ClassNode, FunctionNode, etc.
         ▼
┌─────────────────┐
│  Indexer        │
│  build_graph    │
└────────┬────────┘
         │ Entity, Relation
         ▼
┌─────────────────┐
│  Knowledge      │
│  Graph          │
└─────────────────┘
```

## Consequences

### Positive

1. **統一的なAPI**: 全言語で同じインターフェースを使用可能
2. **高パフォーマンス**: C言語ベースで高速、増分パースで更に効率化
3. **エラー耐性**: 構文エラーがあっても部分的なAST取得可能
4. **拡張容易**: 新言語はグラマー追加とパーサー実装のみ

### Negative

1. **グラマーサイズ**: 各言語のグラマーファイルが必要（数MB）
2. **言語固有知識**: 正確な抽出には言語仕様の理解が必要
3. **ネイティブ依存**: Tree-sitterはCライブラリに依存

### Mitigations

| リスク | 対策 |
|--------|------|
| グラマーサイズ | 遅延ロード、必要な言語のみインストール |
| 言語固有知識 | 各言語のTree-sitterクエリをテスト駆動で開発 |
| ネイティブ依存 | Pythonバインディングでラップ、CI/CDで複数環境テスト |

## Tree-sitter Query Examples

### Python: クラス抽出

```scheme
; Python class with bases
(class_definition
  name: (identifier) @class.name
  superclasses: (argument_list
    (identifier) @class.base)*
  body: (block
    (function_definition
      name: (identifier) @method.name
      decorators: (decorator
        (identifier) @decorator)*)?))
```

### TypeScript: インターフェース抽出

```scheme
; TypeScript interface with generics
(interface_declaration
  name: (type_identifier) @interface.name
  type_parameters: (type_parameters
    (type_parameter
      name: (type_identifier) @generic.name))?
  body: (interface_body
    (property_signature
      name: (property_identifier) @property.name
      type: (_) @property.type)?
    (method_signature
      name: (property_identifier) @method.name)?))
```

## Language Support Priority

| Priority | Language | Parser Package | Status |
|----------|----------|----------------|--------|
| High | Python | tree-sitter-python | REQ-LANG-001 |
| High | TypeScript | tree-sitter-typescript | REQ-LANG-002 |
| High | JavaScript | tree-sitter-javascript | REQ-LANG-003 |
| Medium | Rust | tree-sitter-rust | REQ-LANG-004 |
| Medium | Go | tree-sitter-go | REQ-LANG-005 |

## References

- [Tree-sitter Official](https://tree-sitter.github.io/)
- [Tree-sitter Python Bindings](https://github.com/tree-sitter/py-tree-sitter)
- [Tree-sitter Query Syntax](https://tree-sitter.github.io/tree-sitter/using-parsers#query-syntax)
- [CodeGraphMCPServer](https://github.com/nahisaho/CodeGraphMCPServer) - Reference implementation

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-31 | MUSUBI SDD | Initial version |
