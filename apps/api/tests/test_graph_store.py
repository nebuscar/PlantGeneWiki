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
            ("gene:atha:Atha01G0000010.v1.36", "Gene", "Atha01G0000010.v1.36", "arabidopsis_thaliana"),
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
                    "test.jsonl",
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
                "gene:atha:Atha01G0000010.v1.36",
                "belongs_to_species",
                "species:arabidopsis_thaliana",
                "arabidopsis_thaliana",
                "dataset:test",
                "test",
                json.dumps({"source": "gene:atha:Atha01G0000010.v1.36"}),
            ),
        )
        connection.commit()
        connection.close()
        self.store = SQLiteGraphStore(self.db_path)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_get_node(self) -> None:
        node = self.store.get_node("gene:atha:Atha01G0000010.v1.36")
        self.assertIsNotNone(node)
        self.assertEqual(node["object_type"], "Gene")

    def test_search_nodes(self) -> None:
        nodes = self.store.search_nodes("Atha01G0000010", object_type="Gene")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["label"], "Atha01G0000010.v1.36")

    def test_get_neighbors(self) -> None:
        result = self.store.get_neighbors("gene:atha:Atha01G0000010.v1.36")
        self.assertEqual(result["node"]["object_type"], "Gene")
        self.assertEqual(result["edges"][0]["predicate"], "belongs_to_species")
        self.assertEqual(result["nodes"][0]["object_type"], "Species")

    def test_list_species_genes(self) -> None:
        result = self.store.list_species_genes("arabidopsis_thaliana")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["genes"][0]["object_type"], "Gene")


if __name__ == "__main__":
    unittest.main()

