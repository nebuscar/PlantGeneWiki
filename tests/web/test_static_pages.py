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
        self.assertIn('Sequence Records for Atha01G0000010', html)

    def test_gene_page_uses_genecards_like_card_structure(self):
        html = (PROJECT_ROOT / "apps" / "web" / "dist" / "genes" / "Atha01G0000010.v1.36" / "index.html").read_text(encoding="utf-8")

        self.assertIn('class="gene-card-shell"', html)
        self.assertIn('Gene Overview', html)
        self.assertIn('Molecular Annotation', html)
        self.assertIn('PlantGeneWiki Summary', html)
        self.assertIn('Knowledge Score: sample', html)
        self.assertIn('Aliases &amp; Identifiers for Atha01G0000010', html)
        self.assertIn('Aliases &amp; Descriptions for Atha01G0000010', html)
        self.assertIn('Other Links for Atha01G0000010', html)
        self.assertIn('Summaries for Atha01G0000010', html)
        self.assertIn('Research Products for Atha01G0000010', html)
        self.assertIn('Genomics &amp; Location for Atha01G0000010', html)
        self.assertIn('Pending GFF/GTF normalization', html)
        self.assertIn('class="resource-strip"', html)
        self.assertIn('Object Type', html)
        self.assertIn('Primary Dataset', html)

    def test_home_page_uses_explore_gene_panel(self):
        html = (PROJECT_ROOT / "apps" / "web" / "dist" / "index.html").read_text(encoding="utf-8")

        self.assertIn('Explore a Gene', html)
        self.assertIn('Search PlantGeneWiki for any term', html)
        self.assertIn('Knowledge object index', html)

    def test_sequence_record_page_shows_core_metadata(self):
        html = (PROJECT_ROOT / "apps" / "web" / "dist" / "sequence-records" / "Atha01G0000010.1.v1.36" / "index.html").read_text(encoding="utf-8")

        self.assertIn('Atha01G0000010.1.v1.36', html)
        self.assertIn('SequenceRecord', html)
        self.assertIn('/datasets/pgcp_atha_gene_json_202606', html)
        self.assertIn('Length', html)


if __name__ == "__main__":
    unittest.main()