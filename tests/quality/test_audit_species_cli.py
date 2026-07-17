########## 0. imports ##########
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.quality.test_species_audit import build_species_fixture


########## 1. params ##########
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "maintenance" / "audit_species_mvp.py"


########## 2. tests ##########
class AuditSpeciesCliTest(unittest.TestCase):
    def test_cli_writes_report_and_returns_quality_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            species_dir = build_species_fixture(root)
            output_path = root / "quality" / "report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--species-dir",
                    str(species_dir),
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
        self.assertEqual(json.loads(result.stdout)["status"], "pass")

    def test_cli_returns_one_for_failed_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            species_dir = build_species_fixture(root)
            manifest_path = species_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["counts"]["genes"] = 2
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--species-dir", str(species_dir)],
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
