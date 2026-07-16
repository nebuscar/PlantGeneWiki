<script setup lang="ts">
withDefaults(defineProps<{ title?: string; message?: string }>(), {
  title: "Planned capability",
  message: "This workflow is defined but not yet available.",
});
</script>

<template>
  <div class="state-card state-card--planning"><div><strong>{{ title }}</strong><p>{{ message }}</p></div></div>
</template>
