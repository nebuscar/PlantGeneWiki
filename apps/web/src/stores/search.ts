import { defineStore } from "pinia";
import { ref } from "vue";

export const useSearchStore = defineStore("search", () => {
  const query = ref("");

  function setQuery(value: string) {
    query.value = value.trim();
  }

  function clearQuery() {
    query.value = "";
  }

  return { query, setQuery, clearQuery };
});
