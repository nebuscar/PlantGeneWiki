"""Audit one normalized species directory for MVP data integrity."""

from __future__ import annotations

########## 0. imports ##########
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


########## 1. constants ##########
REQUIRED_FILES = {
    "species": "species.jsonl",
    "datasets": "datasets.jsonl",
    "genes": "genes.jsonl",
    "gene_locations": "gene_locations.jsonl",
    "gene_structures": "gene_structures.jsonl",
    "sequence_records": "sequence_records.jsonl",
    "evidence_claims": "evidence_claims.jsonl",
    "relations": "relations.jsonl",
}
NODE_KEYS = (
    "species",
    "datasets",
    "genes",
    "gene_locations",
    "gene_structures",
    "sequence_records",
    "evidence_claims",
)
VALID_STRANDS = {"+", "-", ".", "?", None, ""}
COVERAGE_THRESHOLDS = {
    "gene_location_coverage": 1.0,
    "gene_structure_coverage": 1.0,
    "gene_evidence_coverage": 1.0,
    "sequence_gene_coverage": 0.95,
}


########## 2. public api ##########
def audit_species_directory(species_dir: str | Path) -> dict[str, Any]:
    path = Path(species_dir).resolve()
    issues: list[dict[str, Any]] = []
    manifest = _read_manifest(path, issues)
    records_by_key: dict[str, list[dict[str, Any]]] = {}
    metrics: dict[str, Any] = {}

    for key, filename in REQUIRED_FILES.items():
        file_path = path / filename
        if not file_path.is_file():
            issues.append(_issue("missing_required_file", file=filename))
            records_by_key[key] = []
            metrics[key] = {"count": 0, "duplicate_ids": 0}
            continue
        records = list(_read_jsonl(file_path, issues))
        records_by_key[key] = records
        object_ids = [
            str(record["object_id"])
            for record in records
            if record.get("object_id")
        ]
        duplicate_ids = sum(count - 1 for count in Counter(object_ids).values() if count > 1)
        metrics[key] = {"count": len(records), "duplicate_ids": duplicate_ids}
        if duplicate_ids:
            issues.append(
                _issue(
                    "duplicate_object_id",
                    file=filename,
                    count=duplicate_ids,
                )
            )

    _validate_manifest(path, manifest, metrics, issues)
    _validate_locations(records_by_key["gene_locations"], metrics, issues)
    _add_coverage_metrics(records_by_key, metrics)
    _validate_coverage(metrics, issues)
    _validate_relation_endpoints(records_by_key, metrics, issues)

    return {
        "species_id": manifest.get("species_id") or path.name,
        "status": "fail" if issues else "pass",
        "metrics": metrics,
        "issues": issues,
        "audited_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


########## 3. readers ##########
def _read_manifest(path: Path, issues: list[dict[str, Any]]) -> dict[str, Any]:
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        issues.append(_issue("missing_manifest", file="manifest.json"))
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        issues.append(_issue("invalid_manifest", file="manifest.json"))
        return {}


def _read_jsonl(path: Path, issues: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                issues.append(
                    _issue(
                        "invalid_jsonl_record",
                        file=path.name,
                        line=line_number,
                    )
                )
                continue
            if not isinstance(record, dict):
                issues.append(
                    _issue(
                        "invalid_jsonl_record",
                        file=path.name,
                        line=line_number,
                    )
                )
                continue
            yield record


########## 4. validators ##########
def _validate_manifest(
    path: Path,
    manifest: dict[str, Any],
    metrics: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    output_dir = manifest.get("output_dir")
    manifest_output = Path(str(output_dir)) if output_dir else None
    if manifest_output and not manifest_output.is_absolute():
        manifest_output = path / manifest_output
    output_matches = bool(manifest_output) and manifest_output.resolve() == path
    metrics["manifest_output_matches"] = output_matches
    if not output_matches:
        issues.append(_issue("manifest_output_mismatch", file="manifest.json"))

    manifest_counts = manifest.get("counts") or {}
    for key in REQUIRED_FILES:
        expected = manifest_counts.get(key)
        observed = metrics[key]["count"]
        if expected != observed:
            issues.append(
                _issue(
                    "manifest_count_mismatch",
                    object_type=key,
                    expected=expected,
                    observed=observed,
                )
            )


def _validate_locations(
    records: list[dict[str, Any]],
    metrics: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    invalid = 0
    for record in records:
        location = record.get("genome_location") or {}
        start = location.get("start")
        end = location.get("end")
        strand = location.get("strand")
        valid = (
            isinstance(start, int)
            and isinstance(end, int)
            and start > 0
            and end >= start
            and strand in VALID_STRANDS
            and bool(location.get("seqid"))
        )
        if not valid:
            invalid += 1
    metrics["invalid_gene_locations"] = invalid
    if invalid:
        issues.append(_issue("invalid_gene_location", count=invalid))


def _add_coverage_metrics(
    records: dict[str, list[dict[str, Any]]],
    metrics: dict[str, Any],
) -> None:
    gene_ids = _object_ids(records["genes"])
    location_ids = _object_ids(records["gene_locations"])
    structure_ids = _object_ids(records["gene_structures"])
    evidence_subjects = {
        str(record.get("subject"))
        for record in records["evidence_claims"]
        if record.get("subject")
    }
    gene_keys = {
        _base_gene_key(str(record.get("id") or record.get("object_id") or ""))
        for record in records["genes"]
    }
    sequence_gene_keys = {
        _base_gene_key(str(record.get("inferred_gene_id") or ""))
        for record in records["sequence_records"]
        if record.get("inferred_gene_id")
    }
    metrics["gene_location_coverage"] = _coverage(gene_ids, location_ids)
    metrics["gene_structure_coverage"] = _coverage(gene_ids, structure_ids)
    metrics["gene_evidence_coverage"] = _coverage(gene_ids, evidence_subjects)
    metrics["sequence_gene_coverage"] = _coverage(gene_keys, sequence_gene_keys)
    metrics["sequence_types"] = dict(
        Counter(
            str(record.get("sequence_type") or "unknown")
            for record in records["sequence_records"]
        )
    )

def _validate_coverage(
    metrics: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    for metric, threshold in COVERAGE_THRESHOLDS.items():
        observed = metrics[metric]
        if observed < threshold:
            issues.append(
                _issue(
                    "coverage_below_threshold",
                    metric=metric,
                    threshold=threshold,
                    observed=observed,
                )
            )

def _validate_relation_endpoints(
    records: dict[str, list[dict[str, Any]]],
    metrics: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    node_ids = set().union(*(_object_ids(records[key]) for key in NODE_KEYS))
    missing_sources: list[str] = []
    missing_targets: list[str] = []
    for relation in records["relations"]:
        source = str(relation.get("source") or "")
        target = str(relation.get("target") or "")
        if source not in node_ids:
            missing_sources.append(source)
        if target not in node_ids:
            missing_targets.append(target)
    metrics["dangling_relation_sources"] = len(missing_sources)
    metrics["dangling_relation_targets"] = len(missing_targets)
    if missing_sources:
        issues.append(
            _issue(
                "dangling_relation_source",
                count=len(missing_sources),
                examples=sorted(set(missing_sources))[:3],
            )
        )
    if missing_targets:
        issues.append(
            _issue(
                "dangling_relation_target",
                count=len(missing_targets),
                examples=sorted(set(missing_targets))[:3],
            )
        )


########## 5. helpers ##########
def _object_ids(records: list[dict[str, Any]]) -> set[str]:
    return {
        str(record.get("object_id"))
        for record in records
        if record.get("object_id")
    }


def _base_gene_key(value: str) -> str:
    gene_id = value.rsplit(":", 1)[-1]
    for marker in (".1.v", ".2.v", ".3.v", ".v"):
        if marker in gene_id:
            return gene_id.split(marker, 1)[0]
    return gene_id


def _coverage(expected: set[str], observed: set[str]) -> float:
    if not expected:
        return 0.0
    return round(len(expected & observed) / len(expected), 6)


def _issue(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "error", **details}
