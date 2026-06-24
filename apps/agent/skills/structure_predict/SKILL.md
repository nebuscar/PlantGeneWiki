---
name: structure_predict
label: 蛋白质结构预测（ESMFold）
icon: "🔬"
description: >
  接受氨基酸序列，使用 ESMFold（Meta AI，3B 参数蛋白质语言模型）预测蛋白质三维结构，
  输出 PDB 文件和 pLDDT 置信度图。支持单链和多聚体（链间用':'分隔）。
  在线限制：≤400 残基，预测耗时约 2–10 分钟（CPU）。
  更长序列请使用命令行脚本。
triggers:
  - "预测蛋白质结构"
  - "ESMFold"
  - "蛋白质三维结构"
  - "protein structure"
  - "结构预测"
  - "folding"
  - "给我预测这个蛋白的结构"
  - "这段氨基酸的三维结构"
  - "生成PDB"
input_schema:
  type: object
  properties:
    sequence:
      type: string
      description: >
        氨基酸序列（FASTA 格式或纯序列字符串）。
        标准20种氨基酸：ACDEFGHIKLMNPQRSTVWY。
        多聚体：链间用 ':' 分隔（如 CHAINА:CHAINB）。
        在线限制：≤ 400 残基。
    name:
      type: string
      description: "蛋白质名称，用于输出文件命名（默认从 FASTA header 提取）"
    num_recycles:
      type: integer
      description: "结构优化循环次数（默认 4，范围 1–8；越多越精确但越慢）"
    run_foldseek:
      type: boolean
      description: >
        预测完成后自动提交 PDB 到 Foldseek 公开服务器，搜索 PDB 和 AlphaFold
        数据库中的结构相似体（默认 false）。搜索需额外 30–120 秒。
  required:
    - sequence
starter:
  label: "🔬 蛋白质结构预测"
  message: "帮我预测这段蛋白质序列的三维结构：MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDF"
---

# 蛋白质结构预测（ESMFold）

## Purpose
使用 ESMFold（Meta AI）根据氨基酸序列直接预测蛋白质三维结构，无需多序列比对（MSA）。

## When to Use
- 用户提供氨基酸序列，要求预测三维结构
- 用户想了解蛋白质的折叠构象
- 作为后续 MSA 或功能分析的结构参考

## Response Guidelines
1. 报告序列长度（`seq_len`）和实际耗时（`inference_time_s`）；预测前说明 CPU 预计耗时（约每 100 残基 3–5 分钟）
2. 提供 PDB 文件路径（`pdb`）和 pLDDT 置信度图路径（`plddt_png`），格式化为可点击链接
3. 报告平均 pLDDT（`mean_plddt`）和 pTM（`ptm`），以 `confidence_label` 作为整体评价：
   - `very_high`（≥90）：结构高度可信，接近实验精度
   - `high`（70–90）：主链可信，可用于初步功能分析
   - `low`（50–70）：低置信度，谨慎解读
   - `very_low`（<50）：可能为固有无序区（IDR），结构无参考价值
4. 列出 `confidence_summary` 各区间的残基百分比（`very_high_pct`、`high_pct`、`low_pct`、`very_low_pct`）
5. 若 `ptm < 0.5`，主动提示整体拓扑置信度低，不建议直接用于分子对接或功能预测
6. 若 `foldseek` 字段存在且 `top_hits` 非空：
   - 说明搜索的数据库（`databases`）和命中数（`total_hits`）
   - 展示前 5 条命中：target、database、prob、seq_id、description、taxon
   - 重点标注 **高 prob + 低 seq_id** 的命中（结构相似但序列远缘，远程同源体），说明其生物学意义
   - 若最佳命中来自 PDB（实验结构），建议用户下载对应 PDB 进行叠合比较
7. 若 `available` 为 false，说明失败原因（序列过长 / 超时 / 非法字符）；超 400 残基时给出本地 CLI 示例
8. 建议后续分析：PDB 文件可用 PyMOL 或 ChimeraX 打开；高置信度结构 + Foldseek 命中可进行活性位点比对（P2Rank/fpocket）
