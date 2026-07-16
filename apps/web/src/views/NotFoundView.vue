<script setup lang="ts">
import { RouterLink } from "vue-router";
</script>

<template>
  <section class="planning-view">
    <p class="eyebrow">404</p>
    <h1>Page not found</h1>
    <p>The requested PhytoAtlas route does not exist.</p>
    <RouterLink :to="{ name: 'home' }">Return home</RouterLink>
  </section>
</template>
