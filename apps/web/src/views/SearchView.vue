<script setup lang="ts">
import { watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import EmptyState from "../components/states/EmptyState.vue";
import ErrorState from "../components/states/ErrorState.vue";
import LoadingState from "../components/states/LoadingState.vue";
import SearchFilters from "../components/search/SearchFilters.vue";
import SearchResultCard from "../components/search/SearchResultCard.vue";
import { useGraphSearch } from "../composables/useGraphSearch";
import { useSearchStore } from "../stores/search";

const route = useRoute();
const router = useRouter();
const searchStore = useSearchStore();
const { filters, loading, error, nodes, count, setFilters, executeSearch } = useGraphSearch();

function queryValue(value: unknown) {
  return typeof value === "string" ? value : "";
}

function loadRouteState() {
  setFilters({
    q: queryValue(route.query.q),
    objectType: queryValue(route.query.object_type),
    speciesId: queryValue(route.query.species_id),
  });
  searchStore.setQuery(filters.q);
  void executeSearch();
}

function submitSearch() {
  const query: Record<string, string> = {};
  if (filters.q.trim()) {
    query.q = filters.q.trim();
  }
  if (filters.objectType) {
    query.object_type = filters.objectType;
  }
  if (filters.speciesId.trim()) {
    query.species_id = filters.speciesId.trim();
  }
  void router.push({ name: "search", query });
}

watch(() => route.query, loadRouteState, { immediate: true });
</script>

<template>
  <div class="search-view">
    <header class="search-heading">
      <p class="eyebrow">Unified graph search</p>
      <h1>Explore PhytoAtlas</h1>
      <p>Find indexed knowledge objects by identifier or label, then narrow results by object type and species.</p>
    </header>
    <form id="search-form" class="search-page-form" role="search" @submit.prevent="submitSearch">
      <label class="sr-only" for="search-page-query">Search knowledge objects</label>
      <input
        id="search-page-query"
        v-model="filters.q"
        name="q"
        type="search"
        placeholder="Enter a gene, species, dataset, or sequence identifier"
        autocomplete="off"
      />
      <button type="submit">Search</button>
    </form>
    <div class="search-layout">
      <SearchFilters v-model:object-type="filters.objectType" v-model:species-id="filters.speciesId" />
      <section class="search-results" aria-live="polite">
        <div class="results-heading">
          <div>
            <p class="eyebrow">Results</p>
            <h2>{{ filters.q ? `${count} indexed objects` : "Start with a search term" }}</h2>
          </div>
        </div>
        <LoadingState v-if="loading" />
        <ErrorState v-else-if="error" :message="error" />
        <EmptyState
          v-else-if="filters.q && nodes.length === 0"
          title="No matching objects"
          message="Try a full identifier, another object type, or remove the species filter."
        />
        <EmptyState
          v-else-if="!filters.q"
          title="Search the knowledge graph"
          message="Enter an identifier or label to query the current graph index."
        />
        <ol v-else class="result-list">
          <li v-for="node in nodes" :key="node.node_id"><SearchResultCard :node="node" /></li>
        </ol>
      </section>
    </div>
  </div>
</template>

<style scoped>
.search-heading { max-width: 760px; margin-bottom: 28px; }
.search-heading h1 { margin-bottom: 12px; color: var(--color-forest-950); font-size: clamp(2.4rem, 6vw, 4.5rem); letter-spacing: -0.05em; }
.search-heading > p:last-child { color: var(--color-muted); }
.search-page-form { display: grid; grid-template-columns: minmax(0, 1fr) auto; margin-bottom: 28px; overflow: hidden; border: 1px solid var(--color-border); border-radius: 12px; background: #fff; }
.search-page-form input { min-width: 0; height: 56px; padding: 0 18px; border: 0; outline: 0; }
.search-page-form button { min-width: 120px; border: 0; color: #fff; background: var(--color-forest-700); font-weight: 750; }
.search-layout { display: grid; grid-template-columns: minmax(220px, 280px) minmax(0, 1fr); gap: 28px; }
.results-heading { display: flex; justify-content: space-between; margin-bottom: 18px; }
.results-heading h2 { font-size: 1.35rem; }
.result-list { display: grid; gap: 14px; padding: 0; margin: 0; list-style: none; }
@media (max-width: 760px) { .search-layout { grid-template-columns: 1fr; } }
</style>
