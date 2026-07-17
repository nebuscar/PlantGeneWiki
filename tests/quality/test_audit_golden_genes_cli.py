########## 0. imports ##########
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.quality.test_golden_gene_audit import build_golden_fixture


########## 1. params ##########
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "maintenance" / "audit_golden_genes.py"


########## 2. tests ##########
class AuditGoldenGenesCliTest(unittest.TestCase):
    def test_cli_writes_report_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            species_dir, manifest_path = build_golden_fixture(root)
            output_path = root / "report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--species-dir",
                    str(species_dir),
                    "--manifest",
                    str(manifest_path),
                    "--output",
                    str(output_path),
                ],
                cwd=REPO_ROOT,
                env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(json.loads(result.stdout)["passed_gene_count"], 1)

    def test_cli_returns_one_for_failed_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            species_dir, manifest_path = build_golden_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["genes"][0]["expected"]["minimum_transcripts"] = 2
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--species-dir",
                    str(species_dir),
                    "--manifest",
                    str(manifest_path),
                ],
                cwd=REPO_ROOT,
                env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
