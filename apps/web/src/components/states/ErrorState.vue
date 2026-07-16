<script setup lang="ts">
withDefaults(defineProps<{ title?: string; message?: string }>(), {
  title: "Unable to load data",
  message: "The API did not return the requested knowledge.",
});
</script>

<template>
  <div class="state-card state-card--error" role="alert">
    <div>
      <strong>{{ title }}</strong>
      <p>{{ message }}</p>
      <slot />
    </div>
  </div>
</template>
