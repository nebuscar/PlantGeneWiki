import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "build"))

from build_web_data import build  # noqa: E402


class BuildWebDataTests(unittest.TestCase):
    def test_builds_api_shaped_static_outputs(self):
        input_dir = PROJECT_ROOT / "examples" / "knowledge_objects"
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "api"
            counts = build(input_dir, output_dir)

            self.assertEqual(counts["species"], 1)
            self.assertEqual(counts["genes"], 1)
            self.assertEqual(counts["datasets"], 1)
            self.assertEqual(counts["relations"], 2)
            self.assertEqual(counts["evidence_claims"], 1)

            gene = json.loads((output_dir / "genes" / "Atha01G0000010.v1.36.json").read_text(encoding="utf-8"))
            self.assertEqual(gene["object_type"], "Gene")
            self.assertEqual(gene["species"], "arabidopsis_thaliana")

            search_index = json.loads((output_dir / "search" / "index.json").read_text(encoding="utf-8"))
            self.assertTrue(any(item["href"] == "/genes/Atha01G0000010.v1.36" for item in search_index))

            dataset = json.loads((output_dir / "datasets" / "pgcp_atha_gene_json_202606.json").read_text(encoding="utf-8"))
            self.assertEqual(dataset["location"], {"type": "internal", "label": "internal_raw_storage"})
            self.assertNotIn("/home/", json.dumps(dataset))

            graph_edges = json.loads((output_dir / "graph" / "edges.json").read_text(encoding="utf-8"))
            self.assertEqual({edge["predicate"] for edge in graph_edges}, {"has_gene", "provided_by_dataset"})


if __name__ == "__main__":
    unittest.main()
