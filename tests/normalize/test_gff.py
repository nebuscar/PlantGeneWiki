import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from phytoatlas.normalize.gff import normalize_gff3_dataset, parse_gff_attributes, write_normalized_gff_outputs  # noqa: E402


class GffNormalizeTests(unittest.TestCase):
    def test_parse_gff_attributes_handles_pgcp_style_fields(self):
        attrs = parse_gff_attributes("ID=Atha01G0000010.v1.36;Name=Atha01G0000010;Source_ID=AT1G01010.Araport11.447;")

        self.assertEqual(attrs["ID"], "Atha01G0000010.v1.36")
        self.assertEqual(attrs["Name"], "Atha01G0000010")
        self.assertEqual(attrs["Source_ID"], "AT1G01010.Araport11.447")

    def test_normalizes_gff3_to_gene_locations_structures_dataset_and_relations(self):
        with tempfile.TemporaryDirectory() as directory:
            gff_path = Path(directory) / "arabidopsis_thaliana.genomic.gff.gz"
            with gzip.open(gff_path, "wt", encoding="utf-8") as handle:
                handle.write(
                    "##gff-version 3\n"
                    "Chr1\tphytozomev12\tgene\t3631\t5899\t.\t+\t.\tID=Atha01G0000010.v1.36;Name=Atha01G0000010;Source_ID=AT1G01010.Araport11.447;\n"
                    "Chr1\tphytozomev12\tmRNA\t3631\t5899\t.\t+\t.\tParent=Atha01G0000010.v1.36;ID=Atha01G0000010.1.v1.36;Name=Atha01G0000010.1;Source_ID=AT1G01010.1.Araport11.447;\n"
                    "Chr1\tphytozomev12\tfive_prime_UTR\t3631\t3759\t.\t+\t.\tParent=Atha01G0000010.1.v1.36;ID=Atha01G0000010.1.five_prime_UTR.1.v1.36;\n"
                    "Chr1\tphytozomev12\tCDS\t3760\t3913\t.\t+\t0\tParent=Atha01G0000010.1.v1.36;ID=Atha01G0000010.1.CDS.1.v1.36;\n"
                    "Chr1\tphytozomev12\tCDS\t3996\t4276\t.\t+\t2\tParent=Atha01G0000010.1.v1.36;ID=Atha01G0000010.1.CDS.2.v1.36;\n"
                    "Chr1\tphytozomev12\tthree_prime_UTR\t5631\t5899\t.\t+\t.\tParent=Atha01G0000010.1.v1.36;ID=Atha01G0000010.1.three_prime_UTR.1.v1.36;\n"
                    "Chr1\tphytozomev12\tgene\t6788\t9130\t.\t-\t.\tID=Atha01G0000020.v1.36;Name=Atha01G0000020;Source_ID=AT1G01020.Araport11.447;\n"
                    "Chr1\tphytozomev12\tmRNA\t6788\t9130\t.\t-\t.\tParent=Atha01G0000020.v1.36;ID=Atha01G0000020.1.v1.36;Name=Atha01G0000020.1;\n"
                    "Chr1\tphytozomev12\tCDS\t6915\t7069\t.\t-\t2\tParent=Atha01G0000020.1.v1.36;ID=Atha01G0000020.1.CDS.1.v1.36;\n"
                )

            result = normalize_gff3_dataset(
                input_path=gff_path,
                species_name="Arabidopsis thaliana",
                species_id="arabidopsis_thaliana",
                source="PGCP",
                version="v1",
                assembly="PGCP_v1",
                updated_at="2026-06-25",
            )

            dataset = result.datasets[0]
            self.assertEqual(dataset["object_type"], "Dataset")
            self.assertEqual(dataset["object_id"], "dataset:pgcp:arabidopsis_thaliana:v1:genome_annotation")
            self.assertEqual(dataset["dataset_type"], "genome_annotation")
            self.assertEqual(dataset["coordinate_system"], "1-based-closed")
            self.assertEqual(dataset["stats"]["feature_counts"]["gene"], 2)
            self.assertEqual(dataset["stats"]["feature_counts"]["mRNA"], 2)
            self.assertEqual(dataset["stats"]["feature_counts"]["CDS"], 3)

            first_location = result.gene_locations[0]
            self.assertEqual(first_location["object_type"], "Gene")
            self.assertEqual(first_location["object_id"], "gene:arabidopsis_thaliana:Atha01G0000010.v1.36")
            self.assertEqual(first_location["name"], "Atha01G0000010")
            self.assertEqual(first_location["genome_location"]["seqid"], "Chr1")
            self.assertEqual(first_location["genome_location"]["start"], 3631)
            self.assertEqual(first_location["genome_location"]["end"], 5899)
            self.assertEqual(first_location["genome_location"]["strand"], "+")
            self.assertEqual(first_location["feature_ids"]["primary_transcript"], "Atha01G0000010.1.v1.36")

            first_structure = result.gene_structures[0]
            self.assertEqual(first_structure["object_id"], "gene:arabidopsis_thaliana:Atha01G0000010.v1.36")
            self.assertEqual(first_structure["transcripts"][0]["transcript_id"], "Atha01G0000010.1.v1.36")
            self.assertEqual(len(first_structure["transcripts"][0]["cds"]), 2)
            self.assertEqual(first_structure["transcripts"][0]["cds"][0]["phase"], "0")
            self.assertEqual(len(first_structure["transcripts"][0]["utrs"]), 2)
            self.assertEqual(result.relations[0]["predicate"], "contains_gene")

    def test_writes_normalized_gff_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            gff_path = directory_path / "sample.gff.gz"
            with gzip.open(gff_path, "wt", encoding="utf-8") as handle:
                handle.write("Chr1\tsource\tgene\t1\t10\t.\t+\t.\tID=gene1;Name=Gene One;\n")

            result = normalize_gff3_dataset(
                input_path=gff_path,
                species_name="Test species",
                species_id="test_species",
                source="PGCP",
                version="v1",
                assembly="PGCP_v1",
            )
            output_dir = directory_path / "out"
            write_normalized_gff_outputs(result, output_dir)

            self.assertTrue((output_dir / "datasets.jsonl").exists())
            self.assertTrue((output_dir / "gene_locations.jsonl").exists())
            self.assertTrue((output_dir / "gene_structures.jsonl").exists())
            self.assertTrue((output_dir / "relations.jsonl").exists())
            manifest = json.loads((output_dir / "annotation_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["dataset_type"], "genome_annotation")
            self.assertEqual(manifest["feature_counts"]["gene"], 1)


if __name__ == "__main__":
    unittest.main()
