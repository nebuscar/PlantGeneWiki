---
name: blast_search
label: BLAST 序列相似性搜索
icon: "🔍"
description: >
  接受用户提交的核酸或蛋白序列，在指定物种的基因组/蛋白组中执行 BLAST 比对，
  返回相似度最高的命中基因列表。序列类型自动判断（ACGT 占比 ≥90% 用 blastn，否则用 blastp）。
  需要登录账号才可使用。
triggers:
  - "序列比对"
  - "BLAST 搜索"
  - "找与此序列相似的基因"
  - "用这段序列比对"
  - "帮我鉴定这个序列"
input_schema:
  type: object
  properties:
    sequence:
      type: string
      description: "核酸或蛋白序列（纯序列字符串，不含 FASTA header）"
    species:
      type: array
      items:
        type: string
      description: "目标物种列表，如 ['Arabidopsis_thaliana', 'Glycine_max']"
    evalue:
      type: number
      description: "E-value 阈值，默认 1e-5"
    max_hits:
      type: integer
      description: "最多返回命中数，默认 10"
  required:
    - sequence
    - species
starter:
  label: "🔍 BLAST 序列搜索"
  message: "用这段蛋白序列在 Arabidopsis_thaliana 中做 BLAST 比对：MWRWLIFWLALVVAISGLTTFISTHCVMPLDKISDDISGQNQFTEEFR"
---

# BLAST 序列相似性搜索

## Purpose
接受任意核酸或蛋白序列，自动检测类型后选择 blastn / blastp，在用户指定物种中搜索相似基因。

## When to Use
- 用户粘贴 DNA 或蛋白序列并要求比对
- 用户想鉴定未知序列对应哪个基因
- 用户想找某序列在其他物种中的同源基因

## Response Guidelines
1. 说明序列类型（核酸/蛋白）和使用的 BLAST 程序
2. 按相似度表格展示命中结果（物种 | 基因ID | 相似度% | E-value | 覆盖度%）
3. 标注相似度 ≥80% 为强匹配
4. 推荐对 top1 命中进行 gene_report 或 homolog_compare 深入分析
5. 附上数据来源链接
