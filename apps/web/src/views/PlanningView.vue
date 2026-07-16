<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const title = computed(() => String(route.meta.title ?? "PhytoAtlas"));
</script>

<template>
  <section class="planning-view">
    <p class="eyebrow">PhytoAtlas</p>
    <h1>{{ title }}</h1>
    <p>This route is ready for its API-backed view.</p>
  </section>
</template>
