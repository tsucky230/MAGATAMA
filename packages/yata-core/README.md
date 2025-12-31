# YATA Core - Knowledge Graph Engine

独立したライブラリとして、コード解析と知識グラフ構築機能を提供します。

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

```python
from yata_core import Entity, EntityType, Location

# エンティティを作成
entity = Entity(
    id="func_001",
    name="calculate",
    type=EntityType.FUNCTION,
    location=Location(file="main.py", line=10, column=0)
)
```

## ライセンス

MIT License
