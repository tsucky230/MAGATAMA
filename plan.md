# 計画書: comP インデックス連携機能（comP Bridge）

**ブランチ**: `ftr/comp-bridge`
**作成日**: 2026-06-12
**ステータス**: 計画（未実装）

---

## 1. 背景と目的

[comP](https://github.com/tsucky230/comP) は VSCode 拡張 + Rust デーモンで構成されるコードインデックスエンジンで、
ワークスペースを解析した結果を `<workspace>/.comp/index.db`（SQLite）に保存する。
現状 comP のインデックスは comP 自身の MCP デーモン経由でしか利用できない。

本機能は **YATA が comP のインデックス（SQLite）を直接読み取り、YATA の知識グラフに変換する**
アダプターを追加する。これにより:

- comP がバックグラウンドで構築したインデックスを、YATA の既存 34 ツール
  （`search_entities` / `get_related_entities` / `hybrid_search` / `analyze_impact` など）から利用できる
- VSCode を起動していなくても、Claude Desktop / Cursor / Copilot Chat から
  プロジェクト全体の構造に LLM が質問できる
- YATA 側で再パースする必要がない（comP の解析結果をそのまま流用、トークン・時間の節約）

```
[comP Rust Daemon] ──書込──> .comp/index.db (SQLite, WALモード)
                                   │ 読み取り専用で接続
                                   ▼
                     [YATA CompIndexReader] ──変換──> NetworkXKnowledgeGraph
                                   │
                                   ▼
                  [YATA MCP Server (FastMCP)] ──MCP──> Claude Desktop / Cursor / Copilot
```

**方式の選定理由**: comP デーモンへの HTTP/IPC 接続ではなく SQLite 直読みを採用する。
comP のスキーマ定義（`daemon/src/graph/schema.rs`）が WAL モード + `busy_timeout=5000` を
明示的に設定しており、「MCP デーモンが書き込み中でも別プロセスから並行読み取りできる」ことを
設計意図としてコメントに記している。デーモンプロセスの起動・生存管理が不要になり、
実装が Python 標準ライブラリ `sqlite3` だけで完結する。

---

## 2. 前提知識（実装者が読むべき情報）

### 2.1 comP のインデックス格納場所とスキーマ

- 場所: `<ワークスペースルート>/.comp/index.db`
- 参照実装: `e:/dev/comP/daemon/src/graph/schema.rs`

```sql
-- files: インデックス済みソースファイル
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,        -- ファイルパス
    hash TEXT NOT NULL,
    language TEXT NOT NULL,
    last_indexed INTEGER NOT NULL DEFAULT 0,
    char_count INTEGER NOT NULL DEFAULT 0   -- migration 002 で追加
);

-- nodes: シンボル（関数・クラス・型など）
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,         -- files.id への FK
    name TEXT NOT NULL,
    kind TEXT NOT NULL,               -- 下記 2.2 の値
    line INTEGER NOT NULL,            -- ★1-based（tree-sitter row + 1 で格納される）
    col INTEGER NOT NULL,             -- 0-based
    scope TEXT,                       -- 親スコープ名（クラス名など）。YATAのscope（可視性）とは意味が異なる
    is_exported INTEGER DEFAULT 0,
    signature TEXT                    -- 関数シグネチャ
);

-- edges: シンボル間の依存
CREATE TABLE edges (
    from_id INTEGER NOT NULL,         -- nodes.id
    to_id INTEGER NOT NULL,           -- nodes.id
    kind TEXT NOT NULL,               -- 下記 2.3 の値
    PRIMARY KEY (from_id, to_id, kind)
);

-- metadata: key-value（tokens_sent, tokens_saved, queries_count, version など）
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
```

### 2.2 comP の `nodes.kind` の取りうる値

参照: `e:/dev/comP/daemon/src/indexer/parser.rs` の `SymbolKind::as_str()`

`function`, `class`, `interface`, `struct`, `enum`, `type`, `variable`,
`constant`, `module`, `namespace`, `method`, `property`, `unknown`

### 2.3 comP の `edges.kind` の取りうる値

参照: `e:/dev/comP/daemon/src/indexer/dependency.rs` の `EdgeKind::as_str()`

`import`, `function_call`, `type_reference`, `inheritance`

※ スキーマコメントには `calls`, `references`, `extends`, `implements` も例示されているため、
これらも受理できるようにする（将来の comP バージョン互換のため）。
**未知の kind はエラーにせず `DEPENDS_ON` にフォールバックする。**

### 2.4 YATA 側のドメインモデル

| ファイル | 内容 |
|---|---|
| `packages/magatama-core/src/magatama_core/domain/entities/base.py` | `Entity`（pydantic, frozen）, `EntityType` |
| `packages/magatama-core/src/magatama_core/domain/entities/relationships.py` | `Relationship`, `RelationshipType` |
| `packages/magatama-core/src/magatama_core/domain/value_objects/ids.py` | `EntityId(value: str)` |
| `packages/magatama-core/src/magatama_core/domain/value_objects/location.py` | `Location(file, line>=1, column>=0)` |
| `packages/magatama-core/src/magatama_core/infrastructure/storage/networkx_graph.py` | `NetworkXKnowledgeGraph`（`entities.add/delete/all`, `relationships.add/delete/all` を持つ） |
| `packages/magatama-mcp/src/magatama_mcp/server/protocol.py` | FastMCP サーバー本体。`@mcp.tool()` でツール登録。**今回ツールを追加するのはこのファイル** |

注意: `packages/magatama-mcp/src/magatama_mcp/server/mcp_server.py`（`MagatamaMcpServer`）は CLI
（`magatama query` 等）から使われる別実装。今回の必須スコープは `protocol.py` のみ（§4 Task 4 参照）。

---

## 3. マッピング仕様

### 3.1 EntityType マッピング（comP `nodes.kind` → YATA `EntityType`）

| comP kind | YATA EntityType | 備考 |
|---|---|---|
| `function` | `FUNCTION` | |
| `class` | `CLASS` | |
| `interface` | `INTERFACE` | |
| `struct` | `STRUCT` | |
| `enum` | `ENUM` | |
| `type` | `TYPE` | |
| `variable` | `VARIABLE` | |
| `constant` | `VARIABLE` | YATA に CONSTANT が無いため |
| `module` | `MODULE` | |
| `namespace` | `MODULE` | |
| `method` | `METHOD` | |
| `property` | `VARIABLE` | |
| `unknown` / その他 | `VARIABLE` | フォールバック。エラーにしない |

### 3.2 RelationshipType マッピング（comP `edges.kind` → YATA `RelationshipType`）

| comP kind | YATA RelationshipType |
|---|---|
| `import` / `imports` | `IMPORTS` |
| `function_call` / `calls` | `CALLS` |
| `type_reference` / `references` | `REFERENCES` |
| `inheritance` / `extends` | `INHERITS` |
| `implements` | `IMPLEMENTS` |
| その他（未知） | `DEPENDS_ON` |

### 3.3 Entity への変換ルール

comP の **nodes 1行 → YATA Entity 1個**、さらに **files 1行 → MODULE Entity 1個** を生成する。

**シンボル（nodes 由来）**:

- `id`: `EntityId(value=f"comp:{alias}:n{node_id}")`
  - `alias` はワークスペースルートのフォルダ名を小文字化したもの（例: `e:/dev/myproj` → `myproj`）。
    複数の comP インデックスを同時ロードしても ID が衝突しないようにするため
  - `n` プレフィックスは files 由来 Entity（`f` プレフィックス）との衝突防止
- `name`: `nodes.name`
- `type`: §3.1 のマッピング
- `location`: `Location(file=files.path, line=max(nodes.line, 1), column=max(nodes.col, 0))`
  - comP の line は 1-based だが、防御的に `max(..., 1)` でクランプする
    （YATA の `Location` は `line >= 1` をバリデーションするため、0 が来ると例外になる）
- `docstring`: `nodes.signature`（NULL なら `None`）。シグネチャ情報の格納先として流用する
- `scope`: `is_exported == 1` なら `"public"`、それ以外は `"private"`
  - comP の `nodes.scope`（親スコープ名）はここには入れない（§3.4 で関係に変換）

**ファイル（files 由来）**:

- `id`: `EntityId(value=f"comp:{alias}:f{file_id}")`
- `name`: `files.path`（パス全体。検索でパス断片がヒットするように）
- `type`: `MODULE`
- `location`: `Location(file=files.path, line=1, column=0)`
- `docstring`: `f"language={files.language}"`
- `scope`: `"public"`

### 3.4 Relationship への変換ルール

1. **edges 由来**: `Relationship(source_id=comp:{alias}:n{from_id}, target_id=comp:{alias}:n{to_id}, type=§3.2のマッピング, metadata={"origin": "comp"})`
   - from_id / to_id が nodes に存在しない（孤立エッジ）の場合はスキップし、スキップ数をカウントする
2. **ファイル包含**: 各 node について `Relationship(source_id=f{file_id}のEntity, target_id=そのnodeのEntity, type=CONTAINS, metadata={"origin": "comp"})`
3. **親スコープ包含（ベストエフォート）**: `nodes.scope` が非 NULL のとき、
   **同一ファイル内**で `name == scope` の node が**ちょうど 1 件**あれば
   `Relationship(source_id=親, target_id=子, type=CONTAINS, metadata={"origin": "comp-scope"})` を追加。
   0 件または複数件の場合は何もしない（曖昧な推測をしない）

---

## 4. 実装タスク

### Task 1: `CompIndexReader` の実装

**新規ファイル**: `packages/magatama-core/src/magatama_core/infrastructure/storage/comp_index_reader.py`

```python
"""comP index.db reader.

Reads a comP (https://github.com/tsucky230/comP) SQLite index in read-only
mode and converts it into YATA domain entities/relationships.
"""

from __future__ import annotations

import sqlite3
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

from magatama_core.domain.entities.base import Entity, EntityType
from magatama_core.domain.entities.relationships import Relationship, RelationshipType
from magatama_core.domain.value_objects.ids import EntityId
from magatama_core.domain.value_objects.location import Location

# §3.1 のマッピング
_KIND_TO_ENTITY_TYPE: dict[str, EntityType] = {
    "function": EntityType.FUNCTION,
    "class": EntityType.CLASS,
    "interface": EntityType.INTERFACE,
    "struct": EntityType.STRUCT,
    "enum": EntityType.ENUM,
    "type": EntityType.TYPE,
    "variable": EntityType.VARIABLE,
    "constant": EntityType.VARIABLE,
    "module": EntityType.MODULE,
    "namespace": EntityType.MODULE,
    "method": EntityType.METHOD,
    "property": EntityType.VARIABLE,
}
_DEFAULT_ENTITY_TYPE = EntityType.VARIABLE

# §3.2 のマッピング
_EDGE_TO_RELATIONSHIP_TYPE: dict[str, RelationshipType] = {
    "import": RelationshipType.IMPORTS,
    "imports": RelationshipType.IMPORTS,
    "function_call": RelationshipType.CALLS,
    "calls": RelationshipType.CALLS,
    "type_reference": RelationshipType.REFERENCES,
    "references": RelationshipType.REFERENCES,
    "inheritance": RelationshipType.INHERITS,
    "extends": RelationshipType.INHERITS,
    "implements": RelationshipType.IMPLEMENTS,
}
_DEFAULT_RELATIONSHIP_TYPE = RelationshipType.DEPENDS_ON


@dataclass
class CompIndexData:
    """Result of reading a comP index."""

    alias: str
    db_path: str
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    files_count: int = 0
    nodes_count: int = 0
    edges_count: int = 0
    skipped_edges: int = 0
    metadata: dict[str, str] = field(default_factory=dict)


class CompIndexNotFoundError(FileNotFoundError):
    """Raised when no comP index.db can be located at the given path."""


def resolve_db_path(path: str | Path) -> Path:
    """Resolve a user-supplied path to the actual index.db file.

    Accepts: workspace root, the .comp directory, or the .db file itself.
    Raises CompIndexNotFoundError if nothing is found.
    """
    p = Path(path)
    candidates = [p, p / "index.db", p / ".comp" / "index.db"]
    for c in candidates:
        if c.is_file() and c.suffix == ".db":
            return c
    raise CompIndexNotFoundError(
        f"comP index not found at {path!r} (tried: "
        + ", ".join(str(c) for c in candidates) + ")"
    )


def derive_alias(db_path: Path) -> str:
    """Derive a stable alias from the workspace root folder name.

    <root>/.comp/index.db -> root folder name, lowercased.
    Falls back to the parent directory name for direct .db paths.
    """
    parent = db_path.parent
    if parent.name == ".comp":
        return parent.parent.name.lower()
    return parent.name.lower()


class CompIndexReader:
    """Reads a comP SQLite index in read-only mode."""

    def read(self, path: str | Path) -> CompIndexData:
        db_path = resolve_db_path(path)
        alias = derive_alias(db_path)
        # 読み取り専用 URI 接続。comP デーモンが書き込み中でも WAL により並行読み取り可能
        uri = f"file:{urllib.parse.quote(db_path.as_posix())}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            return self._read_all(conn, alias, db_path)
        finally:
            conn.close()

    def _read_all(
        self, conn: sqlite3.Connection, alias: str, db_path: Path
    ) -> CompIndexData:
        data = CompIndexData(alias=alias, db_path=str(db_path))

        # metadata（存在しないテーブルでも落ちないよう防御）
        try:
            for row in conn.execute("SELECT key, value FROM metadata"):
                data.metadata[row["key"]] = row["value"]
        except sqlite3.OperationalError:
            pass

        # files -> MODULE entities
        file_entity_ids: dict[int, EntityId] = {}
        for row in conn.execute(
            "SELECT id, path, language FROM files ORDER BY id"
        ):
            eid = EntityId(value=f"comp:{alias}:f{row['id']}")
            file_entity_ids[row["id"]] = eid
            data.entities.append(
                Entity(
                    id=eid,
                    name=row["path"],
                    type=EntityType.MODULE,
                    location=Location(file=row["path"], line=1, column=0),
                    docstring=f"language={row['language']}",
                    scope="public",
                )
            )
            data.files_count += 1

        # nodes -> symbol entities
        node_entity_ids: dict[int, EntityId] = {}
        # 親スコープ解決用: (file_id, name) -> [node_id, ...]
        nodes_by_file_and_name: dict[tuple[int, str], list[int]] = {}
        # 親スコープ解決用: node_id -> (file_id, scope)
        node_scopes: dict[int, tuple[int, str]] = {}

        for row in conn.execute(
            "SELECT id, file_id, name, kind, line, col, scope,"
            " is_exported, signature FROM nodes ORDER BY id"
        ):
            file_path = ""
            file_eid = file_entity_ids.get(row["file_id"])
            # files に無い file_id を持つ node はスキップしない（locationだけ不明扱い）
            for e in data.entities:
                if file_eid is not None and e.id == file_eid:
                    file_path = e.name
                    break
            eid = EntityId(value=f"comp:{alias}:n{row['id']}")
            node_entity_ids[row["id"]] = eid
            data.entities.append(
                Entity(
                    id=eid,
                    name=row["name"],
                    type=_KIND_TO_ENTITY_TYPE.get(
                        row["kind"], _DEFAULT_ENTITY_TYPE
                    ),
                    location=Location(
                        file=file_path or "<unknown>",
                        line=max(int(row["line"]), 1),
                        column=max(int(row["col"]), 0),
                    ),
                    docstring=row["signature"],
                    scope="public" if row["is_exported"] else "private",
                )
            )
            data.nodes_count += 1

            key = (row["file_id"], row["name"])
            nodes_by_file_and_name.setdefault(key, []).append(row["id"])
            if row["scope"]:
                node_scopes[row["id"]] = (row["file_id"], row["scope"])

            # ファイル包含 CONTAINS
            if file_eid is not None:
                data.relationships.append(
                    Relationship(
                        source_id=file_eid,
                        target_id=eid,
                        type=RelationshipType.CONTAINS,
                        metadata={"origin": "comp"},
                    )
                )

        # 親スコープ包含 CONTAINS（同一ファイル内で一意に解決できる場合のみ）
        for child_id, (file_id, scope_name) in node_scopes.items():
            parents = nodes_by_file_and_name.get((file_id, scope_name), [])
            if len(parents) == 1 and parents[0] != child_id:
                data.relationships.append(
                    Relationship(
                        source_id=node_entity_ids[parents[0]],
                        target_id=node_entity_ids[child_id],
                        type=RelationshipType.CONTAINS,
                        metadata={"origin": "comp-scope"},
                    )
                )

        # edges -> relationships
        for row in conn.execute("SELECT from_id, to_id, kind FROM edges"):
            src = node_entity_ids.get(row["from_id"])
            dst = node_entity_ids.get(row["to_id"])
            if src is None or dst is None:
                data.skipped_edges += 1
                continue
            data.relationships.append(
                Relationship(
                    source_id=src,
                    target_id=dst,
                    type=_EDGE_TO_RELATIONSHIP_TYPE.get(
                        row["kind"], _DEFAULT_RELATIONSHIP_TYPE
                    ),
                    metadata={"origin": "comp", "comp_kind": row["kind"]},
                )
            )
            data.edges_count += 1

        return data
```

**実装上の注意（上記スケルトンからの改善余地・必須修正）**:

- ⚠️ 上記スケルトンの `file_path` 解決はリスト線形探索になっている。実装時は
  `file_id -> path` の dict（`file_paths: dict[int, str]`）を files 読み取り時に作り、
  O(1) で引くこと
- `__init__.py`（`packages/magatama-core/src/magatama_core/infrastructure/storage/__init__.py`）に
  `CompIndexReader`, `CompIndexData`, `CompIndexNotFoundError`, `resolve_db_path` を再エクスポートする
- Windows パス対応のため `db_path.as_posix()` + `urllib.parse.quote` を使う（スペース・`#` 対策）

### Task 2: `LoadCompIndexUseCase` の実装

**新規ファイル**: `packages/magatama-core/src/magatama_core/application/usecases/comp_usecase.py`

```python
"""Use case for loading a comP external index into the knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from magatama_core.domain.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from magatama_core.infrastructure.storage.comp_index_reader import (
    CompIndexReader,
    CompIndexNotFoundError,
)


@dataclass
class LoadCompIndexResult:
    success: bool
    alias: str = ""
    db_path: str = ""
    entities_loaded: int = 0
    relationships_loaded: int = 0
    entities_removed: int = 0       # replace 時に削除した旧エンティティ数
    skipped_edges: int = 0
    comp_metadata: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class LoadCompIndexUseCase:
    """Load (or reload) a comP index.db into the knowledge graph.

    mode="replace": 同じ alias の既存 comp エンティティを全削除してから投入（デフォルト）
    mode="merge":   既存をそのままに追加投入（同一IDは上書き）
    """

    def __init__(self, knowledge_graph: KnowledgeGraphRepository) -> None:
        self._graph = knowledge_graph
        self._reader = CompIndexReader()

    def execute(
        self, path: str | Path, mode: str = "replace"
    ) -> LoadCompIndexResult:
        if mode not in ("replace", "merge"):
            return LoadCompIndexResult(
                success=False, errors=[f"Invalid mode: {mode!r}"]
            )
        try:
            data = self._reader.read(path)
        except CompIndexNotFoundError as e:
            return LoadCompIndexResult(success=False, errors=[str(e)])
        except Exception as e:  # sqlite3.DatabaseError など
            return LoadCompIndexResult(
                success=False, errors=[f"Failed to read comP index: {e}"]
            )

        removed = 0
        if mode == "replace":
            prefix = f"comp:{data.alias}:"
            stale = [
                e.id for e in self._graph.entities.all()
                if e.id.value.startswith(prefix)
            ]
            for eid in stale:
                # 関連 relationship も削除（entity 削除だけでは graph に残る実装の場合に備える）
                for rel in list(self._graph.relationships.get_outgoing(eid)):
                    self._graph.relationships.delete(
                        rel.source_id, rel.target_id, rel.type
                    )
                for rel in list(self._graph.relationships.get_incoming(eid)):
                    self._graph.relationships.delete(
                        rel.source_id, rel.target_id, rel.type
                    )
                if self._graph.entities.delete(eid):
                    removed += 1

        for entity in data.entities:
            self._graph.entities.add(entity)
        for rel in data.relationships:
            self._graph.relationships.add(rel)

        return LoadCompIndexResult(
            success=True,
            alias=data.alias,
            db_path=data.db_path,
            entities_loaded=len(data.entities),
            relationships_loaded=len(data.relationships),
            entities_removed=removed,
            skipped_edges=data.skipped_edges,
            comp_metadata=data.metadata,
        )
```

**実装上の注意**:

- `relationships.delete()` のシグネチャは
  `packages/magatama-core/src/magatama_core/infrastructure/storage/in_memory_repository.py:103` を
  実装前に必ず確認し、引数の形（個別引数か Relationship オブジェクトか）を合わせること
- `usecases/__init__.py` に再エクスポートを追加すること

### Task 3: MCP ツールの追加（`protocol.py`）

**変更ファイル**: `packages/magatama-mcp/src/magatama_mcp/server/protocol.py`

`create_mcp_server()` 内、既存ツール群の末尾（`get_call_graph` の後）に 2 ツールを追加する。
ファイル先頭の import に `LoadCompIndexUseCase` を追加し、`knowledge_graph` 初期化付近で
use case を 1 つ生成して closure で共有する（既存ツールと同じパターン）。

```python
    # ===== External Index Tools (comP Bridge) =====

    load_comp_index_usecase = LoadCompIndexUseCase(knowledge_graph=knowledge_graph)

    @mcp.tool()
    def read_external_graph(path: str, mode: str = "replace") -> dict[str, Any]:
        """Load an external comP index (.comp/index.db) into YATA's knowledge graph.

        comP (https://github.com/tsucky230/comP) is a VSCode-based code indexer.
        This tool imports its SQLite index so that all YATA tools
        (search_entities, get_related_entities, analyze_impact, etc.)
        can answer questions about the indexed project without re-parsing.

        Args:
            path: Workspace root containing .comp/index.db, the .comp directory,
                  or a direct path to the .db file.
            mode: "replace" (default) removes previously loaded entities from the
                  same workspace before loading; "merge" adds on top.

        Returns:
            Load statistics: entities_loaded, relationships_loaded, alias, etc.
        """
        result = load_comp_index_usecase.execute(path, mode=mode)
        return {
            "success": result.success,
            "alias": result.alias,
            "db_path": result.db_path,
            "entities_loaded": result.entities_loaded,
            "relationships_loaded": result.relationships_loaded,
            "entities_removed": result.entities_removed,
            "skipped_edges": result.skipped_edges,
            "comp_metadata": result.comp_metadata,
            "errors": result.errors,
        }

    @mcp.tool()
    def get_external_graph_info(path: str) -> dict[str, Any]:
        """Inspect a comP index (.comp/index.db) without loading it.

        Returns file/node/edge counts and comP metadata. Use this to check
        whether an index exists and how fresh it is before calling
        read_external_graph.
        """
        from magatama_core.infrastructure.storage.comp_index_reader import (
            CompIndexNotFoundError,
            resolve_db_path,
        )
        import sqlite3
        import urllib.parse

        try:
            db_path = resolve_db_path(path)
        except CompIndexNotFoundError as e:
            return {"exists": False, "error": str(e)}
        uri = f"file:{urllib.parse.quote(db_path.as_posix())}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True)
            try:
                conn.execute("PRAGMA busy_timeout=5000")
                files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
                nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
                edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
                meta = dict(
                    conn.execute("SELECT key, value FROM metadata").fetchall()
                )
                last_indexed = conn.execute(
                    "SELECT MAX(last_indexed) FROM files"
                ).fetchone()[0]
            finally:
                conn.close()
        except sqlite3.Error as e:
            return {"exists": True, "db_path": str(db_path), "error": str(e)}
        return {
            "exists": True,
            "db_path": str(db_path),
            "files": files,
            "nodes": nodes,
            "edges": edges,
            "last_indexed": last_indexed,
            "metadata": meta,
        }
```

**ドキュメント上の表記**: ツール数が 34 → 36 になるため、README の「34 Tools」表記を更新する（Task 5）。

### Task 4（任意・推奨）: CLI コマンドの追加

**変更ファイル**: `packages/magatama-mcp/src/magatama_mcp/cli/main.py`

動作確認を CLI から行えるよう、`magatama comp-load <path>` コマンドを追加する。
ただし `cli/main.py` は `MagatamaMcpServer`（`mcp_server.py`）ベースなので、
`MagatamaMcpServer.__init__` にも `LoadCompIndexUseCase` を組み込み、
`_handle_read_external_graph` ハンドラー + `Tool` 定義を追加する
（`protocol.py` と同じマッピング・同じ戻り値構造にする）。

時間が無ければこのタスクは丸ごとスキップしてよい（MCP 経由の機能には影響しない）。

### Task 5: ドキュメント更新

1. `README.md` / `README.en.md`:
   - MCP Tools の表に `read_external_graph` / `get_external_graph_info` の行を追加
   - 「34 Tools」→「36 Tools」に更新（バッジ的記述・特徴セクション含め全箇所 grep すること）
   - 「comP 連携」セクションを新設し、本計画書 §1 の図と Claude Desktop からの利用手順を記載
2. `CHANGELOG.md`: `## [Unreleased]` セクションに追加機能を記載

---

## 5. テスト計画

### 5.1 テストフィクスチャ

**新規ファイル**: `packages/magatama-core/tests/infrastructure/test_comp_index_reader.py`

フィクスチャは実 DB ファイルを同梱せず、**テスト内で SQLite を生成**する:

```python
import sqlite3
from pathlib import Path

import pytest

SCHEMA = """
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,
    language TEXT NOT NULL,
    last_indexed INTEGER NOT NULL DEFAULT 0,
    char_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    line INTEGER NOT NULL,
    col INTEGER NOT NULL,
    scope TEXT,
    is_exported INTEGER DEFAULT 0,
    signature TEXT
);
CREATE TABLE edges (
    from_id INTEGER NOT NULL,
    to_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    PRIMARY KEY (from_id, to_id, kind)
);
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
"""


@pytest.fixture
def comp_db(tmp_path: Path) -> Path:
    """<tmp>/myproject/.comp/index.db を作成して workspace root を返す。"""
    workspace = tmp_path / "myproject"
    comp_dir = workspace / ".comp"
    comp_dir.mkdir(parents=True)
    db_path = comp_dir / "index.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT INTO files (id, path, hash, language) VALUES (?, ?, ?, ?)",
        [
            (1, "src/main.py", "abc123", "python"),
            (2, "src/util.py", "def456", "python"),
        ],
    )
    conn.executemany(
        "INSERT INTO nodes (id, file_id, name, kind, line, col, scope,"
        " is_exported, signature) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (1, 1, "main", "function", 10, 0, None, 1, "def main() -> None"),
            (2, 2, "Helper", "class", 5, 0, None, 1, None),
            (3, 2, "run", "method", 8, 4, "Helper", 0, "def run(self)"),
            (4, 2, "MAGIC", "constant", 1, 0, None, 1, None),
        ],
    )
    conn.executemany(
        "INSERT INTO edges (from_id, to_id, kind) VALUES (?, ?, ?)",
        [
            (1, 3, "function_call"),
            (1, 2, "type_reference"),
            (999, 1, "function_call"),  # 孤立エッジ（スキップされるべき）
        ],
    )
    conn.execute(
        "INSERT INTO metadata (key, value) VALUES ('version', '2')"
    )
    conn.commit()
    conn.close()
    return workspace
```

### 5.2 テストケース一覧

**`test_comp_index_reader.py`（CompIndexReader 単体）**:

| # | テスト | 期待値 |
|---|---|---|
| 1 | `resolve_db_path(workspace)` | `.comp/index.db` を解決 |
| 2 | `resolve_db_path(workspace / ".comp")` | 同上 |
| 3 | `resolve_db_path(db ファイル直指定)` | そのまま返す |
| 4 | `resolve_db_path(存在しないパス)` | `CompIndexNotFoundError` |
| 5 | `read()` のエンティティ数 | 6（files 2 + nodes 4） |
| 6 | kind マッピング | `function`→FUNCTION, `class`→CLASS, `method`→METHOD, `constant`→VARIABLE |
| 7 | 未知 kind（例: `"weird"` を追加投入） | VARIABLE にフォールバック、例外なし |
| 8 | Entity ID 形式 | `comp:myproject:n1`, `comp:myproject:f1` |
| 9 | location | node1 → `file="src/main.py", line=10, column=0` |
| 10 | `line=0` の行を投入 | `line=1` にクランプされ例外なし |
| 11 | is_exported | node1 → scope `"public"`、node3 → `"private"` |
| 12 | edges マッピング | `function_call`→CALLS, `type_reference`→REFERENCES |
| 13 | 未知 edge kind | DEPENDS_ON にフォールバック |
| 14 | 孤立エッジ（from_id=999） | スキップされ `skipped_edges == 1` |
| 15 | ファイル包含 | `f2` →CONTAINS→ `n2`, `n3`, `n4` が存在 |
| 16 | 親スコープ包含 | `n2`(Helper) →CONTAINS→ `n3`(run) が存在（origin=comp-scope） |
| 17 | metadata | `{"version": "2"}` を含む |
| 18 | 読み取り専用性 | `read()` 実行後に DB の hash 値等が不変／コネクションが close 済み |

**新規ファイル**: `packages/magatama-core/tests/application/test_comp_usecase.py`（UseCase）:

| # | テスト | 期待値 |
|---|---|---|
| 1 | `execute(workspace)` 成功 | `success=True`, `entities_loaded=6` |
| 2 | グラフへの反映 | `knowledge_graph.entities.count() == 6` |
| 3 | 2回連続 `execute`（replace） | エンティティ数が 6 のまま（重複しない）、`entities_removed == 6` |
| 4 | `mode="merge"` | 同一 ID 上書きでエンティティ数が増えない（実装依存：上書き仕様を確認して書く） |
| 5 | 存在しないパス | `success=False`, `errors` 非空、例外を投げない |
| 6 | 壊れた DB（テキストファイルを .db として置く） | `success=False`, `errors` 非空 |
| 7 | `mode="invalid"` | `success=False` |
| 8 | ロード後 `get_neighbors` | `Helper` の EntityId から `run` が辿れる |

**変更ファイル**: `packages/magatama-mcp/tests/test_protocol.py`（MCPツール）:

- 既存テストのパターンを踏襲し、`read_external_graph` / `get_external_graph_info` が
  ツール一覧に登録されていること、フィクスチャ DB に対して正しい統計を返すことを検証
- ツール総数をアサートしているテストがあれば 34 → 36 に更新する（実装前に
  `grep -rn "34" packages/magatama-mcp/tests/` で確認すること）

### 5.3 実行コマンド

```bash
cd e:/dev/YATA
uv sync --all-packages
uv run pytest packages/magatama-core/tests/infrastructure/test_comp_index_reader.py -v
uv run pytest packages/magatama-core/tests/application/test_comp_usecase.py -v
uv run pytest packages/magatama-mcp/tests/test_protocol.py -v
uv run pytest          # 最後に全テスト（既存リグレッション確認）
```

---

## 6. 動作確認（E2E・手動）

1. comP でインデックス済みのワークスペースを用意する（例: `e:/dev/comP` 自体に
   `.comp/index.db` があればそれを使う。なければ VSCode で comP を起動して任意の
   プロジェクトをインデックスする）
2. YATA MCP サーバーを起動: `uv run magatama serve`
3. Claude Desktop / Claude Code に YATA を MCP 登録し、以下を実行:
   - `get_external_graph_info(path="<ワークスペース>")` → counts が返る
   - `read_external_graph(path="<ワークスペース>")` → `success: true`
   - `search_entities(query="<既知の関数名>")` → comP 由来エンティティがヒットする
   - `get_related_entities(entity_id="comp:<alias>:n<id>")` → 呼び出し関係が辿れる
4. **並行アクセス確認**: VSCode で comP デーモンが起動（書き込み中）の状態で
   `read_external_graph` を実行してもエラーにならないこと

---

## 7. リスクと対策

| リスク | 対策 |
|---|---|
| comP デーモン書き込み中のロック競合 | 読み取り専用接続 + `busy_timeout=5000`（comP 側も WAL + 同値を設定済み）。`immutable=1` は**使わない**（WAL ファイルの変更を見落とすため） |
| comP スキーマの将来変更 | `metadata.version` を読んで結果に含める。カラム不足は `sqlite3.OperationalError` を捕捉し `errors` で返す（クラッシュさせない） |
| node/edge kind の追加 | 未知値はフォールバック（VARIABLE / DEPENDS_ON）で受理 |
| 巨大インデックス（数十万 nodes） | v1 では全件ロードを許容。`read_external_graph` の戻り値に件数を含め、利用者が判断できるようにする。ページング・遅延ロードは将来拡張（§8） |
| ID 衝突 | `comp:{alias}:` プレフィックスで YATA 既存の `ent_xxx` と分離。alias で複数ワークスペースも分離 |
| Windows パス（スペース・日本語） | SQLite URI は `as_posix()` + `urllib.parse.quote` でエンコード。テストの tmp_path で自動的にある程度カバーされる |
| インデックスの鮮度（stale read） | v1 はツール呼び出しごとに明示リロード（`read_external_graph` 再実行）。`get_external_graph_info` の `last_indexed` で鮮度確認可能 |

---

## 8. 将来拡張（このブランチではやらない）

- **自動リロード**: `files.last_indexed` の MAX を記憶し、各ツール呼び出し時に変化していたら自動再ロード
- **comP セッションメモリ連携**: `.comp/session-memory.json` の読み取りツール
- **逆方向ブリッジ**: YATA の 47 フレームワーク知識グラフを comP の MCP に提供
- **comP HTTP/IPC 直結**: デーモンの圧縮コンテキスト生成（`get_context` 相当）を YATA 経由で呼ぶ
- **SQLite 遅延ロード**: 全件メモリ展開せず、クエリごとに index.db へ直接 SQL を発行するリポジトリ実装

---

## 9. 作業手順とコミット粒度

ブランチ `ftr/comp-bridge` 上で以下の順に実装し、各ステップでテストを通してからコミットする:

1. `feat(core): add CompIndexReader for comP index.db` — Task 1 + テスト（§5.2 reader分）
2. `feat(core): add LoadCompIndexUseCase` — Task 2 + テスト（§5.2 usecase分）
3. `feat(mcp): add read_external_graph / get_external_graph_info tools` — Task 3 + テスト
4. `feat(cli): add comp-load command`（Task 4 を実施する場合のみ）
5. `docs: add comP bridge documentation` — Task 5

## 10. 完了条件（Definition of Done）

- [ ] §5.2 の全テストケースが実装され、`uv run pytest` が全件パスする（既存テスト含む）
- [ ] `read_external_graph` / `get_external_graph_info` が `magatama serve` のツール一覧に出る
- [ ] §6 の手動 E2E 手順 1〜4 が成功する
- [ ] README（日英）・CHANGELOG が更新されている
- [ ] 新規コードに型ヒントと docstring がある（既存コードのスタイルに合わせる）
