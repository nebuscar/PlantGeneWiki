<script setup lang="ts">
import ObjectSectionNav, { type ObjectSection } from "./ObjectSectionNav.vue";

defineProps<{
  objectType: string;
  title: string;
  subtitle?: string;
  sections: ObjectSection[];
}>();
</script>

<template>
  <div class="object-page">
    <header class="object-hero">
      <p class="eyebrow">{{ objectType }}</p>
      <h1>{{ title }}</h1>
      <p v-if="subtitle">{{ subtitle }}</p>
    </header>
    <div class="object-page__layout">
      <ObjectSectionNav :sections="sections" />
      <div class="object-page__content"><slot /></div>
    </div>
  </div>
</template>

<style scoped>
.object-hero { margin-bottom: 34px; padding: 36px; border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: linear-gradient(145deg, #fff, var(--color-moss-50)); }
.object-hero h1 { margin-bottom: 10px; overflow-wrap: anywhere; color: var(--color-forest-950); font-size: clamp(2.2rem, 6vw, 4.6rem); letter-spacing: -0.05em; line-height: 1; }
.object-hero > p:last-child { margin: 0; color: var(--color-muted); }
.object-page__layout { display: grid; grid-template-columns: 190px minmax(0, 1fr); gap: 30px; }
.object-page__content { display: grid; gap: 20px; min-width: 0; }
@media (max-width: 800px) {
  .object-page__layout { grid-template-columns: 1fr; }
  .object-page__layout :deep(.object-section-nav) { position: static; grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .object-page__layout :deep(.object-section-nav p) { grid-column: 1 / -1; }
}
</style>
