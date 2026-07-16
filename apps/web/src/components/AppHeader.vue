<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useSearchStore } from "../stores/search";
import GlobalSearch from "./GlobalSearch.vue";

const route = useRoute();
const router = useRouter();
const searchStore = useSearchStore();
const showCompactSearch = computed(() => route.name !== "home");

function openSearch(query: string) {
  searchStore.setQuery(query);
  void router.push({ name: "search", query: { q: query } });
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner">
      <RouterLink class="brand-link" :to="{ name: 'home' }" aria-label="PhytoAtlas home">
        <span class="brand-mark" aria-hidden="true">PA</span>
        <span>PhytoAtlas</span>
      </RouterLink>
      <nav class="primary-nav" aria-label="Primary navigation">
        <RouterLink :to="{ name: 'search' }">Explore</RouterLink>
        <RouterLink :to="{ name: 'graph' }">Knowledge Graph</RouterLink>
        <RouterLink :to="{ name: 'literature' }">Literature</RouterLink>
        <RouterLink :to="{ name: 'tools' }">Tools</RouterLink>
      </nav>
      <GlobalSearch
        v-if="showCompactSearch"
        class="header-search"
        compact
        placeholder="Search PhytoAtlas"
        @submit="openSearch"
      />
    </div>
  </header>
</template>
