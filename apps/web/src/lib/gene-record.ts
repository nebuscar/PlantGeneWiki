import type { GraphNode } from "../types/graph";

export interface GenomeLocationSummary {
  assembly: string;
  coordinates: string;
  strand: string;
  coordinateSystem: string;
}

export interface TranscriptSummary {
  transcriptId: string;
  name: string;
  location: string;
  cdsCount: number;
  exonCount: number;
  utrCount: number;
}

export interface FunctionAnnotations {
  description: string;
  goTerms: string[];
  tfType: string;
  tfFamily: string;
}

export interface SequenceSummary {
  nodeId: string;
  publicId: string;
  name: string;
  length: number | null;
}

export interface SequenceGroups {
  cds: SequenceSummary[];
  protein: SequenceSummary[];
}

export function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function formatLocation(value: unknown): string {
  const location = asRecord(value);
  const seqid = asString(location.seqid);
  const start = asNumber(location.start);
  const end = asNumber(location.end);
  const strand = asString(location.strand);
  return seqid && start !== null && end !== null
    ? `${seqid}:${start}-${end}${strand ? ` (${strand})` : ""}`
    : "";
}

export function findRelatedNodes(nodes: GraphNode[], objectType: string): GraphNode[] {
  return nodes
    .filter((node) => node.object_type === objectType)
    .sort((left, right) => left.node_id.localeCompare(right.node_id));
}

export function readGenomeLocation(node: GraphNode | null): GenomeLocationSummary {
  const properties = asRecord(node?.properties);
  const nested = properties.genome_location ?? properties.location;
  const location = Object.keys(asRecord(nested)).length ? asRecord(nested) : properties;
  return {
    assembly: asString(location.assembly),
    coordinates: formatLocation(location),
    strand: asString(location.strand),
    coordinateSystem: asString(location.coordinate_system),
  };
}

export function readTranscriptSummaries(node: GraphNode | null): TranscriptSummary[] {
  const properties = asRecord(node?.properties);
  return asArray(properties.transcripts)
    .map((value) => {
      const transcript = asRecord(value);
      return {
        transcriptId: asString(transcript.transcript_id),
        name: asString(transcript.name),
        location: formatLocation(transcript.location),
        cdsCount: asArray(transcript.cds).length,
        exonCount: asArray(transcript.exons).length,
        utrCount: asArray(transcript.utrs).length,
      };
    })
    .sort((left, right) => left.transcriptId.localeCompare(right.transcriptId));
}

export function readFunctionAnnotations(node: GraphNode | null): FunctionAnnotations {
  const properties = asRecord(node?.properties);
  const annotations = asRecord(properties.annotations);
  const transcriptionFactor = asRecord(annotations.transcription_factor);
  const goTerms = asArray(annotations.go ?? properties.go)
    .filter((value): value is string => typeof value === "string");
  return {
    description: asString(properties.description),
    goTerms,
    tfType: asString(transcriptionFactor.type),
    tfFamily: asString(transcriptionFactor.family),
  };
}

export function groupSequenceRecords(nodes: GraphNode[]): SequenceGroups {
  const groups: SequenceGroups = { cds: [], protein: [] };
  for (const node of nodes) {
    const properties = asRecord(node.properties);
    const sequenceType = asString(properties.sequence_type).toUpperCase();
    if (sequenceType !== "CDS" && sequenceType !== "PROTEIN") {
      continue;
    }
    const publicId = asString(properties.id) || asString(properties.sequence_id) || node.node_id;
    const summary = {
      nodeId: node.node_id,
      publicId,
      name: asString(properties.name) || node.label || publicId,
      length: asNumber(properties.length),
    };
    groups[sequenceType === "CDS" ? "cds" : "protein"].push(summary);
  }
  for (const records of [groups.cds, groups.protein]) {
    records.sort(
      (left, right) =>
        left.publicId.localeCompare(right.publicId) || left.nodeId.localeCompare(right.nodeId),
    );
  }
  return groups;
}
