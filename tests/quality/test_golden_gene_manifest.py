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


if __name__ == "__main__":
    unittest.main()
