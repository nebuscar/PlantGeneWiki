########## 0. imports ##########
import json
import unittest
from collections import Counter
from pathlib import Path


########## 1. params ##########
REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "config" / "quality" / "arabidopsis_golden_genes.json"


########## 2. tests ##########
class GoldenGeneManifestTest(unittest.TestCase):
    def test_manifest_has_balanced_unique_gene_contracts(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        genes = manifest["genes"]
        self.assertEqual(len(genes), 20)
        self.assertEqual(Counter(item["group"] for item in genes), {
            "engineering_boundary": 10,
            "biological_representative": 10,
        })
        self.assertEqual(len({item["object_id"] for item in genes}), 20)
        self.assertEqual(len(manifest["required_sections"]), 9)
        self.assertEqual(manifest["allowed_unavailable_sections"], ["homology", "publications"])

    def test_manifest_has_measured_cds_feature_minima(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        for gene in manifest["genes"]:
            value = gene["expected"]["minimum_cds_features"]
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 0)
        target = next(gene for gene in manifest["genes"] if gene["public_id"] == "Atha01G0038670.v1.36")
        self.assertEqual(target["expected"]["minimum_cds_features"], 381)


if __name__ == "__main__":
    unittest.main()
