#!/usr/bin/env Rscript

# ============================================
# 韦恩图批量绘制脚本
# 功能：自动搜索指定目录下所有 _protein.faa.extracted.tsv 文件，
#       批量生成韦恩图
# ============================================

library(VennDiagram)

# ============================================
# 帮助文档
# ============================================
show_help <- function() {
    cat("
韦恩图批量绘制脚本
================================================

用法：
    Rscript plot_venn.R [选项]

选项：
    -i, --input DIR       输入根目录（默认：当前目录）
                          会递归搜索该目录下所有 _protein.faa.extracted.tsv 文件

    -o, --output DIR      输出根目录（默认：当前目录）
                          图片将保存到此目录下

    -f, --format FMT      输出图片格式(默认:png)
                          支持:png, tiff, svg

    -r, --resolution N    输出图片分辨率(dpi)(默认:300)
                          仅对 png 和 tiff 格式有效

    -w, --width N         输出图片宽度(像素)(默认:800)

    -h, --height N        输出图片高度(像素)(默认:800)

    --color               输出彩色图（默认：彩色）
                          颜色 = 浅蓝, 浅绿, 浅珊瑚

    --no-color            输出黑白图
                          适用于论文投稿

    --help                显示此帮助文档

示例：
    # 使用默认参数处理当前目录下所有文件
    Rscript plot_venn.R

    # 指定输入和输出目录
    Rscript plot_venn.R -i ./data/annotations -o ./results/venn

    # 输出高分辨率 PNG
    Rscript plot_venn.R -f png -r 600 -w 1200 -h 1200

    # 输出 TIFF 格式（论文投稿用）
    Rscript plot_venn.R -f tiff -r 300 -w 2000 -h 2000

    # 输出 SVG 矢量图
    Rscript plot_venn.R -f svg

    # 黑白图
    Rscript plot_venn.R --no-color

================================================
")
}

# ============================================
# 解析命令行参数
# ============================================
parse_args <- function() {
    args <- commandArgs(trailingOnly = TRUE)
    
    # 默认值
    params <- list(
        input_dir = ".",
        output_dir = ".",
        format = "png",
        resolution = 300,
        width = 800,
        height = 800,
        use_color = TRUE
    )
    
    if (length(args) == 0) {
        return(params)
    }
    
    i <- 1
    while (i <= length(args)) {
        if (args[i] %in% c("-h", "--help")) {
            show_help()
            quit(save = "no", status = 0)
        } else if (args[i] %in% c("-i", "--input")) {
            if (i + 1 <= length(args)) {
                params$input_dir <- args[i + 1]
                i <- i + 1
            } else {
                cat("错误：-i/--input 需要指定一个目录\n")
                quit(save = "no", status = 1)
            }
        } else if (args[i] %in% c("-o", "--output")) {
            if (i + 1 <= length(args)) {
                params$output_dir <- args[i + 1]
                i <- i + 1
            } else {
                cat("错误：-o/--output 需要指定一个目录\n")
                quit(save = "no", status = 1)
            }
        } else if (args[i] %in% c("-f", "--format")) {
            if (i + 1 <= length(args)) {
                params$format <- tolower(args[i + 1])
                if (!params$format %in% c("png", "tiff", "svg")) {
                    cat("错误：-f/--format 参数必须是 png、tiff 或 svg\n")
                    quit(save = "no", status = 1)
                }
                i <- i + 1
            } else {
                cat("错误：-f/--format 需要指定格式\n")
                quit(save = "no", status = 1)
            }
        } else if (args[i] %in% c("-r", "--resolution")) {
            if (i + 1 <= length(args)) {
                params$resolution <- as.numeric(args[i + 1])
                if (is.na(params$resolution) || params$resolution < 72) {
                    cat("错误：-r/--resolution 需要 >= 72 的数字\n")
                    quit(save = "no", status = 1)
                }
                i <- i + 1
            } else {
                cat("错误：-r/--resolution 需要指定数字\n")
                quit(save = "no", status = 1)
            }
        } else if (args[i] %in% c("-w", "--width")) {
            if (i + 1 <= length(args)) {
                params$width <- as.numeric(args[i + 1])
                if (is.na(params$width) || params$width < 100) {
                    cat("错误：-w/--width 需要 >= 100 的数字\n")
                    quit(save = "no", status = 1)
                }
                i <- i + 1
            } else {
                cat("错误：-w/--width 需要指定数字\n")
                quit(save = "no", status = 1)
            }
        } else if (args[i] %in% c("-h", "--height")) {
            if (i + 1 <= length(args)) {
                params$height <- as.numeric(args[i + 1])
                if (is.na(params$height) || params$height < 100) {
                    cat("错误：-h/--height 需要 >= 100 的数字\n")
                    quit(save = "no", status = 1)
                }
                i <- i + 1
            } else {
                cat("错误：-h/--height 需要指定数字\n")
                quit(save = "no", status = 1)
            }
        } else if (args[i] == "--color") {
            params$use_color <- TRUE
        } else if (args[i] == "--no-color") {
            params$use_color <- FALSE
        } else {
            cat("错误：未知参数", args[i], "\n")
            show_help()
            quit(save = "no", status = 1)
        }
        i <- i + 1
    }
    
    return(params)
}

# ============================================
# 获取要处理的文件列表
# ============================================
get_files <- function(input_dir) {
    files <- list.files(
        path = input_dir,
        pattern = "_protein\\.faa\\.extracted\\.tsv$",
        recursive = TRUE,
        full.names = TRUE
    )
    
    cat("在目录", input_dir, "中找到", length(files), "个匹配的文件\n")
    return(files)
}

# ============================================
# 提取物种名
# ============================================
extract_species_name <- function(file_path, index) {
    filename <- basename(file_path)
    species <- sub("_protein\\.faa\\.extracted\\.tsv$", "", filename)
    species <- sub("[_\\.]+$", "", species)
    
    if (species == "") {
        species <- paste0("sample", index)
    }
    
    return(species)
}

# ============================================
# 读取 TSV 文件
# ============================================
read_tsv_file <- function(file_path) {
    data <- read.table(file_path, header = TRUE, sep = "\t", fill = TRUE, quote = "", stringsAsFactors = FALSE)
    data[is.na(data)] <- ""
    
    required_cols <- c("protein_id", "GO", "KEGG", "Pfam")
    missing_cols <- required_cols[!required_cols %in% colnames(data)]
    if (length(missing_cols) > 0) {
        stop("文件缺少必要的列: ", paste(missing_cols, collapse = ", "))
    }
    
    all_genes <- unique(data$protein_id[data$protein_id != ""])
    GO_genes <- unique(data$protein_id[data$GO != "" & !is.na(data$GO)])
    KEGG_genes <- unique(data$protein_id[data$KEGG != "" & !is.na(data$KEGG)])
    Pfam_genes <- unique(data$protein_id[data$Pfam != "" & !is.na(data$Pfam)])
    
    return(list(
        all_genes = all_genes,
        GO_genes = GO_genes,
        KEGG_genes = KEGG_genes,
        Pfam_genes = Pfam_genes,
        stats = c(
            total = length(all_genes),
            GO = length(GO_genes),
            KEGG = length(KEGG_genes),
            Pfam = length(Pfam_genes)
        )
    ))
}

# ============================================
# 绘制韦恩图
# ============================================
draw_venn <- function(gene_lists, output_path, params) {
    if (params$use_color) {
        fill_colors <- c("lightblue", "lightgreen", "lightcoral")
        cat_colors <- c("darkblue", "darkgreen", "darkred")
        alpha_val <- 0.5
    } else {
        fill_colors <- NULL
        cat_colors <- c("black", "black", "black")
        alpha_val <- 1
    }
    
    if (params$format == "tiff") {
        venn.diagram(
            x = gene_lists,
            filename = output_path,
            fill = fill_colors,
            col = "black",
            label.col = "black",
            cat.col = cat_colors,
            alpha = alpha_val,
            compression = "lzw",
            resolution = params$resolution,
            width = params$width,
            height = params$height,
            units = "px"
        )
    } else if (params$format == "svg") {
        venn.diagram(
            x = gene_lists,
            filename = output_path,
            fill = fill_colors,
            col = "black",
            label.col = "black",
            cat.col = cat_colors,
            alpha = alpha_val,
            width = params$width,
            height = params$height
        )
    } else {  # png 默认
        venn.diagram(
            x = gene_lists,
            filename = output_path,
            fill = fill_colors,
            col = "black",
            label.col = "black",
            cat.col = cat_colors,
            alpha = alpha_val,
            resolution = params$resolution,
            width = params$width,
            height = params$height,
            units = "px"
        )
    }
}

# ============================================
# 处理单个文件
# ============================================
process_file <- function(file_path, output_dir, params, index, total) {
    cat("\n========================================\n")
    cat("正在处理 [", index, "/", total, "]: ", basename(file_path), "\n", sep = "")
    
    species_name <- extract_species_name(file_path, index)
    cat("物种名:", species_name, "\n")
    
    result <- tryCatch({
        read_tsv_file(file_path)
    }, error = function(e) {
        cat("读取文件失败:", e$message, "\n")
        return(NULL)
    })
    
    if (is.null(result)) {
        cat("跳过:", file_path, "\n")
        return(FALSE)
    }
    
    cat("总基因数:", result$stats["total"], "\n")
    cat("GO 注释数:", result$stats["GO"], "\n")
    cat("KEGG 注释数:", result$stats["KEGG"], "\n")
    cat("Pfam 注释数:", result$stats["Pfam"], "\n")
    
    if (!dir.exists(output_dir)) {
        dir.create(output_dir, recursive = TRUE)
        cat("创建输出目录:", output_dir, "\n")
    }
    
    output_filename <- paste0(species_name, "_venn_annotation.", params$format)
    output_path <- file.path(output_dir, output_filename)
    
    gene_lists <- list(GO = result$GO_genes, KEGG = result$KEGG_genes, Pfam = result$Pfam_genes)
    draw_venn(gene_lists, output_path, params)
    
    cat("已保存:", output_path, "\n")
    return(TRUE)
}

# ============================================
# 主程序
# ============================================
main <- function() {
    params <- parse_args()
    
    cat("\n========================================\n")
    cat("韦恩图批量绘制脚本\n")
    cat("========================================\n")
    cat("输入目录:", params$input_dir, "\n")
    cat("输出目录:", params$output_dir, "\n")
    cat("输出格式:", params$format, "\n")
    cat("图片尺寸:", params$width, "x", params$height, "px\n")
    if (params$format %in% c("png", "tiff")) {
        cat("分辨率:", params$resolution, "dpi\n")
    }
    cat("颜色模式:", ifelse(params$use_color, "彩色", "黑白"), "\n")
    cat("========================================\n")
    
    files <- get_files(params$input_dir)
    
    if (length(files) == 0) {
        cat("未找到任何文件\n")
        cat("支持的文件格式: *_protein.faa.extracted.tsv\n")
        return()
    }
    
    cat("\n共找到", length(files), "个文件，开始处理...\n")
    
    success_count <- 0
    for (i in seq_along(files)) {
        if (process_file(files[i], params$output_dir, params, i, length(files))) {
            success_count <- success_count + 1
        }
    }
    
    cat("\n========================================\n")
    cat("批量处理完成！\n")
    cat("成功处理:", success_count, "/", length(files), "个文件\n")
    cat("输出目录:", params$output_dir, "\n")
    cat("========================================\n")
}

# 运行主程序
if (!interactive()) {
    main()
}