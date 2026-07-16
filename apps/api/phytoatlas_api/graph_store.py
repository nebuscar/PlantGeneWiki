"""SQLite-backed graph query store for PhytoAtlas."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Literal


DEFAULT_GRAPH_DB = Path(
    "/DATA/data2/phytoatlas/graph/pgcp_v1/phytoatlas_pgcp_v1.sqlite"
)
DEFAULT_GRAPH_SUMMARY = Path("/DATA/data2/phytoatlas/graph/pgcp_v1/graph_summary.json")


class GraphStoreError(RuntimeError):
    """Raised when the graph store cannot satisfy a query."""


class SQLiteGraphStore:
    """Small read-only query layer over the PhytoAtlas graph SQLite index."""

    def __init__(self, database_path: str | Path = DEFAULT_GRAPH_DB) -> None:
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        if not self.database_path.exists():
            raise GraphStoreError(f"Graph database does not exist: {self.database_path}")
        connection = sqlite3.connect(f"file:{self.database_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def get_summary(self, summary_path: str | Path = DEFAULT_GRAPH_SUMMARY) -> dict[str, Any]:
        path = Path(summary_path)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))

        with self.connect() as connection:
            node_count = connection.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edge_count = connection.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            node_types = {
                row["object_type"]: row["count"]
                for row in connection.execute(
                    "SELECT object_type, COUNT(*) AS count FROM nodes GROUP BY object_type"
                )
            }
            edge_predicates = {
                row["predicate"]: row["count"]
                for row in connection.execute(
                    "SELECT predicate, COUNT(*) AS count FROM edges GROUP BY predicate"
                )
            }
        return {
            "database": str(self.database_path),
            "node_count": node_count,
            "edge_count": edge_count,
            "node_types": node_types,
            "edge_predicates": edge_predicates,
        }

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT node_id, object_type, label, species_id, source_file, properties_json
                FROM nodes
                WHERE node_id = ?
                """,
                (node_id,),
            ).fetchone()
        return self._node_from_row(row) if row else None

    def search_nodes(
        self,
        query: str,
        *,
        limit: int = 20,
        object_type: str | None = None,
        species_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        has_scope = bool(object_type or species_id)
        if has_scope:
            clauses = ["(node_id = ? OR label = ? OR node_id LIKE ? OR label LIKE ?)"]
            params: list[Any] = [query, query, f"{query}%", f"{query}%"]
        else:
            # Global fuzzy/label search is intentionally avoided here: the full graph
            # has more than 100M nodes. Broad semantic/fuzzy search should use a
            # dedicated search index instead of scanning the graph table.
            clauses = ["(node_id = ? OR node_id LIKE ?)"]
            params = [query, f"{query}%"]
        if object_type:
            clauses.append("object_type = ?")
            params.append(object_type)
        if species_id:
            clauses.append("species_id = ?")
            params.append(species_id)
        params.append(max(1, min(limit, 100)))

        sql = f"""
            SELECT node_id, object_type, label, species_id, source_file, properties_json
            FROM nodes
            WHERE {' AND '.join(clauses)}
            ORDER BY
                CASE WHEN node_id = ? THEN 0 WHEN label = ? THEN 1 ELSE 2 END,
                object_type,
                node_id
            LIMIT ?
        """
        params_with_rank = params[:-1] + [query, query, params[-1]]
        with self.connect() as connection:
            rows = connection.execute(sql, params_with_rank).fetchall()
        return [self._node_from_row(row) for row in rows]

    def get_neighbors(
        self,
        node_id: str,
        *,
        direction: Literal["in", "out", "both"] = "both",
        limit: int = 50,
        predicate: str | None = None,
    ) -> dict[str, Any]:
        node = self.get_node(node_id)
        if node is None:
            return {"node": None, "edges": [], "nodes": []}

        limit = max(1, min(limit, 500))
        clauses: list[str] = []
        params: list[Any] = []

        if direction == "out":
            clauses.append("source = ?")
            params.append(node_id)
        elif direction == "in":
            clauses.append("target = ?")
            params.append(node_id)
        else:
            clauses.append("(source = ? OR target = ?)")
            params.extend([node_id, node_id])

        if predicate:
            clauses.append("predicate = ?")
            params.append(predicate)
        params.append(limit)

        edge_sql = f"""
            SELECT source, predicate, target, species_id, source_dataset, evidence, properties_json
            FROM edges
            WHERE {' AND '.join(clauses)}
            LIMIT ?
        """
        with self.connect() as connection:
            edge_rows = connection.execute(edge_sql, params).fetchall()
            edges = [self._edge_from_row(row) for row in edge_rows]
            related_ids = sorted(
                {
                    item
                    for edge in edges
                    for item in (edge["source"], edge["target"])
                    if item != node_id
                }
            )
            related_nodes = self._get_nodes_by_ids(connection, related_ids)

        return {"node": node, "edges": edges, "nodes": related_nodes}

    def list_species_genes(
        self,
        species_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        normalized_species_id = (
            species_id[len("species:") :] if species_id.startswith("species:") else species_id
        )

        with self.connect() as connection:
            total = connection.execute(
                """
                SELECT COUNT(*)
                FROM nodes
                WHERE object_type = 'Gene' AND species_id = ?
                """,
                (normalized_species_id,),
            ).fetchone()[0]
            rows = connection.execute(
                """
                SELECT node_id, object_type, label, species_id, source_file, properties_json
                FROM nodes
                WHERE object_type = 'Gene' AND species_id = ?
                ORDER BY node_id
                LIMIT ? OFFSET ?
                """,
                (normalized_species_id, limit, offset),
            ).fetchall()
        return {
            "species_id": normalized_species_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "genes": [self._node_from_row(row) for row in rows],
        }

    def _get_nodes_by_ids(
        self, connection: sqlite3.Connection, node_ids: list[str]
    ) -> list[dict[str, Any]]:
        if not node_ids:
            return []
        placeholders = ",".join("?" for _ in node_ids)
        rows = connection.execute(
            f"""
            SELECT node_id, object_type, label, species_id, source_file, properties_json
            FROM nodes
            WHERE node_id IN ({placeholders})
            """,
            node_ids,
        ).fetchall()
        return [self._node_from_row(row) for row in rows]

    @staticmethod
    def _node_from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "node_id": row["node_id"],
            "object_type": row["object_type"],
            "label": row["label"],
            "species_id": row["species_id"],
            "source_file": row["source_file"],
            "properties": json.loads(row["properties_json"]),
        }

    @staticmethod
    def _edge_from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "source": row["source"],
            "predicate": row["predicate"],
            "target": row["target"],
            "species_id": row["species_id"],
            "source_dataset": row["source_dataset"],
            "evidence": row["evidence"],
            "properties": json.loads(row["properties_json"]),
        }
