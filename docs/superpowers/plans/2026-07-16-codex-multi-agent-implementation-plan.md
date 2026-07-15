# Codex Multi-Agent Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure five project-scoped Codex development roles with explicit boundaries, safe concurrency limits, automated configuration checks, and documented runtime Agent contracts.

**Architecture:** Register stable Codex multi-agent roles in a trusted project-level `.codex/config.toml`. Store role instructions in focused TOML layers, enforce repository-wide behavior through `AGENTS.md`, and validate configuration structure without invoking experimental multi-agent features.

**Tech Stack:** Codex CLI 0.139.0, TOML, Python 3.12+ `tomllib`, unittest, Markdown, Git worktrees.

## Global Constraints

- Enable only stable `features.multi_agent`; do not enable `multi_agent_v2` or `child_agents_md`.
- Limit concurrent subagents to `max_threads = 4`, nesting to `max_depth = 1`, and jobs to `job_max_runtime_seconds = 1800`.
- Use separate Git worktrees for concurrent write tasks; read-only review tasks may share the main worktree.
- Never store credentials, tokens, `.env` values, `/home/...` paths, or `/DATA/...` paths in Agent configuration.
- Keep Codex development roles separate from product runtime Agent definitions.
- Respond in Simplified Chinese; code comments must be concise English comments; key script sections use numbered long `#` headings.

---

## File Map

- Create: `AGENTS.md` - repository-wide Codex behavior and engineering rules.
- Create: `.codex/config.toml` - stable multi-agent registry and concurrency limits.
- Create: `.codex/agents/data-curator.toml` - data governance role.
- Create: `.codex/agents/vector-engineer.toml` - vector retrieval role.
- Create: `.codex/agents/graph-engineer.toml` - structured graph role.
- Create: `.codex/agents/application-engineer.toml` - API and frontend integration role.
- Create: `.codex/agents/reviewer.toml` - read-only quality gate role.
- Create: `tests/config/test_codex_agents.py` - structural, boundary, and secret-safety tests.
- Create: `docs/architecture/runtime-agent-contracts.md` - product runtime Agent interface definitions only.

### Task 1: Add repository-level Agent instructions

**Files:**
- Create: `AGENTS.md`

**Interfaces:**
- Consumes: repository engineering rules confirmed by the project owner.
- Produces: instructions inherited by the root task and all project subagents.

- [ ] **Step 1: Create `AGENTS.md`**

```markdown
# PlantGeneWiki Agent Instructions

## Communication

- Always respond in Simplified Chinese.
- Explain the purpose, logic, validation, and remaining risks of each change.

## Code style

- Do not add redundant process output.
- Do not add redundant blank lines.
- Use concise English code comments only.
- Separate key script stages with numbered long headings such as `########## 0. params ##########`.

## Engineering boundaries

- Read existing code and schemas before editing.
- Keep changes scoped to the assigned role and task.
- Do not commit credentials, `.env` files, raw data, generated indexes, or internal server paths.
- Do not treat vector similarity as a verified biological relation.
- Do not bypass normalization to read raw source data from the API or frontend.
- Preserve user changes and unrelated dirty worktree content.
- Run focused tests before reporting completion.

## Multi-agent collaboration

- The root task owns decomposition, integration, and final acceptance.
- Concurrent write tasks must use separate Git worktrees.
- Read-only audits may run in parallel in the main worktree.
- Every subagent report must list changed files, validation results, unresolved issues, and risks.
```

- [ ] **Step 2: Verify formatting and commit**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
git add --intent-to-add AGENTS.md
git diff --check -- AGENTS.md
git add AGENTS.md
git commit -m "Add project Agent instructions"
```

Expected: one new tracked instruction file and no unrelated staged changes.

### Task 2: Write failing tests for the Codex role registry

**Files:**
- Create: `tests/config/test_codex_agents.py`

**Interfaces:**
- Consumes: future `.codex/config.toml` and role TOML files.
- Produces: executable contract for role names, limits, permissions, instructions, and secret safety.

- [ ] **Step 1: Create the configuration test**

```python
########## 0. imports ##########
import unittest
from pathlib import Path
import tomllib

########## 1. params ##########
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / ".codex" / "config.toml"
EXPECTED_ROLES = {
    "data-curator": "workspace-write",
    "vector-engineer": "workspace-write",
    "graph-engineer": "workspace-write",
    "application-engineer": "workspace-write",
    "reviewer": "read-only",
}
FORBIDDEN_TEXT = ("DB_PASSWORD", "api_key", "token =", "/home/", "/DATA/")

########## 2. tests ##########
class CodexAgentConfigTest(unittest.TestCase):
    def test_registry_uses_stable_multi_agent_limits(self):
        config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertTrue(config["features"]["multi_agent"])
        self.assertNotIn("multi_agent_v2", config["features"])
        agents = config["agents"]
        self.assertEqual(agents["max_threads"], 4)
        self.assertEqual(agents["max_depth"], 1)
        self.assertEqual(agents["job_max_runtime_seconds"], 1800)

    def test_all_roles_have_safe_focused_config(self):
        config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for role_name, sandbox_mode in EXPECTED_ROLES.items():
            role = config["agents"][role_name]
            role_path = CONFIG_PATH.parent / role["config_file"]
            self.assertTrue(role["description"])
            self.assertTrue(role_path.is_file())
            role_text = role_path.read_text(encoding="utf-8")
            role_config = tomllib.loads(role_text)
            self.assertEqual(role_config["sandbox_mode"], sandbox_mode)
            self.assertGreater(len(role_config["developer_instructions"]), 200)
            for forbidden in FORBIDDEN_TEXT:
                self.assertNotIn(forbidden, role_text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
.venv/bin/python -m unittest discover -s tests/config -p 'test_codex_agents.py' -v
```

Expected: FAIL because `.codex/config.toml` does not exist.

### Task 3: Register the five Codex development roles

**Files:**
- Create: `.codex/config.toml`
- Create: `.codex/agents/data-curator.toml`
- Create: `.codex/agents/vector-engineer.toml`
- Create: `.codex/agents/graph-engineer.toml`
- Create: `.codex/agents/application-engineer.toml`
- Create: `.codex/agents/reviewer.toml`
- Test: `tests/config/test_codex_agents.py`

**Interfaces:**
- Consumes: exact role names and safety expectations from Task 2.
- Produces: spawnable project roles `data-curator`, `vector-engineer`, `graph-engineer`, `application-engineer`, and `reviewer`.

- [ ] **Step 1: Create `.codex/config.toml`**

```toml
[features]
multi_agent = true

[agents]
max_threads = 4
max_depth = 1
job_max_runtime_seconds = 1800

[agents.data-curator]
description = "Audit, normalize, archive, and trace biological datasets and schemas."
config_file = "agents/data-curator.toml"
nickname_candidates = ["Curator", "Archivist"]

[agents.vector-engineer]
description = "Design and validate chunks, embeddings, Qdrant indexes, and semantic retrieval."
config_file = "agents/vector-engineer.toml"
nickname_candidates = ["Vector", "Retriever"]

[agents.graph-engineer]
description = "Design knowledge objects, evidence-backed relations, graph imports, and graph queries."
config_file = "agents/graph-engineer.toml"
nickname_candidates = ["Graph", "Mapper"]

[agents.application-engineer]
description = "Integrate FastAPI, frontend pages, service contracts, and application workflows."
config_file = "agents/application-engineer.toml"
nickname_candidates = ["App", "Integrator"]

[agents.reviewer]
description = "Perform read-only review of tests, data quality, regressions, secrets, and scope."
config_file = "agents/reviewer.toml"
nickname_candidates = ["Reviewer", "Auditor"]
```

- [ ] **Step 2: Create `.codex/agents/data-curator.toml`**

```toml
sandbox_mode = "workspace-write"
developer_instructions = """
You are the PlantGeneWiki data curator. Own dataset inventory, archive records, schemas, normalization, entity resolution inputs, provenance, versions, and reproducible manifests. Inspect source structure before changing parsers. Preserve raw data and never delete a source until a verified archive exists. Keep source labels in Dataset metadata rather than directory-specific downstream schemas. Do not change frontend presentation, vector retrieval design, or graph semantics unless an interface mismatch must be reported. Use focused tests for parsers and data contracts. Report changed files, validation results, unresolved records, and data-loss risks.
"""
```

- [ ] **Step 3: Create `.codex/agents/vector-engineer.toml`**

```toml
sandbox_mode = "workspace-write"
developer_instructions = """
You are the PlantGeneWiki vector retrieval engineer. Own KnowledgeChunk contracts, embedding generation, Qdrant collections, metadata filters, incremental indexing, semantic search, and retrieval evaluation. Consume normalized and approved knowledge objects; never index raw files directly as authoritative knowledge. Keep chunk provenance, object identifiers, dataset versions, and evidence status in payload metadata. Do not encode vector similarity as a verified biological relation. Add retrieval fixtures and measurable relevance checks before changing search behavior. Report changed files, validation results, retrieval limitations, and index migration risks.
"""
```

- [ ] **Step 4: Create `.codex/agents/graph-engineer.toml`**

```toml
sandbox_mode = "workspace-write"
developer_instructions = """
You are the PlantGeneWiki structured graph engineer. Own knowledge object types, identifiers, relation predicates, EvidenceClaim links, graph import contracts, graph storage adapters, and graph queries. Every factual edge must retain source, version, and evidence status. Keep inferred, asserted, and curated relations distinguishable. Do not treat embedding proximity as graph evidence and do not let the frontend invent relations. Preserve SQLite only as an offline snapshot until a formal graph store is selected. Add schema and query tests for every graph behavior change. Report changed files, validation results, semantic ambiguities, and migration risks.
"""
```

- [ ] **Step 5: Create `.codex/agents/application-engineer.toml`**

```toml
sandbox_mode = "workspace-write"
developer_instructions = """
You are the PlantGeneWiki application engineer. Own FastAPI endpoints, request and response schemas, frontend data access, page interactions, service configuration, and integration tests. Read normalized stores through explicit adapters or APIs; never make frontend or API code depend on raw source directories. Keep vector search, graph queries, and analysis jobs behind separate service contracts. Preserve stable permanent fields on Wiki pages even when values are unavailable. Follow existing project patterns and avoid unrelated redesigns. Report changed files, validation results, API compatibility concerns, and deployment risks.
"""
```

- [ ] **Step 6: Create `.codex/agents/reviewer.toml`**

```toml
sandbox_mode = "read-only"
developer_instructions = """
You are the PlantGeneWiki reviewer. Perform read-only review focused on correctness, biological provenance, data loss, regressions, test gaps, leaked secrets, internal paths, and scope creep. Verify claims against code, schemas, tests, manifests, and command output. Rank findings by severity and cite exact files and lines. Do not rewrite implementation or approve destructive migration without count, size, and checksum evidence. Distinguish confirmed defects from open questions. Report findings first, then remaining risks and test coverage; state clearly when no issue is found.
"""
```

- [ ] **Step 7: Run the configuration tests**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
.venv/bin/python -m unittest discover -s tests/config -p 'test_codex_agents.py' -v
```

Expected: both tests pass.

- [ ] **Step 8: Commit the tested role registry**

```bash
cd /home/nizhu/Projects/PlantGeneWiki
git add .codex/config.toml .codex/agents tests/config/test_codex_agents.py
git commit -m "Configure project Codex subagents"
```

### Task 4: Document product runtime Agent contracts

**Files:**
- Create: `docs/architecture/runtime-agent-contracts.md`

**Interfaces:**
- Consumes: normalized Dataset, Knowledge Object, Relation, EvidenceClaim, and indexing concepts from the approved design.
- Produces: framework-neutral contracts for seven future runtime Agents; no executable runtime framework.

- [ ] **Step 1: Create the contract document**

```markdown
# Runtime Agent Contracts

## Scope

These contracts describe future PlantGeneWiki product Agents. They do not configure Codex development subagents and do not select an orchestration framework.

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
```

- [ ] **Step 2: Verify this remains documentation-only**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
git add --intent-to-add docs/architecture/runtime-agent-contracts.md
git diff --check -- docs/architecture/runtime-agent-contracts.md
git status --short
```

Expected: only the new Markdown contract is dirty; no runtime package, dependency, or database configuration is added.

- [ ] **Step 3: Commit the runtime contracts**

```bash
cd /home/nizhu/Projects/PlantGeneWiki
git add docs/architecture/runtime-agent-contracts.md
git commit -m "Define runtime Agent contracts"
```

### Task 5: Validate Codex configuration and repository health

**Files:**
- Verify: `.codex/config.toml`
- Verify: `.codex/agents/*.toml`
- Verify: `AGENTS.md`
- Verify: `tests/config/test_codex_agents.py`

**Interfaces:**
- Consumes: all prior Agent configuration tasks.
- Produces: evidence that installed Codex accepts the project configuration and existing application tests still pass.

- [ ] **Step 1: Validate installed feature status and strict configuration parsing**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
codex features list | rg '^multi_agent\s+stable\s+true$'
codex --strict-config -C /home/nizhu/Projects/PlantGeneWiki features list
```

Expected: `multi_agent` is stable and enabled; strict configuration parsing exits with status `0`; no warning mentions unknown role or Agent fields.

- [ ] **Step 2: Run focused and existing tests**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
.venv/bin/python -m unittest discover -s tests/config -v
cd /home/nizhu/Projects/PlantGeneWiki/apps/api
../../.venv/bin/python -m unittest discover -s tests -v
```

Expected: two configuration tests and four API tests pass.

- [ ] **Step 3: Inspect configuration safety and Git state**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
rg -n 'DB_PASSWORD|api_key|token =|/home/|/DATA/' .codex AGENTS.md docs/architecture/runtime-agent-contracts.md && exit 1 || true
git diff --check
git status --short
git log -5 --oneline
```

Expected: no secret or internal-path match; no whitespace error; clean worktree; separate commits for project instructions, Codex roles, and runtime contracts.
