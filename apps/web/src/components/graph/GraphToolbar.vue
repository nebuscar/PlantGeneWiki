<script setup lang="ts">
const centerQuery = defineModel<string>("centerQuery", { required: true });
const speciesId = defineModel<string>("speciesId", { required: true });
const predicate = defineModel<string>("predicate", { required: true });
defineEmits<{ submit: [] }>();
</script>

<template>
  <form class="graph-toolbar" @submit.prevent="$emit('submit')">
    <label>
      <span>Center gene</span>
      <input v-model="centerQuery" name="center_query" type="search" placeholder="Atha01G0000010.v1.36" />
    </label>
    <label>
      <span>Species</span>
      <input v-model="speciesId" name="species_id" type="text" placeholder="arabidopsis_thaliana" />
    </label>
    <label>
      <span>Predicate</span>
      <input v-model="predicate" name="predicate" type="text" list="predicate-options" placeholder="All relationships" />
      <datalist id="predicate-options">
        <option value="belongs_to_species" />
        <option value="has_sequence" />
        <option value="has_location" />
        <option value="has_structure" />
        <option value="belongs_to_orthogroup" />
      </datalist>
    </label>
    <button type="submit">Load graph</button>
  </form>
</template>

<style scoped>
.graph-toolbar { display: grid; grid-template-columns: 1.2fr 1fr 1fr auto; gap: 14px; padding: 20px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); box-shadow: var(--shadow-card); }
label { display: grid; gap: 6px; color: var(--color-muted); font-size: 0.78rem; font-weight: 750; text-transform: uppercase; }
input { min-width: 0; height: 42px; padding: 0 11px; border: 1px solid var(--color-border); border-radius: 8px; }
button { align-self: end; height: 42px; padding: 0 20px; border: 0; border-radius: 8px; color: #fff; background: var(--color-forest-700); cursor: pointer; font-weight: 750; }
@media (max-width: 900px) { .graph-toolbar { grid-template-columns: 1fr 1fr; } }
@media (max-width: 600px) { .graph-toolbar { grid-template-columns: 1fr; } }
</style>
