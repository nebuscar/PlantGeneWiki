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

        normalized_species_id = (
            species_id[len("species:") :]
            if species_id and species_id.startswith("species:")
            else species_id
        )
        has_scope = bool(object_type or species_id)
        rank_node_id = query
        if object_type == "Gene" and normalized_species_id:
            rank_node_id = f"gene:{normalized_species_id}:{query}"
            clauses = ["(node_id = ? OR label = ? OR node_id LIKE ? OR label LIKE ?)"]
            params: list[Any] = [
                rank_node_id,
                query,
                f"{rank_node_id}%",
                f"{query}%",
            ]
        elif has_scope:
            clauses = ["(node_id = ? OR label = ? OR node_id LIKE ? OR label LIKE ?)"]
            params = [query, query, f"{query}%", f"{query}%"]
        else:
            # Global fuzzy/label search is intentionally avoided here: the full graph
            # has more than 100M nodes. Broad semantic/fuzzy search should use a
            # dedicated search index instead of scanning the graph table.
            clauses = ["(node_id = ? OR node_id LIKE ?)"]
            params = [query, f"{query}%"]
        if object_type:
            clauses.append("object_type = ?")
            params.append(object_type)
        if normalized_species_id:
            clauses.append("species_id = ?")
            params.append(normalized_species_id)
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
        params_with_rank = params[:-1] + [rank_node_id, query, params[-1]]
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
        exclude_predicates: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        node = self.get_node(node_id)
        empty = {
            "node": node,
            "edges": [],
            "nodes": [],
            "total_edges": 0,
            "matched_edges": 0,
            "predicate_counts": {},
            "truncated": False,
        }
        if node is None:
            return empty

        limit = max(1, min(limit, 500))
        if direction == "out":
            direction_clause = "source = ?"
            direction_params: list[Any] = [node_id]
        elif direction == "in":
            direction_clause = "target = ?"
            direction_params = [node_id]
        else:
            direction_clause = "(source = ? OR target = ?)"
            direction_params = [node_id, node_id]

        clauses = [direction_clause]
        params = list(direction_params)
        if predicate:
            clauses.append("predicate = ?")
            params.append(predicate)
        for excluded in sorted({item for item in exclude_predicates if item}):
            clauses.append("predicate != ?")
            params.append(excluded)

        with self.connect() as connection:
            predicate_counts = {
                row["predicate"]: row["count"]
                for row in connection.execute(
                    f"""
                    SELECT predicate, COUNT(*) AS count
                    FROM edges
                    WHERE {direction_clause}
                    GROUP BY predicate
                    ORDER BY predicate
                    """,
                    direction_params,
                )
            }
            matched_edges = connection.execute(
                f"SELECT COUNT(*) FROM edges WHERE {' AND '.join(clauses)}",
                params,
            ).fetchone()[0]
            edge_rows = connection.execute(
                f"""
                SELECT source, predicate, target, species_id, source_dataset, evidence, properties_json
                FROM edges
                WHERE {' AND '.join(clauses)}
                ORDER BY predicate, source, target, edge_id
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
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

        return {
            "node": node,
            "edges": edges,
            "nodes": related_nodes,
            "total_edges": sum(predicate_counts.values()),
            "matched_edges": matched_edges,
            "predicate_counts": predicate_counts,
            "truncated": len(edges) < matched_edges,
        }

    def get_gene_wiki_record(self, node_id: str) -> dict[str, Any]:
        node = self.get_node(node_id)
        if node is None or node["object_type"] != "Gene":
            return {"node": None, "edges": [], "nodes": []}

        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT source, predicate, target, species_id, source_dataset, evidence, properties_json
                FROM edges
                WHERE source = ? OR target = ?
                ORDER BY predicate, source, target, edge_id
                """,
                (node_id, node_id),
            ).fetchall()
            edges = [self._edge_from_row(row) for row in rows]
            related_ids = sorted(
                {
                    value
                    for edge in edges
                    for value in (edge["source"], edge["target"])
                    if value != node_id
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
            "source_file": (
                Path(row["source_file"]).name if row["source_file"] else None
            ),
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
