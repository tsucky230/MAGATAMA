# YATA Core - Knowledge Graph Engine

[![PyPI version](https://badge.fury.io/py/yata-core.svg)](https://badge.fury.io/py/yata-core)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

独立したライブラリとして、コード解析と知識グラフ構築機能を提供します。

## 特徴

- 🔍 **マルチ言語解析**: Python, TypeScript, JavaScript, Rust, Go
- 🕸️ **知識グラフ**: NetworkX によるエンティティ・関係性グラフ
- 🔗 **関係性検出**: CALLS, IMPORTS, CONTAINS, INHERITS
- 💾 **永続化**: JSON / SQLite ストレージ

## インストール

```bash
pip install yata-core
```

### オプション言語サポート

```bash
# Rust サポート
pip install yata-core[rust]

# Go サポート
pip install yata-core[go]

# 全言語サポート
pip install yata-core[all-languages]
```

## 使用方法

### 基本的な使い方

```python
from yata_core.infrastructure.parsers import PythonParser
from yata_core.infrastructure.storage import NetworkXKnowledgeGraph
from yata_core.application.usecases import ParseFileUseCase

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
from yata_core.domain.entities import EntityType

# 関数をすべて取得
functions = list(graph.entities.get_by_type(EntityType.FUNCTION))

# 名前で検索
all_entities = list(graph.entities.all())
matches = [e for e in all_entities if "process" in e.name.lower()]
```

### グラフの永続化

```python
from yata_core.infrastructure.storage import JSONGraphSerializer

serializer = JSONGraphSerializer()

# 保存
serializer.save(graph, Path("graph.json"))

# 読み込み
loaded_graph = serializer.load(Path("graph.json"))
```

## アーキテクチャ

YATA Core は Clean Architecture に基づいて設計されています：

```
yata_core/
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

| 言語 | 拡張子 | パーサー |
|------|--------|----------|
| Python | `.py` | `PythonParser` |
| TypeScript | `.ts`, `.tsx` | `TypeScriptParser` |
| JavaScript | `.js`, `.jsx` | `JavaScriptParser` |
| Rust | `.rs` | `RustParser` |
| Go | `.go` | `GoParser` |

## ライセンス

MIT License - 詳細は [LICENSE](../../LICENSE) を参照してください。

## 関連プロジェクト

- [yata-mcp](https://github.com/your-org/yata/tree/main/packages/yata-mcp) - MCP Server
