# Arabidopsis Golden Gene Wiki Acceptance Design

## 1. Purpose

This milestone turns the Arabidopsis Gene Wiki page into a repeatable product contract. It uses real normalized graph data instead of synthetic page-only fixtures.

The acceptance set must detect regressions in:

- normalized Gene knowledge objects;
- graph relations and endpoint integrity;
- graph API lookup and neighborhood behavior;
- permanent Gene Wiki sections;
- readable presentation of rich and missing fields.

## 2. Scope

The first version covers 20 Arabidopsis thaliana genes:

- 10 engineering boundary genes selected from production data characteristics;
- 10 biologically representative genes selected for recognizable functions and demonstration value.

The set is versioned in the repository and remains stable until a documented data-version migration requires an update.

This milestone does not add literature, homology, a vector database, or a production graph database. Missing Publications and Homology content is acceptable when the page renders an explicit unavailable state.

## 3. Golden Gene Contract

The repository stores the golden set as structured JSON. Each entry contains:

- stable PhytoAtlas gene object ID;
- public gene ID;
- known source aliases;
- selection group and reason;
- expected strand;
- expected transcription-factor status;
- minimum GO term count;
- minimum transcript, CDS, and protein record counts;
- required page sections;
- sections allowed to be unavailable.

Expected values describe durable biological or structural characteristics. They must not duplicate full production records.

## 4. Selection Method

### 4.1 Engineering Boundary Genes

Candidates are ranked from the production Arabidopsis graph and normalized JSONL data. The final set covers:

- positive and negative strands;
- single- and multi-transcript genes;
- transcription factors from different families;
- genes with many GO terms;
- long descriptions and sparse descriptions;
- high sequence and relation counts;
- records with intentionally unavailable optional knowledge.

Selection statistics are reproducible, but the final IDs are curated and frozen.

### 4.2 Biological Representative Genes

Candidates are established Arabidopsis genes with recognizable roles in areas such as flowering, development, hormone signaling, defense, photosynthesis, and RNA regulation.

Every candidate must first resolve from a known Araport alias to the current PhytoAtlas gene object. A famous gene is not included when the current source data cannot support a stable mapping.

## 5. Acceptance Layers

### 5.1 Data Layer

For every golden gene, validation checks:

- one unique Gene node exists;
- species, dataset, location, structure, sequence, and evidence expectations are satisfied;
- genomic coordinates and strand are valid;
- aliases, GO terms, and transcription-factor annotations meet the contract;
- all selected relation endpoints exist;
- records do not expose absolute internal paths.

### 5.2 API Layer

Validation checks:

- lookup by public ID;
- lookup by full object ID;
- alias lookup when alias resolution is implemented;
- deterministic neighborhood ordering;
- no silent loss of required Location, Structure, Sequence, or Evidence relations.

The current generic one-hop query uses an unordered LIMIT. The implementation must remove this nondeterminism before the page can be treated as accepted.

### 5.3 Page Layer

The Gene Wiki page keeps these permanent sections:

1. Overview
2. Identifiers
3. Location
4. Structure
5. Function
6. Sequences
7. Homology
8. Evidence
9. Publications

Acceptance requires:

- permanent sections remain visible;
- location, structure, and function are rendered as readable fields instead of raw JSON;
- transcript and sequence records are grouped clearly;
- sequence records remain navigable;
- missing optional data uses one consistent unavailable state;
- loading, error, and empty states remain usable;
- internal storage paths and import-only details are not displayed.

## 6. Implementation Boundaries

The milestone introduces:

- a versioned golden gene manifest;
- a production-data selection and validation command;
- deterministic API behavior required by Gene pages;
- API contract tests;
- Vue component and browser-level smoke acceptance for representative rich and sparse genes;
- a generated acceptance report outside Git-tracked data paths.

The milestone avoids:

- copying complete production records into tests;
- using page snapshots as the only acceptance mechanism;
- hard-failing Homology or Publications when their source datasets are absent;
- coupling the contract to PGCP folder names or server-specific paths.

## 7. Delivery Order

1. Profile real Arabidopsis candidates.
2. Freeze the 20-gene manifest.
3. Add failing data-contract tests.
4. Implement the golden-set validator and report.
5. Add failing API contract tests.
6. make neighborhood retrieval deterministic and complete for page-critical relations.
7. Add failing Gene page tests.
8. render stable readable Gene sections.
9. run data, API, Vue, build, and browser smoke verification.

## 8. Completion Criteria

The milestone is complete when:

- all 20 genes pass the data contract;
- API results are deterministic;
- one rich and one sparse real gene pass full page smoke acceptance;
- all permanent sections behave correctly;
- the full existing test suite and Vue production build pass;
- no credentials, absolute internal paths, raw production data, or generated graph indexes are committed.
