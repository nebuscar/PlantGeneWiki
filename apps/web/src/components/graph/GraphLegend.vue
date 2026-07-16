<script setup lang="ts">
const items = [
  ["Gene", "#1769aa"],
  ["Species", "#3b8c59"],
  ["Dataset", "#d77a1f"],
  ["Sequence", "#7b61d1"],
  ["Location / Structure", "#71808a"],
];
</script>

<template>
  <div class="graph-legend" aria-label="Graph legend">
    <span v-for="[label, color] in items" :key="label">
      <i :style="{ backgroundColor: color }"></i>{{ label }}
    </span>
  </div>
</template>

<style scoped>
.graph-legend { display: flex; flex-wrap: wrap; gap: 12px; color: var(--color-muted); font-size: 0.78rem; }
.graph-legend span { display: inline-flex; align-items: center; gap: 6px; }
.graph-legend i { width: 9px; height: 9px; border-radius: 50%; }
</style>
