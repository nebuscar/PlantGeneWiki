<script setup lang="ts">
import PlanningState from "../components/states/PlanningState.vue";
</script>

<template>
  <section class="planning-module">
    <p class="eyebrow">Literature</p>
    <h1>Evidence-aware literature curation</h1>
    <PlanningState title="Planned module" message="The literature module will collect, screen, classify, extract, and trace plant genomics evidence through reviewed pipelines." />
  </section>
</template>

<style scoped>
.planning-module { max-width: 820px; }
.planning-module h1 { color: var(--color-forest-950); font-size: clamp(2.3rem, 6vw, 4.8rem); letter-spacing: -0.05em; }
</style>
