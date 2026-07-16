<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import ErrorState from "../components/states/ErrorState.vue";
import LoadingState from "../components/states/LoadingState.vue";
import KnowledgeSection from "../components/objects/KnowledgeSection.vue";
import NotAvailable from "../components/objects/NotAvailable.vue";
import ObjectPageLayout from "../components/objects/ObjectPageLayout.vue";
import { useObjectRecord } from "../composables/useObjectRecord";
import { listSpeciesGenes } from "../services/graph";
import type { GraphNode } from "../types/graph";

const route = useRoute();
const speciesId = computed(() => String(route.params.id ?? "").replace(/^species:/, ""));
const objectId = computed(() => `species:${speciesId.value}`);
const { node, neighborhood, loading, error } = useObjectRecord("Species", objectId);
const genes = ref<GraphNode[]>([]);
const genesLoading = ref(false);
const genesError = ref("");

const sections = [
  { id: "overview", label: "Overview" },
  { id: "taxonomy", label: "Taxonomy" },
  { id: "genome-versions", label: "Genome Versions" },
  { id: "genes", label: "Genes" },
  { id: "datasets", label: "Datasets" },
  { id: "related-species", label: "Related Species" },
  { id: "evidence", label: "Evidence" },
  { id: "publications", label: "Publications" },
];

function text(value: unknown) {
  return typeof value === "object" && value !== null ? JSON.stringify(value, null, 2) : String(value);
}

function property(...keys: string[]) {
  for (const key of keys) {
    const value = node.value?.properties[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return null;
}

function related(type: string) {
  return neighborhood.value?.nodes.filter((item) => item.object_type === type) ?? [];
}

watch(
  speciesId,
  async (id) => {
    genes.value = [];
    genesError.value = "";
    if (!id) return;
    genesLoading.value = true;
    try {
      genes.value = (await listSpeciesGenes(id, 50, 0)).genes;
    } catch (reason) {
      genesError.value = reason instanceof Error ? reason.message : "Unable to load species genes";
    } finally {
      genesLoading.value = false;
    }
  },
  { immediate: true },
);
</script>

<template>
  <LoadingState v-if="loading" />
  <ErrorState v-else-if="error" :message="error" />
  <ObjectPageLayout v-else object-type="Species" :title="node?.label || speciesId" :subtitle="node?.node_id" :sections="sections">
    <KnowledgeSection id="overview" title="Overview"><p v-if="property('description')">{{ text(property("description")) }}</p><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="taxonomy" title="Taxonomy"><pre v-if="property('taxonomy')">{{ text(property("taxonomy")) }}</pre><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="genome-versions" title="Genome Versions"><pre v-if="property('genome_versions', 'version')">{{ text(property("genome_versions", "version")) }}</pre><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="genes" title="Genes">
      <LoadingState v-if="genesLoading" />
      <ErrorState v-else-if="genesError" :message="genesError" />
      <ul v-else-if="genes.length" class="object-list"><li v-for="gene in genes" :key="gene.node_id"><RouterLink :to="{ name: 'gene', params: { id: gene.label || gene.node_id } }">{{ gene.label || gene.node_id }}</RouterLink></li></ul>
      <NotAvailable v-else />
    </KnowledgeSection>
    <KnowledgeSection id="datasets" title="Datasets"><ul v-if="related('Dataset').length" class="object-list"><li v-for="item in related('Dataset')" :key="item.node_id"><RouterLink :to="{ name: 'dataset', params: { id: item.label || item.node_id } }">{{ item.label || item.node_id }}</RouterLink></li></ul><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="related-species" title="Related Species"><ul v-if="related('Species').length" class="object-list"><li v-for="item in related('Species')" :key="item.node_id">{{ item.label || item.node_id }}</li></ul><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="evidence" title="Evidence"><pre v-if="property('evidence_records', 'evidence')">{{ text(property("evidence_records", "evidence")) }}</pre><NotAvailable v-else /></KnowledgeSection>
    <KnowledgeSection id="publications" title="Publications"><ul v-if="related('Literature').length" class="object-list"><li v-for="item in related('Literature')" :key="item.node_id">{{ item.label || item.node_id }}</li></ul><NotAvailable v-else /></KnowledgeSection>
  </ObjectPageLayout>
</template>

<style scoped>
.object-list { display: grid; gap: 8px; padding: 0; margin: 0; list-style: none; }
.object-list li { padding: 12px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-moss-50); }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
