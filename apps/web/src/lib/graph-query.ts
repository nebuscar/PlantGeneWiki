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
