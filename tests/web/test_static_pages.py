import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StaticWebPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["python3", "scripts/build/build_web_data.py"], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True)
        subprocess.run(["npm", "run", "build"], cwd=PROJECT_ROOT / "apps" / "web", check=True, capture_output=True, text=True)

    def test_gene_page_links_to_dataset_and_sequence_record(self):
        html = (PROJECT_ROOT / "apps" / "web" / "dist" / "genes" / "Atha01G0000010.v1.36" / "index.html").read_text(encoding="utf-8")

        self.assertIn('/datasets/pgcp_atha_gene_json_202606', html)
        self.assertIn('/sequence-records/Atha01G0000010.1.v1.36', html)
        self.assertIn('Sequence Records', html)

    def test_sequence_record_page_shows_core_metadata(self):
        html = (PROJECT_ROOT / "apps" / "web" / "dist" / "sequence-records" / "Atha01G0000010.1.v1.36" / "index.html").read_text(encoding="utf-8")

        self.assertIn('Atha01G0000010.1.v1.36', html)
        self.assertIn('SequenceRecord', html)
        self.assertIn('/datasets/pgcp_atha_gene_json_202606', html)
        self.assertIn('Length', html)


if __name__ == "__main__":
    unittest.main()
