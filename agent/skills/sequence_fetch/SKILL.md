---
name: sequence_fetch
label: 序列获取
icon: "📥"
description: >
  按物种和序列类型检索并返回 FASTA 格式序列，支持单基因查询和全物种批量下载。
  覆盖基因组（genome）、基因（gene）、CDS、蛋白（pep）四类文件。
  单基因直接展示序列；多基因（≤100条）合并后提供下载链接；基因组文件仅返回下载路径。
  需要登录账号才可使用。
triggers:
  - "获取序列"
  - "下载序列"
  - "CDS 序列"
  - "pep 文件"
  - "蛋白序列"
  - "基因组 FASTA"
  - "导出 FASTA"
input_schema:
  type: object
  properties:
    species:
      type: string
      description: "物种名，如 Arabidopsis_thaliana"
    gene_ids:
      type: array
      items:
        type: string
      description: "基因 ID 列表（为空时返回全物种文件信息）"
    seq_type:
      type: string
      enum: [genome, gene, CDS, pep]
      description: "序列类型：genome=基因组，gene=基因序列，CDS=编码序列，pep=蛋白序列。默认 CDS"
  required:
    - species
starter:
  label: "📥 序列获取"
  message: "获取 Arabidopsis_thaliana 中 AT1G01010 和 AT2G29980 的 CDS 序列"
---

# 序列获取

## Purpose
从服务器 FASTA 文件中提取指定基因序列，或提供批量/全物种文件下载路径。

## When to Use
- 用户需要特定基因的序列用于下游分析（PCR 引物设计、比对等）
- 用户想下载某物种的全部 CDS 或蛋白序列

## Response Guidelines
1. 单基因（1条）：在对话中展示完整 FASTA 序列
2. 少量基因（2-100条）：展示前3条预览，提供文件下载链接
3. 大批量（>100条）或基因组文件：仅返回服务器文件路径/下载链接
4. 找不到的基因单独列出提示
5. 附上数据来源链接
