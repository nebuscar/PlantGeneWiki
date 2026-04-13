# calc_protein_properties.py 使用说明

## 概述

批量计算蛋白序列的理化性质，包括**蛋白长度**、**等电点（pI）**和**分子量（MW）**。脚本遍历输入目录下每个物种子目录，读取其中的蛋白 FASTA 文件，逐条计算并导出结果。

---

## 输入数据

### 目录结构要求

输入根目录下每个**子目录**视为一个物种，子目录内需包含以 `protein.faa` 结尾的蛋白 FASTA 文件：

```
input_dir/
├── species_A/
│   └── GCF_000001.protein.faa
├── species_B/
│   └── GCF_000002.protein.faa
└── species_C/
    └── assembly.protein.faa
```

- 若子目录中无 `protein.faa` 文件，该物种将被跳过并输出 `[WARN]`。
- 若存在多个 `protein.faa` 文件，仅使用第一个并输出警告。

### FASTA 文件格式

标准 FASTA 格式，每条序列以 `>` 开头的描述行后跟氨基酸序列。例如：

```
>protein1 some description
MKTLLILAVVATALAHAQPSVQA...
>protein2 another description
MTNIRKSHPLMKIIHVFGNGTA...
```

---

## 输出数据

### 输出列

| 列名               | 含义                          | 数据类型   | 说明                                         |
|--------------------|-------------------------------|-----------|----------------------------------------------|
| `Protein_ID`       | 蛋白 ID                       | 字符串     | 取自 FASTA 描述行 `>` 后的第一个空格前的内容  |
| `Protein_Length`   | 蛋白长度                      | 整数       | 为原始序列长度（含非标准氨基酸，去终止符 `*`）  |
| `Isoelectric_Point`| 等电点（pI）                   | 浮点数/空  | 保留 2 位小数；无法计算时为空                  |
| `Molecular_Weight` | 分子量（Da）                   | 浮点数/空  | 保留 2 位小数；无法计算时为空                  |

### 输出格式

支持 `csv`（默认）、`tsv`、`txt`（制表符分隔）、`xlsx` 四种格式。

### 输出位置

输出文件名统一为 `{物种目录名}_protein_properties.{格式后缀}`，输出目录取决于参数：

| 参数组合                      | 输出位置                                       |
|------------------------------|-----------------------------------------------|
| 未指定 `-o`                   | 结果保存到各物种自身目录                        |
| 指定 `-o` 但无 `-r`           | 所有结果保存到同一输出目录                       |
| 指定 `-o` 且 `-r`             | 按输入目录结构递归创建子目录存放结果              |

---

## 使用方法

### 基本用法

```bash
# 结果保存到各物种自身目录，CSV 格式
python calc_protein_properties.py -i /path/to/input_dir

# 指定输出目录，输出为 xlsx 格式
python calc_protein_properties.py -i /path/to/input_dir -o /path/to/output_dir -f xlsx

# 按输入目录结构递归创建输出子目录
python calc_protein_properties.py -i /path/to/input_dir -o /path/to/output_dir -r -f xlsx
```

### 参数说明

| 参数              | 必需 | 说明                                                       |
|-------------------|------|-----------------------------------------------------------|
| `-i, --input`     | 是   | 输入根目录，其下每个子目录视为一个物种                      |
| `-o, --output`    | 否   | 统一输出目录；未指定时结果保存到各物种自身目录               |
| `-f, --format`    | 否   | 输出格式：`csv`/`tsv`/`txt`/`xlsx`（默认 `csv`）           |
| `-r, --recursive` | 否   | 按输入目录结构递归创建输出目录（仅在 `-o` 指定时生效）       |

---

## 计算方法细节

### 依赖库

使用 Biopython 的 `Bio.SeqUtils.ProtParam.ProteinAnalysis` 类进行计算。

### 序列预处理

1. **去终止符**：移除序列末尾的 `*`（翻译终止符号）。
2. **过滤非标准氨基酸**：仅保留 20 种标准氨基酸 `ACDEFGHIKLMNPQRSTVWY`，其他字符（如 `X`、`U`、`O`、`J`、`B`、`Z` 等）均被剔除，以避免 `ProteinAnalysis` 抛出异常。
3. **长度记录**：`Protein_Length` 记录的是原始序列长度（去 `*` 后，但包含非标准氨基酸字符），而非过滤后的长度。

> 注意：等电点和分子量的计算基于过滤后的序列，而蛋白长度基于原始序列，两者可能存在差异。例如，含 `X` 的序列长度会包含 `X`，但 `X` 不参与 pI 和 MW 的计算。

### 等电点（Isoelectric Point, pI）

- **算法**：Biopython 实现的 Bjellqvist 法，通过二分法搜索使蛋白质净电荷为零时的 pH 值。
- **原理**：根据各氨基酸残基的 pKa 值计算在不同 pH 下的质子化/去质子化状态，求净电荷为零的 pH。
- **精度**：结果保留 2 位小数。

### 分子量（Molecular Weight, MW）

- **算法**：累加各氨基酸残基的平均同位素质量，再加上一个水分子的质量（18.015 Da），减去每条肽键产生的水分子。
- **公式**：MW = Σ(残基质量) + 18.015 − (n−1) × 18.015，其中 n 为残基数。
- **单位**：道尔顿（Da）。
- **精度**：结果保留 2 位小数。

### 无法计算的情况

以下情况将返回空值（`None`）：

- 序列为空（去 `*` 后长度为 0）
- 过滤非标准氨基酸后序列为空
- `ProteinAnalysis` 计算过程中抛出 `ValueError`（会输出警告信息）

---

## 运行示例输出

```
[OK] 处理中：species_A
   已保存 → /path/to/output_dir/species_A_protein_properties.csv

[OK] 处理中：species_B
   已保存 → /path/to/output_dir/species_B_protein_properties.csv

[DONE] 所有物种处理完成！
```
