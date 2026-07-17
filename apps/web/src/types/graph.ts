export type GraphProperties = Record<string, unknown>;

export interface GraphNode {
  node_id: string;
  object_type: string;
  label: string | null;
  species_id: string | null;
  source_file: string | null;
  properties: GraphProperties;
}

export interface GraphEdge {
  source: string;
  predicate: string;
  target: string;
  species_id: string | null;
  source_dataset: string | null;
  evidence: string | null;
  properties: GraphProperties;
}

export interface GraphSearchParams {
  q: string;
  objectType?: string;
  speciesId?: string;
  limit?: number;
}

export interface GraphSearchResponse {
  query: string;
  count: number;
  nodes: GraphNode[];
}

export type NeighborDirection = "in" | "out" | "both";

export interface NeighborOptions {
  direction?: NeighborDirection;
  predicate?: string;
  excludePredicates?: string[];
  limit?: number;
}

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

export interface GraphQueryState {
  center: string;
  species: string;
  view: string;
  predicate: string;
}

export interface GraphSummary {
  database: string;
  node_count: number;
  edge_count: number;
  node_types: Record<string, number>;
  edge_predicates: Record<string, number>;
}

export interface SpeciesGenePage {
  species_id: string;
  total: number;
  limit: number;
  offset: number;
  genes: GraphNode[];
}
