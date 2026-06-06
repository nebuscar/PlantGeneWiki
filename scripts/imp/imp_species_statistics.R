library(tidyverse)
library(scales)

# Paths
BASE_DIR <- "/DATA/data2/downloads"
META_DIR <- "/home/nizhu/Projects/plantsdb/data/meta"
OUTPUT_DIR <- "/home/nizhu/Projects/plantsdb/docs"
OUTPUT_PREFIX <- "species_statistics"

# Datasets
DATASETS <- list(
  IMP = list(
    data_dir = file.path(BASE_DIR, "IMP"),
    meta_file = file.path(META_DIR, "imp/genome_info_all_imp.tsv"),
    pattern = NULL,
    has_taxonomy = TRUE
  ),
  PGCP = list(
    data_dir = file.path(BASE_DIR, "PGCP"),
    meta_file = file.path(META_DIR, "pgcp/biobigdata_summary.tsv"),
    pattern = ".pep.fa.gz$",
    has_taxonomy = TRUE
  ),
  NCBI = list(
    data_dir = file.path(BASE_DIR, "NCBI"),
    meta_file = file.path(META_DIR, "ncbi/species_list_cleaned.tsv"),
    pattern = NULL,
    has_taxonomy = TRUE
  )
)

NATURE_COLORS <- c("#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F",
                   "#8491B4", "#91D1C2", "#DC0000", "#7E6148", "#B09C85")

dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

# Parse species name
parse_species <- function(name) {
  parts <- str_split(name, "_")[[1]]
  tibble(
    directory = name,
    genus = parts[1],
    genus_initial = str_sub(parts[1], 1, 1)
  )
}

# Process each dataset
all_stats <- tibble()

for (ds_name in names(DATASETS)) {
  ds <- DATASETS[[ds_name]]

  # List files/dirs
  if (ds_name == "PGCP") {
    files <- list.files(ds$data_dir, pattern = ds$pattern)
    species_names <- str_replace(files, "\\.pep\\.fa\\.gz$", "")
  } else {
    species_names <- list.dirs(ds$data_dir, full.names = FALSE)
    species_names <- species_names[!str_starts(species_names, "\\.")]
  }

  species_df <- map_dfr(species_names, parse_species)
  total <- nrow(species_df)

  # Load metadata
  if (file.exists(ds$meta_file)) {
    meta <- read_tsv(ds$meta_file, show_col_types = FALSE) %>%
      set_names(make.names(names(.)))

    if (ds_name == "IMP") {
      mapping <- meta %>%
        select(directory = plantsdb_directory, latin_name = Latin.name, taxid = NCBI.Taxonomy.ID) %>%
        drop_na(directory)
    } else if (ds_name == "PGCP") {
      mapping <- tibble(directory = meta$Species, latin_name = NA, taxid = NA)
    } else if (ds_name == "NCBI") {
      mapping <- meta %>%
        select(directory = Species, latin_name = Species, taxid = `Taxonomy.ID`,
               family = Family, order = Order) %>%
        drop_na(directory)
    }

    species_matched <- species_df %>% left_join(mapping, by = "directory")
    with_meta <- sum(!is.na(species_matched$latin_name))
  } else {
    species_matched <- species_df
    with_meta <- 0
  }

  # Statistics
  genus_initial_df <- species_matched %>% count(genus_initial, name = "count")
  genus_df <- species_matched %>% count(genus, name = "count") %>% arrange(desc(count))

  # Plots
  for (type in c("pie", "bar_top", "bar_alpha", "donut", "stacked")) {
    if (type == "pie") {
      p <- ggplot(genus_initial_df, aes(x = "", y = count, fill = genus_initial)) +
        geom_bar(width = 1, stat = "identity", color = "white", linewidth = 0.3) +
        coord_polar("y", start = 0) +
        scale_fill_manual(values = rep(NATURE_COLORS, 10)) +
        theme_void() + theme(legend.position = "right", legend.key.size = unit(0.3, "cm")) +
        labs(title = sprintf("%s Species Distribution by Genus Initial", ds_name))
      fname <- sprintf("%s/%s_%s_pie.pdf", OUTPUT_DIR, ds_name, type)
    } else if (type == "bar_top") {
      top15 <- genus_df %>% slice_head(n = 15)
      p <- ggplot(top15, aes(x = reorder(genus, count), y = count)) +
        geom_bar(fill = "#3C5488", stat = "identity", width = 0.7) +
        geom_text(aes(label = count), hjust = -0.3, size = 2.5) +
        coord_flip() + scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
        theme_minimal(base_size = 9) +
        theme(panel.grid.major.y = element_blank(), plot.margin = margin(8, 8, 8, 8)) +
        labs(x = "Genus", y = "Number of Species", title = sprintf("Top 15 Genera in %s", ds_name))
      fname <- sprintf("%s/%s_%s.pdf", OUTPUT_DIR, ds_name, type)
    } else if (type == "bar_alpha") {
      p <- ggplot(genus_initial_df, aes(x = genus_initial, y = count)) +
        geom_bar(fill = "#00A087", stat = "identity", width = 0.8) +
        geom_text(aes(label = count), vjust = -0.3, size = 2.5) +
        scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
        theme_minimal(base_size = 9) + theme(panel.grid.minor = element_blank()) +
        labs(x = "First Letter of Genus", y = "Number of Species", title = sprintf("Species by Genus Initial - %s", ds_name))
      fname <- sprintf("%s/%s_%s.pdf", OUTPUT_DIR, ds_name, type)
    } else if (type == "donut") {
      meta_stats <- tibble(status = c("With Info", "Without Info"),
                           count = c(with_meta, total - with_meta))
      p <- ggplot(meta_stats, aes(x = 2, y = count, fill = status)) +
        geom_bar(width = 1, stat = "identity", color = "white") +
        coord_polar("y", start = 0) + xlim(0.5, 2.5) +
        scale_fill_manual(values = c("#00A087", "#E64B35")) +
        theme_void() + theme(legend.position = "bottom") +
        labs(title = sprintf("%s Metadata Coverage", ds_name))
      fname <- sprintf("%s/%s_%s.pdf", OUTPUT_DIR, ds_name, type)
    } else if (type == "stacked") {
      top10 <- genus_df %>% slice_head(n = 10)
      other <- sum(genus_df$count[!(genus_df$genus %in% top10$genus)])
      stacked <- bind_rows(top10, tibble(genus = "Other", count = other)) %>% arrange(desc(count))
      p <- ggplot(stacked, aes(x = reorder(genus, count), y = count)) +
        geom_bar(fill = NATURE_COLORS[1:nrow(stacked)], stat = "identity", width = 0.8) +
        geom_text(aes(label = count), vjust = -0.3, size = 2.5) +
        coord_flip() + scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
        theme_minimal(base_size = 9) + theme(panel.grid.major.y = element_blank()) +
        labs(x = "Genus", y = "Number of Species", title = sprintf("%s Species by Genus", ds_name))
      fname <- sprintf("%s/%s_%s.pdf", OUTPUT_DIR, ds_name, type)
    }

    ggsave(fname, p, width = 130, height = 100, units = "mm")
  }

  # Export
  write_csv(species_matched, sprintf("%s/%s_species_list.csv", OUTPUT_DIR, ds_name))
  write_csv(genus_df, sprintf("%s/%s_genus_stats.csv", OUTPUT_DIR, ds_name))

  all_stats <- bind_rows(all_stats, tibble(
    dataset = ds_name,
    total = total,
    with_metadata = with_meta,
    metadata_pct = 100 * with_meta / total,
    unique_genera = n_distinct(species_matched$genus)
  ))

  cat(sprintf("%s: %d species | %d with metadata (%.1f%%) | %d genera\n",
              ds_name, total, with_meta, 100*with_meta/total, n_distinct(species_matched$genus)))
}

# Combined summary
write_csv(all_stats, sprintf("%s/%s_summary.csv", OUTPUT_DIR, OUTPUT_PREFIX))
cat("\nSummary saved to:", sprintf("%s/%s_summary.csv", OUTPUT_DIR, OUTPUT_PREFIX), "\n")