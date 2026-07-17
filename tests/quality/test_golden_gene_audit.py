########## 0. imports ##########
import json
import tempfile
import unittest
from pathlib import Path

from phytoatlas.quality.golden_gene_audit import audit_golden_genes


########## 1. fixtures ##########
GENE_ID = "gene:arabidopsis_thaliana:Atha01G0000010.v1.36"


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def build_golden_fixture(root: Path) -> tuple[Path, Path]:
    species_dir = root / "arabidopsis_thaliana"
    species_dir.mkdir()
    write_jsonl(species_dir / "genes.jsonl", [{
        "object_id": GENE_ID,
        "id": "Atha01G0000010.v1.36",
        "name": "Atha01G0000010",
        "aliases": ["AT1G01010.Araport11.447"],
        "genome_location": {"strand": "+"},
        "annotations": {
            "go": ["GO:0006355"],
            "transcription_factor": {"type": "TF", "family": "NAC"},
        },
    }])
    write_jsonl(species_dir / "gene_locations.jsonl", [{
        "object_id": GENE_ID,
        "genome_location": {"seqid": "Chr1", "start": 1, "end": 100, "strand": "+"},
    }])
    write_jsonl(species_dir / "gene_structures.jsonl", [{
        "object_id": GENE_ID,
        "transcripts": [{"cds": [{}, {}], "exons": [], "utrs": [{}]}],
    }])
    write_jsonl(species_dir / "sequence_records.jsonl", [
        {"inferred_gene_id": "Atha01G0000010", "sequence_type": "CDS"},
        {"inferred_gene_id": "Atha01G0000010", "sequence_type": "PROTEIN"},
    ])
    manifest_path = root / "golden.json"
    manifest_path.write_text(json.dumps({
        "schema_version": "1.0",
        "species_id": "arabidopsis_thaliana",
        "genes": [{
            "public_id": "Atha01G0000010.v1.36",
            "object_id": GENE_ID,
            "aliases": ["AT1G01010.Araport11.447"],
            "expected": {
                "strand": "+",
                "tf_type": "TF",
                "tf_family": "NAC",
                "minimum_go_terms": 1,
                "minimum_transcripts": 1,
                "minimum_cds_features": 2,
                "minimum_cds_records": 1,
                "minimum_protein_records": 1,
            },
        }],
    }), encoding="utf-8")
    return species_dir, manifest_path


########## 2. tests ##########
class GoldenGeneAuditTest(unittest.TestCase):
    def test_valid_contract_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            species_dir, manifest_path = build_golden_fixture(Path(temp_dir))
            report = audit_golden_genes(species_dir, manifest_path)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["golden_gene_count"], 1)
        self.assertEqual(report["passed_gene_count"], 1)
        self.assertEqual(report["genes"][0]["metrics"]["transcript_count"], 1)
        self.assertEqual(report["genes"][0]["metrics"]["cds_feature_count"], 2)
        self.assertEqual(
            report["genes"][0]["metrics"]["sequence_types"],
            {"CDS": 1, "PROTEIN": 1},
        )

    def test_contract_mismatches_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            species_dir, manifest_path = build_golden_fixture(Path(temp_dir))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected = manifest["genes"][0]["expected"]
            expected["strand"] = "-"
            expected["minimum_go_terms"] = 2
            expected["minimum_cds_features"] = 3
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = audit_golden_genes(species_dir, manifest_path)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(
            {issue["code"] for issue in report["issues"]},
            {
                "strand_mismatch",
                "minimum_go_terms_not_met",
                "minimum_cds_features_not_met",
            },
        )


if __name__ == "__main__":
    unittest.main()
