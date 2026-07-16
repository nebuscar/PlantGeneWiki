<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";
import ErrorState from "../components/states/ErrorState.vue";
import LoadingState from "../components/states/LoadingState.vue";
import EvidencePanel from "../components/objects/EvidencePanel.vue";
import KnowledgeSection from "../components/objects/KnowledgeSection.vue";
import NotAvailable from "../components/objects/NotAvailable.vue";
import ObjectPageLayout from "../components/objects/ObjectPageLayout.vue";
import { useObjectRecord } from "../composables/useObjectRecord";
import type { GraphEdge, GraphNode } from "../types/graph";

const route = useRoute();
const publicId = computed(() => String(route.params.id ?? ""));
const { node, neighborhood, loading, error, reload } = useObjectRecord("Gene", publicId);

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

function valueText(value: unknown) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

function relatedNodes(objectType: string) {
  return neighborhood.value?.nodes.filter((item) => item.object_type === objectType) ?? [];
}

function relationEdges(pattern: RegExp) {
  return neighborhood.value?.edges.filter((edge) => pattern.test(edge.predicate)) ?? [];
}

const locationNodes = computed(() => relatedNodes("GeneLocation"));
const structureNodes = computed(() => relatedNodes("GeneStructure"));
const sequenceNodes = computed(() => relatedNodes("SequenceRecord"));
const publicationNodes = computed(() => relatedNodes("Literature"));
const homologyEdges = computed(() => relationEdges(/ortholog|homolog|orthogroup/i));
const evidenceEdges = computed(() =>
  (neighborhood.value?.edges ?? []).filter((edge) => edge.evidence || edge.source_dataset),
);

function objectRoute(item: GraphNode) {
  const routes: Record<string, string> = {
    Gene: "gene",
    Species: "species",
    Dataset: "dataset",
    SequenceRecord: "sequence-record",
  };
  const name = routes[item.object_type];
  const id = typeof item.properties.id === "string" ? item.properties.id : item.label || item.node_id;
  return name ? { name, params: { id } } : null;
}

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
      <p v-if="property('description', 'function')">{{ valueText(property("description", "function")) }}</p>
      <NotAvailable v-else />
    </KnowledgeSection>

    <KnowledgeSection id="identifiers" title="Identifiers">
      <dl class="field-list">
        <div><dt>Node ID</dt><dd>{{ node?.node_id || "Not available" }}</dd></div>
        <div><dt>Public ID</dt><dd>{{ property("id", "object_id") || node?.label || "Not available" }}</dd></div>
        <div><dt>Aliases</dt><dd><span v-if="property('aliases')">{{ valueText(property("aliases")) }}</span><NotAvailable v-else /></dd></div>
      </dl>
    </KnowledgeSection>

    <KnowledgeSection id="location" title="Location">
      <ul v-if="locationNodes.length" class="relation-list">
        <li v-for="item in locationNodes" :key="item.node_id"><strong>{{ item.label }}</strong><pre>{{ valueText(item.properties) }}</pre></li>
      </ul>
      <p v-else-if="property('location', 'genome_location')">{{ valueText(property("location", "genome_location")) }}</p>
      <NotAvailable v-else />
    </KnowledgeSection>

    <KnowledgeSection id="structure" title="Structure">
      <ul v-if="structureNodes.length" class="relation-list">
        <li v-for="item in structureNodes" :key="item.node_id"><strong>{{ item.label }}</strong><pre>{{ valueText(item.properties) }}</pre></li>
      </ul>
      <p v-else-if="property('structure', 'transcripts')">{{ valueText(property("structure", "transcripts")) }}</p>
      <NotAvailable v-else />
    </KnowledgeSection>

    <KnowledgeSection id="function" title="Function">
      <pre v-if="property('annotations', 'go', 'function')">{{ valueText(property("annotations", "go", "function")) }}</pre>
      <NotAvailable v-else />
    </KnowledgeSection>

    <KnowledgeSection id="sequences" title="Sequences">
      <ul v-if="sequenceNodes.length" class="relation-list">
        <li v-for="item in sequenceNodes" :key="item.node_id">
          <RouterLink v-if="objectRoute(item)" :to="objectRoute(item)!">{{ item.label || item.node_id }}</RouterLink>
          <span v-else>{{ item.label || item.node_id }}</span>
        </li>
      </ul>
      <NotAvailable v-else />
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
pre { max-width: 100%; overflow: auto; white-space: pre-wrap; color: var(--color-ink); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.84rem; }
</style>
