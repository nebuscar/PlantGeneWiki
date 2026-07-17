import { nextTick, ref } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useGeneRecord } from "../../src/composables/useGeneRecord";
import { getGeneWikiRecord, resolveObject } from "../../src/services/graph";
import type { GeneWikiRecord, GraphNode } from "../../src/types/graph";

vi.mock("../../src/services/graph", () => ({
  getGeneWikiRecord: vi.fn(),
  resolveObject: vi.fn(),
}));

const mockedGetGeneWikiRecord = vi.mocked(getGeneWikiRecord);
const mockedResolveObject = vi.mocked(resolveObject);

function makeNode(publicId: string): GraphNode {
  return {
    node_id: `gene:arabidopsis_thaliana:${publicId}`,
    object_type: "Gene",
    label: publicId,
    species_id: "arabidopsis_thaliana",
    source_file: "genes.jsonl",
    properties: { id: publicId },
  };
}

function makeRecord(node: GraphNode): GeneWikiRecord {
  return { node, edges: [], nodes: [] };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

afterEach(() => vi.resetAllMocks());

describe("useGeneRecord", () => {
  it("resolves a public ID and requests its complete Gene Wiki record", async () => {
    const publicId = "Atha01G0000010.v1.36";
    const node = makeNode(publicId);
    const record = makeRecord(node);
    mockedResolveObject.mockResolvedValue(node);
    mockedGetGeneWikiRecord.mockResolvedValue(record);

    const state = useGeneRecord(ref(publicId));

    await vi.waitFor(() => expect(state.record.value).toEqual(record));
    expect(mockedResolveObject).toHaveBeenCalledWith("Gene", publicId);
    expect(mockedGetGeneWikiRecord).toHaveBeenCalledWith(node.node_id);
    expect(state.node.value).toEqual(node);
    expect(state.loading.value).toBe(false);
  });

  it("ignores a stale response after the public ID changes", async () => {
    const firstNode = makeNode("Atha01G0000010.v1.36");
    const secondNode = makeNode("Atha01G0000020.v1.36");
    const firstResponse = deferred<GeneWikiRecord>();
    const secondResponse = deferred<GeneWikiRecord>();
    mockedResolveObject.mockImplementation(async (_objectType, publicId) =>
      publicId === firstNode.label ? firstNode : secondNode,
    );
    mockedGetGeneWikiRecord.mockImplementation((nodeId) =>
      nodeId === firstNode.node_id ? firstResponse.promise : secondResponse.promise,
    );
    const publicId = ref(firstNode.label ?? "");
    const state = useGeneRecord(publicId);
    await vi.waitFor(() =>
      expect(mockedGetGeneWikiRecord).toHaveBeenCalledWith(firstNode.node_id),
    );

    publicId.value = secondNode.label ?? "";
    await nextTick();
    await vi.waitFor(() =>
      expect(mockedGetGeneWikiRecord).toHaveBeenCalledWith(secondNode.node_id),
    );
    const secondRecord = makeRecord(secondNode);
    secondResponse.resolve(secondRecord);
    await vi.waitFor(() => expect(state.record.value).toEqual(secondRecord));

    firstResponse.resolve(makeRecord(firstNode));
    await Promise.resolve();
    await Promise.resolve();
    expect(state.record.value).toEqual(secondRecord);
    expect(state.node.value).toEqual(secondNode);
  });
});
