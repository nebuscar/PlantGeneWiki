# MSA Toolkit 需求设计文档

## 1. 背景与目标

### 1.1 背景
多序列比对（MSA）和进化树构建是比较基因组学的基础分析流程。现有工具链分散，需要一个集成工具来统一处理。

### 1.2 目标
- 集成 MAFFT + trimAl + IQ-TREE 流程
- 支持同物种 MSA（仅比对，无树）
- 支持异物种进化树分析（比对 + 建树 + 可视化）
- 提供 Python API 和命令行两种使用方式

---

## 2. 功能需求

### 2.1 核心功能

| 功能 | 工具 | 输入 | 输出 |
|------|------|------|------|
| 多序列比对 | MAFFT | FASTA | Aligned FASTA |
| 序列修剪 | trimAl | Aligned FASTA | Trimmed FASTA |
| 进化树构建 | IQ-TREE | Trimmed FASTA | Newick Tree |
| MSA 可视化 | pyMSAviz | Trimmed FASTA | PDF |
| 树可视化 | Biopython | Newick Tree | PNG |

### 2.2 用户场景

#### 场景 A：同物种多序列 MSA
- 输入：同一物种的多条序列
- 处理：MAFFT 比对 → trimAl 修剪 → MSA 可视化
- 输出：Aligned FASTA + MSA PDF
- **不建树**（同物种建树无意义）

#### 场景 B：异物种进化树分析
- 输入：多个物种的直系同源基因
- 处理：MAFFT 比对 → trimAl 修剪 → IQ-TREE 建树 → 双可视化
- 输出：Aligned FASTA + Trimmed FASTA + MSA PDF + Tree + Tree PNG

### 2.3 物种自动检测

从序列名提取物种信息：

| 序列名格式 | 提取结果 |
|-----------|---------|
| `Acer_negundo\|IMPANE1G...` | Acer_negundo |
| `Acer_negundo_GENEID` | Acer_negundo |
| `IMPANE1G00000024328` | IMPANE1G00000024328 |

- 检测到 **1 个物种** → 场景 A（同物种 MSA）
- 检测到 **>1 个物种** → 场景 B（自动触发建树）

---

## 3. 命令行接口

### 3.1 主命令

```bash
python3 msa_toolkit.py -i <input.fa> -o <output_dir/> [options]
```

### 3.2 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i, --input` | 输入 FASTA 文件（必需） | - |
| `-o, --output` | 输出目录 | `.` |
| `--tree` | 显式触发建树（即使单物种） | False |
| `--bootstrap` | Bootstrap 重复次数（需 ≥1000） | 0 |
| `--trim-mode` | trimAl 修剪模式 | `automated1` |
| `--msa-only` | 仅做 MSA，不建树 | False |
| `--threads` | 并行线程数 | 4 |
| `-f, --force` | 覆盖已有文件 | False |

### 3.3 trimAl 修剪模式

| 模式 | 说明 |
|------|------|
| `automated1` | 自动选择最佳策略（推荐） |
| `strict` | 严格修剪 |
| `strictplus` | 严格+ |
| `gappyout` | 基于间隙比例 |
| `gt90` | 保留 >90% 残基的列 |

---

## 4. 输出文件

```
output_dir/
├── <stem>.aligned.fasta      # MAFFT 比对结果
├── <stem>.trimmed.fasta      # trimAl 修剪结果
├── <stem>.msa.pdf            # MSA 可视化
├── <stem>.treefile           # IQ-TREE Newick 树
├── <stem>.tree.png           # 树可视化 PNG
└── <stem>.trimmed.fasta.*    # IQ-TREE 中间文件
```

---

## 5. 技术实现

### 5.1 依赖工具

| 工具 | 版本 | 用途 |
|------|------|------|
| MAFFT | - | 多序列比对 |
| trimAl | 1.5+ | 序列修剪 |
| IQ-TREE | 3.0+ | 最大似然建树 |
| pyMSAviz | - | MSA 可视化 |
| Biopython | - | 序列处理、树可视化 |
| Matplotlib | - | 绑图 |

### 5.2 Python API

```python
from msa_toolkit import run_mafft, run_trimal, run_iqtree, detect_species

# 单独使用
run_mafft("input.fa", "output.fa")
run_trimal("aligned.fa", "trimmed.fa")

# 物种检测
species = detect_species("input.fa")
print(f"Detected {len(species)} species: {species}")
```

---

## 6. 使用示例

### 6.1 多物种进化树

```bash
python3 msa_toolkit.py -i orthologs.fa -o output/ --bootstrap 1000
```

**自动检测到 3 个物种，执行完整流程并生成进化树。**

### 6.2 同物种 MSA（仅比对）

```bash
python3 msa_toolkit.py -i same_species.fa -o output/
```

**自动检测到 1 个物种，仅做 MSA 不建树。**

### 6.3 强制建树（单物种显式要求）

```bash
python3 msa_toolkit.py -i same_species.fa -o output/ --tree
```

---

## 7. 目录结构

```
scripts/msa/
├── msa_toolkit.py      # 集成工具主脚本
├── __init__.py         # 模块导出
└── test_input.fa       # 测试数据
```

---

## 8. 待确认事项

1. **IQ-TREE bootstrap 阈值**：是否严格要求 ≥1000？
2. **输出文件名格式**：是否需要统一命名规范？
3. **中间文件清理**：是否需要自动删除 IQ-TREE 的 `.log`、`.ckp.gz` 等中间文件？
4. **可视化样式**：树标签是否需要进一步定制（如显示基因 ID）？