import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import GeneView from "../../src/views/GeneView.vue";
import { getGeneWikiRecord, resolveObject } from "../../src/services/graph";
import type { GeneWikiRecord, GraphNode } from "../../src/types/graph";

vi.mock("../../src/services/graph", () => ({
  getGeneWikiRecord: vi.fn(),
  resolveObject: vi.fn(),
}));

function graphNode(
  nodeId: string,
  objectType: string,
  label: string,
  properties: Record<string, unknown>,
): GraphNode {
  return {
    node_id: nodeId,
    object_type: objectType,
    label,
    species_id: "arabidopsis_thaliana",
    source_file: "/DATA/data2/private.jsonl",
    properties,
  };
}

function transcript(index: number, strand = "+") {
  return {
    transcript_id: `Atha04G0031690.${index}.v1.36`,
    name: `Atha04G0031690.${index}`,
    location: { seqid: "Chr4", start: 1000 + index, end: 2000 + index, strand },
    cds: [{}],
    exons: [],
    utrs: [],
  };
}

function sequenceNode(index: number, sequenceType: "CDS" | "PROTEIN"): GraphNode {
  const publicId = `Atha04G0031690.${index}.v1.36`;
  return graphNode(`seq:${sequenceType.toLowerCase()}:${index}`, "SequenceRecord", publicId, {
    id: publicId,
    name: publicId,
    sequence_type: sequenceType,
    length: sequenceType === "CDS" ? 1200 : 399,
  });
}

const richGene = graphNode(
  "gene:arabidopsis_thaliana:Atha04G0031690.v1.36",
  "Gene",
  "Atha04G0031690",
  {
    id: "Atha04G0031690.v1.36",
    aliases: ["AT4G30820.Araport11.447"],
    description: "Rich golden gene fixture",
    annotations: { go: ["GO:1", "GO:2", "GO:3", "GO:4"] },
  },
);
const richLocation = graphNode("location:rich", "GeneLocation", "Chr4", {
  genome_location: {
    assembly: "PGCP_v1",
    coordinate_system: "1-based-closed",
    seqid: "Chr4",
    start: 1000,
    end: 9000,
    strand: "+",
  },
});
const richStructure = graphNode("structure:rich", "GeneStructure", "Rich structure", {
  transcripts: Array.from({ length: 27 }, (_, index) => transcript(index + 1)),
});
const richRecord: GeneWikiRecord = {
  node: richGene,
  nodes: [
    richLocation,
    richStructure,
    ...Array.from({ length: 27 }, (_, index) => sequenceNode(index + 1, "CDS")),
    ...Array.from({ length: 27 }, (_, index) => sequenceNode(index + 1, "PROTEIN")),
  ],
  edges: [
    {
      source: richGene.node_id,
      predicate: "belongs_to_species",
      target: "species:arabidopsis_thaliana",
      species_id: "arabidopsis_thaliana",
      source_dataset: "dataset:test",
      evidence: "evidence:test",
      properties: {},
    },
  ],
};

const sparseGene = graphNode(
  "gene:arabidopsis_thaliana:Atha01G0000130.v1.36",
  "Gene",
  "Atha01G0000130",
  {
    id: "Atha01G0000130.v1.36",
    aliases: ["AT1G01130.Araport11.447"],
  },
);
const sparseRecord: GeneWikiRecord = {
  node: sparseGene,
  nodes: [
    graphNode("location:sparse", "GeneLocation", "Chr1", {
      genome_location: {
        assembly: "PGCP_v1",
        coordinate_system: "1-based-closed",
        seqid: "Chr1",
        start: 100,
        end: 900,
        strand: "-",
      },
    }),
    graphNode("structure:sparse", "GeneStructure", "Sparse structure", {
      transcripts: [
        {
          transcript_id: "Atha01G0000130.1.v1.36",
          name: "Atha01G0000130.1",
          location: { seqid: "Chr1", start: 100, end: 900, strand: "-" },
          cds: [{}],
          exons: [],
          utrs: [],
        },
      ],
    }),
    graphNode("seq:sparse:cds", "SequenceRecord", "Atha01G0000130.1.v1.36", {
      id: "Atha01G0000130.1.v1.36",
      sequence_type: "CDS",
      length: 600,
    }),
    graphNode("seq:sparse:protein", "SequenceRecord", "Atha01G0000130.1.v1.36", {
      id: "Atha01G0000130.1.v1.36",
      sequence_type: "PROTEIN",
      length: 199,
    }),
  ],
  edges: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe = vi.fn();
      disconnect = vi.fn();
      unobserve = vi.fn();
    },
  );
});

async function mountGene(publicId: string, gene: GraphNode, record: GeneWikiRecord) {
  vi.mocked(resolveObject).mockResolvedValue(gene);
  vi.mocked(getGeneWikiRecord).mockResolvedValue(record);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/genes/:id", name: "gene", component: GeneView },
      { path: "/sequence-records/:id", name: "sequence-record", component: { template: "<div />" } },
    ],
  });
  await router.push(`/genes/${publicId}`);
  const wrapper = mount(GeneView, { global: { plugins: [createPinia(), router] } });
  await flushPromises();
  return wrapper;
}

const permanentHeadings = [
  "Overview",
  "Identifiers",
  "Location",
  "Structure",
  "Function",
  "Sequences",
  "Homology",
  "Evidence",
  "Publications",
];

describe("GeneView", () => {
  it("renders a rich real-data-shaped gene record", async () => {
    const wrapper = await mountGene("Atha04G0031690.v1.36", richGene, richRecord);
    expect(wrapper.get("h1").text()).toContain("Atha04G0031690");
    expect(wrapper.text()).toContain("27 transcripts");
    expect(wrapper.text()).toContain("CDS (27)");
    expect(wrapper.text()).toContain("Protein (27)");
    expect(wrapper.text()).not.toContain('"transcripts":');
    expect(wrapper.text()).not.toContain("/DATA/data2");
  });

  it("keeps all permanent sections readable for a sparse gene", async () => {
    const wrapper = await mountGene("Atha01G0000130.v1.36", sparseGene, sparseRecord);
    for (const heading of permanentHeadings) {
      expect(wrapper.text()).toContain(heading);
    }
    expect(wrapper.text()).toContain("AT1G01130.Araport11.447");
    expect(wrapper.text()).toContain("Not available");
    expect(wrapper.text()).not.toContain("[object Object]");
  });
});
