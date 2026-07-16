import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

export const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    component: () => import("../views/HomeView.vue"),
    meta: { title: "Home" },
  },
  {
    path: "/search",
    name: "search",
    component: () => import("../views/SearchView.vue"),
    meta: { title: "Search" },
  },
  {
    path: "/genes/:id",
    name: "gene",
    component: () => import("../views/GeneView.vue"),
    meta: { title: "Gene" },
  },
  {
    path: "/species/:id",
    name: "species",
    component: () => import("../views/SpeciesView.vue"),
    meta: { title: "Species" },
  },
  {
    path: "/graph",
    name: "graph",
    component: () => import("../views/PlanningView.vue"),
    meta: { title: "Knowledge Graph" },
  },
  {
    path: "/datasets/:id",
    name: "dataset",
    component: () => import("../views/DatasetView.vue"),
    meta: { title: "Dataset" },
  },
  {
    path: "/sequence-records/:id",
    name: "sequence-record",
    component: () => import("../views/SequenceRecordView.vue"),
    meta: { title: "Sequence Record" },
  },
  {
    path: "/literature",
    name: "literature",
    component: () => import("../views/LiteratureView.vue"),
    meta: { title: "Literature" },
  },
  {
    path: "/tools",
    name: "tools",
    component: () => import("../views/ToolsView.vue"),
    meta: { title: "Tools" },
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("../views/NotFoundView.vue"),
    meta: { title: "Not Found" },
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
