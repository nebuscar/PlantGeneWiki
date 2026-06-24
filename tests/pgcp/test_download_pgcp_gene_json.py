import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "importers" / "pgcp" / "gene_records"))

from download_pgcp_gene_json import (  # noqa: E402
    extract_gene_ids,
    is_complete_json_file,
    write_json_atomic,
)


class DownloadPgcpGeneJsonTests(unittest.TestCase):
    def test_extract_gene_ids_deduplicates_and_ignores_invalid_rows(self):
        payload = {
            "species": {
                "gene": [
                    {"gene_ID": "gene-1"},
                    {"gene_ID": ""},
                    {"other": "value"},
                    {"gene_ID": "gene-1"},
                    {"gene_ID": "gene-2"},
                ]
            }
        }

        self.assertEqual(extract_gene_ids(payload), ["gene-1", "gene-2"])

    def test_extract_gene_ids_rejects_missing_gene_list(self):
        with self.assertRaisesRegex(ValueError, "gene list"):
            extract_gene_ids({"species": {}})

    def test_complete_json_file_checks_boundaries_without_full_parse(self):
        with tempfile.TemporaryDirectory() as directory:
            complete = Path(directory) / "complete.json"
            truncated = Path(directory) / "truncated.json"
            complete.write_text('  {"value": 1}\n', encoding="utf-8")
            truncated.write_text('{"value": 1', encoding="utf-8")

            self.assertTrue(is_complete_json_file(complete))
            self.assertFalse(is_complete_json_file(truncated))

    def test_write_json_atomic_leaves_complete_json_without_part_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gene.json"
            write_json_atomic(path, {"gene": "Atha01G0000010.v1.36"})

            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"gene": "Atha01G0000010.v1.36"},
            )
            self.assertFalse(path.with_suffix(".json.part").exists())


if __name__ == "__main__":
    unittest.main()
