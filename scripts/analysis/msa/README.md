# MSA 工具包使用文档

## 概述

本工具包集成 MAFFT、trimAl、IQ-TREE 和 pyMSAviz，提供从原始序列到多序列比对、修剪、可视化和建树的完整流程，支持 DNA、RNA 和蛋白序列的自动化分析。

## 依赖

- **conda 环境**：`plantsdb`（使用前请执行 `conda activate plantsdb`）
- **外部工具**：`mafft`、`trimal`、`iqtree`
- **Python 包**：`pymsaviz`、`biopython`

## 目录结构

```
scripts/analysis/msa/
├── __init__.py           # 包入口，导出主要 API
├── msa_align.py          # 序列比对模块（MAFFT）
├── msa_trim.py           # 比对修剪模块（trimAl）
├── msa_tree_build.py     # 系统发育树构建模块（IQ-TREE）
├── msa_tree_view.py      # 系统发育树可视化模块
├── msa_view.py           # MSA 可视化模块（pyMSAviz）
├── msa_pipeline.py       # 完整分析流程编排
└── msa_toolkit.py        # 统一入口 CLI 工具
```

## 功能模块

| 模块文件 | 功能 | 主要 API |
|----------|------|----------|
| `msa_align.py` | 使用 MAFFT 进行多序列比对，支持多种算法 | `run_mafft(seqs, algo, seq_type)` |
| `msa_trim.py` | 使用 trimAl 修剪比对结果，去除低质量列 | `run_trimal(aligned_fasta, mode)` |
| `msa_tree_build.py` | 使用 IQ-TREE 构建最大似然系统发育树 | `run_iqtree(fasta, model, bootstrap)` |
| `msa_tree_view.py` | 渲染系统发育树图像（PNG/SVG） | `render_tree(treefile, output)` |
| `msa_view.py` | 使用 pyMSAviz 生成 MSA 彩色可视化 PDF | `render_msa(aligned_fasta, output)` |
| `msa_pipeline.py` | 串联全流程：比对 → 修剪 → 可视化 → 建树 | `run_pipeline(seqs, **kwargs)` |
| `msa_toolkit.py` | CLI 统一入口，解析参数并调用流程 | `main()` |

## 序列类型支持

| 类型 | 自动检测规则 |
|------|------------|
| 蛋白（protein） | 序列中含有蛋白特异字符（`D E F H I K L M P Q R S V W Y`）之一 |
| DNA | 仅含 `A T G C N` 且无蛋白特异字符 |
| RNA | 仅含 `A U G C N` 且无蛋白特异字符 |

自动检测优先顺序：蛋白 > DNA > RNA。可通过 `--seq-type` 参数强制指定。

## 使用示例

### CLI 方式

```bash
# 激活环境
conda activate plantsdb

# 基础用法：输入 FASTA，自动比对 + 修剪 + 可视化
python -m scripts.msa.msa_toolkit -i sequences.fasta -o output/

# 指定序列类型和比对算法
python -m scripts.msa.msa_toolkit -i sequences.fasta --seq-type protein --algo linsi

# 比对后同时建树（bootstrap 1000）
python -m scripts.msa.msa_toolkit -i sequences.fasta --tree --bootstrap 1000 --model TEST

# 仅比对，不建树，不修剪
python -m scripts.msa.msa_toolkit -i sequences.fasta --trim-mode none --tree false
```

### Python API 方式

```python
from scripts.msa.msa_pipeline import run_pipeline

result = run_pipeline(
    seqs="sequences.fasta",       # FASTA 文件路径或字符串
    seq_type="auto",              # 自动检测序列类型
    algo="auto",                  # 自动选择 MAFFT 算法
    trim_mode="automated",        # trimAl 自动修剪
    build_tree=True,
    bootstrap=1000,
    model="TEST",
    output_dir="output/msa_result/",
    clean=True,
)

print(result["aligned_fasta"])    # 比对结果路径
print(result["trimmed_fasta"])    # 修剪结果路径
print(result["msa_pdf"])          # MSA 可视化路径
print(result["treefile"])         # 系统发育树路径
print(result["tree_png"])         # 系统发育树图像路径
```

## CLI 参数说明

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | `-i` | 必填 | 输入 FASTA 文件路径 |
| `--output` | `-o` | `./msa_output/` | 输出目录 |
| `--seq-type` | | `auto` | 序列类型：`auto` / `dna` / `rna` / `protein` |
| `--algo` | | `auto` | MAFFT 算法：`auto` / `fftns` / `fftnsi` / `linsi` / `ginsi` / `einsi` |
| `--trim-mode` | | `automated` | trimAl 模式：`automated` / `gappyout` / `strict` / `none` |
| `--tree` | | `false` | 是否构建系统发育树 |
| `--bootstrap` | | `1000` | IQ-TREE bootstrap 次数（须 >= 1000 或设为 0 禁用） |
| `--model` | | `TEST` | IQ-TREE 替换模型，如 `TEST` / `GTR+G` / `LG+G` |
| `--clean` | | `true` | 是否清理 IQ-TREE 中间文件 |

## 输出文件格式

| 文件扩展名 | 内容 |
|-----------|------|
| `.aligned.fasta` | MAFFT 多序列比对结果（FASTA 格式） |
| `.trimmed.fasta` | trimAl 修剪后的比对结果（FASTA 格式） |
| `.msa.pdf` | pyMSAviz 生成的 MSA 彩色可视化图 |
| `.treefile` | IQ-TREE 输出的 Newick 格式系统发育树 |
| `.tree.png` | 系统发育树渲染图像（PNG 格式） |

## 物种检测规则

序列 ID 中物种名的识别规则（按优先级）：

1. 格式 `AT1G12345`（仅数字+字母，无分隔符）→ 物种为 `Arabidopsis thaliana`
2. 格式 `<Species>|<GeneID>` 或 `<Species>_<GeneID>` → 取第一段作为物种前缀
3. FASTA header 中含有 `[Genus species]` 括号格式 → 提取括号内容
4. 无法识别时归为 `Unknown`

## 注意事项

- bootstrap 次数须 >= 1000（在线使用场景），或设为 0 以禁用 bootstrap（快速模式）。
- 在线模式下序列数量上限为 **50 条**，建树上限为 **30 条**；超出时建议本地运行。
- MAFFT `linsi` 算法精度最高，但速度慢，适用于序列数 < 50 且长度 < 2000 的场景。
- `--algo auto` 时：序列数 < 20 使用 `linsi`，否则使用 `fftns`。
- trimAl `automated` 模式会根据比对质量自动选择最优参数，推荐默认使用。
- pyMSAviz 配色方案：蛋白序列使用 Clustal 配色，核酸序列使用 Nucleotide 配色（自动选择）。
