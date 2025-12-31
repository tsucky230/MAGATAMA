# ADR-004: NetworkX + SQLiteによるグラフストレージ

**Project**: YATA (八咫)
**ADR ID**: ADR-004
**Status**: Accepted
**Date**: 2025-12-31
**Deciders**: MUSUBI SDD
**Related Requirements**: REQ-KGC-003, REQ-KGC-005, REQ-KGC-006, REQ-NFR-003, REQ-NFR-005

---

## Context

YATAは、ソースコードから抽出したエンティティと関係性を知識グラフとして保存・検索する必要があります。

グラフストレージの選択肢：

1. **NetworkX + SQLite**: インメモリグラフ + ファイルDB
2. **Neo4j**: 専用グラフデータベース
3. **PostgreSQL + pg_graphql**: RDBベースのグラフ
4. **Redis Graph**: インメモリグラフDB
5. **SQLite (Graph as tables)**: 純粋RDBアプローチ

### 要件

- ローカル実行: 外部サービス不要 (REQ-NFR-007)
- メモリ使用量: 500MB以下 (REQ-NFR-003)
- クエリ速度: 500ms以下 (REQ-NFR-002)
- バージョン管理: 複数バージョン同時保持 (REQ-KGC-005)
- コミュニティ検出: GraphRAG機能 (REQ-KGC-006)

## Decision

**NetworkX (インメモリ) + SQLite (永続化)** のハイブリッドアプローチを採用する。

### 理由

| 基準 | NetworkX+SQLite | Neo4j | PostgreSQL | Redis Graph |
|------|-----------------|-------|------------|-------------|
| **ローカル実行** | ◎ 完全ローカル | △ サーバー必要 | △ サーバー必要 | △ サーバー必要 |
| **依存関係** | ◎ pip installのみ | × DB設定必要 | × DB設定必要 | × DB設定必要 |
| **グラフアルゴリズム** | ◎ NetworkX内蔵 | ○ Cypher | △ 拡張必要 | △ 制限あり |
| **メモリ効率** | ○ 制御可能 | △ JVMオーバーヘッド | ○ | ◎ |
| **開発速度** | ◎ Python native | △ Cypher学習 | ○ | △ |

### アーキテクチャ

```
                     ┌─────────────────────┐
                     │   Application       │
                     │   (QueryService)    │
                     └──────────┬──────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────┐
│                    KnowledgeGraph                          │
│                                                            │
│   ┌─────────────────────┐    ┌─────────────────────┐     │
│   │     NetworkX        │◄──►│      GraphCache     │     │
│   │     DiGraph         │    │                     │     │
│   │                     │    │  LRU Cache          │     │
│   │  - add_node()       │    │  max_size: 10       │     │
│   │  - add_edge()       │    │                     │     │
│   │  - neighbors()      │    └─────────────────────┘     │
│   │  - shortest_path()  │                                 │
│   │  - community()      │                                 │
│   └──────────┬──────────┘                                 │
│              │                                            │
└──────────────┼────────────────────────────────────────────┘
               │ serialize/deserialize
               ▼
┌───────────────────────────────────────────────────────────┐
│                    SQLiteStorage                           │
│                                                            │
│   ~/.yata/db.sqlite                                        │
│                                                            │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│   │  libraries  │  │  entities   │  │  relations  │      │
│   │             │  │             │  │             │      │
│   │ id          │  │ id          │  │ id          │      │
│   │ name        │  │ library_id  │  │ library_id  │      │
│   │ version     │  │ kind        │  │ source_id   │      │
│   │ path        │  │ name        │  │ target_id   │      │
│   │ metadata    │  │ file_path   │  │ kind        │      │
│   │ created_at  │  │ data (JSON) │  │ metadata    │      │
│   └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                            │
│   ┌─────────────┐                                         │
│   │ communities │                                         │
│   │             │                                         │
│   │ id          │                                         │
│   │ library_id  │                                         │
│   │ entities    │                                         │
│   │ summary     │                                         │
│   └─────────────┘                                         │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

## Implementation

### SQLite Schema

```sql
-- Libraries table
CREATE TABLE libraries (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    path TEXT,
    language TEXT,
    description TEXT,
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, version)
);

-- Entities table
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    library_id TEXT NOT NULL,
    kind TEXT NOT NULL,  -- 'class', 'function', 'method', 'type', 'module'
    name TEXT NOT NULL,
    qualified_name TEXT,
    file_path TEXT NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    signature TEXT,
    docstring TEXT,
    data TEXT,  -- JSON for additional attributes
    FOREIGN KEY (library_id) REFERENCES libraries(id) ON DELETE CASCADE
);

CREATE INDEX idx_entities_library ON entities(library_id);
CREATE INDEX idx_entities_kind ON entities(kind);
CREATE INDEX idx_entities_name ON entities(name);

-- Relations table
CREATE TABLE relations (
    id TEXT PRIMARY KEY,
    library_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    kind TEXT NOT NULL,  -- 'inherits', 'calls', 'depends', 'implements', 'type_ref'
    metadata TEXT,  -- JSON
    FOREIGN KEY (library_id) REFERENCES libraries(id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE INDEX idx_relations_library ON relations(library_id);
CREATE INDEX idx_relations_source ON relations(source_id);
CREATE INDEX idx_relations_target ON relations(target_id);
CREATE INDEX idx_relations_kind ON relations(kind);

-- Communities table (for GraphRAG)
CREATE TABLE communities (
    id TEXT PRIMARY KEY,
    library_id TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 0,  -- hierarchy level
    parent_id TEXT,
    entity_ids TEXT NOT NULL,  -- JSON array
    summary TEXT,
    metadata TEXT,  -- JSON
    FOREIGN KEY (library_id) REFERENCES libraries(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES communities(id) ON DELETE CASCADE
);

CREATE INDEX idx_communities_library ON communities(library_id);
```

### Storage Port Implementation

```python
# infrastructure/storage/sqlite.py
import sqlite3
import json
from pathlib import Path
from typing import Optional
import networkx as nx

from yata.core.graph import KnowledgeGraph
from yata.core.entities import Entity, EntityKind
from yata.core.relations import Relation, RelationKind
from yata.application.ports import StoragePort

class SQLiteStorage(StoragePort):
    """SQLite-based persistent storage for knowledge graphs"""
    
    def __init__(self, db_path: str = "~/.yata/db.sqlite"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA_SQL)
    
    def save_graph(
        self, 
        library_id: str, 
        graph: KnowledgeGraph,
        version: str
    ) -> None:
        """Persist knowledge graph to SQLite"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("BEGIN TRANSACTION")
            try:
                # Save entities
                for entity in graph.get_all_entities():
                    conn.execute("""
                        INSERT OR REPLACE INTO entities 
                        (id, library_id, kind, name, qualified_name, 
                         file_path, line_start, line_end, signature, 
                         docstring, data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entity.id, library_id, entity.kind.value,
                        entity.name, entity.qualified_name,
                        entity.file_path, entity.line_start, entity.line_end,
                        entity.signature, entity.docstring,
                        json.dumps(entity.metadata)
                    ))
                
                # Save relations
                for relation in graph.get_all_relations():
                    conn.execute("""
                        INSERT OR REPLACE INTO relations
                        (id, library_id, source_id, target_id, kind, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        relation.id, library_id, relation.source_id,
                        relation.target_id, relation.kind.value,
                        json.dumps(relation.metadata)
                    ))
                
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
    
    def load_graph(
        self, 
        library_id: str, 
        version: Optional[str] = None
    ) -> KnowledgeGraph:
        """Load knowledge graph from SQLite"""
        graph = KnowledgeGraph()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Load entities
            cursor = conn.execute("""
                SELECT * FROM entities WHERE library_id = ?
            """, (library_id,))
            
            for row in cursor:
                entity = Entity(
                    id=row["id"],
                    kind=EntityKind(row["kind"]),
                    name=row["name"],
                    qualified_name=row["qualified_name"],
                    file_path=row["file_path"],
                    line_start=row["line_start"],
                    line_end=row["line_end"],
                    signature=row["signature"],
                    docstring=row["docstring"],
                    metadata=json.loads(row["data"] or "{}")
                )
                graph.add_entity(entity)
            
            # Load relations
            cursor = conn.execute("""
                SELECT * FROM relations WHERE library_id = ?
            """, (library_id,))
            
            for row in cursor:
                relation = Relation(
                    id=row["id"],
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    kind=RelationKind(row["kind"]),
                    metadata=json.loads(row["metadata"] or "{}")
                )
                graph.add_relation(relation)
        
        return graph
    
    def delete_graph(
        self, 
        library_id: str, 
        version: Optional[str] = None
    ) -> None:
        """Delete knowledge graph for a library"""
        with sqlite3.connect(self.db_path) as conn:
            # CASCADE will handle entities, relations, communities
            conn.execute("DELETE FROM libraries WHERE id = ?", (library_id,))
    
    def list_libraries(self) -> list[dict]:
        """List all indexed libraries"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT l.*, 
                       COUNT(DISTINCT e.id) as entity_count,
                       COUNT(DISTINCT r.id) as relation_count
                FROM libraries l
                LEFT JOIN entities e ON l.id = e.library_id
                LEFT JOIN relations r ON l.id = r.library_id
                GROUP BY l.id
            """)
            return [dict(row) for row in cursor]
```

### KnowledgeGraph with NetworkX

```python
# core/graph.py
import networkx as nx
from typing import Iterator, Optional
from community import community_louvain  # python-louvain

from yata.core.entities import Entity, EntityKind
from yata.core.relations import Relation, RelationKind

class KnowledgeGraph:
    """Knowledge graph using NetworkX for graph operations"""
    
    def __init__(self):
        self._graph = nx.DiGraph()
        self._entities: dict[str, Entity] = {}
        self._relations: dict[str, Relation] = {}
    
    def add_entity(self, entity: Entity) -> str:
        """Add entity to graph"""
        self._entities[entity.id] = entity
        self._graph.add_node(
            entity.id,
            kind=entity.kind.value,
            name=entity.name,
            data=entity
        )
        return entity.id
    
    def add_relation(self, relation: Relation) -> None:
        """Add relation (edge) to graph"""
        self._relations[relation.id] = relation
        self._graph.add_edge(
            relation.source_id,
            relation.target_id,
            kind=relation.kind.value,
            data=relation
        )
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID"""
        return self._entities.get(entity_id)
    
    def find_entities(
        self, 
        query: str, 
        kind: Optional[EntityKind] = None
    ) -> list[Entity]:
        """Find entities by name (partial match)"""
        results = []
        query_lower = query.lower()
        for entity in self._entities.values():
            if kind and entity.kind != kind:
                continue
            if query_lower in entity.name.lower():
                results.append(entity)
        return results
    
    def get_dependencies(
        self, 
        entity_id: str, 
        depth: int = 3
    ) -> list[Entity]:
        """Get dependencies (outgoing edges) up to depth"""
        if entity_id not in self._graph:
            return []
        
        visited = set()
        result = []
        
        def traverse(node_id: str, current_depth: int):
            if current_depth > depth or node_id in visited:
                return
            visited.add(node_id)
            
            for successor in self._graph.successors(node_id):
                if successor in self._entities:
                    result.append(self._entities[successor])
                    traverse(successor, current_depth + 1)
        
        traverse(entity_id, 0)
        return result
    
    def get_callers(self, entity_id: str) -> list[Entity]:
        """Get callers (incoming 'calls' edges)"""
        if entity_id not in self._graph:
            return []
        
        callers = []
        for predecessor in self._graph.predecessors(entity_id):
            edge_data = self._graph.edges[predecessor, entity_id]
            if edge_data.get("kind") == RelationKind.CALLS.value:
                if predecessor in self._entities:
                    callers.append(self._entities[predecessor])
        return callers
    
    def get_implementations(self, interface_id: str) -> list[Entity]:
        """Get implementing classes"""
        if interface_id not in self._graph:
            return []
        
        implementations = []
        for predecessor in self._graph.predecessors(interface_id):
            edge_data = self._graph.edges[predecessor, interface_id]
            if edge_data.get("kind") == RelationKind.IMPLEMENTS.value:
                if predecessor in self._entities:
                    implementations.append(self._entities[predecessor])
        return implementations
    
    def detect_communities(self) -> list[dict]:
        """Detect communities using Louvain algorithm (GraphRAG)"""
        # Convert to undirected for community detection
        undirected = self._graph.to_undirected()
        
        # Run Louvain algorithm
        partition = community_louvain.best_partition(undirected)
        
        # Group entities by community
        communities = {}
        for node_id, community_id in partition.items():
            if community_id not in communities:
                communities[community_id] = []
            if node_id in self._entities:
                communities[community_id].append(self._entities[node_id])
        
        return [
            {
                "id": f"community_{cid}",
                "entities": entities,
                "entity_count": len(entities)
            }
            for cid, entities in communities.items()
        ]
    
    def get_stats(self) -> dict:
        """Get graph statistics"""
        kind_counts = {}
        for entity in self._entities.values():
            kind = entity.kind.value
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        
        return {
            "entity_count": len(self._entities),
            "relation_count": len(self._relations),
            "entity_kinds": kind_counts,
            "node_count": self._graph.number_of_nodes(),
            "edge_count": self._graph.number_of_edges()
        }
    
    def get_all_entities(self) -> Iterator[Entity]:
        """Iterate all entities"""
        return iter(self._entities.values())
    
    def get_all_relations(self) -> Iterator[Relation]:
        """Iterate all relations"""
        return iter(self._relations.values())
```

### Graph Cache

```python
# infrastructure/storage/cache.py
from collections import OrderedDict
from typing import Optional
from yata.core.graph import KnowledgeGraph

class GraphCache:
    """LRU cache for loaded knowledge graphs"""
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self._cache: OrderedDict[str, KnowledgeGraph] = OrderedDict()
    
    def get(self, library_id: str) -> Optional[KnowledgeGraph]:
        """Get graph from cache, move to end (LRU)"""
        if library_id in self._cache:
            self._cache.move_to_end(library_id)
            return self._cache[library_id]
        return None
    
    def put(self, library_id: str, graph: KnowledgeGraph) -> None:
        """Add graph to cache, evict if necessary"""
        if library_id in self._cache:
            self._cache.move_to_end(library_id)
        else:
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)  # Remove oldest
            self._cache[library_id] = graph
    
    def invalidate(self, library_id: str) -> None:
        """Remove graph from cache"""
        self._cache.pop(library_id, None)
    
    def clear(self) -> None:
        """Clear all cached graphs"""
        self._cache.clear()
```

## Consequences

### Positive

1. **ローカル完結**: 外部サーバー不要でREQ-NFR-007準拠
2. **豊富なグラフアルゴリズム**: NetworkXによるコミュニティ検出、最短経路等
3. **シンプルな永続化**: SQLiteファイルでバックアップ・移行容易
4. **メモリ制御**: キャッシュサイズで使用量制御可能

### Negative

1. **スケーラビリティ**: 大規模グラフ（100万ノード以上）では性能低下
2. **同時接続**: SQLiteは書き込み時に排他ロック
3. **メモリ使用**: 大きなグラフはインメモリで保持

### Mitigations

| リスク | 対策 |
|--------|------|
| スケーラビリティ | LRUキャッシュ、遅延ロード、シャーディング検討 |
| 同時接続 | WALモード有効化、読み取り専用接続の活用 |
| メモリ使用 | キャッシュサイズ制限、大きなライブラリは分割 |

## Performance Targets

| 指標 | 目標値 | 備考 |
|------|--------|------|
| グラフロード | < 1秒 | 10,000エンティティ |
| クエリ応答 | < 200ms | 平均 |
| メモリ使用 | < 500MB | 10ライブラリ同時 (REQ-NFR-003) |
| 保存時間 | < 2秒 | インクリメンタル |

## References

- [NetworkX Documentation](https://networkx.org/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [python-louvain](https://github.com/taynaud/python-louvain)
- [GraphRAG (Microsoft)](https://github.com/microsoft/graphrag)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-31 | MUSUBI SDD | Initial version |
