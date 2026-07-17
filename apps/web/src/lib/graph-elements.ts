import type { EdgeDefinition, NodeDefinition } from "cytoscape";
import type { GraphNode, GraphRecord, GraphSelection } from "../types/graph";

export const SEQUENCE_SUMMARY_ID = "presentation:sequence-summary";

export interface CytoscapeNeighborhood {
  nodes: NodeDefinition[];
  edges: EdgeDefinition[];
  selectionById: Map<string, GraphSelection>;
}

export function toCytoscapeElements(
  neighborhood: GraphRecord,
  options: { sequenceCount?: number } = {},
): CytoscapeNeighborhood {
  const nodeById = new Map<string, GraphNode>();
  nodeById.set(neighborhood.node.node_id, neighborhood.node);
  for (const node of neighborhood.nodes) {
    nodeById.set(node.node_id, node);
  }

  const selectionById = new Map<string, GraphSelection>();
  const nodes: NodeDefinition[] = [...nodeById.values()].map((node) => {
    selectionById.set(node.node_id, { kind: "node", node });
    return {
      data: {
        id: node.node_id,
        label: node.label || node.node_id,
        objectType: node.object_type,
        speciesId: node.species_id,
        isCenter: node.node_id === neighborhood.node.node_id,
      },
    };
  });

  const duplicateCounts = new Map<string, number>();
  const edges: EdgeDefinition[] = neighborhood.edges.map((edge) => {
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

  const sequenceCount = options.sequenceCount ?? 0;
  if (sequenceCount > 0) {
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
  }

  return { nodes, edges, selectionById };
}
