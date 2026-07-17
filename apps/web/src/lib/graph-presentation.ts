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
  const nodes = neighborhood.nodes.filter(
    (node) => nodeSequenceType(node) === sequenceType,
  );
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
