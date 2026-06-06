#!/usr/bin/env Rscript
# Species Manifest Visualization
# For publication-quality figures

# Load required libraries
library(tidyverse)
library(cowplot)
library(viridis)
library(readxl)
library(sysfonts)
library(showtext)

# Font setup for Chinese support
font_add_google("Noto Sans", "noto")
font_add_google("Noto Sans SC", "noto_sc")
showtext_auto()

# Read data
wb <- "/home/nizhu/Projects/PlantGeneWiki/species_manifest.xlsx"
ws <- read_excel(wb, sheet = "species_list")

# Basic stats
total_species <- nrow(ws)
cat("Total species:", total_species, "\n")

# Prepare data
rank_data <- data.frame(
  Rank = ws$Taxonomic_Rank,
  Count = 1
) %>%
  group_by(Rank) %>%
  summarize(Count = n()) %>%
  arrange(-Count)

kingdom_data <- data.frame(
  Kingdom = ws$Kingdom,
  Count = 1
) %>%
  group_by(Kingdom) %>%
  summarize(Count = n()) %>%
  arrange(-Count)

family_data <- data.frame(
  Family = ws$Family,
  Count = 1
) %>%
  filter(!is.na(Family), Family != "/") %>%
  group_by(Family) %>%
  summarize(Count = n()) %>%
  arrange(-Count) %>%
  head(20)

genus_data <- data.frame(
  Genus = ws$Genus,
  Count = 1
) %>%
  filter(!is.na(Genus), Genus != "/") %>%
  group_by(Genus) %>%
  summarize(Count = n()) %>%
  arrange(-Count) %>%
  head(15)

# Color palette
rank_colors <- c(
  species = "#2E86AB",
  variety = "#A23B72",
  subspecies = "#F18F01",
  forma = "#C73E1D",
  varietas = "#6B7B8C",
  genus = "#3C3C3C"
)
kingdom_colors <- c(
  Viridiplantae = "#2E86AB",
  Rhodophyta = "#A23B72",
  Metazoa = "#F18F01"
)
family_palette <- viridis(20, option = "plasma")
genus_palette <- viridis(15, option = "viridis")

# Theme for publication
pub_theme <- theme_minimal(base_family = "noto_sc") +
  theme(
    text = element_text(color = "#333333"),
    panel.grid.major = element_blank(),
    panel.grid.minor = element_blank(),
    axis.text = element_text(size = 11, color = "#333333"),
    axis.title = element_text(size = 12, face = "bold"),
    plot.title = element_text(size = 14, face = "bold", hjust = 0),
    legend.position = "right",
    legend.title = element_text(size = 11, face = "bold"),
    legend.text = element_text(size = 10)
  )

# ============ Figure 1: Species Summary Card ============
p1 <- ggplot() +
  annotate(
    "text",
    x = 1,
    y = 1,
    label = as.character(total_species),
    size = 20,
    fontface = "bold",
    color = "#2E86AB",
    family = "noto_sc"
  ) +
  annotate(
    "text",
    x = 1,
    y = 0.7,
    label = "Unique Species",
    size = 8,
    color = "#666666",
    family = "noto_sc"
  ) +
  coord_cartesian(clip = "off") +
  theme_void() +
  theme(plot.margin = margin(20, 20, 20, 20))

# ============ Figure 2: Taxonomic Rank Distribution (Donut) ============
p2 <- ggplot(rank_data, aes(x = "", y = Count, fill = Rank)) +
  geom_bar(width = 1, stat = "identity", color = "white", linewidth = 0.5) +
  coord_polar("y", start = 0) +
  scale_fill_manual(values = rank_colors) +
  geom_text(
    aes(label = paste0(Count, "\n(", round(Count / sum(Count) * 100, 1), "%)")),
    position = position_stack(vjust = 0.5),
    size = 3,
    color = "white",
    fontface = "bold",
    family = "noto_sc"
  ) +
  labs(title = "Taxonomic Rank Distribution", fill = "Rank") +
  pub_theme +
  theme(
    axis.text = element_blank(),
    axis.title = element_blank(),
    panel.grid = element_blank(),
    plot.title = element_text(hjust = 0.5)
  )

# ============ Figure 3: Top 20 Families (Horizontal Bar) ============
p3 <- ggplot(family_data, aes(x = reorder(Family, Count), y = Count)) +
  geom_bar(fill = family_palette, stat = "identity", width = 0.8) +
  geom_text(aes(label = Count), hjust = -0.2, size = 3, color = "#333333") +
  scale_x_discrete() +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  labs(title = "Top 20 Plant Families", x = "Family", y = "Species Count") +
  pub_theme +
  theme(
    axis.text.x = element_text(angle = 0, hjust = 1, size = 10),
    plot.title = element_text(hjust = 0.5)
  ) +
  coord_flip()

# ============ Figure 4: Top 15 Genera (Horizontal Bar) ============
p4 <- ggplot(genus_data, aes(x = reorder(Genus, Count), y = Count)) +
  geom_bar(fill = genus_palette, stat = "identity", width = 0.8) +
  geom_text(aes(label = Count), hjust = -0.2, size = 3, color = "#333333") +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  labs(title = "Top 15 Genera", x = "Genus", y = "Species Count") +
  pub_theme +
  theme(
    axis.text.x = element_text(angle = 0, hjust = 1, size = 10),
    plot.title = element_text(hjust = 0.5)
  ) +
  coord_flip()

# ============ Figure 5: Kingdom Distribution (Pie) ============
p5 <- ggplot(kingdom_data, aes(x = "", y = Count, fill = Kingdom)) +
  geom_bar(width = 1, stat = "identity", color = "white", linewidth = 0.5) +
  coord_polar("y", start = 0) +
  scale_fill_manual(
    values = c(
      Viridiplantae = "#2E86AB",
      Rhodophyta = "#A23B72",
      Metazoa = "#F18F01"
    )
  ) +
  geom_text(
    aes(label = paste0(Kingdom, "\n", Count)),
    position = position_stack(vjust = 0.5),
    size = 4,
    color = "white",
    fontface = "bold",
    family = "noto_sc"
  ) +
  labs(title = "Kingdom Distribution", fill = "Kingdom") +
  pub_theme +
  theme(
    axis.text = element_blank(),
    axis.title = element_blank(),
    panel.grid = element_blank(),
    plot.title = element_text(hjust = 0.5)
  )

# ============ Combine All Figures ============
# Top row: summary + rank + kingdom
top_row <- plot_grid(
  p1,
  p2,
  p5,
  ncol = 3,
  rel_widths = c(0.8, 1.2, 1),
  labels = c("A", "B", "C"),
  label_size = 14,
  label_fontface = "bold"
)

# Bottom row: families + genera
bottom_row <- plot_grid(
  p3,
  p4,
  ncol = 2,
  labels = c("D", "E"),
  label_size = 14,
  label_fontface = "bold"
)

# Final combined figure
final_plot <- plot_grid(top_row, bottom_row, ncol = 1, rel_heights = c(1, 1.3))

# Save figures
ggsave(
  "/home/nizhu/Projects/PlantGeneWiki/docs/species_overview_combined.png",
  final_plot,
  width = 14,
  height = 12,
  dpi = 300,
  bg = "white"
)

ggsave(
  "/home/nizhu/Projects/PlantGeneWiki/docs/species_rank_distribution.png",
  p2,
  width = 6,
  height = 5,
  dpi = 300,
  bg = "white"
)

ggsave(
  "/home/nizhu/Projects/PlantGeneWiki/docs/species_top_families.png",
  p3,
  width = 10,
  height = 8,
  dpi = 300,
  bg = "white"
)

ggsave(
  "/home/nizhu/Projects/PlantGeneWiki/docs/species_top_genera.png",
  p4,
  width = 10,
  height = 6,
  dpi = 300,
  bg = "white"
)

ggsave(
  "/home/nizhu/Projects/PlantGeneWiki/docs/species_kingdom_distribution.png",
  p5,
  width = 6,
  height = 5,
  dpi = 300,
  bg = "white"
)

ggsave(
  "/home/nizhu/Projects/PlantGeneWiki/docs/species_summary_card.png",
  p1,
  width = 4,
  height = 3,
  dpi = 300,
  bg = "white"
)

cat("\nAll figures saved to /home/nizhu/Projects/PlantGeneWiki/docs/\n")
cat("Files generated:\n")
cat("  - species_overview_combined.png (main figure)\n")
cat("  - species_rank_distribution.png\n")
cat("  - species_top_families.png\n")
cat("  - species_top_genera.png\n")
cat("  - species_kingdom_distribution.png\n")
cat("  - species_summary_card.png\n")
