#! /home/nizhu/software/miniforge3/envs/renv/bin/Rscript

# 输出问候
print("hello R")

# 1. 查看 R 版本
cat("\n===== R 版本 =====\n")
R.version.string

# 2. 查看当前使用的 R 所在路径（最关键！）
cat("\n===== 当前使用的 R 路径 =====\n")
cat(R.home("bin"), "\n")

# 3. 查看 R 安装位置
cat("\n===== R 安装目录 =====\n")
cat(R.home(), "\n")