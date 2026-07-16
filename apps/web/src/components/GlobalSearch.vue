<script setup lang="ts">
import { ref } from "vue";

withDefaults(
  defineProps<{
    placeholder?: string;
    compact?: boolean;
  }>(),
  {
    placeholder: "Search genes, species, datasets, and sequences",
    compact: false,
  },
);

const emit = defineEmits<{
  submit: [query: string];
}>();
const query = ref("");

function submitSearch() {
  const value = query.value.trim();
  if (!value) {
    return;
  }
  query.value = value;
  emit("submit", value);
}
</script>

<template>
  <form class="global-search" :class="{ 'global-search--compact': compact }" role="search" @submit.prevent="submitSearch">
    <label class="sr-only" for="global-search-input">Search PhytoAtlas</label>
    <input
      id="global-search-input"
      v-model="query"
      name="q"
      type="search"
      :placeholder="placeholder"
      autocomplete="off"
    />
    <button type="submit" aria-label="Search">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m21 21-4.35-4.35m2.35-5.65a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" />
      </svg>
      <span v-if="!compact">Search</span>
    </button>
  </form>
</template>
