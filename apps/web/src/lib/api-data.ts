export type Relation = {
  source: string;
  predicate: string;
  target: string;
  label?: string;
  evidence?: string[];
  source_dataset?: string;
};

export type EvidenceRecord = {
  evidence_id: string;
  source: string;
  claim: string;
  evidence_type?: string;
  confidence: "low" | "medium" | "high";
  review_status?: string;
  source_dataset?: string;
  source_url?: string;
};

export type Species = {
  object_id: string;
  object_type: "Species";
  id: string;
  name: string;
  common_name?: string;
  description: string;
  genome_versions?: string[];
  related_objects?: Relation[];
  datasets?: string[];
};

export type Gene = {
  object_id: string;
  object_type: "Gene";
  id: string;
  name: string;
  species: string;
  description: string;
  aliases?: string[];
  annotations?: string[];
  related_objects?: Relation[];
  evidence_records?: EvidenceRecord[];
  datasets?: string[];
};

export type Dataset = {
  object_id: string;
  object_type: "Dataset";
  id: string;
  name: string;
  dataset_type: string;
  source: string;
  status: string;
  location_policy: string;
  description?: string;
  updated_at?: string;
  [key: string]: unknown;
};

export type SequenceRecord = {
  object_id: string;
  object_type: "SequenceRecord";
  id: string;
  name: string;
  description: string;
  sequence_id: string;
  species: string;
  dataset: string;
  sequence_type: string;
  length: number;
  checksum?: Record<string, string>;
  inferred_gene_id?: string;
  inference_method?: string;
  confidence?: string;
  related_objects?: Relation[];
  updated_at?: string;
};

export type SearchItem = {
  type: string;
  id: string;
  title: string;
  href: string;
  summary: string;
};

export type GraphNode = {
  id: string;
  label: string;
  type: string;
};

export type GraphEdge = {
  source: string;
  target: string;
  predicate: string;
  label?: string;
};

const speciesModules = import.meta.glob<Species>("../../public/data/api/species/*.json", { eager: true, import: "default" });
const geneModules = import.meta.glob<Gene>("../../public/data/api/genes/*.json", { eager: true, import: "default" });
const datasetModules = import.meta.glob<Dataset>("../../public/data/api/datasets/*.json", { eager: true, import: "default" });
const sequenceRecordModules = import.meta.glob<SequenceRecord>("../../public/data/api/sequence_records/*.json", { eager: true, import: "default" });
const searchModules = import.meta.glob<SearchItem[]>("../../public/data/api/search/index.json", { eager: true, import: "default" });
const graphNodeModules = import.meta.glob<GraphNode[]>("../../public/data/api/graph/nodes.json", { eager: true, import: "default" });
const graphEdgeModules = import.meta.glob<GraphEdge[]>("../../public/data/api/graph/edges.json", { eager: true, import: "default" });
const evidenceModules = import.meta.glob<EvidenceRecord[]>("../../public/data/api/evidence/claims.json", { eager: true, import: "default" });

function values<T>(modules: Record<string, T>): T[] {
  return Object.values(modules);
}

function firstArray<T>(modules: Record<string, T[]>): T[] {
  return Object.values(modules)[0] ?? [];
}

export const species = values(speciesModules).sort((a, b) => a.name.localeCompare(b.name));
export const genes = values(geneModules).sort((a, b) => a.name.localeCompare(b.name));
export const datasets = values(datasetModules).sort((a, b) => a.name.localeCompare(b.name));
export const sequenceRecords = values(sequenceRecordModules).sort((a, b) => a.name.localeCompare(b.name));
export const searchItems = firstArray(searchModules);
export const evidenceClaims = firstArray(evidenceModules);

export const graph = {
  nodes: firstArray(graphNodeModules),
  edges: firstArray(graphEdgeModules)
};

export function getSpecies(id: string) {
  return species.find((item) => item.id === id);
}

export function getGene(id: string) {
  return genes.find((item) => item.id === id);
}

export function getDataset(id: string) {
  return datasets.find((item) => item.id === id);
}

export function getSequenceRecord(id: string) {
  return sequenceRecords.find((item) => item.id === id);
}

export function hrefForObjectRef(ref: string): string | undefined {
  if (ref.startsWith("species:")) {
    return `/species/${ref.slice("species:".length)}`;
  }
  if (ref.startsWith("gene:")) {
    return `/genes/${ref.slice("gene:".length)}`;
  }
  if (ref.startsWith("dataset:")) {
    const dataset = datasets.find((item) => item.object_id === ref || `dataset:${item.id}` === ref);
    return dataset ? `/datasets/${dataset.id}` : undefined;
  }
  if (ref.startsWith("seq:")) {
    const sequenceRecord = sequenceRecords.find((item) => item.object_id === ref);
    return sequenceRecord ? `/sequence-records/${sequenceRecord.id}` : undefined;
  }
  return undefined;
}
