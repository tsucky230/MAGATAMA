# magatama-core - Knowledge Graph Engine

[![PyPI version](https://badge.fury.io/py/magatama-core.svg)](https://badge.fury.io/py/magatama-core)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> [MAGATAMA](https://github.com/tsucky230/MAGATAMA)（[YATA](https://github.com/nahisaho/YATA) のフォーク）の
> コアライブラリパッケージです（パッケージ名 `magatama-core` / import 名 `magatama_core`）。

独立したライブラリとして、コード解析と知識グラフ構築機能を提供します。

## 特徴

- 🔍 **マルチ言語解析**: Python, TypeScript, Rust, Go, Java, C# ほか **24 言語**
- 🕸️ **知識グラフ**: NetworkX によるエンティティ・関係性グラフ
- 🔗 **関係性検出**: CALLS, IMPORTS, CONTAINS, INHERITS
- 💾 **永続化**: JSON / SQLite ストレージ

## インストール

```bash
pip install magatama-core
```

### オプション言語サポート

```bash
# Rust サポート
pip install magatama-core[rust]

# Go サポート
pip install magatama-core[go]

# 全言語サポート
pip install magatama-core[all-languages]
```

## 使用方法

### 基本的な使い方

```python
from magatama_core.infrastructure.parsers import PythonParser
from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph
from magatama_core.application.usecases import ParseFileUseCase

# パーサーとグラフを作成
parser = PythonParser()
graph = NetworkXKnowledgeGraph()

# ユースケースを設定
parse_file = ParseFileUseCase(
    parsers={".py": parser},
    knowledge_graph=graph,
)

# ファイルを解析
from pathlib import Path
result = parse_file.execute(Path("your_file.py"))

print(f"Entities: {result.entity_count}")
print(f"Relationships: {result.relationship_count}")
```

### エンティティの検索

```python
from magatama_core.domain.entities import EntityType

# 関数をすべて取得
functions = list(graph.entities.get_by_type(EntityType.FUNCTION))

# 名前で検索
all_entities = list(graph.entities.all())
matches = [e for e in all_entities if "process" in e.name.lower()]
```

### グラフの永続化

```python
from magatama_core.infrastructure.storage import JSONGraphSerializer

serializer = JSONGraphSerializer()

# 保存
serializer.save(graph, Path("graph.json"))

# 読み込み
loaded_graph = serializer.load(Path("graph.json"))
```

## アーキテクチャ

magatama-core は Clean Architecture に基づいて設計されています：

```
magatama_core/
├── domain/          # ドメイン層
│   ├── entities/    # FunctionEntity, ClassEntity, etc.
│   ├── value_objects/ # EntityId, Location
│   └── repositories/ # インターフェース
├── application/     # アプリケーション層
│   ├── usecases/    # ParseFileUseCase, etc.
│   └── services/    # Benchmark, etc.
└── infrastructure/  # インフラ層
    ├── parsers/     # PythonParser, TypeScriptParser, etc.
    └── storage/     # NetworkXKnowledgeGraph, SQLiteKnowledgeGraph
```

## 対応言語

合計 **24 言語**に対応しています（主要なものを抜粋）。全一覧は
[ルート README](https://github.com/tsucky230/MAGATAMA#-対応言語-24-言語) を参照。

| 言語 | 拡張子 | パーサー |
|------|--------|----------|
| Python | `.py` | `PythonParser` |
| TypeScript | `.ts`, `.tsx` | `TypeScriptParser` |
| JavaScript | `.js`, `.jsx` | `JavaScriptParser` |
| Rust | `.rs` | `RustParser` |
| Go | `.go` | `GoParser` |
| Java / C# / C / C++ / Ruby / PHP ほか | — | （計 24 言語） |

## ライセンス

MIT License - 詳細は [LICENSE](../../LICENSE) を参照してください。

## 関連プロジェクト

- [magatama-mcp](https://github.com/tsucky230/MAGATAMA/tree/main/packages/magatama-mcp) - MCP Server
