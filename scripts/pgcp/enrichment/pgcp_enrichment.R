#!/usr/bin/env Rscript
#
# PGCP GO 富集分析
# 使用超几何检验 + BH FDR校正 (与 Python 版本一致的逻辑)
# 使用 clusterProfiler 可视化
#

suppressPackageStartupMessages({
  library(clusterProfiler)
  library(ggplot2)
  library(dplyr)
})

args <- commandArgs(TRUE)
if (length(args) < 1) {
  SPECIES <- "abies_alba"
  DATA_DIR <- "/DATA/data2/downloads/PGCP"
} else if (length(args) < 2) {
  SPECIES <- args[1]
  DATA_DIR <- "/DATA/data2/downloads/PGCP"
} else {
  SPECIES <- args[1]
  DATA_DIR <- args[2]
}

OUTPUT_DIR <- file.path(DATA_DIR, "enrichment", SPECIES)
TOP_N <- 30
ALPHA <- 0.05
dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

cat("============================================================\n")
cat("PGCP GO 富集分析 (clusterProfiler)\n")
cat("============================================================\n")
cat("物种: ", SPECIES, "\n")
cat("数据目录: ", DATA_DIR, "\n")
cat("输出目录: ", OUTPUT_DIR, "\n")
cat("============================================================\n\n")

# Step 1: 从 longest.gff.gz 构建 transcript->gene 映射
cat("[1/3] 解析 longest.gff.gz 构建 transcript->gene 映射...\n")

longest_file <- file.path(DATA_DIR, paste0(SPECIES, ".longest.gff.gz"))
if (!file.exists(longest_file)) {
  cat("错误: 文件不存在: ", longest_file, "\n")
  quit(status = 1)
}

transcript_to_gene <- new.env(parent = emptyenv())
con <- gzfile(longest_file, "rt")
while (length(line <- readLines(con, n = 1, warn = FALSE)) > 0) {
  if (startsWith(line, "#")) next
  fields <- strsplit(line, "\t")[[1]]
  if (length(fields) < 9) next
  if (fields[[3]] != "transcript") next

  attrs <- fields[[9]]
  transcript_id <- NA
  gene_id <- NA

  if (grepl("ID=", attrs)) {
    id <- regmatches(attrs, regexpr("ID=[^;]+", attrs))
    transcript_id <- sub("ID=", "", id)
  }
  if (grepl("Parent=", attrs)) {
    parent <- regmatches(attrs, regexpr("Parent=[^;]+", attrs))
    gene_id <- sub("Parent=", "", parent)
  }

  if (!is.na(transcript_id) && !is.na(gene_id)) {
    transcript_to_gene[[transcript_id]] <- gene_id
  }
}
close(con)
cat("  transcript->gene 映射条目: ", length(ls(transcript_to_gene)), "\n\n")

# Step 2: 解析 interpro.gff.gz 获取 polypeptide-GO 映射
cat("[2/3] 解析 interpro.gff.gz 获取 GO 注释...\n")

interpro_file <- file.path(DATA_DIR, paste0(SPECIES, ".interpro.gff.gz"))
if (!file.exists(interpro_file)) {
  cat("错误: 文件不存在: ", interpro_file, "\n")
  quit(status = 1)
}

poly_go <- new.env(parent = emptyenv())
con <- gzfile(interpro_file, "rt")
while (length(line <- readLines(con, n = 1, warn = FALSE)) > 0) {
  if (startsWith(line, "#")) next
  fields <- strsplit(line, "\t")[[1]]
  if (length(fields) < 9) next
  if (fields[[3]] != "protein_match") next

  attrs <- fields[[9]]
  poly_id <- NA

  if (grepl("Target=", attrs)) {
    target <- regmatches(attrs, regexpr("Target=[^;]+", attrs))
    target <- sub("Target=", "", target)
    poly_id <- strsplit(target, " ")[[1]][1]
  }
  if (is.na(poly_id)) next

  if (grepl("Ontology_term=", attrs)) {
    ontology <- regmatches(attrs, regexpr("Ontology_term=\"[^\"]+\"", attrs))
    ontology <- sub("Ontology_term=", "", ontology)
    ontology <- sub("\"", "", ontology, fixed = TRUE)
    ontology <- sub("\"", "", ontology, fixed = TRUE)
    go_terms <- strsplit(ontology, '","')[[1]]
    go_terms <- go_terms[grepl("^GO:", go_terms)]

    if (length(go_terms) > 0) {
      if (exists(poly_id, envir = poly_go)) {
        poly_go[[poly_id]] <- unique(c(poly_go[[poly_id]], go_terms))
      } else {
        poly_go[[poly_id]] <- go_terms
      }
    }
  }
}
close(con)

poly_ids <- ls(poly_go)
cat("  带有 GO 注释的 polypeptide 数: ", length(poly_ids), "\n")
cat("  GO terms 总数: ", length(unique(unlist(sapply(poly_ids, function(p) poly_go[[p]])))), "\n\n")

# Step 3: 映射 polypeptide 到 gene ID 并构建 TERM2GENE
cat("[3/3] 映射 polypeptide 到 gene ID...\n")

gene_ids <- unique(sapply(poly_ids, function(p) {
  gene <- transcript_to_gene[[p]]
  if (!is.null(gene)) gene else NULL
}))
gene_ids <- gene_ids[!is.null(gene_ids)]
cat("  唯一基因数: ", length(gene_ids), "\n\n")

# 构建 TERM2GENE
term2gene <- data.frame(TERM = character(), GENE = character(), stringsAsFactors = FALSE)
for (poly_id in poly_ids) {
  gene <- transcript_to_gene[[poly_id]]
  if (is.null(gene)) next
  for (go in poly_go[[poly_id]]) {
    term2gene <- rbind(term2gene, data.frame(TERM = go, GENE = gene))
  }
}
cat("  TERM2GENE 行数: ", nrow(term2gene), "\n\n")

# Step 4: GO 富集分析 (使用超几何检验手动计算 + clusterProfiler 可视化)
cat("[4/3] GO 富集分析...\n")

# 加载 GO ontology
go_ontology_raw <- as.data.frame(GO.db::GOTERM)
# 去重：每个 GO ID 只保留第一个条目
go_ontology_raw <- go_ontology_raw[!duplicated(go_ontology_raw$go_id), ]
# 构建查找表
go_lookup <- data.frame(
  ID = go_ontology_raw$go_id,
  Description = go_ontology_raw$Term,
  ONTOLOGY = go_ontology_raw$Ontology,
  stringsAsFactors = FALSE
)

# 确保 ONTOLOGY 只取首个有效值
go_lookup$ONTOLOGY <- ifelse(
  grepl("biological_process", go_lookup$ONTOLOGY, ignore.case = TRUE), "BP",
  ifelse(
    grepl("molecular_function", go_lookup$ONTOLOGY, ignore.case = TRUE), "MF",
    ifelse(
      grepl("cellular_component", go_lookup$ONTOLOGY, ignore.case = TRUE), "CC",
      NA
    )
  )
)

# 手动超几何检验 (与 Python 版本一致)
bg_gene_count <- length(ls(transcript_to_gene))  # 总背景基因数
gene_set <- gene_ids                              # 查询基因

# 统计每个 term 关联的基因
term_genes <- split(term2gene$GENE, term2gene$TERM)

results <- list()
for (term in names(term_genes)) {
  genes_in_term <- unique(term_genes[[term]])
  k <- length(genes_in_term)      # 查询基因中属于该 term 的数量
  m <- length(genes_in_term)      # 背景基因中属于该 term 的数量
  n <- bg_gene_count - m          # 背景基因中不属于该 term 的数量
  N <- bg_gene_count              # 总背景基因数

  if (k < 1 || m < 1) next

  # 超几何检验 p-value
  pvalue <- phyper(k - 1, m, n, length(gene_set), lower.tail = FALSE)
  gene_list <- paste(genes_in_term, collapse = "/")

  results[[term]] <- data.frame(
    ID = term,
    Description = term,  # 先用 ID，后面统一填充
    GeneRatio = paste0(k, "/", length(gene_set)),
    BgRatio = paste0(m, "/", N),
    Count = k,
    pvalue = pvalue,
    geneID = gene_list,
    stringsAsFactors = FALSE
  )
}

if (length(results) == 0) {
  cat("  [警告] 没有 GO 富集结果\n")
} else {
  # 合并结果
  go_df <- do.call(rbind, results)
  rownames(go_df) <- NULL

  # 使用 go_lookup 填充 Description 和 ONTOLOGY
  go_df$Description <- sapply(go_df$ID, function(id) {
    desc <- go_lookup$Description[go_lookup$ID == id]
    if (length(desc) > 0 && !is.na(desc[1])) as.character(desc[1]) else id
  })

  # BH FDR 校正
  go_df$p.adjust <- p.adjust(go_df$pvalue, method = "BH")

  # 添加 ontology 分类
  go_df$ONTOLOGY <- sapply(go_df$ID, function(id) {
    ont <- go_lookup$ONTOLOGY[go_lookup$ID == id]
    if (length(ont) > 0 && !is.na(ont[1])) as.character(ont[1]) else {
      # 如果 ONTOLOGY 缺失，根据 Description 猜测
      desc <- go_lookup$Description[go_lookup$ID == id]
      if (length(desc) > 0 && grepl("process|regulation", desc[1], ignore.case = TRUE)) {
        "BP"
      } else if (length(desc) > 0 && grepl("activity|binding", desc[1], ignore.case = TRUE)) {
        "MF"
      } else {
        "CC"  # 默认归为细胞组件
      }
    }
  })

  # 按 p.adjust 排序
  go_df <- go_df[order(go_df$p.adjust), ]

  # 过滤显著结果
  sig_df <- go_df[go_df$p.adjust < ALPHA, ]
  cat("  显著 GO terms: ", nrow(sig_df), "\n")

  cat("\n  按分类统计:\n")
  for (ont in c("BP", "MF", "CC")) {
    n <- sum(sig_df$ONTOLOGY == ont, na.rm = TRUE)
    cat("    ", ont, ": ", n, " terms\n")
  }

  # 保存结果
  go_output <- file.path(OUTPUT_DIR, paste0(SPECIES, ".go_enrichment.tsv"))
  cat("\n  保存结果...\n")
  write.table(go_df, go_output, sep = "\t", row.names = FALSE, quote = FALSE)
  cat("  结果已保存: ", go_output, "\n")

  # 生成气泡图 (使用 clusterProfiler 绘图)
  cat("\n  生成可视化图表...\n")

  for (ont in c("BP", "MF", "CC")) {
    ont_data <- sig_df[sig_df$ONTOLOGY == ont, ]
    if (nrow(ont_data) == 0) {
      cat("    ", ont, ": 无显著结果\n")
      next
    }

    ont_data <- head(ont_data, TOP_N)

    p <- ggplot(ont_data, aes(x = Count, y = reorder(Description, Count))) +
      geom_point(aes(size = Count, color = p.adjust)) +
      scale_color_gradient(low = "red", high = "blue", name = "FDR") +
      scale_size(range = c(3, 8)) +
      labs(title = paste0("GO Enrichment - ", SPECIES, " (", ont, ")"),
           x = "Gene Count", y = "") +
      theme_bw() +
      theme(plot.title = element_text(hjust = 0.5, size = 12, face = "bold"),
            axis.text.y = element_text(size = 9),
            legend.position = "right")

    out_png <- file.path(OUTPUT_DIR, paste0(SPECIES, ".go_", tolower(ont), "_bubble.png"))
    ggsave(out_png, p, width = 10, height = max(6, nrow(ont_data) * 0.3), dpi = 150)
    cat("    ", ont, ": ", out_png, "\n")
  }

  # 总览图
  if (nrow(sig_df) > 0) {
    top_all <- head(sig_df, TOP_N * 3)

    p_overview <- ggplot(top_all, aes(x = Count, y = reorder(Description, p.adjust))) +
      geom_point(aes(size = Count, color = ONTOLOGY)) +
      scale_color_manual(values = c(BP = "#e74c3c", MF = "#3498db", CC = "#2ecc71")) +
      scale_size(range = c(3, 8)) +
      labs(title = paste0("GO Enrichment Overview - ", SPECIES),
           x = "Gene Count", y = "") +
      theme_bw() +
      theme(plot.title = element_text(hjust = 0.5, size = 12, face = "bold"),
            axis.text.y = element_text(size = 8),
            legend.position = "right")

    out_overview <- file.path(OUTPUT_DIR, paste0(SPECIES, ".go_overview.png"))
    ggsave(out_overview, p_overview, width = 12, height = max(8, nrow(top_all) * 0.25), dpi = 150)
    cat("    Overview: ", out_overview, "\n")
  }
}

cat("\n============================================================\n")
cat("完成！\n")
cat("============================================================\n")