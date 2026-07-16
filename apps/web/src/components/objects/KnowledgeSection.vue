<script setup lang="ts">
defineProps<{ id: string; title: string; description?: string }>();
</script>

<template>
  <section :id="id" class="knowledge-section">
    <header>
      <h2>{{ title }}</h2>
      <p v-if="description">{{ description }}</p>
    </header>
    <div class="knowledge-section__body"><slot /></div>
  </section>
</template>

<style scoped>
.knowledge-section { scroll-margin-top: 104px; padding: 34px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); box-shadow: var(--shadow-card); }
.knowledge-section header { margin-bottom: 20px; }
.knowledge-section h2 { margin-bottom: 6px; color: var(--color-forest-950); font-size: 1.55rem; }
.knowledge-section header p { margin: 0; color: var(--color-muted); }
.knowledge-section__body { min-width: 0; }
</style>
