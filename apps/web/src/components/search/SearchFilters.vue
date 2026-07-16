<script setup lang="ts">
const objectType = defineModel<string>("objectType", { required: true });
const speciesId = defineModel<string>("speciesId", { required: true });
</script>

<template>
  <aside class="search-filters" aria-label="Search filters">
    <div class="filter-heading">
      <h2>Filters</h2>
      <p>Use fields supported by the graph API.</p>
    </div>
    <label>
      <span>Object type</span>
      <select v-model="objectType" name="object_type">
        <option value="">All object types</option>
        <option value="Gene">Gene</option>
        <option value="Species">Species</option>
        <option value="Dataset">Dataset</option>
        <option value="SequenceRecord">Sequence record</option>
        <option value="GeneLocation">Gene location</option>
        <option value="GeneStructure">Gene structure</option>
      </select>
    </label>
    <label>
      <span>Species ID</span>
      <input
        v-model="speciesId"
        name="species_id"
        type="text"
        placeholder="arabidopsis_thaliana"
        autocomplete="off"
      />
    </label>
    <button type="submit" form="search-form">Apply filters</button>
  </aside>
</template>

<style scoped>
.search-filters { display: grid; gap: 20px; padding: 24px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); align-self: start; }
.filter-heading h2 { margin-bottom: 4px; font-size: 1.15rem; }
.filter-heading p { margin: 0; color: var(--color-muted); font-size: 0.86rem; }
label { display: grid; gap: 7px; color: var(--color-forest-900); font-size: 0.86rem; font-weight: 700; }
input, select { width: 100%; height: 42px; padding: 0 11px; border: 1px solid var(--color-border); border-radius: 8px; background: #fff; }
button { height: 42px; border: 0; border-radius: 8px; color: #fff; background: var(--color-forest-700); cursor: pointer; font-weight: 750; }
</style>
