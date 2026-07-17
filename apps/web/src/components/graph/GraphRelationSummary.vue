<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  counts: Record<string, number>;
  selectedPredicate: string;
}>();
const emit = defineEmits<{ select: [predicate: string] }>();
const coreCount = computed(() =>
  Object.entries(props.counts)
    .filter(([predicate]) => predicate !== "has_sequence")
    .reduce((total, [, count]) => total + count, 0),
);
const predicates = computed(() =>
  Object.entries(props.counts).sort(([left], [right]) => left.localeCompare(right)),
);

function predicateLabel(predicate: string): string {
  return predicate.replaceAll("_", " ");
}
</script>

<template>
  <div class="relation-summary" role="group" aria-labelledby="relationship-filter-label">
    <span id="relationship-filter-label">Relationship view</span>
    <div class="relation-summary__options">
      <button
        type="button"
        data-predicate=""
        :aria-pressed="selectedPredicate === ''"
        @click="emit('select', '')"
      >
        Core · {{ coreCount }}
      </button>
      <button
        v-for="[predicate, count] in predicates"
        :key="predicate"
        type="button"
        :data-predicate="predicate"
        :aria-pressed="selectedPredicate === predicate"
        @click="emit('select', predicate)"
      >
        {{ predicateLabel(predicate) }} · {{ count }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.relation-summary {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}
.relation-summary > span {
  color: var(--color-muted);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.045em;
  text-transform: uppercase;
}
.relation-summary__options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
button {
  min-height: 34px;
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-muted);
  background: #fff;
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: capitalize;
}
button:hover {
  border-color: var(--color-leaf-500);
  color: var(--color-forest-700);
}
button[aria-pressed="true"] {
  border-color: var(--color-forest-700);
  color: #fff;
  background: var(--color-forest-700);
}
@media (max-width: 760px) {
  .relation-summary {
    grid-template-columns: 1fr;
  }
}
</style>
