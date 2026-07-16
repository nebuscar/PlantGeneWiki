<script setup lang="ts">
withDefaults(defineProps<{ title?: string; message?: string }>(), {
  title: "No results",
  message: "Try another identifier, keyword, or filter.",
});
</script>

<template>
  <div class="state-card"><div><strong>{{ title }}</strong><p>{{ message }}</p></div></div>
</template>
