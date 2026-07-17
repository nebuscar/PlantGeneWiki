"""Audit normalized records against a golden gene contract."""

from __future__ import annotations

########## 0. imports ##########
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


########## 1. readers ##########
def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _index(path: Path) -> dict[str, dict[str, Any]]:
    return {str(record["object_id"]): record for record in _read_jsonl(path) if record.get("object_id")}


########## 2. validators ##########
def _issue(code: str, object_id: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "error", "object_id": object_id, **details}


def _contains_absolute_path(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_absolute_path(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_absolute_path(item) for item in value)
    return isinstance(value, str) and Path(value).is_absolute()


def _minimum(issues: list[dict[str, Any]], object_id: str, code: str, observed: int, expected: int) -> None:
    if observed < expected:
        issues.append(_issue(code, object_id, expected=expected, observed=observed))


########## 3. public api ##########
def audit_golden_genes(species_dir: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    root = Path(species_dir)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    genes = _index(root / "genes.jsonl")
    locations = _index(root / "gene_locations.jsonl")
    structures = _index(root / "gene_structures.jsonl")
    sequences: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in _read_jsonl(root / "sequence_records.jsonl"):
        sequences[str(record.get("inferred_gene_id") or "")].append(record)
    results: list[dict[str, Any]] = []
    all_issues: list[dict[str, Any]] = []
    for contract in manifest.get("genes", []):
        object_id = str(contract["object_id"])
        expected = contract.get("expected", {})
        gene = genes.get(object_id)
        location = locations.get(object_id)
        structure = structures.get(object_id)
        issues: list[dict[str, Any]] = []
        if gene is None:
            issues.append(_issue("missing_gene", object_id))
            results.append({"object_id": object_id, "status": "fail", "metrics": {}, "issues": issues})
            all_issues.extend(issues)
            continue
        if location is None:
            issues.append(_issue("missing_location", object_id))
        if structure is None:
            issues.append(_issue("missing_structure", object_id))
        aliases = [str(item) for item in gene.get("aliases", [])]
        for alias in contract.get("aliases", []):
            if alias not in aliases:
                issues.append(_issue("missing_alias", object_id, alias=alias))
        annotations = gene.get("annotations") or {}
        tf = annotations.get("transcription_factor") or {}
        observed_strand = (gene.get("genome_location") or {}).get("strand")
        if observed_strand != expected.get("strand"):
            issues.append(_issue("strand_mismatch", object_id, expected=expected.get("strand"), observed=observed_strand))
        if tf.get("type") != expected.get("tf_type"):
            issues.append(_issue("tf_type_mismatch", object_id))
        if tf.get("family") != expected.get("tf_family"):
            issues.append(_issue("tf_family_mismatch", object_id))
        transcripts = (structure or {}).get("transcripts") or []
        cds_feature_count = sum(len(item.get("cds") or []) for item in transcripts)
        sequence_records = sequences.get(str(gene.get("name") or ""), [])
        sequence_types = Counter(str(item.get("sequence_type") or "").upper() for item in sequence_records)
        metrics = {
            "go_count": len(annotations.get("go") or []),
            "transcript_count": len(transcripts),
            "cds_feature_count": cds_feature_count,
            "sequence_types": dict(sorted(sequence_types.items())),
        }
        for metric, code, observed in (
            ("minimum_go_terms", "minimum_go_terms_not_met", metrics["go_count"]),
            ("minimum_transcripts", "minimum_transcripts_not_met", metrics["transcript_count"]),
            ("minimum_cds_features", "minimum_cds_features_not_met", cds_feature_count),
            ("minimum_cds_records", "minimum_cds_records_not_met", sequence_types["CDS"]),
            ("minimum_protein_records", "minimum_protein_records_not_met", sequence_types["PROTEIN"]),
        ):
            _minimum(issues, object_id, code, observed, int(expected.get(metric, 0)))
        if any(_contains_absolute_path(record) for record in (gene, location, structure, sequence_records)):
            issues.append(_issue("absolute_internal_path", object_id))
        status = "fail" if issues else "pass"
        results.append({"object_id": object_id, "status": status, "metrics": metrics, "issues": issues})
        all_issues.extend(issues)
    return {
        "species_id": manifest.get("species_id") or root.name,
        "status": "fail" if all_issues else "pass",
        "golden_gene_count": len(results),
        "passed_gene_count": sum(item["status"] == "pass" for item in results),
        "genes": results,
        "issues": all_issues,
        "audited_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
