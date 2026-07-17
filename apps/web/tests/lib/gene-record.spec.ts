import { describe, expect, it } from "vitest";
import {
  findRelatedNodes,
  groupSequenceRecords,
  readFunctionAnnotations,
  readGenomeLocation,
  readTranscriptSummaries,
} from "../../src/lib/gene-record";
import type { GraphNode } from "../../src/types/graph";

function graphNode(
  nodeId: string,
  objectType: string,
  properties: Record<string, unknown>,
): GraphNode {
  return {
    node_id: nodeId,
    object_type: objectType,
    label: nodeId,
    species_id: "arabidopsis_thaliana",
    source_file: "/DATA/data2/private.jsonl",
    properties,
  };
}

describe("gene record formatters", () => {
  it("reads stable genome location fields", () => {
    const node = graphNode("location:gene:test", "GeneLocation", {
      genome_location: {
        assembly: "PGCP_v1",
        coordinate_system: "1-based-closed",
        end: 5899,
        seqid: "Chr1",
        start: 3631,
        strand: "+",
      },
    });

    expect(readGenomeLocation(node)).toEqual({
      assembly: "PGCP_v1",
      coordinates: "Chr1:3631-5899 (+)",
      strand: "+",
      coordinateSystem: "1-based-closed",
    });
  });

  it("summarizes transcripts without exposing raw properties", () => {
    const node = graphNode("structure:gene:test", "GeneStructure", {
      source_file: "/DATA/data2/internal.gff3",
      transcripts: [
        {
          transcript_id: "Atha01G0000010.1.v1.36",
          name: "Atha01G0000010.1",
          location: { seqid: "Chr1", start: 3631, end: 5899, strand: "+" },
          cds: [{}, {}, {}, {}, {}, {}],
          exons: [],
          utrs: [{}, {}],
        },
      ],
    });

    const summaries = readTranscriptSummaries(node);
    expect(summaries).toEqual([
      {
        transcriptId: "Atha01G0000010.1.v1.36",
        name: "Atha01G0000010.1",
        location: "Chr1:3631-5899 (+)",
        cdsCount: 6,
        exonCount: 0,
        utrCount: 2,
      },
    ]);
    expect(JSON.stringify(summaries)).not.toContain("source_file");
    expect(JSON.stringify(summaries)).not.toContain("/DATA/data2");
  });

  it("reads function annotations defensively", () => {
    const node = graphNode("gene:test", "Gene", {
      description: "No apical meristem protein",
      annotations: {
        go: ["GO:0006355", "GO:0003677"],
        transcription_factor: { type: "TF", family: "NAC" },
      },
    });

    expect(readFunctionAnnotations(node)).toEqual({
      description: "No apical meristem protein",
      goTerms: ["GO:0006355", "GO:0003677"],
      tfType: "TF",
      tfFamily: "NAC",
    });
  });

  it("groups CDS and protein records with route-safe IDs", () => {
    const cds = graphNode("seq:cds:test", "SequenceRecord", {
      id: "Atha01G0000010.1.v1.36",
      name: "Atha01G0000010.1.v1.36",
      sequence_type: "CDS",
      length: 1290,
    });
    const protein = graphNode("seq:protein:test", "SequenceRecord", {
      id: "Atha01G0000010.1.v1.36",
      name: "Atha01G0000010.1.v1.36",
      sequence_type: "PROTEIN",
      length: 429,
    });

    const groups = groupSequenceRecords([protein, cds]);
    expect(groups.cds).toEqual([
      {
        nodeId: "seq:cds:test",
        publicId: "Atha01G0000010.1.v1.36",
        name: "Atha01G0000010.1.v1.36",
        length: 1290,
      },
    ]);
    expect(groups.protein).toHaveLength(1);
    expect(groups.protein[0].length).toBe(429);
  });

  it("finds related nodes by type in stable order", () => {
    const second = graphNode("sequence:2", "SequenceRecord", {});
    const first = graphNode("sequence:1", "SequenceRecord", {});
    const location = graphNode("location:1", "GeneLocation", {});
    expect(findRelatedNodes([second, location, first], "SequenceRecord")).toEqual([
      first,
      second,
    ]);
  });
});
