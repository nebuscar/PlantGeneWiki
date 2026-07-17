<script setup lang="ts">
import { computed } from "vue";
import { readTranscriptSummaries } from "../../lib/gene-record";
import type { GraphNode } from "../../types/graph";
import NotAvailable from "../objects/NotAvailable.vue";

const props = defineProps<{ nodes: GraphNode[] }>();
const transcripts = computed(() => props.nodes.flatMap(readTranscriptSummaries));
</script>

<template>
  <div v-if="transcripts.length" class="structure-panel">
    <p class="summary">{{ transcripts.length }} transcripts</p>
    <ul class="transcript-list">
      <li v-for="transcript in transcripts" :key="transcript.transcriptId">
        <div><strong>{{ transcript.name || transcript.transcriptId }}</strong><code>{{ transcript.transcriptId }}</code></div>
        <span>{{ transcript.location || "Location not available" }}</span>
        <dl>
          <div><dt>CDS</dt><dd>{{ transcript.cdsCount }}</dd></div>
          <div><dt>Exons</dt><dd>{{ transcript.exonCount }}</dd></div>
          <div><dt>UTRs</dt><dd>{{ transcript.utrCount }}</dd></div>
        </dl>
      </li>
    </ul>
  </div>
  <NotAvailable v-else />
</template>

<style scoped>
.structure-panel { display: grid; gap: 14px; }
.summary { margin: 0; color: var(--color-forest-700); font-weight: 800; }
.transcript-list { display: grid; gap: 12px; padding: 0; margin: 0; list-style: none; }
.transcript-list li { display: grid; gap: 10px; padding: 16px; border: 1px solid var(--color-border); border-radius: 10px; background: var(--color-moss-50); }
.transcript-list li > div { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px 16px; }
.transcript-list code, .transcript-list span { overflow-wrap: anywhere; color: var(--color-muted); }
.transcript-list dl { display: flex; flex-wrap: wrap; gap: 20px; margin: 0; }
.transcript-list dl div { display: flex; gap: 6px; }
.transcript-list dt { color: var(--color-muted); }
.transcript-list dd { margin: 0; font-weight: 800; }
</style>
