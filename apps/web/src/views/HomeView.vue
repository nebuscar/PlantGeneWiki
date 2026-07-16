<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import GlobalSearch from "../components/GlobalSearch.vue";
import ErrorState from "../components/states/ErrorState.vue";
import LoadingState from "../components/states/LoadingState.vue";
import PlanningState from "../components/states/PlanningState.vue";
import { getGraphSummary } from "../services/graph";
import { useSearchStore } from "../stores/search";
import type { GraphSummary } from "../types/graph";

const router = useRouter();
const searchStore = useSearchStore();
const summary = ref<GraphSummary | null>(null);
const loading = ref(true);
const error = ref("");

function formatMetric(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function openSearch(query: string) {
  searchStore.setQuery(query);
  void router.push({ name: "search", query: { q: query } });
}

onMounted(async () => {
  try {
    summary.value = await getGraphSummary();
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Unknown API error";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="home-view">
    <section class="hero-section">
      <div class="hero-copy">
        <p class="eyebrow">Plant knowledge, connected</p>
        <h1>Explore plant genomes as a living knowledge atlas.</h1>
        <p class="hero-description">
          Search biological objects, inspect evidence, and move between genes, species,
          sequences, datasets, and graph relationships.
        </p>
      </div>
      <GlobalSearch @submit="openSearch" />
      <div class="example-row">
        <span>Try:</span>
        <button type="button" @click="openSearch('Atha01G0000010.v1.36')">Atha01G0000010.v1.36</button>
        <button type="button" @click="openSearch('Arabidopsis thaliana')">Arabidopsis thaliana</button>
      </div>
    </section>

    <section class="home-section" aria-labelledby="coverage-heading">
      <div class="section-heading">
        <p class="eyebrow">Current coverage</p>
        <h2 id="coverage-heading">A graph-backed foundation</h2>
      </div>
      <LoadingState v-if="loading" />
      <ErrorState v-else-if="error" :message="error" />
      <div v-else-if="summary" class="metric-grid">
        <article class="metric-card">
          <strong>{{ formatMetric(summary.node_count) }}</strong>
          <span>Knowledge objects</span>
        </article>
        <article class="metric-card">
          <strong>{{ formatMetric(summary.edge_count) }}</strong>
          <span>Typed relationships</span>
        </article>
        <article class="metric-card">
          <strong>{{ formatMetric(Object.keys(summary.node_types).length) }}</strong>
          <span>Object types</span>
        </article>
      </div>
    </section>

    <section class="home-section object-section" aria-labelledby="objects-heading">
      <div class="section-heading">
        <p class="eyebrow">Knowledge objects</p>
        <h2 id="objects-heading">Enter the atlas from any object.</h2>
      </div>
      <div class="object-grid">
        <RouterLink :to="{ name: 'search', query: { object_type: 'Gene' } }"><span>Gene</span><p>Identifiers, locations, sequences, functions, and evidence.</p></RouterLink>
        <RouterLink :to="{ name: 'search', query: { object_type: 'Species' } }"><span>Species</span><p>Genome resources, annotations, traits, and comparative context.</p></RouterLink>
        <RouterLink :to="{ name: 'search', query: { object_type: 'Dataset' } }"><span>Dataset</span><p>Versioned sources with provenance and update records.</p></RouterLink>
        <RouterLink :to="{ name: 'search', query: { object_type: 'SequenceRecord' } }"><span>Sequence</span><p>Traceable CDS and protein records linked to genes.</p></RouterLink>
      </div>
    </section>

    <section class="home-section feature-grid">
      <article class="feature-card feature-card--graph">
        <p class="eyebrow">Relationship reasoning</p>
        <h2>Navigate the knowledge graph.</h2>
        <p>Inspect typed biological relationships around a selected object.</p>
        <RouterLink class="text-link" :to="{ name: 'graph' }">Open Knowledge Graph</RouterLink>
      </article>
      <article class="feature-card">
        <p class="eyebrow">Analysis workflows</p>
        <h2>Move from knowledge to computation.</h2>
        <PlanningState message="GO, KEGG, BLAST, and additional analyses will be connected through verified API workflows." />
      </article>
    </section>
  </div>
</template>
