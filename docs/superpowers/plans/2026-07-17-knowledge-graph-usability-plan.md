# Knowledge Graph Usability Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an immediately useful, URL-addressable Knowledge Graph workbench that shows a readable real Arabidopsis core graph, preserves complete relationship counts, and exposes real sequence nodes on demand.

**Architecture:** Extend the existing read-only SQLite neighborhood response with indexed count and truncation metadata, then keep route state, API state, presentation summaries, and real graph objects in separate frontend units. Sequence grouping is a derived display model only; real SequenceRecord nodes are fetched and rendered only after an explicit user action.

**Tech Stack:** Python 3 standard library, SQLite, FastAPI, Vue 3 Composition API, Vue Router, TypeScript, Cytoscape, Vitest, Vue Test Utils.

## Global Constraints

- Execute in an isolated worktree created with `superpowers:using-git-worktrees`; use branch `feature/kg-usability` and the repository's ignored `.worktrees/` directory.
- Follow strict TDD for every behavior change: failing test, observed expected failure, minimal implementation, passing focused test, then refactor.
- The API and frontend may read only the normalized graph layer.
- Do not commit credentials, `.env` files, raw data, generated indexes, logs, internal server paths, or browser artifacts.
- A sequence summary is presentation-derived and must never be represented as a persisted `GraphNode` or verified biological relation.
- Public gene IDs require an explicit normalized species scope; never issue an unscoped fallback search.
- Use concise English code comments only, no redundant output, and no redundant blank lines.
- Preserve unrelated user changes and keep the base `nizhu` checkout untouched during implementation.

## Execution Preflight

After `superpowers:using-git-worktrees` creates the isolated worktree, reuse the already validated dependency environments without committing symlinks:

```bash
BASE_ROOT="$(git worktree list --porcelain | awk '/^worktree / {print substr($0, 10); exit}')"
[ -e .venv ] || ln -s "$BASE_ROOT/.venv" .venv
[ -e apps/web/node_modules ] || ln -s "$BASE_ROOT/apps/web/node_modules" apps/web/node_modules
.venv/bin/python -m unittest discover -s tests -v
cd apps/api
../../.venv/bin/python -m unittest discover -s tests -v
cd ../web
npm test
```

Expected baseline: core Python, API, and Web suites pass with zero failures. If any baseline test fails, stop and report it before changing production code.

---

### Task 1: Add complete neighborhood counts and predicate exclusion to the graph store

**Files:**
- Modify: `apps/api/phytoatlas_api/graph_store.py:91-162`
- Modify: `apps/api/tests/test_graph_store.py:18-176`

**Interfaces:**
- Consumes: existing `SQLiteGraphStore.get_node()` and read-only `edges` table indexes.
- Produces: `SQLiteGraphStore.get_neighbors(node_id, *, direction="both", limit=50, predicate=None, exclude_predicates=()) -> dict` with `total_edges`, `matched_edges`, `predicate_counts`, and `truncated`.

- [ ] **Step 1: Add failing store tests for counts, exclusions, and truncation**

Add this helper and the two tests to `SQLiteGraphStoreTest`:

```python
    def insert_edge(self, predicate: str, target: str) -> None:
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            """
            INSERT INTO edges
            (source, predicate, target, species_id, source_dataset, evidence, properties_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
                predicate,
                target,
                "arabidopsis_thaliana",
                "dataset:test",
                "test",
                "{}",
            ),
        )
        connection.commit()
        connection.close()

    def test_get_neighbors_reports_complete_counts_after_exclusion(self) -> None:
        self.insert_edge("has_sequence", "GeneLocation:gene:atha:Atha01G0000010.v1.36")
        self.insert_edge("has_sequence", "species:arabidopsis_thaliana")
        self.insert_edge("has_structure", "GeneLocation:gene:atha:Atha01G0000010.v1.36")

        result = self.store.get_neighbors(
            "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
            exclude_predicates=("has_sequence", "has_sequence"),
            limit=10,
        )

        self.assertEqual(result["total_edges"], 4)
        self.assertEqual(result["matched_edges"], 2)
        self.assertEqual(
            result["predicate_counts"],
            {"belongs_to_species": 1, "has_sequence": 2, "has_structure": 1},
        )
        self.assertFalse(result["truncated"])
        self.assertEqual(
            [edge["predicate"] for edge in result["edges"]],
            ["belongs_to_species", "has_structure"],
        )

    def test_get_neighbors_reports_filtered_truncation(self) -> None:
        self.insert_edge("has_sequence", "GeneLocation:gene:atha:Atha01G0000010.v1.36")
        self.insert_edge("has_sequence", "species:arabidopsis_thaliana")

        result = self.store.get_neighbors(
            "gene:arabidopsis_thaliana:Atha01G0000010.v1.36",
            predicate="has_sequence",
            limit=1,
        )

        self.assertEqual(result["total_edges"], 3)
        self.assertEqual(result["matched_edges"], 2)
        self.assertEqual(result["predicate_counts"]["has_sequence"], 2)
        self.assertEqual(len(result["edges"]), 1)
        self.assertTrue(result["truncated"])
```

- [ ] **Step 2: Run the focused tests and verify the expected failure**

Run from `apps/api`:

```bash
../../.venv/bin/python -m unittest discover -s tests -p 'test_graph_store.py' -v
```

Expected: both new tests fail because `get_neighbors()` does not accept `exclude_predicates` and does not return metadata.

- [ ] **Step 3: Implement metadata and exclusion in one indexed neighborhood query path**

Replace `get_neighbors()` with this behavior-preserving implementation:

```python
    def get_neighbors(
        self,
        node_id: str,
        *,
        direction: Literal["in", "out", "both"] = "both",
        limit: int = 50,
        predicate: str | None = None,
        exclude_predicates: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        node = self.get_node(node_id)
        empty = {
            "node": node,
            "edges": [],
            "nodes": [],
            "total_edges": 0,
            "matched_edges": 0,
            "predicate_counts": {},
            "truncated": False,
        }
        if node is None:
            return empty

        limit = max(1, min(limit, 500))
        if direction == "out":
            direction_clause = "source = ?"
            direction_params: list[Any] = [node_id]
        elif direction == "in":
            direction_clause = "target = ?"
            direction_params = [node_id]
        else:
            direction_clause = "(source = ? OR target = ?)"
            direction_params = [node_id, node_id]

        clauses = [direction_clause]
        params = list(direction_params)
        if predicate:
            clauses.append("predicate = ?")
            params.append(predicate)
        for excluded in sorted({item for item in exclude_predicates if item}):
            clauses.append("predicate != ?")
            params.append(excluded)

        with self.connect() as connection:
            predicate_counts = {
                row["predicate"]: row["count"]
                for row in connection.execute(
                    f"""
                    SELECT predicate, COUNT(*) AS count
                    FROM edges
                    WHERE {direction_clause}
                    GROUP BY predicate
                    ORDER BY predicate
                    """,
                    direction_params,
                )
            }
            matched_edges = connection.execute(
                f"SELECT COUNT(*) FROM edges WHERE {' AND '.join(clauses)}",
                params,
            ).fetchone()[0]
            edge_rows = connection.execute(
                f"""
                SELECT source, predicate, target, species_id, source_dataset, evidence, properties_json
                FROM edges
                WHERE {' AND '.join(clauses)}
                ORDER BY predicate, source, target, edge_id
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
            edges = [self._edge_from_row(row) for row in edge_rows]
            related_ids = sorted(
                {
                    item
                    for edge in edges
                    for item in (edge["source"], edge["target"])
                    if item != node_id
                }
            )
            related_nodes = self._get_nodes_by_ids(connection, related_ids)

        return {
            "node": node,
            "edges": edges,
            "nodes": related_nodes,
            "total_edges": sum(predicate_counts.values()),
            "matched_edges": matched_edges,
            "predicate_counts": predicate_counts,
            "truncated": len(edges) < matched_edges,
        }
```

- [ ] **Step 4: Run focused and complete API tests**

```bash
cd apps/api
../../.venv/bin/python -m unittest discover -s tests -p 'test_graph_store.py' -v
../../.venv/bin/python -m unittest discover -s tests -v
```

Expected: all store and API tests pass with zero failures.

- [ ] **Step 5: Commit the graph-store contract**

```bash
git add apps/api/phytoatlas_api/graph_store.py apps/api/tests/test_graph_store.py
git commit -m "Add graph neighborhood metadata"
```

### Task 2: Expose exclusions through FastAPI and the dependency-free server

**Files:**
- Modify: `apps/api/phytoatlas_api/main.py:48-67`
- Modify: `apps/api/phytoatlas_api/simple_server.py:17-84`
- Modify: `apps/api/tests/test_main.py:1-36`
- Create: `apps/api/tests/test_simple_server.py`
- Modify: `apps/api/README.md:1-30`

**Interfaces:**
- Consumes: Task 1 `exclude_predicates` store argument and metadata response.
- Produces: repeatable `exclude_predicate` HTTP query parameters in both API implementations.

- [ ] **Step 1: Add failing FastAPI forwarding test**

Import `graph_neighbors` in `test_main.py` and add:

```python
class GraphNeighborApiTest(unittest.TestCase):
    @patch("phytoatlas_api.main.get_graph_store")
    def test_graph_neighbors_forwards_repeated_exclusions(self, get_store):
        expected = {
            "node": {"node_id": "gene:test"},
            "edges": [],
            "nodes": [],
            "total_edges": 54,
            "matched_edges": 0,
            "predicate_counts": {"has_sequence": 54},
            "truncated": False,
        }
        get_store.return_value.get_neighbors.return_value = expected

        result = graph_neighbors(
            "gene:test",
            direction="both",
            predicate=None,
            exclude_predicate=["has_sequence", "has_sequence"],
            limit=100,
        )

        self.assertEqual(result, expected)
        get_store.return_value.get_neighbors.assert_called_once_with(
            "gene:test",
            direction="both",
            predicate=None,
            exclude_predicates=("has_sequence", "has_sequence"),
            limit=100,
        )
```

- [ ] **Step 2: Add failing standard-server query parser test**

Create `test_simple_server.py`:

```python
########## 0. imports ##########
import unittest

from phytoatlas_api.simple_server import neighbor_query_options

########## 1. tests ##########
class NeighborQueryOptionsTest(unittest.TestCase):
    def test_preserves_repeated_exclusion_parameters(self):
        options = neighbor_query_options(
            {
                "direction": ["both"],
                "predicate": ["belongs_to_species"],
                "exclude_predicate": ["has_sequence", "contains_gene"],
                "limit": ["125"],
            }
        )
        self.assertEqual(
            options,
            {
                "direction": "both",
                "predicate": "belongs_to_species",
                "exclude_predicates": ("has_sequence", "contains_gene"),
                "limit": 125,
            },
        )

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run both tests and verify missing adapters**

```bash
cd apps/api
../../.venv/bin/python -m unittest discover -s tests -p 'test_main.py' -v
../../.venv/bin/python -m unittest discover -s tests -p 'test_simple_server.py' -v
```

Expected: FastAPI test fails on the missing argument and standard-server test fails to import `neighbor_query_options`.

- [ ] **Step 4: Implement both HTTP adapters**

Change the FastAPI endpoint signature and forwarding:

```python
def graph_neighbors(
    node_id: str,
    direction: Literal["in", "out", "both"] = Query(default="both"),
    predicate: str | None = Query(default=None),
    exclude_predicate: list[str] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    try:
        result = get_graph_store().get_neighbors(
            node_id,
            direction=direction,
            predicate=predicate,
            exclude_predicates=tuple(exclude_predicate or ()),
            limit=limit,
        )
    except GraphStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result["node"] is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    return result
```

Add this helper to `simple_server.py` and call `self.store.get_neighbors(node_id, **neighbor_query_options(query))`:

```python
def neighbor_query_options(query: dict[str, list[str]]) -> dict[str, object]:
    return {
        "direction": query.get("direction", ["both"])[0],
        "predicate": query.get("predicate", [None])[0],
        "exclude_predicates": tuple(query.get("exclude_predicate", [])),
        "limit": int_query(query, "limit", 50, 500),
    }
```

Update `apps/api/README.md` to document `predicate`, repeatable `exclude_predicate`, and the four metadata fields.

- [ ] **Step 5: Run complete API verification**

```bash
cd apps/api
../../.venv/bin/python -m compileall -q phytoatlas_api
../../.venv/bin/python -m unittest discover -s tests -v
```

Expected: compilation succeeds and all API tests pass with zero failures.

- [ ] **Step 6: Commit the HTTP contract**

```bash
git add apps/api/phytoatlas_api/main.py apps/api/phytoatlas_api/simple_server.py apps/api/tests/test_main.py apps/api/tests/test_simple_server.py apps/api/README.md
git commit -m "Expose graph relationship filters"
```

### Task 3: Add typed graph query and service contracts

**Files:**
- Modify: `apps/web/src/types/graph.ts:1-58`
- Modify: `apps/web/src/services/graph.ts:1-102`
- Create: `apps/web/src/lib/graph-query.ts`
- Modify: `apps/web/tests/services/graph.spec.ts:1-113`
- Create: `apps/web/tests/lib/graph-query.spec.ts`
- Modify: `apps/web/tests/lib/graph-elements.spec.ts:13-43`
- Modify: `apps/web/tests/views/graph.spec.ts:20-26`
- Modify: `apps/web/tests/views/object-routes.spec.ts:23-31`

**Interfaces:**
- Consumes: Task 2 query parameters and response metadata.
- Produces: required `GraphNeighborhood` metadata, repeated exclusion serialization, and stable route query helpers.

- [ ] **Step 1: Add failing service test for repeatable exclusions**

Import `getNeighbors` and add:

```typescript
  it("serializes every excluded predicate", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          node: null,
          nodes: [],
          edges: [],
          total_edges: 0,
          matched_edges: 0,
          predicate_counts: {},
          truncated: false,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await getNeighbors("gene:test", {
      excludePredicates: ["has_sequence", "contains_gene"],
      limit: 100,
    });

    const request = vi.mocked(fetch).mock.calls[0][0].toString();
    const query = new URL(request, "http://localhost").searchParams;
    expect(query.getAll("exclude_predicate")).toEqual(["has_sequence", "contains_gene"]);
    expect(query.get("limit")).toBe("100");
  });

  it("passes cancellation through public object resolution", async () => {
    const node: GraphNode = {
      node_id: "gene:arabidopsis_thaliana:Atha01",
      object_type: "Gene",
      label: "Atha01",
      species_id: "arabidopsis_thaliana",
      source_file: "genes.jsonl",
      properties: { id: "Atha01" },
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ query: "Atha01", count: 1, nodes: [node] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const controller = new AbortController();
    await resolveObject("Gene", "Atha01", "arabidopsis_thaliana", controller.signal);
    expect(fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ signal: controller.signal }),
    );
  });
```

- [ ] **Step 2: Add failing route-query helper tests**

Create `graph-query.spec.ts`:

```typescript
import { describe, expect, it } from "vitest";
import {
  DEFAULT_GRAPH_QUERY,
  graphQueryError,
  readGraphQuery,
  writeGraphQuery,
} from "../../src/lib/graph-query";

describe("graph query contract", () => {
  it("distinguishes a bare route from a supplied route", () => {
    expect(readGraphQuery({})).toBeNull();
    expect(readGraphQuery({ center: "Atha01", species: "arabidopsis_thaliana" })).toEqual({
      center: "Atha01",
      species: "arabidopsis_thaliana",
      view: "core",
      predicate: "",
    });
  });

  it("validates scoped public identifiers", () => {
    expect(graphQueryError({ ...DEFAULT_GRAPH_QUERY, center: "" })).toBe("Enter a gene ID.");
    expect(graphQueryError({ ...DEFAULT_GRAPH_QUERY, species: "" })).toBe(
      "Choose a species before searching by public gene ID.",
    );
    expect(
      graphQueryError({ ...DEFAULT_GRAPH_QUERY, center: "gene:arabidopsis_thaliana:Atha01", species: "" }),
    ).toBe("");
  });

  it("writes only stable supported parameters", () => {
    expect(writeGraphQuery({ ...DEFAULT_GRAPH_QUERY, predicate: "has_location" })).toEqual({
      center: "Atha04G0031690.v1.36",
      species: "arabidopsis_thaliana",
      view: "core",
      predicate: "has_location",
    });
  });
});
```

- [ ] **Step 3: Run tests and verify missing contracts**

```bash
cd apps/web
npm test -- tests/services/graph.spec.ts tests/lib/graph-query.spec.ts
```

Expected: tests fail because `excludePredicates` and `graph-query.ts` do not exist.

- [ ] **Step 4: Implement types, serialization, and route helpers**

In `types/graph.ts`, introduce the shared real-record shape, make `GeneWikiRecord` independent of API metadata, and add exact neighborhood metadata:

```typescript
export interface GraphRecord {
  node: GraphNode;
  edges: GraphEdge[];
  nodes: GraphNode[];
}

export interface GraphNeighborhood extends GraphRecord {
  total_edges: number;
  matched_edges: number;
  predicate_counts: Record<string, number>;
  truncated: boolean;
}

export interface GeneWikiRecord extends GraphRecord {}

export interface NeighborOptions {
  direction?: NeighborDirection;
  predicate?: string;
  excludePredicates?: string[];
  limit?: number;
}

export interface GraphQueryState {
  center: string;
  species: string;
  view: string;
  predicate: string;
}
```

Add `{ total_edges: 0, matched_edges: 0, predicate_counts: {}, truncated: false }` to every existing `GraphNeighborhood` fixture in `graph-elements.spec.ts`, `graph.spec.ts`, and `object-routes.spec.ts` so type checking remains green in this task.

In `getNeighbors()`, append every exclusion before the request:

```typescript
  for (const predicate of options.excludePredicates ?? []) {
    query.append("exclude_predicate", predicate);
  }
```

Add `signal?: AbortSignal` as the fourth `resolveObject()` argument. Pass it to `getNode(candidate, signal)` for full IDs and `searchNodes(params, signal)` for public IDs.

Create `graph-query.ts`:

```typescript
import type { LocationQuery, LocationQueryRaw } from "vue-router";
import type { GraphQueryState } from "../types/graph";

export const DEFAULT_GRAPH_QUERY: GraphQueryState = {
  center: "Atha04G0031690.v1.36",
  species: "arabidopsis_thaliana",
  view: "core",
  predicate: "",
};

const supportedKeys = ["center", "species", "view", "predicate"] as const;

function firstValue(value: LocationQuery[string]): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

export function readGraphQuery(query: LocationQuery): GraphQueryState | null {
  if (!supportedKeys.some((key) => query[key] !== undefined)) return null;
  return {
    center: firstValue(query.center).trim(),
    species: firstValue(query.species).trim(),
    view: firstValue(query.view).trim() || "core",
    predicate: firstValue(query.predicate).trim(),
  };
}

export function graphQueryError(query: GraphQueryState): string {
  if (!query.center) return "Enter a gene ID.";
  if (query.view !== "core") return `Unsupported graph view: ${query.view}.`;
  if (!query.center.includes(":") && !query.species) {
    return "Choose a species before searching by public gene ID.";
  }
  return "";
}

export function writeGraphQuery(query: GraphQueryState): LocationQueryRaw {
  const output: LocationQueryRaw = {
    center: query.center,
    species: query.species,
    view: query.view,
  };
  if (query.predicate) output.predicate = query.predicate;
  return output;
}
```

- [ ] **Step 5: Run focused tests and build type checking**

```bash
cd apps/web
npm test -- tests/services/graph.spec.ts tests/lib/graph-query.spec.ts
npm run build
```

Expected: focused tests and production build pass.

- [ ] **Step 6: Commit the typed contracts**

```bash
git add apps/web/src/types/graph.ts apps/web/src/services/graph.ts apps/web/src/lib/graph-query.ts apps/web/tests/services/graph.spec.ts apps/web/tests/lib/graph-query.spec.ts apps/web/tests/lib/graph-elements.spec.ts apps/web/tests/views/graph.spec.ts apps/web/tests/views/object-routes.spec.ts
git commit -m "Add graph query contracts"
```

### Task 4: Separate real nodes from presentation summaries and centralize graph styles

**Files:**
- Modify: `apps/web/src/types/graph.ts:1-75`
- Modify: `apps/web/src/lib/graph-elements.ts:1-50`
- Create: `apps/web/src/lib/graph-style.ts`
- Modify: `apps/web/src/components/graph/GraphCanvas.vue:1-79`
- Modify: `apps/web/tests/lib/graph-elements.spec.ts:1-51`
- Create: `apps/web/tests/lib/graph-style.spec.ts`

**Interfaces:**
- Consumes: Task 3 `GraphNeighborhood` metadata.
- Produces: `GraphSelection` discriminated union, `selectionById`, a dashed summary item, and hover/selection-only labels.

- [ ] **Step 1: Add failing summary integrity test**

Extend `graph-elements.spec.ts` with metadata on the fixture and add:

```typescript
  it("adds a derived sequence summary without mutating graph truth", () => {
    const originalNodes = [...neighborhood.nodes];
    const elements = toCytoscapeElements(neighborhood, { sequenceCount: 54 });
    const summary = elements.nodes.find((item) => item.data.id === SEQUENCE_SUMMARY_ID);

    expect(summary?.data).toMatchObject({
      label: "Sequences (54)",
      presentationKind: "summary",
      objectType: "SequenceSummary",
    });
    expect(elements.selectionById.get(SEQUENCE_SUMMARY_ID)).toEqual({
      kind: "summary",
      summary: {
        id: SEQUENCE_SUMMARY_ID,
        label: "Sequences (54)",
        predicate: "has_sequence",
        count: 54,
      },
    });
    expect(neighborhood.nodes).toEqual(originalNodes);
    expect(neighborhood.nodes.some((node) => node.node_id === SEQUENCE_SUMMARY_ID)).toBe(false);
  });
```

- [ ] **Step 2: Add failing style-contract test**

Create `graph-style.spec.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { graphStyles } from "../../src/lib/graph-style";

describe("graph style contract", () => {
  it("hides default labels and distinguishes presentation summaries", () => {
    const style = (selector: string) =>
      graphStyles.find((item) => item.selector === selector)?.style as Record<string, unknown>;
    expect(style("node").label).toBe("");
    expect(style("edge").label).toBe("");
    expect(style("node[?isCenter], node:selected, node.hovered").label).toBe("data(label)");
    expect(style("edge:selected, edge.hovered").label).toBe("data(predicate)");
    expect(style('node[presentationKind = "summary"]')["border-style"]).toBe("dashed");
    expect(style('edge[presentationKind = "summary"]')["line-style"]).toBe("dashed");
  });
});
```

- [ ] **Step 3: Run tests and observe missing presentation contracts**

```bash
cd apps/web
npm test -- tests/lib/graph-elements.spec.ts tests/lib/graph-style.spec.ts
```

Expected: tests fail because the summary ID, selection map, and style module do not exist.

- [ ] **Step 4: Implement the discriminated selection model**

Add to `types/graph.ts`:

```typescript
export interface SequenceSummarySelection {
  id: string;
  label: string;
  predicate: "has_sequence";
  count: number;
}

export type GraphSelection =
  | { kind: "node"; node: GraphNode }
  | { kind: "summary"; summary: SequenceSummarySelection };
```

Update `graph-elements.ts` to accept `GraphRecord`, export `SEQUENCE_SUMMARY_ID`, accept `{ sequenceCount?: number }`, store real-node selections as `{ kind: "node", node }`, and add this summary only when the count is positive:

```typescript
export const SEQUENCE_SUMMARY_ID = "presentation:sequence-summary";

const summary = {
  id: SEQUENCE_SUMMARY_ID,
  label: `Sequences (${sequenceCount})`,
  predicate: "has_sequence" as const,
  count: sequenceCount,
};
nodes.push({
  data: {
    id: summary.id,
    label: summary.label,
    objectType: "SequenceSummary",
    presentationKind: "summary",
    isCenter: false,
  },
});
edges.push({
  data: {
    id: `${neighborhood.node.node_id}|has_sequence|${summary.id}|summary`,
    source: neighborhood.node.node_id,
    target: summary.id,
    predicate: "has_sequence",
    presentationKind: "summary",
  },
});
selectionById.set(summary.id, { kind: "summary", summary });
```

- [ ] **Step 5: Extract styles and update canvas events**

Create `graph-style.ts` by moving the existing style array, setting base node and edge labels to `""`, and adding these selectors:

```typescript
import type { StylesheetJson } from "cytoscape";

export const graphStyles: StylesheetJson = [
  { selector: "node", style: { label: "", "background-color": "#71808a", width: 34, height: 34 } },
  { selector: 'node[objectType = "Gene"]', style: { "background-color": "#1769aa" } },
  { selector: 'node[objectType = "Species"]', style: { "background-color": "#3b8c59" } },
  { selector: 'node[objectType = "Dataset"]', style: { "background-color": "#d77a1f" } },
  { selector: 'node[objectType = "SequenceRecord"]', style: { "background-color": "#7b61d1" } },
  { selector: "node[?isCenter]", style: { width: 48, height: 48, "border-width": 4, "border-color": "#0b3d36" } },
  { selector: "node[?isCenter], node:selected, node.hovered", style: { label: "data(label)", "font-size": 10, "text-wrap": "ellipsis", "text-max-width": "110px", "text-valign": "bottom", "text-margin-y": 8 } },
  { selector: 'node[presentationKind = "summary"]', style: { shape: "round-rectangle", "background-color": "#ffffff", "border-color": "#7b61d1", "border-width": 3, "border-style": "dashed", color: "#5c45ad", width: 118, height: 42 } },
  { selector: "node:selected", style: { "border-width": 5, "border-color": "#68a65f" } },
  { selector: "edge", style: { label: "", width: 1.6, "line-color": "#aab8b1", "target-arrow-color": "#aab8b1", "target-arrow-shape": "triangle", "curve-style": "bezier" } },
  { selector: 'edge[presentationKind = "summary"]', style: { "line-style": "dashed", "line-color": "#7b61d1", "target-arrow-color": "#7b61d1" } },
  { selector: "edge:selected, edge.hovered", style: { label: "data(predicate)", "font-size": 8, color: "#627067", "text-background-color": "#ffffff", "text-background-opacity": 0.85, "text-background-padding": "2px" } },
];
```

Make `GraphCanvas` accept `GraphRecord | null`, emit `GraphSelection`, pass `sequenceCount` to the converter, import `graphStyles`, and register mouseover/mouseout handlers that add or remove `hovered` on nodes and edges.

- [ ] **Step 6: Run focused tests and build**

```bash
cd apps/web
npm test -- tests/lib/graph-elements.spec.ts tests/lib/graph-style.spec.ts
npm run build
```

Expected: tests and production build pass.

- [ ] **Step 7: Commit the presentation boundary**

```bash
git add apps/web/src/types/graph.ts apps/web/src/lib/graph-elements.ts apps/web/src/lib/graph-style.ts apps/web/src/components/graph/GraphCanvas.vue apps/web/tests/lib/graph-elements.spec.ts apps/web/tests/lib/graph-style.spec.ts
git commit -m "Add readable graph presentation model"
```

### Task 5: Build the route-driven core graph workbench

**Files:**
- Modify: `apps/web/src/views/GraphView.vue:1-67`
- Modify: `apps/web/src/components/graph/GraphToolbar.vue:1-45`
- Create: `apps/web/src/components/graph/GraphRelationSummary.vue`
- Modify: `apps/web/tests/views/graph.spec.ts:1-67`

**Interfaces:**
- Consumes: Tasks 2-4 API, query, selection, and summary contracts.
- Produces: bare-route example loading, deep-link loading, scoped resolution, URL synchronization, relationship controls, and stale-request protection.

- [ ] **Step 1: Replace the single graph view test with failing route behavior tests**

Use these exact shared fixtures and `mountGraph(path)` helper with `resolveObject`, `getNode`, and `getNeighbors` mocked:

```typescript
const center: GraphNode = {
  node_id: "gene:arabidopsis_thaliana:Atha04G0031690.v1.36",
  object_type: "Gene",
  label: "Atha04G0031690",
  species_id: "arabidopsis_thaliana",
  source_file: "genes.jsonl",
  properties: { id: "Atha04G0031690.v1.36" },
};

function coreNode(nodeId: string, objectType: string, label: string): GraphNode {
  return {
    node_id: nodeId,
    object_type: objectType,
    label,
    species_id: "arabidopsis_thaliana",
    source_file: `${objectType.toLowerCase()}.jsonl`,
    properties: {},
  };
}

const species = coreNode("species:arabidopsis_thaliana", "Species", "Arabidopsis thaliana");
const dataset = coreNode("dataset:pgcp:arabidopsis", "Dataset", "PGCP Arabidopsis");
const location = coreNode("location:Atha04G0031690", "GeneLocation", "Chr4:15006485-15008650");
const structure = coreNode("structure:Atha04G0031690", "GeneStructure", "27 transcripts");

const coreNeighborhood: GraphNeighborhood = {
  node: center,
  nodes: [species, dataset, location, structure],
  edges: [
    { source: center.node_id, predicate: "belongs_to_species", target: species.node_id, species_id: "arabidopsis_thaliana", source_dataset: "dataset:test", evidence: "test", properties: {} },
    { source: dataset.node_id, predicate: "contains_gene", target: center.node_id, species_id: "arabidopsis_thaliana", source_dataset: "dataset:test", evidence: "test", properties: {} },
    { source: center.node_id, predicate: "has_location", target: location.node_id, species_id: "arabidopsis_thaliana", source_dataset: "dataset:test", evidence: "test", properties: {} },
    { source: center.node_id, predicate: "has_structure", target: structure.node_id, species_id: "arabidopsis_thaliana", source_dataset: "dataset:test", evidence: "test", properties: {} },
    { source: center.node_id, predicate: "provided_by_dataset", target: dataset.node_id, species_id: "arabidopsis_thaliana", source_dataset: "dataset:test", evidence: "test", properties: {} },
  ],
  total_edges: 59,
  matched_edges: 5,
  predicate_counts: {
    belongs_to_species: 1,
    contains_gene: 1,
    has_location: 1,
    has_sequence: 54,
    has_structure: 1,
    provided_by_dataset: 1,
  },
  truncated: false,
};

async function mountGraph(path: string, configure: () => void = () => undefined) {
  vi.mocked(resolveObject).mockResolvedValue(center);
  vi.mocked(getNode).mockResolvedValue(center);
  vi.mocked(getNeighbors).mockResolvedValue(coreNeighborhood);
  configure();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/graph", name: "graph", component: GraphView },
      { path: "/genes/:id", name: "gene", component: { template: "<div />" } },
    ],
  });
  await router.push(path);
  const wrapper = mount(GraphView, {
    global: {
      plugins: [router],
      stubs: { GraphCanvas: { template: "<div data-test='graph-canvas' />" } },
    },
  });
  await flushPromises();
  await flushPromises();
  return { router, wrapper };
}
```

Add tests asserting:

```typescript
it("seeds and loads the real example from a bare route", async () => {
  const { router, wrapper } = await mountGraph("/graph");
  expect(router.currentRoute.value.query).toEqual({
    center: "Atha04G0031690.v1.36",
    species: "arabidopsis_thaliana",
    view: "core",
  });
  expect(resolveObject).toHaveBeenCalledWith(
    "Gene",
    "Atha04G0031690.v1.36",
    "arabidopsis_thaliana",
    expect.any(AbortSignal),
  );
  expect(getNeighbors).toHaveBeenCalledWith(
    center.node_id,
    { excludePredicates: ["has_sequence"], limit: 100 },
    expect.any(AbortSignal),
  );
  expect(wrapper.text()).toContain("59 source relationships");
  expect(wrapper.text()).toContain("6 displayed items");
});

it("keeps an invalid supplied route instead of replacing it", async () => {
  const { router, wrapper } = await mountGraph("/graph?center=missing&species=&view=core");
  expect(router.currentRoute.value.query.center).toBe("missing");
  expect(wrapper.text()).toContain("Choose a species before searching by public gene ID.");
  expect(resolveObject).not.toHaveBeenCalled();
});

it("updates the route when a relationship control is selected", async () => {
  const { router, wrapper } = await mountGraph("/graph");
  await wrapper.get('[data-predicate="has_location"]').trigger("click");
  await flushPromises();
  expect(router.currentRoute.value.query.predicate).toBe("has_location");
  expect(getNeighbors).toHaveBeenLastCalledWith(
    center.node_id,
    { predicate: "has_location", limit: 100 },
    expect.any(AbortSignal),
  );
});
```

Add these edge and race tests:

```typescript
it("rejects an empty submitted center without a request", async () => {
  const { wrapper } = await mountGraph("/graph");
  vi.clearAllMocks();
  await wrapper.get('[name="center_query"]').setValue("");
  await wrapper.get("form").trigger("submit");
  expect(wrapper.text()).toContain("Enter a gene ID.");
  expect(resolveObject).not.toHaveBeenCalled();
  expect(getNode).not.toHaveBeenCalled();
  expect(getNeighbors).not.toHaveBeenCalled();
});

it("loads a full node ID without a species scope", async () => {
  const nodeId = encodeURIComponent(center.node_id);
  await mountGraph(`/graph?center=${nodeId}&species=&view=core`);
  expect(getNode).toHaveBeenCalledWith(center.node_id, expect.any(AbortSignal));
  expect(resolveObject).not.toHaveBeenCalled();
});

it("maps service unavailability to stable user copy", async () => {
  const { wrapper } = await mountGraph("/graph", () => {
    vi.mocked(getNeighbors).mockRejectedValue(
      new ApiError(503, "/api/graph/neighbors/gene:test", "private database path"),
    );
  });
  expect(wrapper.text()).toContain("Knowledge graph is temporarily unavailable.");
  expect(wrapper.text()).not.toContain("private database path");
});

it("does not let an older request replace a newer route", async () => {
  let resolveFirst!: (node: GraphNode) => void;
  const first = new Promise<GraphNode>((resolve) => { resolveFirst = resolve; });
  const second = { ...center, node_id: "gene:arabidopsis_thaliana:second", label: "Second" };
  const { router, wrapper } = await mountGraph(
    "/graph?center=first&species=arabidopsis_thaliana&view=core",
    () => {
      vi.mocked(resolveObject)
        .mockReturnValueOnce(first)
        .mockResolvedValueOnce(second);
      vi.mocked(getNeighbors).mockImplementation(async (nodeId) => ({
        ...coreNeighborhood,
        node: nodeId === second.node_id ? second : center,
      }));
    },
  );
  await router.push("/graph?center=second&species=arabidopsis_thaliana&view=core");
  await flushPromises();
  resolveFirst(center);
  await flushPromises();
  expect(wrapper.text()).toContain("Second");
  expect(wrapper.text()).not.toContain("Atha04G0031690");
});
```

- [ ] **Step 2: Run the graph view tests and verify the route behavior is absent**

```bash
cd apps/web
npm test -- tests/views/graph.spec.ts
```

Expected: new tests fail because the current page ignores route queries, silently ignores empty input, and falls back to the first partial result.

- [ ] **Step 3: Implement the relationship summary component**

Create a component with this contract:

```typescript
const props = defineProps<{
  counts: Record<string, number>;
  selectedPredicate: string;
}>();
const emit = defineEmits<{ select: [predicate: string] }>();
const coreCount = computed(() =>
  Object.entries(props.counts)
    .filter(([predicate]) => predicate !== "has_sequence")
    .reduce((total, [, count]) => total + count, 0),
);
```

Render one `Core · <count>` button with `data-predicate=""` and one button per sorted predicate with `data-predicate="<predicate>"`, count text, and `aria-pressed`.

Display predicate labels with `predicate.replaceAll("_", " ")` while retaining the normalized predicate in `data-predicate` and emitted values.

- [ ] **Step 4: Convert the toolbar from placeholder fields to controlled real values**

Wrap the form and relationship summary in one controls component. Keep `centerQuery` and `speciesId` models, remove the free-text predicate input, accept `predicateCounts` and `selectedPredicate`, and emit `selectPredicate` from the summary. Render inline validation with `role="alert"`.

- [ ] **Step 5: Implement route ownership and exact resolution in GraphView**

Use `watch(() => route.fullPath, loadRoute, { immediate: true })`. The load path must:

```typescript
async function loadRoute() {
  const parsed = readGraphQuery(route.query);
  if (parsed === null) {
    await router.replace({ name: "graph", query: writeGraphQuery(DEFAULT_GRAPH_QUERY) });
    return;
  }
  centerQuery.value = parsed.center;
  speciesId.value = parsed.species;
  selectedPredicate.value = parsed.predicate;
  const validation = graphQueryError(parsed);
  if (validation) {
    validationError.value = validation;
    return;
  }
  await loadGraph(parsed);
}
```

Resolve full node IDs with `getNode(center, signal)`; resolve public IDs with `resolveObject("Gene", center, species, signal)`. Do not call the existing `exactNode()` fallback. Select neighbor options exactly as follows:

```typescript
const options = query.predicate && query.predicate !== "has_sequence"
  ? { predicate: query.predicate, limit: 100 }
  : { excludePredicates: ["has_sequence"], limit: 100 };
```

Abort the prior controller before every load, map status 503 to the stable user-facing message, and commit state only when the controller is still current.

Check `controller === requestController` immediately after center resolution and again after neighborhood retrieval so a superseded resolution never starts another API request or commits stale state.

On form submit, validate controlled values, then push `writeGraphQuery()`. On relationship selection, push the same route with the selected predicate. If the resulting full path is unchanged, call `loadRoute()` to support Retry.

Pass `predicate_counts.has_sequence ?? 0` to `GraphCanvas`, render the count `coreNeighborhood.nodes.length + 1 + (sequenceCount > 0 ? 1 : 0)` as displayed items, and update `NodeInspector` only for `{ kind: "node" }` selections. Task 6 adds the explicit summary-selection action.

Preserve the responsive contract: toolbar controls stack below 600px, and the inspector moves below the canvas below 860px. Keep validation and relationship controls as normal labeled DOM elements.

- [ ] **Step 6: Run focused graph tests and complete Web regression**

```bash
cd apps/web
npm test -- tests/views/graph.spec.ts tests/lib/graph-query.spec.ts tests/lib/graph-elements.spec.ts
npm test
npm run build
```

Expected: focused tests, full Web suite, and build pass with zero failures.

- [ ] **Step 7: Commit the core workbench**

```bash
git add apps/web/src/views/GraphView.vue apps/web/src/components/graph/GraphToolbar.vue apps/web/src/components/graph/GraphRelationSummary.vue apps/web/tests/views/graph.spec.ts
git commit -m "Build route-driven graph workbench"
```

### Task 6: Add the on-demand sequence drawer and real sequence modes

**Files:**
- Create: `apps/web/src/components/graph/SequenceDrawer.vue`
- Create: `apps/web/src/lib/graph-presentation.ts`
- Create: `apps/web/tests/components/sequence-drawer.spec.ts`
- Create: `apps/web/tests/lib/graph-presentation.spec.ts`
- Modify: `apps/web/src/views/GraphView.vue`
- Modify: `apps/web/tests/views/graph.spec.ts`

**Interfaces:**
- Consumes: `getNeighbors(center, { predicate: "has_sequence", limit: 100 })` and `groupSequenceRecords()`.
- Produces: `SequenceType = "CDS" | "PROTEIN"`, grouped real links, truncation copy, and filtered real-node graph records.

- [ ] **Step 1: Add failing pure filtering test**

Create `graph-presentation.spec.ts` with this complete fixture and assertion:

```typescript
import { describe, expect, it } from "vitest";
import { filterSequenceNeighborhood } from "../../src/lib/graph-presentation";
import type { GraphNeighborhood, GraphNode } from "../../src/types/graph";

const center: GraphNode = {
  node_id: "gene:test",
  object_type: "Gene",
  label: "Gene test",
  species_id: "arabidopsis_thaliana",
  source_file: "genes.jsonl",
  properties: {},
};
const cds: GraphNode = {
  ...center,
  node_id: "seq:cds:1",
  object_type: "SequenceRecord",
  properties: { sequence_type: "CDS" },
};
const protein: GraphNode = {
  ...center,
  node_id: "seq:protein:1",
  object_type: "SequenceRecord",
  properties: { sequence_type: "PROTEIN" },
};
const sequenceNeighborhood: GraphNeighborhood = {
  node: center,
  nodes: [cds, protein],
  edges: [
    { source: center.node_id, predicate: "has_sequence", target: cds.node_id, species_id: "arabidopsis_thaliana", source_dataset: "dataset:test", evidence: "test", properties: {} },
    { source: center.node_id, predicate: "has_sequence", target: protein.node_id, species_id: "arabidopsis_thaliana", source_dataset: "dataset:test", evidence: "test", properties: {} },
  ],
  total_edges: 2,
  matched_edges: 2,
  predicate_counts: { has_sequence: 2 },
  truncated: false,
};

it("keeps only real nodes and edges for the requested sequence type", () => {
  const filtered = filterSequenceNeighborhood(sequenceNeighborhood, "CDS");
  expect(filtered.nodes.map((node) => node.node_id)).toEqual(["seq:cds:1"]);
  expect(filtered.edges.map((edge) => edge.target)).toEqual(["seq:cds:1"]);
  expect(filtered.node).toEqual(sequenceNeighborhood.node);
  expect(sequenceNeighborhood.nodes).toEqual([cds, protein]);
});
```

- [ ] **Step 2: Add failing drawer interaction tests**

Create `sequence-drawer.spec.ts` with these imports and mock:

```typescript
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, it, vi } from "vitest";
import SequenceDrawer from "../../src/components/graph/SequenceDrawer.vue";
import { getNeighbors } from "../../src/services/graph";
import type { GraphNeighborhood, GraphNode } from "../../src/types/graph";

vi.mock("../../src/services/graph", () => ({ getNeighbors: vi.fn() }));
afterEach(() => vi.clearAllMocks());
```

Create the 54-node response with this helper, mount `SequenceDrawer` with `open=true` and `RouterLink` stubbed, and assert:

```typescript
const center: GraphNode = {
  node_id: "gene:arabidopsis_thaliana:Atha04G0031690.v1.36",
  object_type: "Gene",
  label: "Atha04G0031690",
  species_id: "arabidopsis_thaliana",
  source_file: "genes.jsonl",
  properties: { id: "Atha04G0031690.v1.36" },
};

function sequenceNode(index: number, sequenceType: "CDS" | "PROTEIN"): GraphNode {
  const nodeId = `seq:${sequenceType.toLowerCase()}:${index}`;
  return {
    node_id: nodeId,
    object_type: "SequenceRecord",
    label: `${sequenceType}-${index}`,
    species_id: "arabidopsis_thaliana",
    source_file: "sequence_records.jsonl",
    properties: { id: `${sequenceType}-${index}`, sequence_type: sequenceType, length: 100 + index },
  };
}

const sequenceNodes = [
  ...Array.from({ length: 27 }, (_, index) => sequenceNode(index + 1, "CDS")),
  ...Array.from({ length: 27 }, (_, index) => sequenceNode(index + 1, "PROTEIN")),
];
const sequenceNeighborhood: GraphNeighborhood = {
  node: center,
  nodes: sequenceNodes,
  edges: sequenceNodes.map((node) => ({
    source: center.node_id,
    predicate: "has_sequence",
    target: node.node_id,
    species_id: "arabidopsis_thaliana",
    source_dataset: "dataset:test",
    evidence: "test",
    properties: {},
  })),
  total_edges: 59,
  matched_edges: 54,
  predicate_counts: { has_sequence: 54 },
  truncated: false,
};

vi.mocked(getNeighbors).mockResolvedValue(sequenceNeighborhood);
const wrapper = mount(SequenceDrawer, {
  props: { open: true, centerNodeId: center.node_id, expectedCount: 54 },
  global: { stubs: { RouterLink: true } },
});
await flushPromises();

expect(getNeighbors).toHaveBeenCalledWith(
  center.node_id,
  { predicate: "has_sequence", limit: 100 },
  expect.any(AbortSignal),
);
expect(wrapper.text()).toContain("CDS (27)");
expect(wrapper.text()).toContain("Protein (27)");
await wrapper.get('[data-sequence-type="CDS"]').trigger("click");
expect(wrapper.emitted("showType")?.[0]).toEqual(["CDS", sequenceNeighborhood]);
```

Add this second test using the same helper:

```typescript
it("reports explicit sequence truncation", async () => {
  const nodes = Array.from({ length: 100 }, (_, index) => sequenceNode(index + 1, "CDS"));
  vi.mocked(getNeighbors).mockResolvedValue({
    node: center,
    nodes,
    edges: nodes.map((node) => ({
      source: center.node_id,
      predicate: "has_sequence",
      target: node.node_id,
      species_id: "arabidopsis_thaliana",
      source_dataset: "dataset:test",
      evidence: "test",
      properties: {},
    })),
    total_edges: 155,
    matched_edges: 150,
    predicate_counts: { has_sequence: 150, has_location: 5 },
    truncated: true,
  });
  const wrapper = mount(SequenceDrawer, {
    props: { open: true, centerNodeId: center.node_id, expectedCount: 150 },
    global: { stubs: { RouterLink: true } },
  });
  await flushPromises();
  expect(wrapper.text()).toContain("Showing 100 of 150 sequence relationships.");
});
```

- [ ] **Step 3: Run tests and observe missing modules**

```bash
cd apps/web
npm test -- tests/lib/graph-presentation.spec.ts tests/components/sequence-drawer.spec.ts
```

Expected: imports fail because the helper and drawer do not exist.

- [ ] **Step 4: Implement the pure real-node filter**

Create `graph-presentation.ts`:

```typescript
import type { GraphNeighborhood, GraphNode, GraphRecord } from "../types/graph";

export type SequenceType = "CDS" | "PROTEIN";

function nodeSequenceType(node: GraphNode): string {
  const value = node.properties.sequence_type;
  return typeof value === "string" ? value.toUpperCase() : "";
}

export function filterSequenceNeighborhood(
  neighborhood: GraphNeighborhood,
  sequenceType: SequenceType,
): GraphRecord {
  const nodes = neighborhood.nodes.filter((node) => nodeSequenceType(node) === sequenceType);
  const nodeIds = new Set(nodes.map((node) => node.node_id));
  const edges = neighborhood.edges.filter(
    (edge) => nodeIds.has(edge.source) || nodeIds.has(edge.target),
  );
  return {
    node: neighborhood.node,
    nodes,
    edges,
  };
}
```

- [ ] **Step 5: Implement SequenceDrawer with lazy loading and real links**

The component accepts `open`, `centerNodeId`, and `expectedCount`; emits `close` and `showType`. Watch `open` and `centerNodeId`, abort the prior request, and call `getNeighbors` only when open with a node ID. Derive counts with `groupSequenceRecords(record.nodes)`, render CDS and Protein cards with `data-sequence-type`, render `GeneSequencePanel` for real links, and show stable loading, error, empty, and truncation states.

Use this exact truncation computation:

```typescript
const returnedEdges = computed(() => record.value?.edges.length ?? 0);
const truncationMessage = computed(() =>
  record.value?.truncated
    ? `Showing ${returnedEdges.value} of ${record.value.matched_edges} sequence relationships.`
    : "",
);
```

- [ ] **Step 6: Integrate sequence selection into GraphView**

Handle graph selections exactly as follows so the derived summary remains URL-addressable:

```typescript
function handleSelection(selection: GraphSelection) {
  if (selection.kind === "node") {
    selectedNode.value = selection.node;
    return;
  }
  void selectPredicate("has_sequence");
}
```

When route predicate is `has_sequence`, open the drawer after the core graph loads. On `showType(type, record)`, set a sequence mode containing `filterSequenceNeighborhood(record, type)`. Pass that real record to `GraphCanvas` with `sequenceCount=0`, display `Viewing 27 CDS records` or `Viewing 27 Protein records`, and provide a `Back to core` button that restores the core neighborhood without changing graph truth.

Extend `graph.spec.ts` to emit the summary selection from the canvas stub and assert the route receives `predicate=has_sequence`. Emit `showType` from the drawer stub and assert the canvas receives only the requested type. Assert that returning to core restores the five real nodes plus summary presentation.

- [ ] **Step 7: Run focused, full, and build verification**

```bash
cd apps/web
npm test -- tests/components/sequence-drawer.spec.ts tests/lib/graph-presentation.spec.ts tests/views/graph.spec.ts
npm test
npm run build
```

Expected: all focused tests, the full Web suite, and build pass.

- [ ] **Step 8: Commit sequence exploration**

```bash
git add apps/web/src/components/graph/SequenceDrawer.vue apps/web/src/lib/graph-presentation.ts apps/web/src/views/GraphView.vue apps/web/tests/components/sequence-drawer.spec.ts apps/web/tests/lib/graph-presentation.spec.ts apps/web/tests/views/graph.spec.ts
git commit -m "Add on-demand sequence graph exploration"
```

### Task 7: Add the Gene Wiki deep link

**Files:**
- Modify: `apps/web/src/components/objects/ObjectPageLayout.vue:1-30`
- Modify: `apps/web/src/views/GeneView.vue:1-100`
- Modify: `apps/web/tests/views/gene.spec.ts:150-204`

**Interfaces:**
- Consumes: stable graph URL contract from Task 3.
- Produces: a visible `View in graph` action using public versioned gene ID, species, and `view=core`.

- [ ] **Step 1: Add a failing deep-link assertion to the rich-gene test**

Add the graph route to `mountGene()` and assert:

```typescript
const graphLink = wrapper.get('[data-test="view-in-graph"]');
const graphUrl = new URL(graphLink.attributes("href"), "http://localhost");
expect(graphUrl.pathname).toBe("/graph");
expect(Object.fromEntries(graphUrl.searchParams)).toEqual({
  center: "Atha04G0031690.v1.36",
  species: "arabidopsis_thaliana",
  view: "core",
});
```

- [ ] **Step 2: Run the Gene view test and verify the link is absent**

```bash
cd apps/web
npm test -- tests/views/gene.spec.ts
```

Expected: test fails because `[data-test="view-in-graph"]` does not exist.

- [ ] **Step 3: Add an actions slot to ObjectPageLayout**

Render the slot after the subtitle:

```vue
<div v-if="$slots.actions" class="object-hero__actions"><slot name="actions" /></div>
```

Style it with a top margin and wrapping flex layout; keep existing page layout unchanged when no action slot is supplied.

- [ ] **Step 4: Add the exact graph route to GeneView**

Import `RouterLink` and add:

```typescript
const graphRoute = computed(() => {
  if (!node.value) return null;
  const propertyId = node.value.properties.id;
  const center = typeof propertyId === "string" ? propertyId : node.value.node_id;
  return {
    name: "graph",
    query: {
      center,
      species: node.value.species_id || undefined,
      view: "core",
    },
  };
});
```

Provide the action slot:

```vue
<template #actions>
  <RouterLink
    v-if="graphRoute"
    data-test="view-in-graph"
    class="graph-link"
    :to="graphRoute"
  >View in graph</RouterLink>
</template>
```

- [ ] **Step 5: Run Gene, graph, full Web, and build tests**

```bash
cd apps/web
npm test -- tests/views/gene.spec.ts tests/views/graph.spec.ts
npm test
npm run build
```

Expected: focused tests, full suite, and build pass.

- [ ] **Step 6: Commit the Wiki deep link**

```bash
git add apps/web/src/components/objects/ObjectPageLayout.vue apps/web/src/views/GeneView.vue apps/web/tests/views/gene.spec.ts
git commit -m "Link Gene Wiki to knowledge graph"
```

### Task 8: Run full acceptance and document the verified workflow

**Files:**
- Create: `docs/testing/knowledge-graph-browser-smoke.md`
- Modify: `docs/architecture/arabidopsis-mvp-acceptance.md`

**Interfaces:**
- Consumes: completed API and Web behavior from Tasks 1-7.
- Produces: reproducible live-service commands and a recorded acceptance result.

- [ ] **Step 1: Run all automated quality gates from the worktree**

```bash
WORKTREE_ROOT="$(git rev-parse --show-toplevel)"
cd "$WORKTREE_ROOT"
.venv/bin/python -m unittest discover -s tests -v
cd apps/api
../../.venv/bin/python -m compileall -q phytoatlas_api
../../.venv/bin/python -m unittest discover -s tests -v
cd ../web
npm test
npm run build
git diff --check
```

Expected: core Python, API, Web, and production build all pass; `git diff --check` prints nothing.

- [ ] **Step 2: Start isolated preview services on alternate ports**

From the worktree root:

```bash
PHYTOATLAS_API_PORT=8002 \
PHYTOATLAS_WEB_PORT=4323 \
VITE_API_BASE_URL=http://127.0.0.1:8002 \
./scripts/services/phytoatlas.sh start
./scripts/services/phytoatlas.sh status
```

Expected: API reports port 8002 and Web reports port 4323. Create a local SSH tunnel for 8002 and 4323 without changing the existing 8000/4322 preview.

Run on the local workstation:

```powershell
ssh -N -L 4323:127.0.0.1:4323 -L 8002:127.0.0.1:8002 1206-cpu
```

- [ ] **Step 3: Perform live API assertions**

```bash
curl -fsS 'http://127.0.0.1:8002/api/graph/neighbors/gene%3Aarabidopsis_thaliana%3AAtha04G0031690.v1.36?exclude_predicate=has_sequence&limit=100'
curl -fsS 'http://127.0.0.1:8002/api/graph/neighbors/gene%3Aarabidopsis_thaliana%3AAtha04G0031690.v1.36?predicate=has_sequence&limit=100'
```

Expected first response: `total_edges=59`, `matched_edges=5`, `predicate_counts.has_sequence=54`, five real returned edges, and `truncated=false`.

Expected second response: `matched_edges=54`, 54 real sequence edges, and `truncated=false`.

- [ ] **Step 4: Perform visible browser acceptance**

Use the real browser at `http://localhost:4323/graph` and verify:

1. Bare route becomes the stable example URL and loads automatically.
2. Page reports 59 source relationships and six default presentation items.
3. Core canvas contains Gene, Species, Dataset, Location, Structure, and one dashed Sequence summary.
4. Default labels do not overlap; non-selected labels appear only on hover or selection.
5. Sequence drawer reports CDS 27 and Protein 27 with working real links.
6. Showing CDS renders 27 CDS nodes and no Protein nodes; showing Protein does the inverse.
7. Back to core restores the five real nodes and one summary.
8. Empty, missing-species, not-found, and Retry states match the design.
9. Browser back and forward restore graph state.
10. The rich Gene Wiki `View in graph` link opens the exact gene graph.
11. Browser console has no errors and page text exposes no internal path.

- [ ] **Step 5: Write the reproducible browser smoke document**

Create `docs/testing/knowledge-graph-browser-smoke.md` with the alternate-port start commands from Step 2, the two acceptance URLs, the eleven checks from Step 4, and cleanup:

```bash
./scripts/services/phytoatlas.sh stop
```

State explicitly that sequence summary nodes are presentation-derived and are not persisted knowledge objects.

- [ ] **Step 6: Record the successful acceptance in the architecture gate**

Append this section only after every prior check passes:

```markdown
## 8. Knowledge Graph usability acceptance

Acceptance completed on 2026-07-17 against graph snapshot `pgcp_v1/phytoatlas_pgcp_v1.sqlite`.

| Check | Result |
|---|---|
| Core Python suite | PASS |
| FastAPI suite | PASS |
| Vue suite | PASS |
| Production frontend build | PASS |
| Core graph API | PASS: 59 total, 5 core, 54 sequence relations |
| Default graph presentation | PASS: 5 real nodes and 1 derived summary |
| Sequence drawer | PASS: 27 CDS and 27 Protein records |
| Gene Wiki deep link | PASS |
| Browser console and path safety | PASS |

The derived sequence summary is a presentation element only. It is not stored as a graph node or interpreted as a biological relation.
```

- [ ] **Step 7: Commit acceptance evidence**

```bash
git add docs/testing/knowledge-graph-browser-smoke.md docs/architecture/arabidopsis-mvp-acceptance.md
git commit -m "Document graph usability acceptance"
```

- [ ] **Step 8: Run final branch verification and request review**

```bash
git status --short
git log --oneline --decorate -8
git diff --check HEAD~8..HEAD
```

Expected: clean worktree, eight intentional task commits, and no whitespace errors. Then invoke `superpowers:requesting-code-review`; address verified findings, rerun affected tests, and invoke `superpowers:verification-before-completion` before claiming completion.
