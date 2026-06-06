# MSA Alignment & Trimming — Data Reference

## Data Sources

| Field | Source |
|-------|--------|
| Input sequences | 用户提交的 FASTA 格式文本（inline 或文件路径） |
| Alignment tool | `mafft`（conda 环境 `plantsdb`） |
| Trimming tool | `trimal`（conda 环境 `plantsdb`） |
| Visualization | `pymsaviz`（conda 环境 `plantsdb`） |
| Output directory | `result/result_msa/{timestamp}/` |

## 序列类型检测

自动检测优先顺序：**蛋白 > DNA > RNA**

- 含蛋白特异字符（`D E F H I K L M P Q R S V W Y`）任意之一 → `protein`（使用 Clustal 配色）
- 仅含 `A T G C N` → `dna`（使用 Nucleotide 配色）
- 仅含 `A U G C N` → `rna`（使用 Nucleotide 配色）

## Output Schema

```json
{
  "available": true,
  "seq_type": "protein | dna | rna",
  "n_sequences": 12,
  "n_species": 8,
  "species": ["Arabidopsis_thaliana", "Oryza_sativa", "..."],
  "seq_len_range": [280, 420],
  "trimmed_length": 310,
  "tree_recommended": true,
  "aligned_fasta": "result/result_msa/20240523_143201/sequences.aligned.fasta",
  "trimmed_fasta": "result/result_msa/20240523_143201/sequences.trimmed.fasta",
  "msa_pdf": "result/result_msa/20240523_143201/sequences.msa.pdf",
  "suggestion": "比对和修剪已完成，共 12 条序列，修剪后长度 310 列。物种数量 >= 4，建议进一步使用 msa_build_tree 构建系统发育树。",
  "_sources": [
    { "type": "tool", "name": "mafft" },
    { "type": "tool", "name": "trimal" },
    { "type": "tool", "name": "pymsaviz" }
  ],
  "_skill": "msa_align_trim"
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `available` | bool | 比对是否成功完成 |
| `seq_type` | str | 检测到的序列类型（protein / dna / rna） |
| `n_sequences` | int | 输入序列总数 |
| `n_species` | int | 识别到的物种数量 |
| `species` | list[str] | 物种名列表 |
| `seq_len_range` | [int, int] | 原始序列最短和最长长度 |
| `trimmed_length` | int | trimAl 修剪后的比对列数 |
| `tree_recommended` | bool | 序列数 >= 4 且物种数 >= 3 时为 true，建议建树 |
| `aligned_fasta` | str | MAFFT 比对结果文件路径 |
| `trimmed_fasta` | str | trimAl 修剪结果文件路径 |
| `msa_pdf` | str | pyMSAviz 可视化 PDF 文件路径 |
| `suggestion` | str | 面向用户的自然语言结果摘要和下一步建议 |
| `_sources` | list | 使用的工具列表 |
| `_skill` | str | skill 标识符，固定为 `msa_align_trim` |

## Notes

- 在线模式最多支持 **50 条**序列；超出时应提示用户减少输入。
- pyMSAviz 配色自动根据序列类型选择：蛋白使用 **Clustal** 配色，核酸使用 **Nucleotide** 配色。
- `trimmed_fasta` 路径可直接作为 `msa_build_tree` skill 的输入参数（`fasta_path`）。
- 当 `trimmed_length` < 50 列时，应在 `suggestion` 中警告修剪过度，建议检查输入序列质量。
- `available: false` 时，其他字段除 `suggestion` 外均为 `null`。
