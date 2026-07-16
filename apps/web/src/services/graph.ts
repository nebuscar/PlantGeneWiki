import { apiRequest } from "./http";
import type {
  GraphNeighborhood,
  GraphNode,
  GraphSearchParams,
  GraphSearchResponse,
  GraphSummary,
  NeighborOptions,
  SpeciesGenePage,
} from "../types/graph";

export class ObjectNotFoundError extends Error {
  readonly objectType: string;
  readonly publicId: string;

  constructor(objectType: string, publicId: string) {
    super(`${objectType} not found: ${publicId}`);
    this.name = "ObjectNotFoundError";
    this.objectType = objectType;
    this.publicId = publicId;
  }
}

function appendOptionalParam(params: URLSearchParams, name: string, value?: string | number) {
  if (value !== undefined && value !== "") {
    params.set(name, String(value));
  }
}

export function searchNodes(
  params: GraphSearchParams,
  signal?: AbortSignal,
): Promise<GraphSearchResponse> {
  const query = new URLSearchParams({ q: params.q });
  appendOptionalParam(query, "object_type", params.objectType);
  appendOptionalParam(query, "species_id", params.speciesId);
  appendOptionalParam(query, "limit", params.limit);
  return apiRequest<GraphSearchResponse>(`/api/graph/search?${query.toString()}`, { signal });
}

export function getNode(nodeId: string): Promise<GraphNode> {
  return apiRequest<GraphNode>(`/api/graph/nodes/${encodeURIComponent(nodeId)}`);
}

export function getNeighbors(
  nodeId: string,
  options: NeighborOptions = {},
): Promise<GraphNeighborhood> {
  const query = new URLSearchParams();
  appendOptionalParam(query, "direction", options.direction);
  appendOptionalParam(query, "predicate", options.predicate);
  appendOptionalParam(query, "limit", options.limit);
  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  return apiRequest<GraphNeighborhood>(
    `/api/graph/neighbors/${encodeURIComponent(nodeId)}${suffix}`,
  );
}

export function getGraphSummary(): Promise<GraphSummary> {
  return apiRequest<GraphSummary>("/api/graph/summary");
}

export function listSpeciesGenes(
  speciesId: string,
  limit = 50,
  offset = 0,
): Promise<SpeciesGenePage> {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return apiRequest<SpeciesGenePage>(
    `/api/graph/species/${encodeURIComponent(speciesId)}/genes?${query.toString()}`,
  );
}

function isFullNodeId(publicId: string): boolean {
  return publicId.includes(":");
}

function hasExactPublicId(node: GraphNode, publicId: string): boolean {
  return node.label === publicId || node.properties.id === publicId;
}

export async function resolveObject(objectType: string, publicId: string): Promise<GraphNode> {
  const candidate = publicId.trim();
  if (!candidate) {
    throw new ObjectNotFoundError(objectType, publicId);
  }
  if (isFullNodeId(candidate)) {
    return getNode(candidate);
  }

  const result = await searchNodes({
    q: candidate,
    objectType,
    limit: 20,
  });
  const match = result.nodes.find((node) => hasExactPublicId(node, candidate));
  if (!match) {
    throw new ObjectNotFoundError(objectType, candidate);
  }
  return match;
}
