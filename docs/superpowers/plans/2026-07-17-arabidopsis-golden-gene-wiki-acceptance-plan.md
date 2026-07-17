# Arabidopsis Golden Gene Wiki Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a versioned 20-gene Arabidopsis quality contract and make the real Gene Wiki page pass deterministic data, API, and Vue acceptance checks.

**Architecture:** A repository-owned JSON manifest defines durable expectations for ten engineering boundary genes and ten biologically representative genes. A reusable Python validator audits normalized JSONL data, while a dedicated FastAPI Gene Wiki endpoint returns complete deterministic one-hop records for the Vue page. Focused Vue components render stable fields without exposing raw JSON or internal paths.

**Tech Stack:** Python 3.12, unittest, SQLite read-only graph snapshot, FastAPI, Vue 3, TypeScript, Vitest, Vite.

## Global Constraints

- Use `/DATA/data2/phytoatlas/processed/pgcp_v1` only as runtime input; do not commit production data.
- Keep SQLite as the offline graph snapshot; do not add vector or production graph storage in this milestone.
- Do not require Homology or Publications content while their source datasets are absent.
- Keep all nine permanent Gene Wiki sections visible.
- Do not commit credentials, `.env`, internal absolute paths, generated reports, raw data, or graph indexes.
- Use concise English code comments and numbered `########## n. stage ##########` Python separators.
- Avoid redundant prints and blank lines.

---

### Task 1: Candidate Profiling And Golden Manifest

**Files:**
- Create: `src/phytoatlas/quality/gene_profile.py`
- Create: `scripts/maintenance/profile_gene_candidates.py`
- Create: `config/quality/arabidopsis_golden_genes.json`
- Create: `tests/quality/test_gene_profile.py`
- Create: `tests/quality/test_golden_gene_manifest.py`

**Interfaces:**
- Consumes normalized `genes.jsonl`, `gene_structures.jsonl`, and `sequence_records.jsonl`.
- Produces `profile_gene_candidates(species_dir: str | Path, limit: int = 5) -> dict[str, list[dict[str, Any]]]`.
- Produces a manifest with `schema_version`, `species_id`, section rules, and exactly 20 genes.

- [ ] **Step 1: Write the failing profile test**

```python
########## 0. imports ##########
import json
import tempfile
import unittest
from pathlib import Path
from phytoatlas.quality.gene_profile import profile_gene_candidates

########## 1. tests ##########
class GeneProfileTest(unittest.TestCase):
    def test_profiles_boundary_metrics(self):
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
```

- [ ] **Step 2: Run the test and verify the import failure**

Run: `python -m unittest tests.quality.test_gene_profile -v`

Expected: FAIL with `ModuleNotFoundError: phytoatlas.quality.gene_profile`.

- [ ] **Step 3: Implement deterministic profiling and the CLI**

Use these ranking keys and object ID tie-breaking:

```python
rankings = {
    "highest_transcript_count": lambda item: item["transcript_count"],
    "highest_sequence_count": lambda item: item["sequence_count"],
    "highest_go_count": lambda item: item["go_count"],
    "highest_cds_feature_count": lambda item: item["cds_feature_count"],
    "longest_description": lambda item: item["description_length"],
}
for name, key in rankings.items():
    result[name] = sorted(records, key=lambda item: (-key(item), item["object_id"]))[:limit]
```

Add `transcription_factors` and `sparse_annotations` lists. The CLI accepts `--species-dir`, `--limit`, and optional `--output`.

- [ ] **Step 4: Freeze the 20 real genes**

Engineering boundary genes:

```text
Atha01G0000010.v1.36  AT1G01010  NAC TF, positive strand
Atha01G0000020.v1.36  AT1G01020  negative strand, six transcripts
Atha04G0031690.v1.36  AT4G30820  27 transcripts, 54 sequences
Atha03G0008690.v1.36  AT3G09100  13 GO terms
Atha05G0030650.v1.36  AT5G37510  long description
Atha01G0038670.v1.36  AT1G48090  381 CDS features, no GO
Atha01G0000130.v1.36  AT1G01130  sparse negative single transcript
Atha01G0000180.v1.36  AT1G01180  sparse positive single transcript
Atha01G0000030.v1.36  AT1G01030  B3 TF
Atha02G0017280.v1.36  AT2G23985  26 transcripts, no GO
```

Biological representative genes:

```text
Atha01G0000040.v1.36  AT1G01040  DCL1
Atha01G0055360.v1.36  AT1G65480  FT
Atha05G0009420.v1.36  AT5G10140  FLC
Atha05G0015000.v1.36  AT5G15840  CO
Atha05G0057090.v1.36  AT5G61850  LFY
Atha01G0059300.v1.36  AT1G69120  AP1
Atha01G0054030.v1.36  AT1G64280  NPR1
Atha02G0037780.v1.36  AT2G43010  PIF4
Atha03G0026240.v1.36  AT3G24650  ABI3
Atha01G0009170.v1.36  AT1G09570  PHYA
```

Each record uses this shape and the measured counts as minima:

```json
{
  "group": "engineering_boundary",
  "symbol": null,
  "public_id": "Atha01G0000010.v1.36",
  "object_id": "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
  "aliases": ["AT1G01010.Araport11.447"],
  "reason": "Positive-strand NAC transcription factor",
  "expected": {
    "strand": "+",
    "tf_type": "TF",
    "tf_family": "NAC",
    "minimum_go_terms": 2,
    "minimum_transcripts": 1,
    "minimum_cds_records": 1,
    "minimum_protein_records": 1
  }
}
```

- [ ] **Step 5: Add manifest invariants**

```python
self.assertEqual(len(genes), 20)
self.assertEqual(Counter(item["group"] for item in genes), {
    "engineering_boundary": 10,
    "biological_representative": 10,
})
self.assertEqual(len({item["object_id"] for item in genes}), 20)
self.assertEqual(len(manifest["required_sections"]), 9)
self.assertEqual(manifest["allowed_unavailable_sections"], ["homology", "publications"])
```

- [ ] **Step 6: Verify and commit**

Run: `python -m unittest tests.quality.test_gene_profile tests.quality.test_golden_gene_manifest -v`

Expected: PASS.

Commit: `git commit -m "Add Arabidopsis golden gene contract"`

### Task 2: Golden Gene Data Validator

**Files:**
- Create: `src/phytoatlas/quality/golden_gene_audit.py`
- Create: `scripts/maintenance/audit_golden_genes.py`
- Create: `tests/quality/test_golden_gene_audit.py`
- Create: `tests/quality/test_audit_golden_genes_cli.py`
- Modify: `src/phytoatlas/quality/__init__.py`

**Interfaces:**
- Produces `audit_golden_genes(species_dir: str | Path, manifest_path: str | Path) -> dict[str, Any]`.
- Report keys: `species_id`, `status`, `golden_gene_count`, `passed_gene_count`, `genes`, `issues`, `audited_at`.

- [ ] **Step 1: Write failing validator tests**

Create a one-gene normalized fixture. Assert a valid record passes and a changed strand/GO minimum fails:

```python
report = audit_golden_genes(species_dir, manifest_path)
self.assertEqual(report["status"], "pass")
self.assertEqual(report["passed_gene_count"], 1)
self.assertEqual(report["genes"][0]["metrics"]["sequence_types"], {"CDS": 1, "PROTEIN": 1})
```

```python
self.assertEqual(report["status"], "fail")
self.assertEqual({item["code"] for item in report["issues"]}, {
    "strand_mismatch", "minimum_go_terms_not_met",
})
```

- [ ] **Step 2: Verify failure**

Run: `python -m unittest tests.quality.test_golden_gene_audit -v`

Expected: FAIL because `audit_golden_genes` is absent.

- [ ] **Step 3: Implement indexed JSONL validation**

Load each JSONL file once. Index Gene, GeneLocation, and GeneStructure by `object_id`; group SequenceRecords by `inferred_gene_id`. Validate these codes:

```python
ISSUE_CODES = {
    "missing_gene", "missing_location", "missing_structure", "missing_alias",
    "strand_mismatch", "tf_type_mismatch", "tf_family_mismatch",
    "minimum_go_terms_not_met", "minimum_transcripts_not_met",
    "minimum_cds_records_not_met", "minimum_protein_records_not_met",
    "absolute_internal_path",
}
```

- [ ] **Step 4: Implement CLI behavior**

```python
parser.add_argument("--species-dir", type=Path, required=True)
parser.add_argument("--manifest", type=Path, required=True)
parser.add_argument("--output", type=Path)
```

Exit `0` on pass and `1` on fail. Write generated reports outside Git-tracked paths.

- [ ] **Step 5: Verify and commit**

Run:

```bash
python -m unittest tests.quality.test_golden_gene_audit tests.quality.test_audit_golden_genes_cli -v
python -m unittest discover -s tests/quality -v
```

Expected: PASS.

Commit: `git commit -m "Add golden gene data audit"`

### Task 3: Deterministic Complete Gene Wiki Graph Query

**Files:**
- Modify: `apps/api/phytoatlas_api/graph_store.py`
- Modify: `apps/api/tests/test_graph_store.py`

**Interfaces:**
- Produces `SQLiteGraphStore.get_gene_wiki_record(node_id: str) -> dict[str, Any]`.
- Returns `{"node": GraphNode | None, "edges": list[GraphEdge], "nodes": list[GraphNode]}`.

- [ ] **Step 1: Write failing ordering and completeness tests**

Insert reverse-ordered predicates and assert generic neighbors are sorted. Insert 205 `has_sequence` edges and assert the dedicated query returns all 206 relations including the existing Species edge.

```python
result = self.store.get_gene_wiki_record(self.gene_id)
self.assertEqual(len(result["edges"]), 206)
self.assertEqual(result["edges"], sorted(
    result["edges"], key=lambda edge: (edge["predicate"], edge["source"], edge["target"])
))
```

- [ ] **Step 2: Verify failure**

Run: `cd apps/api && python -m unittest tests.test_graph_store -v`

Expected: FAIL because ordering is undefined and `get_gene_wiki_record` is absent.

- [ ] **Step 3: Make generic neighbor ordering deterministic**

```sql
SELECT source, predicate, target, species_id, source_dataset, evidence, properties_json
FROM edges
WHERE {clauses}
ORDER BY predicate, source, target, edge_id
LIMIT ?
```

- [ ] **Step 4: Implement the complete query**

```python
def get_gene_wiki_record(self, node_id: str) -> dict[str, Any]:
    node = self.get_node(node_id)
    if node is None or node["object_type"] != "Gene":
        return {"node": None, "edges": [], "nodes": []}
    with self.connect() as connection:
        rows = connection.execute(
            """
            SELECT source, predicate, target, species_id, source_dataset, evidence, properties_json
            FROM edges
            WHERE source = ? OR target = ?
            ORDER BY predicate, source, target, edge_id
            """,
            (node_id, node_id),
        ).fetchall()
        edges = [self._edge_from_row(row) for row in rows]
        related_ids = sorted({
            value for edge in edges for value in (edge["source"], edge["target"])
            if value != node_id
        })
        related_nodes = self._get_nodes_by_ids(connection, related_ids)
    return {"node": node, "edges": edges, "nodes": related_nodes}
```

- [ ] **Step 5: Verify and commit**

Run: `python -m unittest tests.test_graph_store -v`

Expected: PASS.

Commit: `git commit -m "Add deterministic Gene Wiki graph query"`

### Task 4: Gene Wiki API And Vue Data Contract

**Files:**
- Modify: `apps/api/phytoatlas_api/main.py`
- Modify: `apps/api/tests/test_main.py`
- Modify: `apps/web/src/types/graph.ts`
- Modify: `apps/web/src/services/graph.ts`
- Create: `apps/web/src/composables/useGeneRecord.ts`
- Modify: `apps/web/tests/services/graph.spec.ts`
- Create: `apps/web/tests/composables/use-gene-record.spec.ts`

**Interfaces:**
- Produces `GET /api/wiki/genes/{node_id:path}`.
- Produces `getGeneWikiRecord(nodeId: string, signal?: AbortSignal): Promise<GeneWikiRecord>`.
- Produces `useGeneRecord(publicId)` returning `node`, `record`, `loading`, `error`, `reload`.

- [ ] **Step 1: Write failing FastAPI route tests**

```python
@patch("phytoatlas_api.main.get_graph_store")
def test_gene_wiki_returns_complete_record(self, get_store):
    expected = {"node": {"node_id": "gene:test"}, "edges": [], "nodes": []}
    get_store.return_value.get_gene_wiki_record.return_value = expected
    self.assertEqual(gene_wiki("gene:test"), expected)
```

Also assert missing genes raise HTTP 404.

- [ ] **Step 2: Add the route**

```python
@app.get("/api/wiki/genes/{node_id:path}")
def gene_wiki(node_id: str) -> dict:
    try:
        result = get_graph_store().get_gene_wiki_record(node_id)
    except GraphStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result["node"] is None:
        raise HTTPException(status_code=404, detail=f"Gene not found: {node_id}")
    return result
```

- [ ] **Step 3: Write failing service and composable tests**

Assert the service requests the encoded full node ID. Assert the composable resolves the public ID, requests the dedicated record, and ignores stale responses.

- [ ] **Step 4: Implement the frontend contract**

```typescript
export interface GeneWikiRecord extends GraphNeighborhood {}

export function getGeneWikiRecord(nodeId: string, signal?: AbortSignal): Promise<GeneWikiRecord> {
  return apiRequest<GeneWikiRecord>(
    `/api/wiki/genes/${encodeURIComponent(nodeId)}`,
    { signal },
  );
}
```

Implement `useGeneRecord` with the existing request-ID stale-response protection from `useObjectRecord`.

- [ ] **Step 5: Verify and commit**

Run:

```bash
cd apps/api
python -m unittest tests.test_main tests.test_graph_store -v
cd ../web
npm test -- --run tests/services/graph.spec.ts tests/composables/use-gene-record.spec.ts
```

Expected: PASS.

Commit: `git commit -m "Connect Gene Wiki page contract to FastAPI"`

### Task 5: Readable Gene Wiki Presentation

**Files:**
- Create: `apps/web/src/lib/gene-record.ts`
- Create: `apps/web/src/components/genes/GeneLocationPanel.vue`
- Create: `apps/web/src/components/genes/GeneStructurePanel.vue`
- Create: `apps/web/src/components/genes/GeneFunctionPanel.vue`
- Create: `apps/web/src/components/genes/GeneSequencePanel.vue`
- Modify: `apps/web/src/views/GeneView.vue`
- Modify: `apps/web/src/components/objects/EvidencePanel.vue`
- Create: `apps/web/tests/lib/gene-record.spec.ts`

**Interfaces:**
- Produces `findRelatedNodes`, `readGenomeLocation`, `readTranscriptSummaries`, `readFunctionAnnotations`, and `groupSequenceRecords`.
- Produces focused components that render stable fields from GraphNode arrays.

- [ ] **Step 1: Write failing formatting tests**

```typescript
expect(readTranscriptSummaries(structureNode)).toEqual([{
  transcriptId: "Atha01G0000010.1.v1.36",
  name: "Atha01G0000010.1",
  location: "Chr1:3631-5899 (+)",
  cdsCount: 6,
  exonCount: 0,
  utrCount: 2,
}]);
```

Assert location fields and CDS/Protein grouping. Ensure no helper exposes `source_file`.

- [ ] **Step 2: Verify failure**

Run: `cd apps/web && npm test -- --run tests/lib/gene-record.spec.ts`

Expected: FAIL because helpers are absent.

- [ ] **Step 3: Implement defensive formatters**

```typescript
export function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

export function formatLocation(value: unknown): string {
  const location = asRecord(value);
  const seqid = typeof location.seqid === "string" ? location.seqid : "";
  const start = typeof location.start === "number" ? location.start : null;
  const end = typeof location.end === "number" ? location.end : null;
  const strand = typeof location.strand === "string" ? location.strand : "";
  return seqid && start !== null && end !== null
    ? `${seqid}:${start}-${end}${strand ? ` (${strand})` : ""}`
    : "";
}
```

- [ ] **Step 4: Implement focused panels**

- `GeneLocationPanel`: Assembly, Coordinates, Strand, Coordinate system.
- `GeneStructurePanel`: transcript cards with ID, location, CDS, exon, and UTR counts.
- `GeneFunctionPanel`: Description, GO chips, TF Type and Family.
- `GeneSequencePanel`: CDS and Protein groups with record ID, length, and RouterLink.

- [ ] **Step 5: Replace raw JSON in GeneView**

Switch to `useGeneRecord`, keep all nine sections, and pass grouped records to the new panels. Replace the corrupted EvidencePanel separator with:

```vue
<code>{{ edge.source }} -> {{ edge.target }}</code>
```

- [ ] **Step 6: Verify and commit**

Run: `npm test -- --run tests/lib/gene-record.spec.ts tests/views/gene.spec.ts`

Expected: formatter tests PASS; the GeneView test may require Task 6 fixtures.

Commit: `git commit -m "Render readable Gene Wiki sections"`

### Task 6: Rich And Sparse Gene Page Regression

**Files:**
- Modify: `apps/web/tests/views/gene.spec.ts`
- Create: `docs/testing/gene-wiki-browser-smoke.md`

**Interfaces:**
- Produces rich and sparse real-data-shaped component tests.
- Produces an exact live-browser smoke procedure.

- [ ] **Step 1: Build compact rich and sparse fixtures**

The rich fixture represents `Atha04G0031690.v1.36`: positive strand, four GO terms, 27 transcripts, 27 CDS, 27 Protein records, Location, Structure, and Evidence.

The sparse fixture represents `Atha01G0000130.v1.36`: negative strand, no GO/TF, one transcript, one CDS, one Protein, no Homology or Literature.

- [ ] **Step 2: Add rich-page assertions**

```typescript
expect(wrapper.get("h1").text()).toContain("Atha04G0031690");
expect(wrapper.text()).toContain("27 transcripts");
expect(wrapper.text()).toContain("CDS (27)");
expect(wrapper.text()).toContain("Protein (27)");
expect(wrapper.text()).not.toContain('"transcripts":');
expect(wrapper.text()).not.toContain("/DATA/data2");
```

- [ ] **Step 3: Add sparse-page assertions**

```typescript
for (const heading of permanentHeadings) expect(wrapper.text()).toContain(heading);
expect(wrapper.text()).toContain("AT1G01130.Araport11.447");
expect(wrapper.text()).toContain("Not available");
expect(wrapper.text()).not.toContain("[object Object]");
```

- [ ] **Step 4: Run Vue tests and build**

Run:

```bash
cd apps/web
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 5: Document live browser smoke**

Runtime commands:

```bash
cd /home/nizhu/Projects/PhytoAtlas/apps/api
PHYTOATLAS_GRAPH_DB=/DATA/data2/phytoatlas/graph/pgcp_v1/phytoatlas_pgcp_v1.sqlite uvicorn phytoatlas_api.main:app --host 0.0.0.0 --port 8000
cd /home/nizhu/Projects/PhytoAtlas/apps/web
VITE_API_BASE=http://127.0.0.1:8000 npm run dev
```

Verify:

```text
http://localhost:4322/genes/Atha04G0031690.v1.36
http://localhost:4322/genes/Atha01G0000130.v1.36
```

Check nine sections, readable fields, sequence counts/links, unavailable Homology/Publications, left navigation, no raw JSON, and no internal paths.

- [ ] **Step 6: Commit**

Commit: `git commit -m "Add real Gene Wiki page regression"`

### Task 7: Production Acceptance And Final Verification

**Files:**
- Modify: `docs/architecture/arabidopsis-mvp-acceptance.md`
- Runtime only: `/DATA/data2/phytoatlas/quality/arabidopsis_golden_genes.json`

- [ ] **Step 1: Run production golden audit**

```bash
cd /home/nizhu/Projects/PhytoAtlas
PYTHONPATH=src python scripts/maintenance/audit_golden_genes.py \
  --species-dir /DATA/data2/phytoatlas/processed/pgcp_v1/arabidopsis_thaliana \
  --manifest config/quality/arabidopsis_golden_genes.json \
  --output /DATA/data2/phytoatlas/quality/arabidopsis_golden_genes.json
```

Expected:

```json
{"species_id":"arabidopsis_thaliana","status":"pass","golden_gene_count":20,"passed_gene_count":20}
```

- [ ] **Step 2: Run all Python suites**

```bash
python -m unittest discover -s tests -v
cd apps/api
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 3: Run all frontend checks**

```bash
cd /home/nizhu/Projects/PhytoAtlas/apps/web
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 4: Complete live browser smoke**

Record date, graph snapshot, tested URLs, and PASS in `docs/architecture/arabidopsis-mvp-acceptance.md`. Do not commit private-address screenshots.

- [ ] **Step 5: Check repository hygiene**

```bash
git diff --check
git status --short
git grep -n "/DATA/data2" -- ':!docs/superpowers' ':!docs/testing' ':!scripts/maintenance'
git grep -n "DB_PASSWORD\|API_KEY\|PRIVATE KEY" -- . ':!.git'
```

Expected: no whitespace errors, unexpected generated files, or credentials.

- [ ] **Step 6: Commit final acceptance documentation**

Commit: `git commit -m "Complete Arabidopsis Gene Wiki acceptance"`

## Self-Review

- Spec coverage: manifest, reproducible selection, data audit, deterministic API, readable permanent sections, rich/sparse regression, browser smoke, and hygiene each have a task.
- Deferred explicitly: alias API resolution, Homology data, Publications data, vector storage, and production graph storage.
- Placeholder scan: no task depends on an unspecified ID, field, command, or expected result.
- Type consistency: `get_gene_wiki_record`, `GET /api/wiki/genes/{node_id:path}`, `GeneWikiRecord`, `getGeneWikiRecord`, and `useGeneRecord` share one neighborhood shape.
