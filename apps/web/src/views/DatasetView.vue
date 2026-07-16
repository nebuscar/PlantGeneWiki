<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import ErrorState from "../components/states/ErrorState.vue";
import LoadingState from "../components/states/LoadingState.vue";
import KnowledgeSection from "../components/objects/KnowledgeSection.vue";
import NotAvailable from "../components/objects/NotAvailable.vue";
import ObjectPageLayout from "../components/objects/ObjectPageLayout.vue";
import { useObjectRecord } from "../composables/useObjectRecord";

const route = useRoute();
const publicId = computed(() => String(route.params.id ?? ""));
const { node, neighborhood, loading, error } = useObjectRecord("Dataset", publicId);
const sections = [
  { id: "overview", label: "Overview" },
  { id: "identifiers", label: "Identifiers" },
  { id: "source", label: "Source" },
  { id: "version", label: "Version" },
  { id: "coverage", label: "Coverage" },
  { id: "provenance", label: "Provenance" },
  { id: "related-objects", label: "Related Objects" },
];

function property(...keys: string[]) {
  for (const key of keys) {
    const value = node.value?.properties[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return null;
}

function text(value: unknown) {
  return typeof value === "object" && value !== null ? JSON.stringify(value, null, 2) : String(value);
}
</script>

<template>
  <LoadingState v-if="loading" />
  <ErrorState v-else-if="error" :message="error" />
  <ObjectPageLayout v-else object-type="Dataset" :title="node?.label || publicId" :subtitle="node?.node_id" :sections="sections">
    <KnowledgeSection id="overview" title="Overview"><p v-if="property('description', 'dataset_type')">{{ text(property("description", "dataset_type")) }}</p><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="identifiers" title="Identifiers"><p>{{ node?.node_id || "Not available" }}</p></KnowledgeSection>
    <KnowledgeSection id="source" title="Source"><pre v-if="property('source', 'provider')">{{ text(property("source", "provider")) }}</pre><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="version" title="Version"><p v-if="property('version', 'release')">{{ text(property("version", "release")) }}</p><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="coverage" title="Coverage"><pre v-if="property('coverage', 'summary')">{{ text(property("coverage", "summary")) }}</pre><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="provenance" title="Provenance"><pre v-if="property('provenance', 'source_files', 'updated_at')">{{ text(property("provenance", "source_files", "updated_at")) }}</pre><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="related-objects" title="Related Objects">
      <ul v-if="neighborhood?.nodes.length" class="object-list"><li v-for="item in neighborhood.nodes" :key="item.node_id">{{ item.object_type }}: {{ item.label || item.node_id }}</li></ul>
      <NotAvailable v-else />
    </KnowledgeSection>
  </ObjectPageLayout>
</template>

<style scoped>
.object-list { display: grid; gap: 8px; padding: 0; margin: 0; list-style: none; }
.object-list li { padding: 12px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-moss-50); }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
