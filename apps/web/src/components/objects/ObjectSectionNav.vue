<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

export interface ObjectSection {
  id: string;
  label: string;
}

const props = defineProps<{ sections: ObjectSection[] }>();
const activeSection = ref(props.sections[0]?.id ?? "");
let observer: IntersectionObserver | null = null;

function openSection(event: MouseEvent, sectionId: string) {
  event.preventDefault();
  const section = document.getElementById(sectionId);
  if (!section) {
    return;
  }
  activeSection.value = sectionId;
  window.history.replaceState(null, "", `#${sectionId}`);
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

onMounted(() => {
  if (!("IntersectionObserver" in window)) {
    return;
  }
  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
      if (visible) {
        activeSection.value = visible.target.id;
      }
    },
    { rootMargin: "-96px 0px -60% 0px", threshold: [0.1, 0.4, 0.8] },
  );
  for (const section of props.sections) {
    const element = document.getElementById(section.id);
    if (element) {
      observer.observe(element);
    }
  }
});

onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <nav class="object-section-nav" aria-label="On this page">
    <p>On this page</p>
    <a
      v-for="section in sections"
      :key="section.id"
      :href="`#${section.id}`"
      :class="{ 'is-active': activeSection === section.id }"
      @click="openSection($event, section.id)"
    >{{ section.label }}</a>
  </nav>
</template>

<style scoped>
.object-section-nav { position: sticky; top: 100px; display: grid; gap: 3px; align-self: start; }
.object-section-nav p { margin: 0 0 10px; color: var(--color-muted); font-size: 0.78rem; font-weight: 800; text-transform: uppercase; }
.object-section-nav a { padding: 8px 12px; border-left: 3px solid transparent; color: var(--color-muted); text-decoration: none; }
.object-section-nav a.is-active { border-left-color: var(--color-leaf-500); color: var(--color-forest-900); background: var(--color-moss-50); font-weight: 750; }
</style>
