<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";
import ErrorState from "../components/states/ErrorState.vue";
import LoadingState from "../components/states/LoadingState.vue";
import KnowledgeSection from "../components/objects/KnowledgeSection.vue";
import NotAvailable from "../components/objects/NotAvailable.vue";
import ObjectPageLayout from "../components/objects/ObjectPageLayout.vue";
import { useObjectRecord } from "../composables/useObjectRecord";

const route = useRoute();
const publicId = computed(() => String(route.params.id ?? ""));
const { node, neighborhood, loading, error } = useObjectRecord("SequenceRecord", publicId);
const sections = [
  { id: "overview", label: "Overview" },
  { id: "identifiers", label: "Identifiers" },
  { id: "type", label: "Type" },
  { id: "length", label: "Length" },
  { id: "checksum", label: "Checksum" },
  { id: "source-dataset", label: "Source Dataset" },
  { id: "related-gene", label: "Related Gene" },
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

function related(type: string) {
  return neighborhood.value?.nodes.filter((item) => item.object_type === type) ?? [];
}
</script>

<template>
  <LoadingState v-if="loading" />
  <ErrorState v-else-if="error" :message="error" />
  <ObjectPageLayout v-else object-type="SequenceRecord" :title="node?.label || publicId" :subtitle="node?.node_id" :sections="sections">
    <KnowledgeSection id="overview" title="Overview"><p v-if="property('description')">{{ text(property("description")) }}</p><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="identifiers" title="Identifiers"><p>{{ node?.node_id || "Not available" }}</p></KnowledgeSection>
    <KnowledgeSection id="type" title="Type"><p v-if="property('sequence_type', 'type')">{{ text(property("sequence_type", "type")) }}</p><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="length" title="Length"><p v-if="property('length')">{{ text(property("length")) }}</p><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="checksum" title="Checksum"><p v-if="property('checksum', 'sha256', 'md5')">{{ text(property("checksum", "sha256", "md5")) }}</p><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="source-dataset" title="Source Dataset"><ul v-if="related('Dataset').length" class="object-list"><li v-for="item in related('Dataset')" :key="item.node_id">{{ item.label || item.node_id }}</li></ul><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="related-gene" title="Related Gene"><ul v-if="related('Gene').length" class="object-list"><li v-for="item in related('Gene')" :key="item.node_id"><RouterLink :to="{ name: 'gene', params: { id: item.label || item.node_id } }">{{ item.label || item.node_id }}</RouterLink></li></ul><NotAvailable v-else /></KnowledgeSection>
  </ObjectPageLayout>
</template>

<style scoped>
.object-list { display: grid; gap: 8px; padding: 0; margin: 0; list-style: none; }
.object-list li { padding: 12px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-moss-50); }
</style>
