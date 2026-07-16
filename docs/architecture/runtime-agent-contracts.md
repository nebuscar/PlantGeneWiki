# Runtime Agent Contracts

## Scope

These contracts describe future PhytoAtlas product Agents. They do not configure Codex development subagents and do not select an orchestration framework.

## Common task envelope

Every Agent accepts and returns a structured task envelope containing:

| Field | Meaning |
|---|---|
| `task_id` | Stable task identifier |
| `task_type` | Declared operation |
| `object_ids` | Related knowledge object identifiers |
| `dataset_id` | Source Dataset identifier |
| `version` | Input contract or dataset version |
| `provenance` | Source and processing lineage |
| `status` | `queued`, `running`, `review_required`, `completed`, or `failed` |
| `created_at` | Creation timestamp |
| `updated_at` | Last state transition timestamp |
| `errors` | Structured failure records |

## Agent boundaries

| Agent | Input | Output | Human review trigger |
|---|---|---|---|
| Data Ingestion Agent | Source registry and collection policy | Raw Dataset and collection log | License ambiguity, checksum change, or source schema drift |
| Normalization Agent | Raw Dataset and target schema | Knowledge Objects, Relations, and candidate EvidenceClaims | Unresolved identifiers, invalid coordinates, or schema violations |
| Literature Curation Agent | Metadata, abstract, or permitted full text | Literature object and candidate claims | Borderline relevance or conflicting entity resolution |
| Evidence Evaluation Agent | Candidate claim and supporting records | Evidence grade, confidence, and review status | Weak, contradictory, or high-impact evidence |
| Indexing Agent | Approved objects and text chunks | Vector index, graph index, and index manifest | Version mismatch, deleted source, or partial index failure |
| User Task Agent | User intent, permissions, and retrieval context | Answer, query plan, or analysis request | Destructive action, unsupported inference, or costly computation |
| Archive Agent | Superseded versions and audit records | Verified archive and recovery manifest | Failed checksum, missing dependency, or retention-policy conflict |

## State rules

- Agents exchange identifiers and structured records, not natural-language-only state.
- Every output retains `dataset_id`, `version`, and `provenance`.
- Machine-generated claims remain distinguishable from curator-approved claims.
- Failed tasks are retryable only when their input version and failure category are recorded.
- Indexing begins only after normalization and required evidence review complete.
- Archive deletion begins only after recovery verification succeeds.
