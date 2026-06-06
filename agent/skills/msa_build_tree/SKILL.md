---
name: msa_build_tree
label: 进化树构建（IQ-TREE）
icon: "🌳"
description: >
  接受已经过 MSA 比对和修剪的 FASTA 文件路径（通常来自 msa_align_trim 的输出），
  使用 IQ-TREE 构建最大似然进化树并生成树图 PNG。
  支持自动模型选择（TEST）和 UFBoot bootstrap（需 ≥1000）。
  最多支持 30 条序列的在线建树（更大规模建议使用命令行）。
triggers:
  - "建进化树"
  - "系统发育分析"
  - "phylogenetic tree"
  - "IQ-TREE"
  - "构建系统树"
  - "进化关系"
  - "建树"
input_schema:
  type: object
  properties:
    trimmed_fasta:
      type: string
      description: "已比对修剪的 FASTA 文件路径（来自 msa_align_trim 输出的 trimmed_fasta）"
    model:
      type: string
      description: >
        IQ-TREE 替代模型，默认 TEST（自动选择）。
        DNA 示例：GTR+G、HKY+G；蛋白示例：LG+G、WAG+G。
    bootstrap:
      type: integer
      description: "UFBoot 重复次数，0 表示不做 bootstrap，需 ≥1000 才会启用"
    show_bootstrap:
      type: boolean
      description: "是否在树图上显示 bootstrap 值，默认 false"
  required:
    - trimmed_fasta
starter:
  label: "🌳 构建进化树"
  message: "请对上次 MSA 比对的结果构建进化树，bootstrap 1000 次"
---

# 进化树构建（IQ-TREE）

## Purpose
基于已比对修剪的序列文件，使用 IQ-TREE 构建最大似然进化树。

## When to Use
- msa_align_trim 完成后，用户要求建树
- 用户已有修剪后的比对文件，直接要求进化树分析
- 多物种直系同源基因进化关系分析

## Response Guidelines
1. 说明实际使用的替代模型（`model`，TEST 时报告最终选定的模型名）和 bootstrap 重复次数（`bootstrap`）
2. 提供树文件路径（`treefile`，Newick 格式）和树图路径（`tree_png`），格式化为可点击链接
3. 根据树图简述拓扑结构：哪些物种/序列聚为一支，是否有明显的外群
4. 若 `bootstrap > 0` 且树图显示支持值 < 70 的分支，建议对应区段结论持保留态度
5. 若 `available` 为 false（超时或失败），说明原因并建议在本地命令行运行 IQ-TREE
6. 若序列数超过 30 条，说明在线限制并给出本地 CLI 示例
