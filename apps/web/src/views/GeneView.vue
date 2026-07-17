<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import GeneFunctionPanel from "../components/genes/GeneFunctionPanel.vue";
import GeneLocationPanel from "../components/genes/GeneLocationPanel.vue";
import GeneSequencePanel from "../components/genes/GeneSequencePanel.vue";
import GeneStructurePanel from "../components/genes/GeneStructurePanel.vue";
import EvidencePanel from "../components/objects/EvidencePanel.vue";
import KnowledgeSection from "../components/objects/KnowledgeSection.vue";
import NotAvailable from "../components/objects/NotAvailable.vue";
import ObjectPageLayout from "../components/objects/ObjectPageLayout.vue";
import ErrorState from "../components/states/ErrorState.vue";
import LoadingState from "../components/states/LoadingState.vue";
import { useGeneRecord } from "../composables/useGeneRecord";
import { findRelatedNodes, readFunctionAnnotations } from "../lib/gene-record";
import type { GraphEdge } from "../types/graph";

const route = useRoute();
const publicId = computed(() => String(route.params.id ?? ""));
const { node, record, loading, error, reload } = useGeneRecord(publicId);

const sections = [
  { id: "overview", label: "Overview" },
  { id: "identifiers", label: "Identifiers" },
  { id: "location", label: "Location" },
  { id: "structure", label: "Structure" },
  { id: "function", label: "Function" },
  { id: "sequences", label: "Sequences" },
  { id: "homology", label: "Homology" },
  { id: "evidence", label: "Evidence" },
  { id: "publications", label: "Publications" },
];

function property(...keys: string[]) {
  for (const key of keys) {
    const value = node.value?.properties[key];
    if (value !== undefined && value !== null && value !== "") {
      return value;
    }
  }
  return null;
}

const relatedNodes = computed(() => record.value?.nodes ?? []);
const locationNode = computed(
  () => findRelatedNodes(relatedNodes.value, "GeneLocation")[0] ?? node.value,
);
const structureNodes = computed(() => findRelatedNodes(relatedNodes.value, "GeneStructure"));
const sequenceNodes = computed(() => findRelatedNodes(relatedNodes.value, "SequenceRecord"));
const publicationNodes = computed(() => findRelatedNodes(relatedNodes.value, "Literature"));
const homologyEdges = computed(() =>
  (record.value?.edges ?? []).filter((edge) => /ortholog|homolog|orthogroup/i.test(edge.predicate)),
);
const evidenceEdges = computed(() =>
  (record.value?.edges ?? []).filter((edge) => edge.evidence || edge.source_dataset),
);
const overviewDescription = computed(() => readFunctionAnnotations(node.value).description);
const aliases = computed(() => {
  const value = property("aliases");
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === "string");
  }
  return typeof value === "string" ? [value] : [];
});

function edgeLabel(edge: GraphEdge) {
  return `${edge.predicate}: ${edge.source === node.value?.node_id ? edge.target : edge.source}`;
}
</script>

<template>
  <LoadingState v-if="loading" />
  <ErrorState v-else-if="error" :message="error">
    <button type="button" @click="reload">Retry</button>
  </ErrorState>
  <ObjectPageLayout
    v-else
    object-type="Gene"
    :title="node?.label || publicId"
    :subtitle="node?.species_id || 'Species not available'"
    :sections="sections"
  >
    <KnowledgeSection id="overview" title="Overview">
      <p v-if="overviewDescription">{{ overviewDescription }}</p>
      <NotAvailable v-else />
    </KnowledgeSection>

    <KnowledgeSection id="identifiers" title="Identifiers">
      <dl class="field-list">
        <div><dt>Node ID</dt><dd>{{ node?.node_id || "Not available" }}</dd></div>
        <div><dt>Public ID</dt><dd>{{ property("id", "object_id") || node?.label || "Not available" }}</dd></div>
        <div><dt>Aliases</dt><dd><span v-if="aliases.length">{{ aliases.join(", ") }}</span><NotAvailable v-else /></dd></div>
      </dl>
    </KnowledgeSection>

    <KnowledgeSection id="location" title="Location">
      <GeneLocationPanel :node="locationNode" />
    </KnowledgeSection>

    <KnowledgeSection id="structure" title="Structure">
      <GeneStructurePanel :nodes="structureNodes" />
    </KnowledgeSection>

    <KnowledgeSection id="function" title="Function">
      <GeneFunctionPanel :node="node" />
    </KnowledgeSection>

    <KnowledgeSection id="sequences" title="Sequences">
      <GeneSequencePanel :nodes="sequenceNodes" />
    </KnowledgeSection>

    <KnowledgeSection id="homology" title="Homology">
      <ul v-if="homologyEdges.length" class="relation-list">
        <li v-for="(edge, index) in homologyEdges" :key="`${edge.predicate}-${index}`">
          <span class="relation-status">{{ edge.evidence ? "Asserted" : "Inferred" }}</span>
          {{ edgeLabel(edge) }}
        </li>
      </ul>
      <NotAvailable v-else />
    </KnowledgeSection>

    <KnowledgeSection id="evidence" title="Evidence">
      <EvidencePanel :edges="evidenceEdges" />
    </KnowledgeSection>

    <KnowledgeSection id="publications" title="Publications">
      <ul v-if="publicationNodes.length" class="relation-list">
        <li v-for="item in publicationNodes" :key="item.node_id">{{ item.label || item.node_id }}</li>
      </ul>
      <NotAvailable v-else />
    </KnowledgeSection>
  </ObjectPageLayout>
</template>

<style scoped>
.field-list { display: grid; gap: 12px; margin: 0; }
.field-list div { display: grid; grid-template-columns: minmax(110px, 180px) minmax(0, 1fr); gap: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--color-border); }
.field-list dt { color: var(--color-muted); font-weight: 750; }
.field-list dd { margin: 0; overflow-wrap: anywhere; }
.relation-list { display: grid; gap: 10px; padding: 0; margin: 0; list-style: none; }
.relation-list li { padding: 14px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-moss-50); overflow-wrap: anywhere; }
.relation-status { margin-right: 8px; color: var(--color-forest-700); font-size: 0.72rem; font-weight: 800; text-transform: uppercase; }
</style>
