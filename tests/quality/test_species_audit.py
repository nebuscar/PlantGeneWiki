########## 0. imports ##########
import json
import tempfile
import unittest
from pathlib import Path

from phytoatlas.quality.species_audit import audit_species_directory


########## 1. fixtures ##########
def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def build_species_fixture(root: Path) -> Path:
    species_dir = root / "arabidopsis_thaliana"
    species_dir.mkdir()
    gene_id = "gene:arabidopsis_thaliana:Atha01G0000010.v1.36"
    sequence_id = "seq:test:arabidopsis_thaliana:v1:cds:Atha01G0000010.1.v1.36"
    records = {
        "species.jsonl": [
            {
                "object_id": "species:arabidopsis_thaliana",
                "object_type": "Species",
                "id": "arabidopsis_thaliana",
            }
        ],
        "datasets.jsonl": [
            {
                "object_id": "dataset:test",
                "object_type": "Dataset",
                "id": "test",
            }
        ],
        "genes.jsonl": [
            {
                "object_id": gene_id,
                "object_type": "Gene",
                "id": "Atha01G0000010.v1.36",
            }
        ],
        "gene_locations.jsonl": [
            {
                "object_id": gene_id,
                "object_type": "Gene",
                "genome_location": {
                    "seqid": "Chr1",
                    "start": 3631,
                    "end": 5899,
                    "strand": "+",
                },
            }
        ],
        "gene_structures.jsonl": [
            {
                "object_id": gene_id,
                "object_type": "GeneStructure",
                "transcripts": [{"transcript_id": "Atha01G0000010.1.v1.36"}],
            }
        ],
        "sequence_records.jsonl": [
            {
                "object_id": sequence_id,
                "object_type": "SequenceRecord",
                "sequence_type": "CDS",
                "inferred_gene_id": "Atha01G0000010",
            }
        ],
        "evidence_claims.jsonl": [
            {
                "object_id": "evidence:test:1",
                "object_type": "EvidenceClaim",
                "subject": gene_id,
            }
        ],
        "relations.jsonl": [
            {
                "source": gene_id,
                "predicate": "has_sequence",
                "target": sequence_id,
            }
        ],
    }
    for filename, values in records.items():
        write_jsonl(species_dir / filename, values)
    counts = {
        "species": 1,
        "datasets": 1,
        "genes": 1,
        "gene_locations": 1,
        "gene_structures": 1,
        "sequence_records": 1,
        "evidence_claims": 1,
        "relations": 1,
    }
    (species_dir / "manifest.json").write_text(
        json.dumps(
            {
                "species_id": "arabidopsis_thaliana",
                "output_dir": str(species_dir),
                "counts": counts,
            }
        ),
        encoding="utf-8",
    )
    return species_dir


########## 2. tests ##########
class SpeciesAuditTest(unittest.TestCase):
    def test_healthy_species_directory_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            species_dir = build_species_fixture(Path(temp_dir))
            report = audit_species_directory(species_dir)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["metrics"]["genes"]["count"], 1)
        self.assertEqual(report["metrics"]["gene_location_coverage"], 1.0)
        self.assertEqual(report["metrics"]["sequence_gene_coverage"], 1.0)
        self.assertEqual(report["issues"], [])

    def test_integrity_problems_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            species_dir = build_species_fixture(Path(temp_dir))
            genes_path = species_dir / "genes.jsonl"
            duplicate = json.loads(genes_path.read_text(encoding="utf-8").splitlines()[0])
            write_jsonl(genes_path, [duplicate, duplicate])
            location_path = species_dir / "gene_locations.jsonl"
            location = json.loads(location_path.read_text(encoding="utf-8"))
            location["genome_location"]["start"] = 6000
            write_jsonl(location_path, [location])
            write_jsonl(
                species_dir / "relations.jsonl",
                [{"source": duplicate["object_id"], "predicate": "points_to", "target": "missing:node"}],
            )
            manifest = json.loads((species_dir / "manifest.json").read_text(encoding="utf-8"))
            manifest["output_dir"] = "../legacy/arabidopsis_thaliana"
            (species_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            report = audit_species_directory(species_dir)
        issue_codes = {issue["code"] for issue in report["issues"]}
        self.assertEqual(report["status"], "fail")
        self.assertIn("manifest_count_mismatch", issue_codes)
        self.assertIn("manifest_output_mismatch", issue_codes)
        self.assertIn("duplicate_object_id", issue_codes)
        self.assertIn("invalid_gene_location", issue_codes)
        self.assertIn("dangling_relation_target", issue_codes)

    def test_coverage_below_threshold_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            species_dir = build_species_fixture(Path(temp_dir))
            write_jsonl(species_dir / "gene_structures.jsonl", [])
            manifest_path = species_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["counts"]["gene_structures"] = 0
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = audit_species_directory(species_dir)
        issue_codes = {issue["code"] for issue in report["issues"]}
        self.assertEqual(report["metrics"]["gene_structure_coverage"], 0.0)
        self.assertEqual(report["status"], "fail")
        self.assertIn("coverage_below_threshold", issue_codes)


    def test_relations_without_object_ids_are_not_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            species_dir = build_species_fixture(Path(temp_dir))
            gene_id = "gene:arabidopsis_thaliana:Atha01G0000010.v1.36"
            write_jsonl(
                species_dir / "relations.jsonl",
                [
                    {"source": gene_id, "predicate": "provided_by", "target": "dataset:test"},
                    {
                        "source": gene_id,
                        "predicate": "belongs_to_species",
                        "target": "species:arabidopsis_thaliana",
                    },
                ],
            )
            manifest_path = species_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["counts"]["relations"] = 2
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = audit_species_directory(species_dir)
        self.assertEqual(report["status"], "pass")


    def test_relative_manifest_output_is_portable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            species_dir = build_species_fixture(Path(temp_dir))
            manifest_path = species_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["output_dir"] = "."
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = audit_species_directory(species_dir)
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["metrics"]["manifest_output_matches"])

if __name__ == "__main__":
    unittest.main()
