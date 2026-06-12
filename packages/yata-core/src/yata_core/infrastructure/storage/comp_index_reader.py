"""comP index.db reader.

Reads a comP (https://github.com/tsucky230/comP) SQLite index in read-only
mode and converts it into YATA domain entities/relationships.
"""

from __future__ import annotations

import sqlite3
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

from yata_core.domain.entities.base import Entity, EntityType
from yata_core.domain.entities.relationships import Relationship, RelationshipType
from yata_core.domain.value_objects.ids import EntityId
from yata_core.domain.value_objects.location import Location

# §3.1 EntityType mapping
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

# §3.2 RelationshipType mapping
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
        # Read-only URI connection. WAL mode allows concurrent reads while comP daemon writes.
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

        # metadata (defensive: table may not exist in older comP versions)
        try:
            for row in conn.execute("SELECT key, value FROM metadata"):
                data.metadata[row["key"]] = row["value"]
        except sqlite3.OperationalError:
            pass

        # files -> MODULE entities; build O(1) lookup dict at the same time
        file_entity_ids: dict[int, EntityId] = {}
        file_paths: dict[int, str] = {}
        for row in conn.execute(
            "SELECT id, path, language FROM files ORDER BY id"
        ):
            fid = int(row["id"])
            eid = EntityId(value=f"comp:{alias}:f{fid}")
            file_entity_ids[fid] = eid
            file_paths[fid] = row["path"]
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
        # For parent-scope resolution: (file_id, name) -> [node_id, ...]
        nodes_by_file_and_name: dict[tuple[int, str], list[int]] = {}
        # node_id -> (file_id, scope_name)
        node_scopes: dict[int, tuple[int, str]] = {}

        for row in conn.execute(
            "SELECT id, file_id, name, kind, line, col, scope,"
            " is_exported, signature FROM nodes ORDER BY id"
        ):
            nid = int(row["id"])
            fid = int(row["file_id"])
            file_path = file_paths.get(fid, "<unknown>")
            eid = EntityId(value=f"comp:{alias}:n{nid}")
            node_entity_ids[nid] = eid
            data.entities.append(
                Entity(
                    id=eid,
                    name=row["name"],
                    type=_KIND_TO_ENTITY_TYPE.get(
                        row["kind"], _DEFAULT_ENTITY_TYPE
                    ),
                    location=Location(
                        file=file_path,
                        line=max(int(row["line"]), 1),
                        column=max(int(row["col"]), 0),
                    ),
                    docstring=row["signature"],
                    scope="public" if row["is_exported"] else "private",
                )
            )
            data.nodes_count += 1

            key = (fid, row["name"])
            nodes_by_file_and_name.setdefault(key, []).append(nid)
            if row["scope"]:
                node_scopes[nid] = (fid, row["scope"])

            # file CONTAINS node
            file_eid = file_entity_ids.get(fid)
            if file_eid is not None:
                data.relationships.append(
                    Relationship(
                        source_id=file_eid,
                        target_id=eid,
                        type=RelationshipType.CONTAINS,
                        metadata={"origin": "comp"},
                    )
                )

        # parent-scope CONTAINS (only when unambiguously resolved within same file)
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
            src = node_entity_ids.get(int(row["from_id"]))
            dst = node_entity_ids.get(int(row["to_id"]))
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
