from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from phytoatlas_api.graph_store import SQLiteGraphStore


class SQLiteGraphStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "graph.sqlite"
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            """
            CREATE TABLE nodes (
                node_id TEXT PRIMARY KEY,
                object_type TEXT NOT NULL,
                label TEXT,
                species_id TEXT,
                source_file TEXT,
                properties_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE edges (
                edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                predicate TEXT NOT NULL,
                target TEXT NOT NULL,
                species_id TEXT,
                source_dataset TEXT,
                evidence TEXT,
                properties_json TEXT NOT NULL
            )
            """
        )
        nodes = [
            ("gene:arabidopsis_thaliana:Atha01G0000010.v1.36", "Gene", "Atha01G0000010", "arabidopsis_thaliana"),
            ("species:arabidopsis_thaliana", "Species", "Arabidopsis thaliana", "arabidopsis_thaliana"),
            (
                "GeneLocation:gene:atha:Atha01G0000010.v1.36",
                "GeneLocation",
                "Chr1:3631-5899",
                "arabidopsis_thaliana",
            ),
        ]
        for node_id, object_type, label, species_id in nodes:
            connection.execute(
                """
                INSERT INTO nodes
                (node_id, object_type, label, species_id, source_file, properties_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    node_id,
                    object_type,
                    label,
                    species_id,
                    "/DATA/data2/legacy/processed/test.jsonl",
                    json.dumps({"object_id": node_id, "name": label}),
                ),
            )
        connection.execute(
            """
            INSERT INTO edges
            (source, predicate, target, species_id, source_dataset, evidence, properties_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
                "belongs_to_species",
                "species:arabidopsis_thaliana",
                "arabidopsis_thaliana",
                "dataset:test",
                "test",
                json.dumps({"source": "gene:arabidopsis_thaliana:Atha01G0000010.v1.36"}),
            ),
        )
        connection.commit()
        connection.close()
        self.store = SQLiteGraphStore(self.db_path)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def insert_edge(self, predicate: str, target: str) -> None:
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            """
            INSERT INTO edges
            (source, predicate, target, species_id, source_dataset, evidence, properties_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
                predicate,
                target,
                "arabidopsis_thaliana",
                "dataset:test",
                "test",
                "{}",
            ),
        )
        connection.commit()
        connection.close()

    def test_get_node(self) -> None:
        node = self.store.get_node("gene:arabidopsis_thaliana:Atha01G0000010.v1.36")
        self.assertIsNotNone(node)
        self.assertEqual(node["object_type"], "Gene")
        self.assertEqual(node["source_file"], "test.jsonl")

    def test_search_nodes(self) -> None:
        nodes = self.store.search_nodes("Atha01G0000010", object_type="Gene")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["label"], "Atha01G0000010")

    def test_search_nodes_resolves_full_gene_id_with_species_scope(self) -> None:
        nodes = self.store.search_nodes(
            "Atha01G0000010.v1.36",
            object_type="Gene",
            species_id="arabidopsis_thaliana",
        )
        self.assertEqual(len(nodes), 1)
        self.assertEqual(
            nodes[0]["node_id"],
            "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
        )

    def test_get_neighbors(self) -> None:
        result = self.store.get_neighbors(
            "gene:arabidopsis_thaliana:Atha01G0000010.v1.36"
        )
        self.assertEqual(result["node"]["object_type"], "Gene")
        self.assertEqual(result["edges"][0]["predicate"], "belongs_to_species")
        self.assertEqual(result["nodes"][0]["object_type"], "Species")

    def test_get_neighbors_reports_complete_counts_after_exclusion(self) -> None:
        self.insert_edge("has_sequence", "GeneLocation:gene:atha:Atha01G0000010.v1.36")
        self.insert_edge("has_sequence", "species:arabidopsis_thaliana")
        self.insert_edge("has_structure", "GeneLocation:gene:atha:Atha01G0000010.v1.36")

        result = self.store.get_neighbors(
            "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
            exclude_predicates=("has_sequence", "has_sequence"),
            limit=10,
        )

        self.assertEqual(result["total_edges"], 4)
        self.assertEqual(result["matched_edges"], 2)
        self.assertEqual(
            result["predicate_counts"],
            {"belongs_to_species": 1, "has_sequence": 2, "has_structure": 1},
        )
        self.assertFalse(result["truncated"])
        self.assertEqual(
            [edge["predicate"] for edge in result["edges"]],
            ["belongs_to_species", "has_structure"],
        )

    def test_get_neighbors_reports_filtered_truncation(self) -> None:
        self.insert_edge("has_sequence", "GeneLocation:gene:atha:Atha01G0000010.v1.36")
        self.insert_edge("has_sequence", "species:arabidopsis_thaliana")

        result = self.store.get_neighbors(
            "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
            predicate="has_sequence",
            limit=1,
        )

        self.assertEqual(result["total_edges"], 3)
        self.assertEqual(result["matched_edges"], 2)
        self.assertEqual(result["predicate_counts"]["has_sequence"], 2)
        self.assertEqual(len(result["edges"]), 1)
        self.assertTrue(result["truncated"])

    def test_filtered_neighbors_stay_within_directional_scan_budget(self) -> None:
        connection = sqlite3.connect(self.db_path)
        connection.execute("CREATE INDEX idx_edges_source ON edges(source)")
        connection.execute("CREATE INDEX idx_edges_target ON edges(target)")
        connection.execute("CREATE INDEX idx_edges_predicate ON edges(predicate)")
        connection.executemany(
            """
            INSERT INTO edges
            (source, predicate, target, species_id, source_dataset, evidence, properties_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    f"gene:unrelated:{index}",
                    "has_sequence",
                    f"seq:unrelated:{index}",
                    "arabidopsis_thaliana",
                    "dataset:test",
                    "test",
                    "{}",
                )
                for index in range(10_000)
            ),
        )
        connection.execute(
            """
            INSERT INTO edges
            (source, predicate, target, species_id, source_dataset, evidence, properties_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
                "has_sequence",
                "GeneLocation:gene:atha:Atha01G0000010.v1.36",
                "arabidopsis_thaliana",
                "dataset:test",
                "test",
                "{}",
            ),
        )
        connection.commit()
        connection.close()

        class BudgetStore(SQLiteGraphStore):
            def connect(inner_self) -> sqlite3.Connection:
                limited = super().connect()
                callbacks = 0

                def progress() -> int:
                    nonlocal callbacks
                    callbacks += 1
                    return int(callbacks > 300)

                limited.set_progress_handler(progress, 100)
                return limited

        result = BudgetStore(self.db_path).get_neighbors(
            "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
            predicate="has_sequence",
            limit=10,
        )
        self.assertEqual(result["matched_edges"], 1)
        self.assertEqual(len(result["edges"]), 1)

    def test_get_neighbors_orders_edges_deterministically(self) -> None:
        connection = sqlite3.connect(self.db_path)
        for predicate, target in (
            ("z_predicate", "species:arabidopsis_thaliana"),
            ("a_predicate", "GeneLocation:gene:atha:Atha01G0000010.v1.36"),
        ):
            connection.execute(
                """
                INSERT INTO edges
                (source, predicate, target, species_id, source_dataset, evidence, properties_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
                    predicate,
                    target,
                    "arabidopsis_thaliana",
                    "dataset:test",
                    "test",
                    "{}",
                ),
            )
        connection.commit()
        connection.close()
        result = self.store.get_neighbors(
            "gene:arabidopsis_thaliana:Atha01G0000010.v1.36"
        )
        self.assertEqual(
            result["edges"],
            sorted(
                result["edges"],
                key=lambda edge: (edge["predicate"], edge["source"], edge["target"]),
            ),
        )

    def test_get_gene_wiki_record_returns_all_edges(self) -> None:
        connection = sqlite3.connect(self.db_path)
        for index in range(205):
            connection.execute(
                """
                INSERT INTO edges
                (source, predicate, target, species_id, source_dataset, evidence, properties_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
                    "has_sequence",
                    f"sequence:{index:03d}",
                    "arabidopsis_thaliana",
                    "dataset:test",
                    "test",
                    "{}",
                ),
            )
        connection.commit()
        connection.close()
        result = self.store.get_gene_wiki_record(
            "gene:arabidopsis_thaliana:Atha01G0000010.v1.36"
        )
        self.assertEqual(len(result["edges"]), 206)
        self.assertEqual(
            result["edges"],
            sorted(
                result["edges"],
                key=lambda edge: (edge["predicate"], edge["source"], edge["target"]),
            ),
        )

    def test_list_species_genes(self) -> None:
        result = self.store.list_species_genes("arabidopsis_thaliana")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["genes"][0]["object_type"], "Gene")


if __name__ == "__main__":
    unittest.main()
