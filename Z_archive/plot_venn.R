#!/usr/bin/env Rscript
library(VennDiagram)

# 读取你的数据文件（注意：是 tsv 格式，不是 excel）
data <- read.table("annotation_six_cols.tsv", header = TRUE, sep = "\t", fill = TRUE, quote = "")

# 替换 NA 为空字符串
data[is.na(data)] <- ""

# 提取非空值的基因 ID 并去重
# 注意：你的列名是 protein_id, GO, KEGG, Pfam（注意大小写）
all_genes <- unique(data$protein_id[data$protein_id != ""])
GO_genes <- unique(data$protein_id[data$GO != "" & !is.na(data$GO)])
KEGG_genes <- unique(data$protein_id[data$KEGG != "" & !is.na(data$KEGG)])
Pfam_genes <- unique(data$protein_id[data$Pfam != "" & !is.na(data$Pfam)])

# 打印统计信息
cat("=== 统计信息 ===\n")
cat("总基因数:", length(all_genes), "\n")
cat("有 GO 注释的基因数:", length(GO_genes), "\n")
cat("有 KEGG 注释的基因数:", length(KEGG_genes), "\n")
cat("有 Pfam 注释的基因数:", length(Pfam_genes), "\n")

# 保存 Venn 图到文件
venn.diagram(
  x = list(
    GO = GO_genes,
    KEGG = KEGG_genes,
    Pfam = Pfam_genes
  ),
  filename = "venn_annotation.png",
  col = "black",
  lwd = 3,
  lty = "solid",
  fill = c("cornflowerblue", "green", "darkorchid1"),
  alpha = 0.5,
  label.col = "black",
  cex = 1.5,
  fontfamily = "serif",
  fontface = "bold",
  cat.col = c("darkblue", "darkgreen", "darkorchid4"),
  cat.cex = 1.5,
  cat.dist = c(0.05, 0.05, 0.05),
  cat.fontfamily = "serif",
  cat.fontface = "bold",
  margin = 0.1
)

# 提示用户图像已保存
message("\nVenn 图已保存为 venn_annotation.png")
