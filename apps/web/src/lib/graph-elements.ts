import type { EdgeDefinition, NodeDefinition } from "cytoscape";
import type { GraphNeighborhood, GraphNode } from "../types/graph";

export interface CytoscapeNeighborhood {
  nodes: NodeDefinition[];
  edges: EdgeDefinition[];
  nodeById: Map<string, GraphNode>;
}

export function toCytoscapeElements(neighborhood: GraphNeighborhood): CytoscapeNeighborhood {
  const nodeById = new Map<string, GraphNode>();
  nodeById.set(neighborhood.node.node_id, neighborhood.node);
  for (const node of neighborhood.nodes) {
    nodeById.set(node.node_id, node);
  }

  const nodes = [...nodeById.values()].map((node) => ({
    data: {
      id: node.node_id,
      label: node.label || node.node_id,
      objectType: node.object_type,
      speciesId: node.species_id,
      isCenter: node.node_id === neighborhood.node.node_id,
    },
  }));

  const duplicateCounts = new Map<string, number>();
  const edges = neighborhood.edges.map((edge) => {
    const baseId = `${edge.source}|${edge.predicate}|${edge.target}`;
    const duplicateIndex = duplicateCounts.get(baseId) ?? 0;
    duplicateCounts.set(baseId, duplicateIndex + 1);
    return {
      data: {
        id: `${baseId}|${duplicateIndex}`,
        source: edge.source,
        target: edge.target,
        predicate: edge.predicate,
        evidence: edge.evidence,
      },
    };
  });

  return { nodes, edges, nodeById };
}
