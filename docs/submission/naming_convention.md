# PlantsDB 文件命名规范

> 版本：1.0
> 日期：2026-04-26

---

## 一、命名原则

1. **一致性**：相同类型的文件使用相同的命名模式
2. **可读性**：命名能反映文件内容，便于理解
3. **可追溯性**：包含足够信息便于溯源和检索
4. **兼容性**：避免特殊字符，仅使用字母、数字、下划线、连字符

---

## 二、物种名称格式

### 2.1 命名规则

- 使用**下划线**连接单词
- 拉丁名首字母大写，其余小写
- 禁止使用空格、中文、特殊符号

### 2.2 正确示例

```
Oryza_sativa
Arabidopsis_thaliana
Nicotiana_tabacum
Solanum_lycopersicum
Zea_mays
```

### 2.3 错误示例

```
Oryza sativa    (使用空格)
oryza_sativa    (首字母小写)
Oryza-sativa    (使用连字符)
水稻             (使用中文)
```

---

## 三、输入文件命名

### 3.1 基因组序列文件

| 类型 | 命名模式 | 示例 |
|------|---------|------|
| 基因组序列 | `{Species}_genome.fna` | `Oryza_sativa_genome.fna` |
| 基因组索引 | `{Species}_genome.fna.fai` | `Oryza_sativa_genome.fna.fai` |

### 3.2 蛋白序列文件

| 类型 | 命名模式 | 示例 |
|------|---------|------|
| 蛋白序列 | `{Species}_protein.faa` | `Oryza_sativa_protein.faa` |

### 3.3 CDS序列文件

| 类型 | 命名模式 | 示例 |
|------|---------|------|
| CDS序列 | `{Species}_cds.fna` | `Oryza_sativa_cds.fna` |

### 3.4 注释文件

| 类型 | 命名模式 | 示例 |
|------|---------|------|
| GFF注释 | `{Species}_annotation.gff` | `Oryza_sativa_annotation.gff` |
| GFF3注释 | `{Species}_annotation.gff3` | `Oryza_sativa_annotation.gff3` |
| GenBank格式 | `{Species}_annotation.gbff` | `Oryza_sativa_annotation.gbff` |

### 3.5 元数据文件

| 类型 | 命名模式 | 示例 |
|------|---------|------|
| 下载溯源 | `README_SOURCES.txt` | `README_SOURCES.txt` |
| MD5校验 | `md5sum.txt` | `md5sum.txt` |

---

## 四、输出文件命名

### 4.1 模块输出文件

| 模块 | 命名模式 | 默认格式 | 列字段 |
|------|---------|---------|-------|
| 基因ID映射 | `{Species}_geneid_protid_mapping` | xlsx | gene_id, protein_id |
| 坐标信息 | `{Species}_coordinates` | tsv | gene_id, chromosome, start_position, end_position, strand, species, sequence |
| CDS/PEP序列 | `{Species}_cds_pep` | xlsx | protein_id, species, cds, pep |
| 蛋白性质 | `{Species}_protein_properties` | xlsx | protein_id, protein_length, isoelectric_point, molecular_weight |
| eggNOG注释 | `{Species}_eggnog_annotation` | tsv | protein_id, species, go, kegg, pfam, function_description |
| 整合结果 | `{Species}_integrated` | xlsx | 合并上述所有模块的关键列 |

### 4.2 字段命名规则

- 全部使用**小写**
- 用**下划线**连接
- 不得使用驼峰命名或连字符

正确示例：`protein_id`, `isoelectric_point`, `start_position`
错误示例：`proteinId`, `isoelectric-point`, `ProteinID`

### 4.2 临时/缓存文件

| 类型 | 命名模式 | 说明 |
|------|---------|------|
| BED格式 | `{Species}.bed` | 坐标提取中间文件 |
| 基因FASTA | `{Species}_genes.fasta` | 序列提取中间文件 |
| eggNOG原始 | `{Species}_protein.emapper.annotations` | eggNOG原始输出 |

### 4.3 报告文件

| 类型 | 命名模式 | 说明 |
|------|---------|------|
| 质检报告 | `{Species}_quality_report.txt` | 数据质量报告 |
| 整合报告 | `integration_report.txt` | 批量整合报告 |

---

## 五、目录结构

### 5.1 输入目录结构

```
{genomes_root}/
└── {Species}/
    ├── {Species}_genome.fna           # 基因组序列
    ├── {Species}_protein.faa          # 蛋白序列
    ├── {Species}_cds.fna              # CDS序列
    ├── {Species}_annotation.gff        # GFF注释
    ├── README_SOURCES.txt              # 下载溯源
    └── md5sum.txt                      # 校验文件
```

### 5.2 输出目录结构

```
{result_root}/
├── annotation/
│   └── {Species}/
│       ├── {Species}_geneid_protid_mapping.xlsx
│       ├── {Species}_coordinates.tsv
│       ├── {Species}_cds_pep.xlsx
│       ├── {Species}_protein_properties.xlsx
│       ├── {Species}_eggnog_annotation.tsv
│       └── {Species}_integrated.xlsx
├── eggnog_output/
│   └── {Species}/
│       └── {Species}_protein.emapper.annotations
└── integrated/
    └── {Species}_integrated.xlsx
```

### 5.3 文档目录结构

```
docs/
├── submission/
│   ├── task_book.md                   # 任务书
│   ├── file_format_spec.md            # 文件格式规范
│   ├── naming_convention.md           # 本文档
│   └── species_list_batch1.tsv        # 第一批物种列表
├── scripts/                           # 脚本文档
└── pipelines/                          # 流程文档
```

---

## 六、格式后缀对照表

| 格式 | 后缀 | MIME类型 |
|------|------|---------|
| Excel表格 | .xlsx | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |
| Tab分隔值 | .tsv | text/tab-separated-values |
| 逗号分隔值 | .csv | text/csv |
| 纯文本 | .txt | text/plain |
| FASTA序列 | .faa / .fna / .fa | text/fasta |
| GFF注释 | .gff / .gff3 | text/gff |
| BED坐标 | .bed | text/bed |

---

## 七、命名检查清单

提交前检查：

- [ ] 物种名使用下划线连接，无空格
- [ ] 文件扩展名正确（小写）
- [ ] 输出文件符合 `{Species}_{module}.{ext}` 模式
- [ ] 无中文字符或特殊符号
- [ ] 路径中无空格（适用于shell脚本）

---

## 八、版本历史

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| 1.0 | 2026-04-26 | 初始版本 |