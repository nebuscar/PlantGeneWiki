########## 0. imports ##########
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from phytoatlas_api.main import app, gene_wiki, graph_neighbors, health

########## 1. tests ##########
class ApiIdentityTest(unittest.TestCase):
    def test_api_uses_phytoatlas_identity(self):
        self.assertEqual(app.title, "PhytoAtlas API")
        self.assertEqual(health(), {"status": "ok"})

class GeneWikiApiTest(unittest.TestCase):
    @patch("phytoatlas_api.main.get_graph_store")
    def test_gene_wiki_returns_complete_record(self, get_store):
        expected = {"node": {"node_id": "gene:test"}, "edges": [], "nodes": []}
        get_store.return_value.get_gene_wiki_record.return_value = expected
        self.assertEqual(gene_wiki("gene:test"), expected)

    @patch("phytoatlas_api.main.get_graph_store")
    def test_gene_wiki_raises_not_found_for_missing_gene(self, get_store):
        get_store.return_value.get_gene_wiki_record.return_value = {
            "node": None,
            "edges": [],
            "nodes": [],
        }
        with self.assertRaises(HTTPException) as context:
            gene_wiki("gene:missing")
        self.assertEqual(context.exception.status_code, 404)

class GraphNeighborApiTest(unittest.TestCase):
    @patch("phytoatlas_api.main.get_graph_store")
    def test_graph_neighbors_forwards_repeated_exclusions(self, get_store):
        expected = {
            "node": {"node_id": "gene:test"},
            "edges": [],
            "nodes": [],
            "total_edges": 54,
            "matched_edges": 0,
            "predicate_counts": {"has_sequence": 54},
            "truncated": False,
        }
        get_store.return_value.get_neighbors.return_value = expected

        result = graph_neighbors(
            "gene:test",
            direction="both",
            predicate=None,
            exclude_predicate=["has_sequence", "has_sequence"],
            limit=100,
        )

        self.assertEqual(result, expected)
        get_store.return_value.get_neighbors.assert_called_once_with(
            "gene:test",
            direction="both",
            predicate=None,
            exclude_predicates=("has_sequence", "has_sequence"),
            limit=100,
        )

if __name__ == "__main__":
    unittest.main()
