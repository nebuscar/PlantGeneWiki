# PlantsDB 文件提交格式规范

> 版本：1.1
> 日期：2026-04-26

---

## 概述

本文档定义 PlantsDB 数据提交的文件格式规范。所有提交文件必须符合此规范。

**字段命名规则**：全部使用小写，用下划线连接（如 `protein_id`, `isoelectric_point`）

---

## 1. 基因ID映射表

**文件命名**：`{Species}_geneid_protid_mapping.xlsx`

**文件格式**：Excel表格 (.xlsx)

**列定义**：

| 列名 | 数据类型 | 说明 |
|------|---------|------|
| gene_id | string | 基因ID，来源于GFF的locus_tag |
| protein_id | string | 蛋白ID，来源于GFF的protein_id |

**示例**：

| gene_id | prot_id |
|---------|---------|
| gene-LOC_Os01g0100100 | LOC_Os01g0100100.1 |
| gene-LOC_Os01g0100200 | LOC_Os01g0100200.1 |

---

## 2. 坐标信息表

**文件命名**：`{Species}_coordinates.tsv`

**文件格式**：Tab-separated values (.tsv)

**列定义**：

| 列名 | 数据类型 | 说明 |
|------|---------|------|
| gene_id | string | 基因ID |
| chromosome | string | 染色体编号 |
| start_position | int | 基因起始位置（1-based） |
| end_position | int | 基因终止位置 |
| strand | string | 链方向（+ 或 -） |
| species | string | 物种名称 |
| sequence | string | 基因序列（FASTA header + 序列） |

**示例**：

```
gene_id	chromosome	start_position	end_position	strand	species	sequence
LOC_Os01g0100100.1	Chr1	3630	3928	+	Oryza_sativa	>LOC_Os01g0100100.1::Chr1:3630-3928
AT1G01010.1	Chr1	3631	5899	+	Arabidopsis_thaliana	>AT1G01010.1::Chr1:3631-5899
```

---

## 3. CDS/PEP序列表

**文件命名**：`{Species}_cds_pep.xlsx`

**文件格式**：Excel表格 (.xlsx)

**列定义**：

| 列名 | 数据类型 | 说明 |
|------|---------|------|
| protein_id | string | 蛋白ID |
| species | string | 物种名称 |
| cds | string | CDS核酸序列 |
| pep | string | 蛋白氨基酸序列 |

**示例**：

| protein_id | species | cds | pep |
|-----------|---------|-----|-----|
| LOC_Os01g0100100.1 | Oryza_sativa | ATGGCC... | MA... |
| AT1G01010.1 | Arabidopsis_thaliana | ATGGCT... | MACC... |

---

## 4. 蛋白理化性质表

**文件命名**：`{Species}_protein_properties.xlsx`

**文件格式**：Excel表格 (.xlsx)

**列定义**：

| 列名 | 数据类型 | 说明 |
|------|---------|------|
| protein_id | string | 蛋白ID |
| protein_length | int | 蛋白长度（氨基酸数） |
| isoelectric_point | float | 等电点（pI），保留2位小数 |
| molecular_weight | float | 分子量（Da），保留2位小数 |

**示例**：

| protein_id | protein_length | isoelectric_point | molecular_weight |
|-----------|---------------|------------------|-----------------|
| LOC_Os01g0100100.1 | 321 | 5.68 | 35234.56 |
| AT1G01010.1 | 298 | 6.23 | 32891.12 |

---

## 5. eggNOG功能注释表

**文件命名**：`{Species}_eggnog_annotation.tsv`

**文件格式**：Tab-separated values (.tsv)

**列定义**：

| 列名 | 数据类型 | 说明 |
|------|---------|------|
| protein_id | string | 蛋白ID |
| species | string | 物种名称 |
| go | string | Gene Ontology注释，多个用逗号分隔，无则为空 |
| kegg | string | KEGG通路注释，无则为空 |
| pfam | string | Pfam结构域注释，无则为空 |
| function_description | string | 功能描述，无则为空 |

**示例**：

```
protein_id	species	go	kegg	pfam	function_description
LOC_Os01g0100100.1	Oryza_sativa	GO:0003677,GO:0004386	K00175,K00176	PF00106,PF00005	Lactate dehydrogenase
AT1G01010.1	Arabidopsis_thaliana	GO:0003723	-	PF00514	RNA-binding protein
```

---

## 6. 整合注释表

**文件命名**：`{Species}_integrated.xlsx`

**文件格式**：Excel表格 (.xlsx)

**列定义**：合并上述所有模块的关键列

| 列名 | 数据类型 | 来源模块 |
|------|---------|---------|
| protein_id | string | 所有模块 |
| gene_id | string | coordinates, mapping |
| chromosome | string | coordinates |
| start_position | int | coordinates |
| end_position | int | coordinates |
| strand | string | coordinates |
| species | string | 所有模块 |
| protein_length | int | protein_properties |
| isoelectric_point | float | protein_properties |
| molecular_weight | float | protein_properties |
| go | string | eggnog |
| kegg | string | eggnog |
| pfam | string | eggnog |
| function_description | string | eggnog |

---

## 7. 质检报告

**文件命名**：`{Species}_quality_report.txt`

**文件格式**：纯文本 (.txt)

**内容结构**：

```
Species: {Species}
Check Date: {YYYY-MM-DD}

=== Data Completeness ===
Mapping file: [PASS/FAIL] - {count} records
Coordinates file: [PASS/FAIL] - {count} genes
CDS/PEP file: [PASS/FAIL] - {count} sequences
Protein properties: [PASS/FAIL] - {count} proteins
eggNOG annotation: [PASS/FAIL] - {count} annotations

=== Format Validation ===
Column headers: [PASS/FAIL] - all lowercase
Data types: [PASS/FAIL]

=== Consistency Checks ===
Protein ID consistency: [PASS/FAIL]
Sequence length match: [PASS/FAIL]

Overall Status: [PASS/FAIL]
```

---

## 8. 格式转换规则

### 8.1 Excel → TSV

```python
import pandas as pd
df = pd.read_excel('input.xlsx')
df.to_csv('output.tsv', sep='\t', index=False)
```

### 8.2 TSV → Excel

```python
import pandas as pd
df = pd.read_csv('input.tsv', sep='\t')
df.to_excel('output.xlsx', index=False)
```

---

## 9. 特殊字符处理

- 序列中的换行符：保持连续，不拆分
- 制表符和逗号：转义或移除
- 空值：留空，不使用 "NA" 或 "null"

---

## 10. 文件编码

- 所有文件使用 **UTF-8** 编码
- Excel文件使用 UTF-8-sig 签名（如需要中文字段）