# Phylogenetic Tree Building — Data Reference

## Data Sources

| Field | Source |
|-------|--------|
| Input | `msa_align_trim` 输出的 `trimmed_fasta` 文件路径 |
| Tree building tool | `iqtree`（conda 环境 `plantsdb`） |
| Output directory | 与比对结果相同目录（`result/result_msa/{timestamp}/`） |

## IQ-TREE 模型建议

| 序列类型 | 推荐模型 | 说明 |
|----------|----------|------|
| DNA | `TEST` | 自动选择最优替换模型（推荐首选） |
| DNA | `GTR+G` | 通用时间可逆模型 + Gamma 速率变异 |
| DNA | `HKY+G` | 较简单的替换模型，适合序列差异较小的情况 |
| 蛋白 | `TEST` | 自动选择最优蛋白替换矩阵（推荐首选） |
| 蛋白 | `LG+G` | Le-Gascuel 矩阵 + Gamma，通用蛋白模型 |
| 蛋白 | `WAG+G` | Whelan-Goldman 矩阵，适合功能保守蛋白 |
| 蛋白 | `JTT+G` | Jones-Taylor-Thornton 矩阵，经典蛋白模型 |

> 使用 `TEST` 时 IQ-TREE 通过 ModelFinder 自动选择最优模型，推荐默认使用。

## Output Schema

```json
{
  "available": true,
  "n_sequences": 12,
  "model": "LG+G4",
  "bootstrap": 1000,
  "treefile": "result/result_msa/20240523_143201/sequences.trimmed.fasta.treefile",
  "tree_png": "result/result_msa/20240523_143201/sequences.tree.png",
  "suggestion": "系统发育树构建完成，共 12 条序列，使用 LG+G4 模型，bootstrap 1000 次。树文件和图像已生成，可下载查看。",
  "_sources": [
    { "type": "tool", "name": "iqtree" }
  ],
  "_skill": "msa_build_tree"
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `available` | bool | 建树是否成功完成 |
| `n_sequences` | int | 参与建树的序列数量 |
| `model` | str | 实际使用的替换模型（TEST 时为最终选定的模型名） |
| `bootstrap` | int | bootstrap 重复次数（0 表示未进行 bootstrap） |
| `treefile` | str | IQ-TREE 输出的 Newick 格式树文件路径 |
| `tree_png` | str | 系统发育树渲染图像路径（PNG 格式） |
| `suggestion` | str | 面向用户的自然语言结果摘要 |
| `_sources` | list | 使用的工具列表 |
| `_skill` | str | skill 标识符，固定为 `msa_build_tree` |

## Notes

- `bootstrap` 必须 >= **1000** 或设为 **0**（禁用 bootstrap 快速模式）；不接受 100、500 等中间值。
- 在线模式下序列数量上限为 **30 条**；超出时应提示用户在本地运行 IQ-TREE。
- IQ-TREE 生成的 `.log`、`.iqtree`、`.bionj`、`.mldist` 等中间文件在完成后自动清理，仅保留 `.treefile`。
- 建树超时限制为 **300 秒**；超时时返回 `available: false` 并在 `suggestion` 中说明原因。
- `available: false` 时，`treefile`、`tree_png`、`model` 均为 `null`，`suggestion` 说明失败原因。
- 输入的 `trimmed_fasta` 须来自 `msa_align_trim` 的输出，直接使用原始（未比对）序列将导致错误。
