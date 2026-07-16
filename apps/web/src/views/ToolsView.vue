<script setup lang="ts">
import PlanningState from "../components/states/PlanningState.vue";
</script>

<template>
  <section class="planning-module">
    <p class="eyebrow">Tools</p>
    <h1>Analysis connected to knowledge objects</h1>
    <PlanningState title="Planned module" message="GO, KEGG, BLAST, genome browsing, and additional analyses will be exposed only after verified backend workflows are available." />
  </section>
</template>

<style scoped>
.planning-module { max-width: 820px; }
.planning-module h1 { color: var(--color-forest-950); font-size: clamp(2.3rem, 6vw, 4.8rem); letter-spacing: -0.05em; }
</style>
