# Protein Structure Prediction (ESMFold) — Data Reference

## Data Sources

| Field | Source |
|-------|--------|
| Model weights | `~/.cache/torch/hub/checkpoints/esmfold_3B_v1.pt`（约 12 GB，首次运行自动下载） |
| Python 环境 | `/home/nizhu/software/miniforge3/envs/esmfold/bin/python` |
| Output directory | `result/result_esmfold/{timestamp}/` |

## pLDDT 置信度分级

| pLDDT 范围 | 颜色 | 置信度等级 | 含义 |
|------------|------|-----------|------|
| > 90 | 深蓝色 | 极高（Very High） | 结构高度可信，接近实验精度，可用于功能分析 |
| 70 – 90 | 浅蓝色 | 高（High） | 主链可信，侧链取向可能有偏差 |
| 50 – 70 | 黄色 | 低（Low） | 结构不可靠，可能为柔性或无序区域 |
| < 50 | 橙色/红色 | 极低（Very Low） | 高度无序区域，预测结构无参考价值 |

> pTM（predicted TM-score）< 0.5 表示整体拓扑置信度低，不建议直接用于对接或功能推断等下游分析。

## Foldseek 结构相似性搜索

当 `run_foldseek: true` 时，预测完成后自动提交 PDB 到 Foldseek 公开服务器。

| 搜索参数 | 值 |
|----------|-----|
| 默认数据库 | `pdb100`（实验结构）+ `afdb-swissprot`（AlphaFold 注释蛋白） |
| 搜索模式 | `3diaa`（结构 + 序列联合比对，推荐） |
| 返回条数 | top 10（按 prob 排序） |
| 超时 | 120 秒 |

**解读要点**

| 模式 | prob | seq_id | 含义 |
|------|------|--------|------|
| 序列相似 + 结构相似 | 高 | 高（>40%） | 同源体，功能可能相同 |
| 结构相似但序列远缘 | 高 | 低（<20%） | 远程结构同源，可能具有相似折叠功能（BLAST 会漏检） |
| prob 低 | 低 | 任意 | 偶然结构相似，意义有限 |

---

## Output Schema

```json
{
  "available": true,
  "name": "AtCBL1",
  "seq_len": 213,
  "pdb": "result/result_esmfold/20240523_150312/AtCBL1.pdb",
  "plddt_png": "result/result_esmfold/20240523_150312/AtCBL1.plddt.png",
  "mean_plddt": 82.4,
  "ptm": 0.73,
  "confidence_label": "high",
  "confidence_summary": {
    "very_high_pct": 38.5,
    "high_pct": 45.1,
    "low_pct": 12.7,
    "very_low_pct": 3.7
  },
  "inference_time_s": 187.3,
  "foldseek": {
    "ticket_id": "abc123",
    "databases": ["pdb100", "afdb-swissprot"],
    "total_hits": 10,
    "top_hits": [
      {
        "target": "4YGS_A",
        "database": "pdb100",
        "prob": 0.9812,
        "evalue": 1.5e-8,
        "seq_id": 0.352,
        "aln_length": 180,
        "q_start": 1,
        "q_end": 180,
        "description": "Calcineurin B-like protein 1",
        "taxon": "Arabidopsis thaliana",
        "tax_id": "3702"
      }
    ]
  },
  "suggestion": "AtCBL1 结构预测完成，序列长度 213 aa，平均 pLDDT 82.4（高置信度）。约 83.6% 的残基置信度 > 70，结构整体可靠。PDB 文件可用 PyMOL 或 ChimeraX 打开查看三维结构。\n\nFoldseek 结构搜索发现 10 个结构相似体。最佳命中：4YGS_A（pdb100，prob=0.9812，序列一致性=35.2%），来自 Arabidopsis thaliana：Calcineurin B-like protein 1。",
  "_sources": [
    { "type": "model", "name": "ESMFold v1", "params": "3.5B" },
    { "type": "checkpoint", "path": "~/.cache/torch/hub/checkpoints/esmfold_3B_v1.pt" }
  ],
  "_skill": "structure_predict"
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `available` | bool | 预测是否成功完成 |
| `name` | str | 蛋白名称（来自 FASTA header 或 `-n` 参数） |
| `seq_len` | int | 输入序列长度（去除非标准字符后） |
| `pdb` | str | 输出 PDB 文件路径 |
| `plddt_png` | str | pLDDT 置信度折线图路径（PNG 格式） |
| `mean_plddt` | float | 全序列平均 pLDDT 分数（0–100） |
| `ptm` | float | 预测 TM-score，反映整体结构置信度（0–1） |
| `confidence_label` | str | 基于平均 pLDDT 的等级标签：`very_high` / `high` / `low` / `very_low` |
| `confidence_summary.very_high_pct` | float | pLDDT > 90 的残基百分比 |
| `confidence_summary.high_pct` | float | pLDDT 70–90 的残基百分比 |
| `confidence_summary.low_pct` | float | pLDDT 50–70 的残基百分比 |
| `confidence_summary.very_low_pct` | float | pLDDT < 50 的残基百分比 |
| `inference_time_s` | float | 模型推理耗时（秒，不含模型加载时间） |
| `foldseek` | dict\|null | Foldseek 结构搜索结果（`run_foldseek=true` 时填充，否则为 null） |
| `foldseek.ticket_id` | str | Foldseek 服务器票据 ID |
| `foldseek.databases` | list | 实际搜索的数据库列表 |
| `foldseek.total_hits` | int | 返回的命中总数（≤ top_n=10） |
| `foldseek.top_hits[].target` | str | 命中结构 ID（如 `4YGS_A`） |
| `foldseek.top_hits[].prob` | float | 结构相似度置信度（0–1，越高越可靠） |
| `foldseek.top_hits[].seq_id` | float | 比对区域序列一致性（0–1） |
| `foldseek.top_hits[].evalue` | float | E-value（统计显著性） |
| `foldseek.top_hits[].description` | str | 命中蛋白功能描述 |
| `foldseek.top_hits[].taxon` | str | 命中蛋白所属物种 |
| `suggestion` | str | 面向用户的自然语言结果摘要和置信度解读 |
| `_sources` | list | 模型和权重来源信息 |
| `_skill` | str | skill 标识符，固定为 `structure_predict` |

## Notes

- 在线模式输入序列长度限制为 **400 残基**；超出时应提示用户在本地运行或截断序列。
- CPU 推理速度约为每 100 残基 3–5 分钟；模型加载（首次）约需 50 秒（不计入 `inference_time_s`）。
- 多聚体支持：多条链使用 `:` 分隔，如 `MKTLL...ACDEF:GHILM...NPQRST`，各链分别计入总长度。
- 非标准氨基酸字符（`B J O U X Z`）自动去除并记录警告；去除后长度低于 6 时报错终止。
- `available: false` 时，除 `name`、`seq_len`、`suggestion` 外的字段均为 `null`。
- 当 `ptm < 0.5` 时，`suggestion` 中应主动提示整体置信度低，不建议用于结构功能预测。
