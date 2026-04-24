#!/usr/bin/env Rscript
library(VennDiagram)

# 获取所有以 "annotation_six_cols.tsv" 结尾的文件
files <- list.files(pattern = "annotation_six_cols.tsv$", recursive = TRUE)

# 检查是否找到文件
if (length(files) == 0) {
    stop("未找到以 'annotation_six_cols.tsv' 结尾的文件")
}

cat("找到", length(files), "个文件:\n")
print(files)
cat("\n")

# 循环处理每个文件
for (i in seq_along(files)) {
    file_path <- files[i]
    
    cat("========================================\n")
    cat("正在处理 [", i, "/", length(files), "]: ", file_path, "\n", sep = "")
    
    # 提取物种名（文件名中去掉 "annotation_six_cols.tsv" 部分）
    species_name <- sub("annotation_six_cols.tsv$", "", basename(file_path))
    species_name <- sub("[_\\.]$", "", species_name)  # 去掉末尾的下划线或点
    
    # 如果物种名为空，使用默认名称
    if (species_name == "") {
        species_name <- paste0("sample", i)
    }
    cat("物种名:", species_name, "\n")
    
    # 读取数据文件
    data <- tryCatch({
        read.table(file_path, header = TRUE, sep = "\t", fill = TRUE, quote = "", stringsAsFactors = FALSE)
    }, error = function(e) {
        cat("读取文件失败:", e$message, "\n")
        return(NULL)
    })
    
    # 如果读取失败，跳过该文件
    if (is.null(data)) {
        cat("跳过:", file_path, "\n")
        next
    }
    
    # 替换 NA 为空字符串
    data[is.na(data)] <- ""
    
    # 检查必需的列是否存在
    required_cols <- c("protein_id", "GO", "KEGG", "Pfam")
    missing_cols <- required_cols[!required_cols %in% colnames(data)]
    if (length(missing_cols) > 0) {
        cat("缺少必要的列:", paste(missing_cols, collapse = ", "), "\n")
        cat("跳过:", file_path, "\n")
        next
    }
    
    # 提取非空值的基因 ID 并去重
    all_genes <- unique(data$protein_id[data$protein_id != ""])
    GO_genes <- unique(data$protein_id[data$GO != "" & !is.na(data$GO)])
    KEGG_genes <- unique(data$protein_id[data$KEGG != "" & !is.na(data$KEGG)])
    Pfam_genes <- unique(data$protein_id[data$Pfam != "" & !is.na(data$Pfam)])
    
    # 打印统计信息
    cat("总基因数:", length(all_genes), "\n")
    cat("GO 注释数:", length(GO_genes), "\n")
    cat("KEGG 注释数:", length(KEGG_genes), "\n")
    cat("Pfam 注释数:", length(Pfam_genes), "\n")
    
    # 生成输出文件名
    output_filename <- paste0(species_name, "_venn_annotation.png")
    
    # 保存 Venn 图
    venn.diagram(
        x = list(
            GO = GO_genes,
            KEGG = KEGG_genes,
            Pfam = Pfam_genes
        ),
        filename = output_filename,
        fill = NULL,
        col = "black",
        label.col = "black",
        cat.col = "black",
        resolution = 300,
        width = 800,
        height = 800
    )
    
    cat("已保存:", output_filename, "\n")
}

cat("\n========================================\n")
cat("批量处理完成！共处理", length(files), "个文件\n")
