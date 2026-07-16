# PhytoAtlas Vue Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Astro frontend with an API-backed Vue 3 application, rename the active project to PhytoAtlas without compatibility aliases, and preserve existing biological identifiers and verified graph data.

**Architecture:** Build a Vue single-page application in `apps/web` with typed API services, route-focused views, reusable Wiki object components, and Cytoscape.js graph rendering. Keep FastAPI independent, rename Python packages in controlled stages, then migrate server data, repository, and project directories only after code verification.

**Tech Stack:** Vue 3.5+, Vite, TypeScript, Vue Router, Pinia, Cytoscape.js, Vitest, Vue Test Utils, FastAPI, Python 3.12, unittest, SQLite offline graph snapshot, Cloudflare static hosting.

## Global Constraints

- Product display name is exactly `PhytoAtlas`.
- Frontend package is `phytoatlas-web`.
- Backend package is `phytoatlas_api`; shared package is `phytoatlas`.
- Backend environment variables use `PHYTOATLAS_`; frontend API URL uses `VITE_API_BASE_URL`.
- Remove Astro configuration, dependencies, pages, generated static API fallback, and `.astro` files.
- Do not preserve old package imports, environment variables, service names, or display-name aliases.
- Preserve biological identifiers such as `gene:`, `species:`, `dataset:`, and `seq:`.
- Frontend reads only HTTP APIs and never reads raw, normalized, or generated JSON data directories.
- Missing permanent object fields render `Not available`; permanent sections remain visible.
- Planned Literature and Tools routes must not fabricate data or executable behavior.
- Code comments are concise English only; key script stages use numbered long `#` headings.
- Concurrent write tasks use separate Git worktrees and must not edit the same files.

---

## File Map

### Vue application

- Create: `apps/web/index.html`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/src/main.ts`
- Create: `apps/web/src/App.vue`
- Create: `apps/web/src/router/index.ts`
- Create: `apps/web/src/types/graph.ts`
- Create: `apps/web/src/services/http.ts`
- Create: `apps/web/src/services/graph.ts`
- Create: `apps/web/src/stores/search.ts`
- Create: `apps/web/src/components/**`
- Create: `apps/web/src/views/**`
- Create: `apps/web/src/styles/tokens.css`
- Create: `apps/web/src/styles/base.css`
- Create: `apps/web/src/styles/components.css`
- Create: `apps/web/tests/**`
- Delete: `apps/web/astro.config.mjs`
- Delete: `apps/web/src/**/*.astro`
- Delete: `apps/web/src/lib/api-data.ts`
- Delete: `apps/web/public/data/api/**`

### Python services and libraries

- Move: `apps/api/plantgenewiki_api` to `apps/api/phytoatlas_api`
- Move: `src/plantgenewiki` to `src/phytoatlas`
- Delete: legacy service script under `scripts/services`
- Create: `scripts/services/phytoatlas.sh`
- Modify: Python imports, environment variables, default paths, tests, schemas, examples, and documentation.

### Retired static publishing

- Delete: `scripts/build/build_web_data.py`
- Delete: `tests/build/test_build_web_data.py`
- Delete: `tests/web/test_static_pages.py`

---

### Task 1: Replace the Astro shell with a tested Vue foundation

**Files:**
- Modify: `apps/web/package.json`
- Regenerate: `apps/web/package-lock.json`
- Create: `apps/web/index.html`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/tsconfig.app.json`
- Create: `apps/web/tsconfig.node.json`
- Modify: `apps/web/tsconfig.json`
- Create: `apps/web/src/env.d.ts`
- Create: `apps/web/src/main.ts`
- Create: `apps/web/src/App.vue`
- Create: `apps/web/src/router/index.ts`
- Create: `apps/web/src/stores/search.ts`
- Create: `apps/web/src/views/PlanningView.vue`
- Create: `apps/web/src/views/NotFoundView.vue`
- Create: `apps/web/src/styles/tokens.css`
- Create: `apps/web/src/styles/base.css`
- Create: `apps/web/src/styles/components.css`
- Create: `apps/web/tests/setup.ts`
- Create: `apps/web/tests/router.spec.ts`
- Delete: `apps/web/astro.config.mjs`
- Delete: `apps/web/src/layouts/BaseLayout.astro`
- Delete: `apps/web/src/pages/**/*.astro`
- Delete: `apps/web/src/lib/api-data.ts`

**Interfaces:**
- Produces: `router`, `useSearchStore`, and route names consumed by all later frontend tasks.
- Routes: `home`, `search`, `gene`, `species`, `graph`, `dataset`, `sequence-record`, `literature`, `tools`, and `not-found`.

- [ ] **Step 1: Write the failing router contract**

```ts
import { describe, expect, it } from "vitest";
import { routes } from "../src/router";

describe("router contract", () => {
  it("registers all PhytoAtlas routes", () => {
    expect(routes.map((route) => route.name)).toEqual([
      "home",
      "search",
      "gene",
      "species",
      "graph",
      "dataset",
      "sequence-record",
      "literature",
      "tools",
      "not-found",
    ]);
  });
});
```

- [ ] **Step 2: Replace the package definition**

Use:

```json
{
  "name": "phytoatlas-web",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 4322",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview --host 0.0.0.0 --port 4322",
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

Install and lock current compatible releases:

```bash
cd apps/web
npm install vue vue-router pinia cytoscape
npm install -D vite @vitejs/plugin-vue typescript vue-tsc vitest @vue/test-utils jsdom
```

- [ ] **Step 3: Create the minimal Vue entry**

```ts
import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import { router } from "./router";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";

createApp(App).use(createPinia()).use(router).mount("#app");
```

- [ ] **Step 4: Create explicit route records**

Use `createWebHistory()` and lazy imports. Export both `routes` and `router`. Temporary unresolved pages use `PlanningView`; do not reference Astro output.

- [ ] **Step 5: Run the focused test and build**

```bash
npm test -- router.spec.ts
npm run build
```

Expected: router test passes and `dist/index.html` is produced without Astro packages.

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "Replace Astro with Vue application shell"
```

### Task 2: Add typed API services and response contracts

**Files:**
- Create: `apps/web/src/types/graph.ts`
- Create: `apps/web/src/services/http.ts`
- Create: `apps/web/src/services/graph.ts`
- Create: `apps/web/tests/services/graph.spec.ts`
- Create: `apps/web/.env.example`

**Interfaces:**
- Produces:
  - `apiRequest<T>(path: string, init?: RequestInit): Promise<T>`
  - `searchNodes(params: GraphSearchParams): Promise<GraphSearchResponse>`
  - `getNode(nodeId: string): Promise<GraphNode>`
  - `getNeighbors(nodeId: string, options?: NeighborOptions): Promise<GraphNeighborhood>`
  - `getGraphSummary(): Promise<GraphSummary>`
  - `listSpeciesGenes(speciesId: string, limit?: number, offset?: number): Promise<SpeciesGenePage>`
  - `resolveObject(objectType: string, publicId: string): Promise<GraphNode>`

- [ ] **Step 1: Write failing fetch tests**

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { searchNodes } from "../../src/services/graph";

afterEach(() => vi.restoreAllMocks());

describe("graph service", () => {
  it("sends graph search filters to FastAPI", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ query: "Atha", count: 0, nodes: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await searchNodes({ q: "Atha", objectType: "Gene", speciesId: "arabidopsis_thaliana", limit: 25 });
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("object_type=Gene"),
      expect.objectContaining({ headers: expect.objectContaining({ Accept: "application/json" }) }),
    );
  });
});
```

- [ ] **Step 2: Implement the HTTP client**

Read `import.meta.env.VITE_API_BASE_URL`, remove a trailing slash, and throw an `ApiError` containing `status`, `path`, and response detail. Do not return static sample data.

- [ ] **Step 3: Define graph types**

Define `GraphNode`, `GraphEdge`, `GraphSearchResponse`, `GraphNeighborhood`, `GraphSummary`, and `SpeciesGenePage` using the current FastAPI response field names.

- [ ] **Step 4: Implement object resolution**

`resolveObject()` first accepts a full node ID; otherwise it calls graph search with one object type and returns the first exact label or properties `id` match. Throw a typed not-found error when no node matches.

- [ ] **Step 5: Verify**

```bash
npm test -- tests/services/graph.spec.ts
npm run build
```

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/types apps/web/src/services apps/web/tests/services apps/web/.env.example
git commit -m "Add typed PhytoAtlas graph API client"
```

### Task 3: Build the botanical application shell and search-first homepage

**Files:**
- Create: `apps/web/src/components/AppHeader.vue`
- Create: `apps/web/src/components/AppFooter.vue`
- Create: `apps/web/src/components/GlobalSearch.vue`
- Create: `apps/web/src/components/states/LoadingState.vue`
- Create: `apps/web/src/components/states/EmptyState.vue`
- Create: `apps/web/src/components/states/ErrorState.vue`
- Create: `apps/web/src/components/states/PlanningState.vue`
- Create: `apps/web/src/views/HomeView.vue`
- Modify: `apps/web/src/styles/tokens.css`
- Modify: `apps/web/src/styles/base.css`
- Modify: `apps/web/src/styles/components.css`
- Create: `apps/web/tests/components/global-search.spec.ts`
- Create: `apps/web/tests/views/home.spec.ts`

**Interfaces:**
- `GlobalSearch` emits `submit(query: string)` and never submits blank input.
- `AppHeader` hides its compact search on route `home`.
- `HomeView` loads `getGraphSummary()` and routes successful searches to `search`.

- [ ] **Step 1: Write failing interaction tests**

```ts
it("does not navigate for blank search", async () => {
  const wrapper = mount(GlobalSearch);
  await wrapper.get("form").trigger("submit");
  expect(wrapper.emitted("submit")).toBeUndefined();
});

it("emits trimmed search text", async () => {
  const wrapper = mount(GlobalSearch);
  await wrapper.get("input").setValue("  Atha01G0000010  ");
  await wrapper.get("form").trigger("submit");
  expect(wrapper.emitted("submit")).toEqual([["Atha01G0000010"]]);
});
```

- [ ] **Step 2: Implement the botanical design tokens**

Use semantic variables for deep blue-green text, botanical green actions, pale green-gray backgrounds, white surfaces, borders, status colors, spacing, and responsive breakpoints.

- [ ] **Step 3: Implement the shared shell**

The header contains `PhytoAtlas`, `Explore`, `Knowledge Graph`, `Literature`, and `Tools`. The homepage has one unified hero search, graph summary metrics, knowledge-object navigation, graph promotion, and analysis planning card.

- [ ] **Step 4: Verify**

```bash
npm test -- tests/components/global-search.spec.ts tests/views/home.spec.ts
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components apps/web/src/views/HomeView.vue apps/web/src/styles apps/web/tests
git commit -m "Build PhytoAtlas search-first homepage"
```

### Task 4: Implement unified search with supported facets

**Files:**
- Create: `apps/web/src/components/search/SearchFilters.vue`
- Create: `apps/web/src/components/search/SearchResultCard.vue`
- Create: `apps/web/src/views/SearchView.vue`
- Create: `apps/web/src/composables/useGraphSearch.ts`
- Create: `apps/web/tests/views/search.spec.ts`

**Interfaces:**
- Query parameters: `q`, `object_type`, and `species_id`.
- First release facets: object type and species only, because those are supported by the current API.
- Search results link Gene, Species, Dataset, and SequenceRecord nodes to their object routes.

- [ ] **Step 1: Write failing route-state tests**

```ts
it("loads filters from route query", async () => {
  const router = createTestRouter("/search?q=Atha&object_type=Gene&species_id=arabidopsis_thaliana");
  const wrapper = mount(SearchView, { global: { plugins: [router] } });
  await router.isReady();
  expect(wrapper.get('[name="q"]').element.value).toBe("Atha");
  expect(wrapper.get('[name="object_type"]').element.value).toBe("Gene");
});
```

- [ ] **Step 2: Implement `useGraphSearch`**

Keep `loading`, `error`, `nodes`, and current filters. Abort the previous request when filters change, retain filters on errors, and call `searchNodes()` only for non-empty queries.

- [ ] **Step 3: Implement the result list**

Render one ordered list with a left faceted filter panel. Do not display unsupported evidence-count filters. Distinguish no result from request error.

- [ ] **Step 4: Verify**

```bash
npm test -- tests/views/search.spec.ts
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/search apps/web/src/views/SearchView.vue apps/web/src/composables apps/web/tests/views/search.spec.ts
git commit -m "Add faceted graph search interface"
```

### Task 5: Build continuous Wiki object infrastructure and Gene page

**Files:**
- Create: `apps/web/src/components/objects/ObjectPageLayout.vue`
- Create: `apps/web/src/components/objects/ObjectSectionNav.vue`
- Create: `apps/web/src/components/objects/KnowledgeSection.vue`
- Create: `apps/web/src/components/objects/EvidencePanel.vue`
- Create: `apps/web/src/components/objects/NotAvailable.vue`
- Create: `apps/web/src/composables/useObjectRecord.ts`
- Create: `apps/web/src/views/GeneView.vue`
- Create: `apps/web/tests/components/object-section-nav.spec.ts`
- Create: `apps/web/tests/views/gene.spec.ts`

**Interfaces:**
- `useObjectRecord(objectType, publicId)` returns `node`, `neighborhood`, `loading`, `error`, and `reload`.
- Permanent Gene sections: Overview, Identifiers, Location, Structure, Function, Sequences, Homology, Evidence, and Publications.
- Section navigation uses anchors and `IntersectionObserver`.

- [ ] **Step 1: Write failing permanent-section tests**

```ts
it("keeps permanent sections when values are absent", async () => {
  mockNeighborhood({ node: geneNode({ properties: {} }), nodes: [], edges: [] });
  const wrapper = mountGeneView();
  await flushPromises();
  for (const heading of ["Overview", "Identifiers", "Location", "Structure", "Function", "Sequences", "Homology", "Evidence", "Publications"]) {
    expect(wrapper.text()).toContain(heading);
  }
  expect(wrapper.text()).toContain("Not available");
});
```

- [ ] **Step 2: Implement scroll-aware section navigation**

Use `IntersectionObserver` to set one active section. Clicking a navigation item updates the URL hash and scrolls to the section.

- [ ] **Step 3: Implement Gene mapping**

Use node properties and neighborhood edges. Keep asserted, inferred, and unavailable relationships visibly distinct. Link related nodes through route helpers; do not invent homology from vector similarity.

- [ ] **Step 4: Verify**

```bash
npm test -- tests/components/object-section-nav.spec.ts tests/views/gene.spec.ts
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/objects apps/web/src/composables/useObjectRecord.ts apps/web/src/views/GeneView.vue apps/web/tests
git commit -m "Build continuous Wiki gene page"
```

### Task 6: Add Species, Dataset, SequenceRecord, and honest planning routes

**Files:**
- Create: `apps/web/src/views/SpeciesView.vue`
- Create: `apps/web/src/views/DatasetView.vue`
- Create: `apps/web/src/views/SequenceRecordView.vue`
- Create: `apps/web/src/views/LiteratureView.vue`
- Create: `apps/web/src/views/ToolsView.vue`
- Modify: `apps/web/src/router/index.ts`
- Create: `apps/web/tests/views/object-routes.spec.ts`

**Interfaces:**
- Species page loads `species:{id}` and `listSpeciesGenes(id)`.
- Dataset and SequenceRecord pages use `resolveObject()`.
- Literature and Tools use `PlanningState` with scope text and no fake actions.

- [ ] **Step 1: Write failing route rendering tests**

Verify each route renders the correct object type and that planning routes contain `Planned module` without enabled execution buttons.

- [ ] **Step 2: Implement permanent object sections**

Species: Overview, Taxonomy, Genome Versions, Genes, Datasets, Related Species, Evidence, Publications.

Dataset: Overview, Identifiers, Source, Version, Coverage, Provenance, Related Objects.

SequenceRecord: Overview, Identifiers, Type, Length, Checksum, Source Dataset, Related Gene.

- [ ] **Step 3: Verify**

```bash
npm test -- tests/views/object-routes.spec.ts
npm run build
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/views apps/web/src/router/index.ts apps/web/tests/views/object-routes.spec.ts
git commit -m "Add PhytoAtlas object and planning routes"
```

### Task 7: Replace the SVG prototype with a Cytoscape graph explorer

**Files:**
- Create: `apps/web/src/components/graph/GraphToolbar.vue`
- Create: `apps/web/src/components/graph/GraphCanvas.vue`
- Create: `apps/web/src/components/graph/GraphLegend.vue`
- Create: `apps/web/src/components/graph/NodeInspector.vue`
- Create: `apps/web/src/lib/graph-elements.ts`
- Create: `apps/web/src/views/GraphView.vue`
- Create: `apps/web/tests/lib/graph-elements.spec.ts`
- Create: `apps/web/tests/views/graph.spec.ts`

**Interfaces:**
- `toCytoscapeElements(neighborhood)` returns stable node and edge elements.
- `GraphCanvas` emits `select(node: GraphNode)`.
- Toolbar controls center query, species, and predicate.

- [ ] **Step 1: Write failing element-mapping tests**

```ts
it("maps one neighborhood without duplicating the center node", () => {
  const elements = toCytoscapeElements(neighborhoodFixture);
  expect(elements.nodes.filter((item) => item.data.id === neighborhoodFixture.node.node_id)).toHaveLength(1);
  expect(elements.edges[0].data.predicate).toBe("belongs_to_species");
});
```

- [ ] **Step 2: Implement Cytoscape lifecycle**

Initialize after mount with a sized container, use a breadth-first or cose layout, preserve warnings in development, update elements on payload change, and call `destroy()` before unmount.

- [ ] **Step 3: Implement graph workflow**

Search one center Gene, fetch neighbors, render graph, select the center by default, and show a Wiki route in `NodeInspector`. Preserve toolbar inputs on error and expose retry.

- [ ] **Step 4: Verify**

```bash
npm test -- tests/lib/graph-elements.spec.ts tests/views/graph.spec.ts
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/graph apps/web/src/lib/graph-elements.ts apps/web/src/views/GraphView.vue apps/web/tests
git commit -m "Add Cytoscape knowledge graph explorer"
```

### Task 8: Rename and test the FastAPI package

**Files:**
- Move: `apps/api/plantgenewiki_api` to `apps/api/phytoatlas_api`
- Modify: `apps/api/phytoatlas_api/main.py`
- Modify: `apps/api/phytoatlas_api/graph_store.py`
- Modify: `apps/api/phytoatlas_api/simple_server.py`
- Modify: `apps/api/tests/test_graph_store.py`
- Create: `apps/api/tests/test_main.py`
- Modify: `apps/api/README.md`

**Interfaces:**
- ASGI entry: `phytoatlas_api.main:app`.
- Environment: `PHYTOATLAS_GRAPH_DB` and `PHYTOATLAS_CORS_ORIGINS`.
- API title: `PhytoAtlas API`.
- Existing endpoint paths and response schemas remain stable.

- [ ] **Step 1: Write failing package and API tests**

```python
########## 0. imports ##########
import unittest
from fastapi.testclient import TestClient
from phytoatlas_api.main import app

########## 1. tests ##########
class ApiIdentityTest(unittest.TestCase):
    def test_api_uses_phytoatlas_identity(self):
        self.assertEqual(app.title, "PhytoAtlas API")
        response = TestClient(app).get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
```

- [ ] **Step 2: Move the package and update imports**

Use `git mv`. Rename `PlantGeneWikiHandler` to `PhytoAtlasHandler`. Replace only the backend environment variables listed above.

- [ ] **Step 3: Change default graph paths**

Use:

```python
DEFAULT_GRAPH_DB = Path("/DATA/data2/phytoatlas/graph/pgcp_v1/phytoatlas_pgcp_v1.sqlite")
DEFAULT_GRAPH_SUMMARY = Path("/DATA/data2/phytoatlas/graph/pgcp_v1/graph_summary.json")
```

- [ ] **Step 4: Verify**

```bash
cd apps/api
../../.venv/bin/python -m compileall -q phytoatlas_api
../../.venv/bin/python -m unittest discover -s tests -v
```

- [ ] **Step 5: Commit**

```bash
git add apps/api
git commit -m "Rename FastAPI service to PhytoAtlas"
```

### Task 9: Rename the reusable Python package and pipeline imports

**Files:**
- Move: `src/plantgenewiki` to `src/phytoatlas`
- Modify: `scripts/importers/genome/normalize_fasta_dataset.py`
- Modify: `scripts/maintenance/batch_normalize_pgcp_genomes.py`
- Modify: `scripts/maintenance/build_pgcp_graph_index.py`
- Modify: `tests/normalize/test_fasta.py`
- Modify: `tests/normalize/test_gff.py`
- Create: `tests/config/test_phytoatlas_imports.py`

**Interfaces:**
- Public imports use `phytoatlas.normalize`.
- Normalized object IDs remain unchanged.
- Graph database output filename becomes `phytoatlas_pgcp_v1.sqlite`.

- [ ] **Step 1: Write a failing import smoke test**

```python
########## 0. imports ##########
import unittest

########## 1. tests ##########
class PackageImportTest(unittest.TestCase):
    def test_normalizers_import_from_phytoatlas(self):
        from phytoatlas.normalize.fasta import normalize_fasta_dataset
        from phytoatlas.normalize.gff import normalize_gff3_dataset
        self.assertTrue(callable(normalize_fasta_dataset))
        self.assertTrue(callable(normalize_gff3_dataset))
```

- [ ] **Step 2: Move the package and update imports**

Use `git mv src/plantgenewiki src/phytoatlas`. Update scripts and tests. Do not rewrite `gene:`, `species:`, `dataset:`, or `seq:` values.

- [ ] **Step 3: Update pipeline descriptions**

Replace product prose with PhytoAtlas while preserving source Dataset labels such as PGCP.

- [ ] **Step 4: Verify**

```bash
.venv/bin/python -m unittest discover -s tests/normalize -v
.venv/bin/python -m unittest discover -s tests/config -v
```

- [ ] **Step 5: Commit**

```bash
git add src scripts tests
git commit -m "Rename reusable package to PhytoAtlas"
```

### Task 10: Remove static publishing and finish active-tree brand migration

**Files:**
- Delete: `apps/web/public/data/api/**`
- Delete: `scripts/build/build_web_data.py`
- Delete: `tests/build/test_build_web_data.py`
- Delete: `tests/web/test_static_pages.py`
- Delete: `apps/web/public/assets/plantgenewiki-logo-full.png`
- Create: `apps/web/public/phytoatlas-mark.svg`
- Create: `apps/web/public/_redirects`
- Delete: legacy service script under `scripts/services`
- Create: `scripts/services/phytoatlas.sh`
- Modify: `.gitignore`
- Modify: `AGENTS.md`
- Modify: `.codex/agents/*.toml`
- Modify: `config/*.yaml`
- Modify: `schemas/*.json`
- Modify: `examples/**`
- Modify: active product documentation outside completed migration records
- Modify: `scripts/**`
- Modify: `tests/**`

**Interfaces:**
- Cloudflare SPA fallback file contains `/* /index.html 200`.
- Runtime code, schemas, examples, configuration, and user documentation contain no legacy display name, package name, environment prefix, schema domain, service filename, or Astro reference.

- [ ] **Step 1: Write a failing repository identity test**

Create `tests/config/test_phytoatlas_identity.py` that scans tracked runtime code, schemas, examples, configuration, and user documentation. Exclude `docs/superpowers/plans` and `docs/superpowers/specs` until Task 12 archives completed migration records in Git history. Assemble retired search tokens from fragments so the test does not contain the forbidden literal itself.

- [ ] **Step 2: Remove static publishing**

Delete generated web API data, its builder, and static HTML tests. The Vue app must continue to pass its API service tests without these files.

- [ ] **Step 3: Complete the mechanical rename**

Update user documentation, schemas, examples, Codex roles, the new service script, logical archive URIs, and maintenance defaults. The new service script manages FastAPI and Vite development processes, uses concise English comments, and contains no obsolete `apps/agent` or Chainlit behavior.

- [ ] **Step 4: Add SPA hosting fallback and new mark**

Create a minimal PhytoAtlas SVG mark and `_redirects`. Update `index.html` favicon and metadata.

- [ ] **Step 5: Verify zero Astro and identity residuals**

```bash
.venv/bin/python -m unittest discover -s tests/config -v
find apps/web -type f -name '*.astro' -print -quit | grep -q . && exit 1 || true
git grep -n -I -E 'astro.config|@astrojs|plantgenewiki|PlantGeneWiki|PLANTGENEWIKI' -- \
  ':!docs/superpowers/plans/**' ':!docs/superpowers/specs/**' && exit 1 || true
cd apps/web
npm test
npm run build
```

Expected: no match, all frontend tests pass, and Vite build succeeds.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Complete PhytoAtlas active-tree migration"
```

### Task 11: Migrate the server data root with verification

**Files outside Git:**
- Move: `/DATA/data2/plantgenewiki` to `/DATA/data2/phytoatlas`
- Rename: `plantgenewiki_pgcp_v1.sqlite` to `phytoatlas_pgcp_v1.sqlite`
- Rename: `.plantgenewiki-manifest.sha256` files to `.phytoatlas-manifest.sha256`
- Modify ignored local mapping: `config/archives.local.yaml`

**Interfaces:**
- Production graph database: `/DATA/data2/phytoatlas/graph/pgcp_v1/phytoatlas_pgcp_v1.sqlite`.
- Archive content and checksums remain unchanged.

- [ ] **Step 1: Stop project processes and record preflight evidence**

```bash
pgrep -af 'uvicorn|phytoatlas|plantgenewiki' || true
stat -c '%d %n' /DATA/data2 /DATA/data2/plantgenewiki
find /DATA/data2/plantgenewiki -type f | wc -l
du -sb /DATA/data2/plantgenewiki
```

Expected: source and parent have the same device ID. Stop matching project processes before the move.

- [ ] **Step 2: Rename the data root**

```bash
mv /DATA/data2/plantgenewiki /DATA/data2/phytoatlas
mv /DATA/data2/phytoatlas/graph/pgcp_v1/plantgenewiki_pgcp_v1.sqlite \
  /DATA/data2/phytoatlas/graph/pgcp_v1/phytoatlas_pgcp_v1.sqlite
find /DATA/data2/phytoatlas -name '.plantgenewiki-manifest.sha256' -exec sh -c \
  'mv "$1" "$(dirname "$1")/.phytoatlas-manifest.sha256"' sh {} \;
```

- [ ] **Step 3: Verify counts, size, database, and manifests**

Repeat file count and byte-size commands against the new root. Run:

```bash
sqlite3 /DATA/data2/phytoatlas/graph/pgcp_v1/phytoatlas_pgcp_v1.sqlite \
  'SELECT COUNT(*) FROM nodes; SELECT COUNT(*) FROM edges;'
find /DATA/data2/phytoatlas -name '.phytoatlas-manifest.sha256' -print
```

If verification fails, move the root back before restarting services.

- [ ] **Step 4: Update local archive mapping and smoke-test FastAPI**

```bash
cd apps/api
PHYTOATLAS_GRAPH_DB=/DATA/data2/phytoatlas/graph/pgcp_v1/phytoatlas_pgcp_v1.sqlite \
  ../../.venv/bin/python -m uvicorn phytoatlas_api.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8000/api/graph/summary
```

Expected: health returns `{"status":"ok"}` and summary returns graph counts.

### Task 12: Final integration, repository rename, and end-to-end verification

**Files:**
- Verify all tracked files.
- Rename the GitHub repository from its legacy name to `nebuscar/PhytoAtlas`.
- Rename the server project directory from its legacy path to `/home/nizhu/Projects/PhytoAtlas`.
- Recreate project `.venv` after the directory move.
- Delete completed migration plans from the active tree after all steps are executed; Git history retains them.

**Interfaces:**
- Git remote: `https://github.com/nebuscar/PhytoAtlas.git`.
- Server project root: `/home/nizhu/Projects/PhytoAtlas`.

- [ ] **Step 1: Run final tests before external rename**

```bash
cd apps/web
npm test
npm run build
cd ../api
../../.venv/bin/python -m unittest discover -s tests -v
cd ../..
.venv/bin/python -m unittest discover -s tests -v
git diff --check
git status --short
```

Expected: all tests pass and the worktree is clean.

- [ ] **Step 2: Rename the GitHub repository and update the remote**

```bash
gh repo rename PhytoAtlas --repo nebuscar/PlantGeneWiki --yes
git remote set-url origin https://github.com/nebuscar/PhytoAtlas.git
git push origin nizhu
```

- [ ] **Step 3: Rename the server directory**

First remove completed feature worktrees. Then:

```bash
cd /home/nizhu/Projects
mv PlantGeneWiki PhytoAtlas
cd PhytoAtlas
```

- [ ] **Step 4: Recreate the project virtual environment**

```bash
mv .venv .venv-before-rename
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r apps/api/requirements.txt
.venv/bin/python -m unittest discover -s apps/api/tests -v
```

Remove `.venv-before-rename` only after the new environment passes.

- [ ] **Step 5: Run local frontend-backend integration**

Terminal 1:

```bash
cd /home/nizhu/Projects/PhytoAtlas/apps/api
PHYTOATLAS_GRAPH_DB=/DATA/data2/phytoatlas/graph/pgcp_v1/phytoatlas_pgcp_v1.sqlite \
  ../../.venv/bin/python -m uvicorn phytoatlas_api.main:app --host 0.0.0.0 --port 8000
```

Terminal 2:

```bash
cd /home/nizhu/Projects/PhytoAtlas/apps/web
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Verify homepage summary, search, Gene Wiki page, Species page, graph selection, dataset route, sequence route, planned routes, refresh on nested routes, and explicit API error states.

- [ ] **Step 6: Retire completed migration records from the active tree**

Delete the completed implementation plan after execution and remove superseded completed cleanup plans/specifications that still encode the retired identity. Keep this approved design after rewriting its historical-name sentences to `legacy product name`.

Commit:

```bash
git add -A docs/superpowers
git commit -m "Retire completed legacy migration records"
```

- [ ] **Step 7: Final active-tree audit**

```bash
cd /home/nizhu/Projects/PhytoAtlas
git grep -n -I -E 'plantgenewiki|PlantGeneWiki|PLANTGENEWIKI|@astrojs|astro.config|\\.astro' && exit 1 || true
git diff --check
git status -sb
git remote -v
```

Expected: no retired identity or Astro match, clean branch, new remote URL, and no biological identifier changes.
