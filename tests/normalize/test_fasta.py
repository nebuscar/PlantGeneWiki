import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from plantgenewiki.normalize.fasta import normalize_fasta_dataset, write_normalized_fasta_outputs  # noqa: E402


class FastaNormalizeTests(unittest.TestCase):
    def test_normalizes_gzipped_fasta_to_dataset_sequence_records_and_relations(self):
        with tempfile.TemporaryDirectory() as directory:
            fasta_path = Path(directory) / "abies_alba.cds.fa.gz"
            with gzip.open(fasta_path, "wt", encoding="utf-8") as handle:
                handle.write(
                    ">Aalbaalba5_s000000100000010.1.v1.0\n"
                    "ATGC\n"
                    "AA\n"
                    ">Aalbaalba5_s000000200000020.2.v1.0 description here\n"
                    "GGGTTT\n"
                )

            result = normalize_fasta_dataset(
                input_path=fasta_path,
                species_name="Abies alba",
                species_id="abies_alba",
                source="PGCP",
                version="v1",
                sequence_type="CDS",
            )

            dataset = result.datasets[0]
            self.assertEqual(dataset["object_type"], "Dataset")
            self.assertEqual(dataset["object_id"], "dataset:pgcp:abies_alba:v1:cds")
            self.assertEqual(dataset["dataset_type"], "sequence_set")
            self.assertEqual(dataset["location_policy"], "internal_raw_storage")
            self.assertEqual(dataset["stats"]["sequence_count"], 2)
            self.assertEqual(dataset["stats"]["total_length"], 12)

            first = result.sequence_records[0]
            self.assertEqual(first["object_type"], "SequenceRecord")
            self.assertEqual(first["sequence_id"], "Aalbaalba5_s000000100000010.1.v1.0")
            self.assertEqual(first["inferred_gene_id"], "Aalbaalba5_s000000100000010")
            self.assertEqual(first["length"], 6)
            self.assertEqual(first["checksum"]["md5"], hashlib.md5(b"ATGCAA").hexdigest())
            self.assertNotIn("sequence", first)

            self.assertEqual(result.summary["sequence_count"], 2)
            self.assertEqual(result.summary["min_length"], 6)
            self.assertEqual(result.summary["max_length"], 6)
            self.assertEqual(result.relations[0]["predicate"], "contains_sequence")

    def test_writes_normalized_outputs_as_jsonl_and_summary_json(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            fasta_path = directory_path / "sample.fa.gz"
            with gzip.open(fasta_path, "wt", encoding="utf-8") as handle:
                handle.write(">seq1.1.v1\nATGC\n")

            result = normalize_fasta_dataset(
                input_path=fasta_path,
                species_name="Test species",
                species_id="test_species",
                source="PGCP",
                version="v1",
                sequence_type="CDS",
            )
            output_dir = directory_path / "out"
            write_normalized_fasta_outputs(result, output_dir)

            self.assertTrue((output_dir / "datasets.jsonl").exists())
            self.assertTrue((output_dir / "sequence_records.jsonl").exists())
            self.assertTrue((output_dir / "relations.jsonl").exists())
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["sequence_count"], 1)


if __name__ == "__main__":
    unittest.main()
