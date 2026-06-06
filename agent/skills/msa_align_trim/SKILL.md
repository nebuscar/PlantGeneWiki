---
name: msa_align_trim
label: 多序列比对（MSA）
icon: "🧬"
description: >
  接受多条 DNA、RNA 或蛋白序列（FASTA 格式），使用 MAFFT 进行多序列比对，
  trimAl 修剪低质量列，并生成 MSA 可视化 PDF。自动检测序列类型和物种数量，
  若检测到多物种则建议后续调用 msa_build_tree 构建进化树。
  最多支持 50 条序列。
triggers:
  - "多序列比对"
  - "MSA"
  - "序列保守性分析"
  - "帮我比对这些序列"
  - "做一个比对"
  - "比较这几个序列"
  - "序列对齐"
  - "alignment"
input_schema:
  type: object
  properties:
    sequences:
      type: string
      description: >
        多条序列的 FASTA 格式文本（含 > 开头的 header 行）。
        序列 ID 格式建议：Genus_species|GeneID 或 Genus_species_GeneID。
        示例：>Arabidopsis_thaliana|AT1G01234\nMSRKL...\n>Glycine_max|Glyma01g001\nMARKL...
    seq_type:
      type: string
      enum: ["auto", "dna", "rna", "protein"]
      description: "序列类型，默认 auto（自动检测）"
    trim_mode:
      type: string
      enum: ["automated1", "gappyout", "strict", "strictplus", "gt90"]
      description: "trimAl 修剪模式，默认 automated1（自动选择最佳策略）"
    algo:
      type: string
      enum: ["auto", "linsi", "ginsi", "einsi", "fftnsi", "fftns"]
      description: "MAFFT 比对算法，默认 auto。linsi 最精确但最慢（适合 <200 条序列）"
    threads:
      type: integer
      description: "CPU 线程数，默认 4"
  required:
    - sequences
starter:
  label: "🧬 多序列比对"
  message: |
    帮我对以下序列做多序列比对：
    >Arabidopsis_thaliana|AT1G01234
    MSRKLVVLAAAALLLVVAEAQNRPQLSQAFDILSRSEEAFKPLLNAQKTSQSPQQNQIITQQDPVLPPLHASSASDNLVPTPPAQAANKMVQTTQLPQ
    >Glycine_max|Glyma01g001230
    MARKLLVLASAALLVVAEAQNRPQLAQAFDILSRSEEAFKPLLHAQKASQSPQQNQIITQQDPVLPPLHASSASDNLVPAPPAQAANKMVQTTQLPQ
---

# 多序列比对（MSA）

## Purpose
对用户提供的多条 DNA、RNA 或蛋白序列进行多序列比对，生成比对结果和 MSA 可视化图。

## When to Use
- 用户提供多条序列，要求比对或分析保守性
- 用户想了解多个同源基因/蛋白的序列相似性
- 用户为进化分析准备比对结果（后续可调用 msa_build_tree）

## Response Guidelines
1. 说明检测到的序列类型（DNA / RNA / 蛋白）、序列数量（`n_sequences`）和物种数（`n_species`）
2. 报告修剪后比对长度（`trimmed_length` 列），简要说明 trimAl 去除了多少低质量列
3. 提供 MSA PDF 路径（`msa_pdf`）：将路径格式化为可点击的文件链接
4. 若 `tree_recommended` 为 true（多物种），主动建议用户继续调用 `msa_build_tree`，并在建议中附上 `trimmed_fasta` 路径
5. 若 `tree_recommended` 为 false（单物种），说明同物种比对无需建树
6. 若序列数超过 50 条，说明在线限制并给出命令行替代方案
