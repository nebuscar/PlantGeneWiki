<script setup lang="ts">
import GraphRelationSummary from "./GraphRelationSummary.vue";

const centerQuery = defineModel<string>("centerQuery", { required: true });
const speciesId = defineModel<string>("speciesId", { required: true });
withDefaults(
  defineProps<{
    predicateCounts: Record<string, number>;
    selectedPredicate: string;
    validationError?: string;
  }>(),
  { validationError: "" },
);
defineEmits<{ submit: []; selectPredicate: [predicate: string] }>();
</script>

<template>
  <section class="graph-toolbar" aria-label="Graph controls">
    <form class="graph-toolbar__form" @submit.prevent="$emit('submit')">
      <label>
        <span>Center gene</span>
        <input
          v-model="centerQuery"
          name="center_query"
          type="search"
          placeholder="Atha04G0031690.v1.36"
        />
      </label>
      <label>
        <span>Species</span>
        <input
          v-model="speciesId"
          name="species_id"
          type="text"
          placeholder="arabidopsis_thaliana"
        />
      </label>
      <button type="submit">Load graph</button>
    </form>
    <p v-if="validationError" class="graph-toolbar__error" role="alert">
      {{ validationError }}
    </p>
    <GraphRelationSummary
      :counts="predicateCounts"
      :selected-predicate="selectedPredicate"
      @select="$emit('selectPredicate', $event)"
    />
  </section>
</template>

<style scoped>
.graph-toolbar {
  padding: 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}
.graph-toolbar__form {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr) auto;
  gap: 14px;
  align-items: end;
}
label {
  display: grid;
  gap: 6px;
  color: var(--color-muted);
  font-size: 0.78rem;
  font-weight: 750;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}
input {
  min-width: 0;
  height: 42px;
  padding: 0 11px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-ink);
  background: #fff;
  font-size: 0.92rem;
  font-weight: 500;
  letter-spacing: 0;
}
input:focus {
  border-color: var(--color-leaf-500);
  outline: 3px solid rgb(88 153 87 / 15%);
}
.graph-toolbar__form > button {
  height: 42px;
  padding: 0 20px;
  border: 0;
  border-radius: 8px;
  color: #fff;
  background: var(--color-forest-700);
  cursor: pointer;
  font-size: 0.88rem;
  font-weight: 750;
}
.graph-toolbar__error {
  margin: 12px 0 0;
  color: var(--color-danger);
  font-size: 0.86rem;
  font-weight: 700;
}
@media (max-width: 600px) {
  .graph-toolbar__form {
    grid-template-columns: 1fr;
  }
  .graph-toolbar__form > button {
    width: 100%;
  }
}
</style>
