########## 0. imports ##########
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from phytoatlas.quality.gene_profile import profile_gene_candidates


########## 1. tests ##########
class GeneProfileTest(unittest.TestCase):
    def test_profiles_boundary_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "genes.jsonl").write_text(json.dumps({
                "object_id": "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
                "id": "Atha01G0000010.v1.36",
                "name": "Atha01G0000010",
                "aliases": ["AT1G01010.Araport11.447"],
                "description": "NAM protein",
                "genome_location": {"strand": "+"},
                "annotations": {"go": ["GO:0006355"], "transcription_factor": {"type": "TF", "family": "NAC"}},
            }) + "\n", encoding="utf-8")
            (root / "gene_structures.jsonl").write_text(json.dumps({
                "object_id": "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
                "transcripts": [{"cds": [{}, {}], "utrs": [{}]}],
            }) + "\n", encoding="utf-8")
            (root / "sequence_records.jsonl").write_text(json.dumps({
                "inferred_gene_id": "Atha01G0000010", "sequence_type": "CDS",
            }) + "\n", encoding="utf-8")
            report = profile_gene_candidates(root, limit=1)
        self.assertEqual(report["highest_go_count"][0]["go_count"], 1)
        self.assertEqual(report["highest_transcript_count"][0]["transcript_count"], 1)
        self.assertEqual(report["highest_sequence_count"][0]["sequence_count"], 1)
        self.assertEqual(report["transcription_factors"][0]["tf_family"], "NAC")

    def test_cli_writes_profile_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gene_id = "gene:arabidopsis_thaliana:Atha01G0000010.v1.36"
            (root / "genes.jsonl").write_text(json.dumps({
                "object_id": gene_id,
                "id": "Atha01G0000010.v1.36",
                "annotations": {},
            }) + "\n", encoding="utf-8")
            (root / "gene_structures.jsonl").write_text(json.dumps({
                "object_id": gene_id,
                "transcripts": [],
            }) + "\n", encoding="utf-8")
            (root / "sequence_records.jsonl").write_text("", encoding="utf-8")
            output_path = root / "profile.json"
            repo_root = Path(__file__).resolve().parents[2]
            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "maintenance" / "profile_gene_candidates.py"),
                    "--species-dir",
                    str(root),
                    "--limit",
                    "1",
                    "--output",
                    str(output_path),
                ],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": str(repo_root / "src")},
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["highest_go_count"][0]["object_id"], gene_id)
        self.assertEqual(json.loads(result.stdout)["highest_go_count"][0]["object_id"], gene_id)
