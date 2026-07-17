import type { StylesheetJson } from "cytoscape";

export const graphStyles: StylesheetJson = [
  {
    selector: "node",
    style: { label: "", "background-color": "#71808a", width: 34, height: 34 },
  },
  { selector: 'node[objectType = "Gene"]', style: { "background-color": "#1769aa" } },
  { selector: 'node[objectType = "Species"]', style: { "background-color": "#3b8c59" } },
  { selector: 'node[objectType = "Dataset"]', style: { "background-color": "#d77a1f" } },
  {
    selector: 'node[objectType = "SequenceRecord"]',
    style: { "background-color": "#7b61d1" },
  },
  {
    selector: "node[?isCenter]",
    style: {
      width: 48,
      height: 48,
      "border-width": 4,
      "border-color": "#0b3d36",
    },
  },
  {
    selector: "node[?isCenter], node:selected, node.hovered",
    style: {
      label: "data(label)",
      "font-size": 10,
      "text-wrap": "ellipsis",
      "text-max-width": "110px",
      "text-valign": "bottom",
      "text-margin-y": 8,
    },
  },
  {
    selector: 'node[presentationKind = "summary"]',
    style: {
      shape: "round-rectangle",
      "background-color": "#ffffff",
      "border-color": "#7b61d1",
      "border-width": 3,
      "border-style": "dashed",
      color: "#5c45ad",
      width: 118,
      height: 42,
    },
  },
  {
    selector: "node:selected",
    style: { "border-width": 5, "border-color": "#68a65f" },
  },
  {
    selector: "edge",
    style: {
      label: "",
      width: 1.6,
      "line-color": "#aab8b1",
      "target-arrow-color": "#aab8b1",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
    },
  },
  {
    selector: 'edge[presentationKind = "summary"]',
    style: {
      "line-style": "dashed",
      "line-color": "#7b61d1",
      "target-arrow-color": "#7b61d1",
    },
  },
  {
    selector: "edge:selected, edge.hovered",
    style: {
      label: "data(predicate)",
      "font-size": 8,
      color: "#627067",
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.85,
      "text-background-padding": "2px",
    },
  },
];
