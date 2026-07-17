########## 0. imports ##########
import tempfile
import unittest
from pathlib import Path

from phytoatlas.normalize.pipeline import build_minimal_species_knowledge_base


########## 1. tests ##########
class PipelineManifestTest(unittest.TestCase):
    def test_manifest_uses_portable_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gene_tsv = root / "species.gene.tsv"
            gene_tsv.write_text(
                "gene_ID\tsource_ID\tlocation\tstart\tend\tstrand\tfunction\tgo\ttf_type\ttf_family\n"
                "Gene01.v1\tSource01\tChr1\t1\t9\t+\tTest gene\tGO:0000001\t\t\n",
                encoding="utf-8",
            )
            fasta = root / "species.cds.fa"
            fasta.write_text(">Gene01.1.v1\nATGAAATAG\n", encoding="utf-8")
            output_dir = root / "processed" / "test_species"
            manifest = build_minimal_species_knowledge_base(
                species_name="Test species",
                species_id="test_species",
                fasta_paths=[fasta],
                gff_path=None,
                gene_tsv_path=gene_tsv,
                output_dir=output_dir,
                source_provider="test",
                import_batch="test_v1",
                version="v1",
                assembly="test_v1",
                updated_at="2026-07-17",
            )
        self.assertEqual(manifest["output_dir"], ".")


if __name__ == "__main__":
    unittest.main()
