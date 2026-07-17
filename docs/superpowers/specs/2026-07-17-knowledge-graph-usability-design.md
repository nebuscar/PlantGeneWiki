# Knowledge Graph Usability Sprint Design

## 1. Purpose

This sprint turns the existing one-hop Knowledge Graph page into an immediately useful, explainable product surface. It preserves normalized graph truth while reducing presentation noise and making every query reproducible through the URL.

The validated acceptance record is `Atha04G0031690.v1.36` in `arabidopsis_thaliana`. Its current one-hop neighborhood contains 59 relations:

- 1 `belongs_to_species`;
- 1 `contains_gene`;
- 1 `has_location`;
- 54 `has_sequence`;
- 1 `has_structure`;
- 1 `provided_by_dataset`.

The current page renders all 59 relations and 60 nodes at once. The new default presents five real core nodes plus one clearly marked sequence summary, while retaining access to all 54 real SequenceRecord nodes on demand.

## 2. Scope

This sprint includes:

- a real default Arabidopsis graph instead of empty placeholder-only inputs;
- stable graph deep links from Gene Wiki pages;
- species-scoped public gene ID resolution;
- URL-synchronized query state;
- complete one-hop predicate counts and explicit truncation metadata;
- a readable core graph with presentation-only sequence grouping;
- an accessible sequence drawer that exposes real SequenceRecord nodes by type;
- clear validation, not-found, unavailable, and stale-request behavior;
- automated store, API, Vue, and presentation tests;
- live API and browser acceptance against the validated rich gene.

This sprint does not add:

- GO enrichment or any other analysis tool;
- vector search or similarity edges;
- multi-hop graph traversal;
- graph editing;
- a new production graph database;
- a species registry selector;
- biological claims derived from display grouping.

## 3. Product Experience

### 3.1 Entry behavior

A bare `/graph` route seeds this real query and loads it automatically:

```text
/graph?center=Atha04G0031690.v1.36&species=arabidopsis_thaliana&view=core
```

If the URL already supplies `center`, the application never replaces it with the example. Invalid deep links remain visible and produce an actionable error.

Every Gene Wiki page exposes a `View in graph` action. It links with the public versioned gene ID and the node's normalized species ID. Loading that link automatically resolves and displays the requested gene.

### 3.2 Toolbar

The toolbar contains:

- Center gene;
- Species;
- Relationship view;
- Load graph.

The example values are real form values, not placeholders. `Core relationships` is the default view. Available relationship types and counts appear after a graph loads and can be selected without typing internal predicate names.

Submitting the form writes the requested state to the URL before loading. Browser refresh, forward, and back restore the same request.

### 3.3 Core graph

The default canvas displays:

- the real center Gene;
- real Species, Dataset, GeneLocation, and GeneStructure neighbors;
- one presentation-only `Sequence summary` item representing the hidden `has_sequence` relations.

The sequence summary uses a dashed border and a `Summary` label. It is not a `GraphNode`, is not returned by the API, and is never persisted as an edge or knowledge object.

The center and selected item keep visible labels. Other node and edge labels appear on hover or selection. This prevents the default canvas from becoming a label cloud.

### 3.4 Inspector and sequence drawer

Selecting a real node opens its normalized metadata in the inspector and preserves existing links to supported Wiki pages.

Selecting `Sequence summary` opens a separate drawer without adding 54 nodes to the core canvas. The drawer retrieves the real `has_sequence` neighborhood, groups records by normalized `sequence_type`, and shows:

- CDS record count and links;
- Protein record count and links;
- an explicit returned-versus-total count when results are truncated.

The acceptance gene must show 27 CDS and 27 Protein records. Users may choose a sequence type to display its real nodes; no sequence nodes appear merely because the summary is visible.

### 3.5 Responsive and accessible behavior

At narrow widths, the toolbar becomes a single column and the inspector moves below the canvas. The graph relationship summary and sequence drawer remain ordinary DOM controls, so canvas interaction is not the only way to inspect or expand content.

Form labels, error messages, relationship controls, summary actions, and drawer links remain keyboard accessible. The canvas retains its accessible name.

## 4. URL Contract

The graph route accepts:

- `center`: public gene ID or full graph node ID;
- `species`: normalized species ID required for public gene IDs;
- `view`: `core` for this sprint;
- `predicate`: optional exact predicate selection.

Unknown query parameters are ignored. Invalid supported values produce validation feedback rather than an unscoped fallback query.

`predicate` behavior is deterministic:

- no predicate loads the complete core projection while excluding sequence details;
- `has_sequence` keeps the core canvas collapsed and opens the sequence drawer;
- any other available predicate limits the real core edges to that exact predicate;
- the frontend never sends the same predicate as both an inclusion and an exclusion.

Route synchronization follows these rules:

1. A bare route receives the example query through `router.replace`.
2. A supplied route is treated as the user's requested state.
3. Form submission updates the route, then loads from the route state.
4. Route changes caused by browser history reload the graph once.
5. Internal state changes do not create duplicate history entries.

## 5. Graph API Contract

`GET /api/graph/neighbors/{node_id}` remains backward compatible. It adds an optional repeatable `exclude_predicate` query parameter and these top-level response fields:

```json
{
  "node": {},
  "nodes": [],
  "edges": [],
  "total_edges": 59,
  "matched_edges": 5,
  "predicate_counts": {
    "belongs_to_species": 1,
    "contains_gene": 1,
    "has_location": 1,
    "has_sequence": 54,
    "has_structure": 1,
    "provided_by_dataset": 1
  },
  "truncated": false
}
```

Field semantics are exact:

- `total_edges` counts all incident edges before predicate inclusion or exclusion;
- `matched_edges` counts incident edges after the requested predicate filters;
- `predicate_counts` groups all incident edges before filtering;
- `truncated` is true when `edges.length < matched_edges`;
- `nodes` contains only endpoints needed by the returned edges;
- an unfiltered request preserves the existing edge and node behavior.

The core request excludes `has_sequence`. The drawer uses `predicate=has_sequence`. Counts use the existing source and target indexes and must not scan unrelated graph nodes.

When inclusion and exclusion parameters are supplied directly to the API, exact predicate inclusion is applied first and exclusions are applied second. Repeated exclusions are deduplicated. Excluding the included predicate therefore produces zero matched edges without changing `total_edges` or `predicate_counts`.

## 6. Frontend Boundaries

The implementation keeps responsibilities separate:

- `GraphView` owns route synchronization, resolution, requests, cancellation, and page state.
- `GraphToolbar` owns controlled form fields and validation display.
- a focused graph presentation module converts an API neighborhood into canvas elements.
- `GraphCanvas` owns Cytoscape lifecycle, layout, visual states, and selection events.
- a relationship summary component exposes predicate counts as normal controls.
- a sequence drawer owns on-demand sequence retrieval, grouping, truncation feedback, and links.
- `NodeInspector` continues to inspect real normalized nodes.

Presentation selections use a discriminated union. A real node selection contains a `GraphNode`; a summary selection contains presentation metadata and source predicate counts. A summary object cannot be passed to APIs or Wiki routes as a node ID.

## 7. Data Flow

1. Read and validate supported route query fields.
2. Seed the real example only when all supported query fields are absent.
3. Resolve a full node ID directly with `getNode`.
4. Resolve a public gene ID with `searchNodes`, `object_type=Gene`, and a required species scope.
5. Accept only an exact node ID, label, or normalized public `properties.id` match.
6. Never fall back to the first partial search result.
7. Request the core neighborhood with `exclude_predicate=has_sequence`.
8. Build real canvas nodes plus one derived sequence summary when `predicate_counts.has_sequence > 0`.
9. Load real sequence records only when the summary drawer opens.
10. Abort the previous request whenever a newer route request begins.
11. Ignore every response whose request controller is no longer current.

## 8. Error and Edge States

| Condition | User-facing behavior |
|---|---|
| Empty center gene | Show `Enter a gene ID.` and make no request. |
| Public ID without species | Show `Choose a species before searching by public gene ID.` and make no request. |
| No exact match | Show `Gene not found: <query>.` and retain the requested URL. |
| Missing full node ID | Show the API not-found message and retain the requested URL. |
| Graph service unavailable | Show `Knowledge graph is temporarily unavailable.` with Retry. |
| Request superseded | Abort silently; never replace newer state. |
| No neighbors | Render the center node and an explicit empty-neighborhood message. |
| Truncated response | Show `Showing <returned> of <matched> relationships.` |
| No sequences | Omit the sequence summary and drawer action. |

Errors never expose absolute paths, raw exception representations, request internals, or graph database locations.

## 9. Performance

Initial loading uses one exact resolution request and one filtered neighborhood request. Sequence nodes are lazy-loaded. Predicate counts are computed for one indexed center neighborhood, not by scanning the nodes table.

The canvas renders the core projection by default. It does not instantiate hidden SequenceRecord Cytoscape elements. Changing a relationship control reuses the resolved center when possible.

## 10. Testing Strategy

### 10.1 Store and API tests

Temporary SQLite tests cover:

- all-predicate counts;
- filtered and excluded predicate counts;
- `total_edges` versus `matched_edges`;
- deterministic returned edge order;
- truncation detection;
- endpoint node completeness;
- backward-compatible unfiltered behavior;
- FastAPI parameter forwarding and response contracts.

### 10.2 Frontend tests

Vue and TypeScript tests cover:

- a bare route seeds and loads the real example;
- a deep link loads its requested gene;
- form state and route state remain synchronized;
- public IDs never trigger an unscoped search;
- no exact match never falls back to a partial result;
- empty input and missing species make no request;
- stale requests cannot replace newer data;
- core presentation contains five real nodes plus one summary for the acceptance record;
- summary elements are explicitly derived and never represented as `GraphNode` objects;
- labels are limited to center, hover, and selection states;
- the sequence drawer groups real CDS and Protein records;
- choosing CDS or Protein displays only real nodes of that type and returning to core removes them;
- Gene Wiki emits the correct `View in graph` link.

### 10.3 Live acceptance

The running API and browser must demonstrate:

- `/graph` becomes the real example deep link and loads successfully;
- the acceptance record reports 59 source relations;
- the default presentation shows six items: five real nodes and one sequence summary;
- the sequence drawer shows 27 CDS and 27 Protein records;
- choosing one sequence type displays its 27 real nodes without mixing the other type into the canvas;
- selecting real nodes updates the inspector;
- labels do not overlap in the default core view;
- empty, invalid, and not-found queries show their designed states;
- browser back and forward restore graph requests;
- no console errors or internal server paths appear.

## 11. Engineering Boundaries

- The API and frontend read only the normalized graph layer.
- No credentials, raw source data, generated indexes, or internal paths are committed.
- Display grouping is explicitly presentation-derived and never a verified biological relation.
- Existing user changes and unrelated files remain untouched.
- Arabidopsis is the acceptance species, while full node IDs and explicitly scoped species IDs remain supported.

## 12. Completion Criteria

The sprint is complete when:

- all focused store, API, Vue, and presentation tests pass;
- the complete existing API and Web suites pass;
- the Vue production build passes;
- the rich-gene live browser acceptance passes;
- the Gene Wiki deep link works end to end;
- the bare KG page has immediate real value without manual placeholder copying;
- no summary object can be mistaken for persisted graph truth;
- no accepted error or truncation state is silent.

GO enrichment remains the next independent milestone after this KG sprint is integrated.
