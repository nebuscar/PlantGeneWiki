# PlantsDB 第一批次数据整理与提交任务书

> 版本：1.1
> 日期：2026-04-26
> 状态：草稿

---

## 一、任务背景

PlantsDB 是一个植物基因组功能注释数据库。第一批次数据整理的目标是在五一前后完成数据的标准化处理与数据库提交。

- **项目目标**：五一前后完成第一批次数据整理与提交
- **数据库**：PlantsDB 自有数据库
- **数据来源**：NCBI GenBank / IMP 数据库

---

## 二、数据范围

### 2.1 筛选标准

完整数据需同时满足以下三个条件：
1. 存在 `{Species}_genome.fna` 基因组文件
2. 存在 `{Species}_protein.faa` 蛋白序列文件
3. 存在 `{Species}_annotation.gff` 注释文件

### 2.2 物种列表

- 来源：`data/meta/ncbi/species_list_cleaned.tsv`
- 筛选后数量：待统计（需运行脚本筛选）
- 存储位置：`docs/submission/species_list_batch1.tsv`

### 2.3 排除条件

以下情况不纳入第一批：
- 缺少任一必需文件（fna/faa/gff）
- 文件大小异常（基因组 < 1MB）
- 格式解析失败

---

## 三、工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│ 阶段一：数据筛选 (4月底)                                         │
├─────────────────────────────────────────────────────────────────┤
│ 1. 扫描基因组目录，筛选有完整三文件的物种                         │
│ 2. 生成 species_list_batch1.tsv                                 │
│ 3. 统计各模块覆盖率                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 阶段二：模块执行 (4月底-5月初)                                    │
├─────────────────────────────────────────────────────────────────┤
│ 1. 坐标提取 ────→ extract_genomic_features.py                   │
│ 2. 序列提取 ────→ extract_cds_pep.py                             │
│ 3. ID映射 ──────→ generate_mapping.py                           │
│ 4. 蛋白性质 ─────→ calc_protein_properties.py                   │
│ 5. 功能注释 ─────→ run_eggnog_nested.sh                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 阶段三：整合与质检 (5月初)                                       │
├─────────────────────────────────────────────────────────────────┤
│ 1. 整合各模块结果 ──→ integrate_outputs.py                   │
│ 2. 数据完整性检查                                               │
│ 3. 格式合规性检查                                               │
│ 4. 生成质量报告                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 阶段四：提交入库 (5月初)                                          │
├─────────────────────────────────────────────────────────────────┤
│ 1. 最终数据校验                                                  │
│ 2. 提交到 PlantsDB                                              │
│ 3. 记录提交日志                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、各模块输出规范

| 模块 | 脚本 | 输出文件 | 默认格式 | 列定义 |
|------|------|---------|---------|-------|
| 坐标提取 | `extract_genomic_features.py` | `{Species}_coordinates.tsv` | tsv | gene_id, chromosome, start_position, end_position, strand, species, sequence |
| 序列提取 | `extract_cds_pep.py` | `{Species}_cds_pep.xlsx` | xlsx | protein_id, species, cds, pep |
| ID映射 | `generate_mapping.py` | `{Species}_geneid_protid_mapping.xlsx` | xlsx | gene_id, prot_id |
| 蛋白性质 | `calc_protein_properties.py` | `{Species}_protein_properties.xlsx` | xlsx | protein_id, protein_length, isoelectric_point, molecular_weight |
| 功能注释 | `run_eggnog_nested.sh` | `{Species}_eggnog_annotation.tsv` | tsv | protein_id, species, go, kegg, pfam, function_description |
| 整合 | `integrate_outputs.py` | `{Species}_integrated.xlsx` | xlsx | 合并上述所有模块的关键列 |

---

## 五、命名规范

### 5.1 物种名称格式

- 使用下划线连接单词
- 例：`Oryza_sativa`, `Arabidopsis_thaliana`, `Nicotiana_tabacum`

### 5.2 文件命名格式

**输入文件**：
```
{Species}_genome.fna     # 基因组序列
{Species}_protein.faa    # 蛋白序列
{Species}_cds.fna        # CDS序列
{Species}_annotation.gff # GFF注释
```

**输出文件**：
```
{Species}_geneid_protid_mapping.xlsx  # 基因ID-蛋白ID映射
{Species}_coordinates.tsv             # 坐标信息
{Species}_cds_pep.xlsx                # CDS和蛋白序列
{Species}_protein_properties.xlsx     # 蛋白理化性质
{Species}_eggnog_annotation.tsv       # eggNOG功能注释
{Species}_integrated.xlsx             # 整合结果
```

### 5.3 目录结构

**输入目录**：
```
{genomes_root}/
└── {Species}/
    ├── {Species}_genome.fna
    ├── {Species}_protein.faa
    ├── {Species}_cds.fna
    └── {Species}_annotation.gff
```

**输出目录**：
```
{result_root}/
└── annotation/
    └── {Species}/
        ├── {Species}_geneid_protid_mapping.xlsx
        ├── {Species}_coordinates.tsv
        ├── {Species}_cds_pep.xlsx
        ├── {Species}_protein_properties.xlsx
        ├── {Species}_eggnog_annotation.tsv
        └── {Species}_integrated.xlsx
```

---

## 六、质检标准

### 6.1 数据完整性检查

- [ ] 所有模块均产生输出文件
- [ ] 输出文件行数 > 0
- [ ] protein_id 在所有模块中一致

### 6.2 格式合规性检查

- [ ] 列头与规范一致（小写）
- [ ] 数值类型正确（整型/浮点型）
- [ ] 字符串无多余空白字符

### 6.3 数据一致性检查

- [ ] 蛋白序列长度与坐标长度匹配
- [ ] CDS翻译后与蛋白序列一致

---

## 七、脚本执行命令

### 7.1 模块执行顺序

```bash
# 1. 坐标提取
python scripts/extract_genomic_features.py -i {genomes_root} -o {result_root}/annotation -f

# 2. 序列提取
python scripts/extract_cds_pep.py -b {genomes_root} -d {result_root}/annotation -f xlsx

# 3. ID映射
python scripts/generate_mapping.py -i {genomes_root} -f xlsx

# 4. 蛋白性质
python scripts/calc_protein_properties.py -i {genomes_root} -o {result_root}/annotation -r -f xlsx

# 5. 功能注释
bash Z_archive/run_eggnog_nested.sh -i {genomes_root} -o {result_root}/eggnog_output -f xlsx -c 30

# 6. 整合
python scripts/integrate_outputs.py -i {result_root}/annotation -o {result_root}/integrated -f xlsx
```

### 7.2 默认路径

- 基因组根目录：`/DATA/data2/downloads/genomes`
- 结果输出目录：`/home/nizhu/Projects/plantsdb/result`

---

## 八、时间计划

| 阶段 | 任务 | 截止日期 |
|------|------|---------|
| 阶段一 | 数据筛选，生成物种列表 | 4月底 |
| 阶段二 | 执行各模块注释脚本 | 5月初 |
| 阶段三 | 整合与质检 | 5月初 |
| 阶段四 | 提交入库 | 五一前后 |

---

## 九、附录

### 9.1 相关文件路径

| 文件 | 路径 |
|------|------|
| 物种列表 | `data/meta/ncbi/species_list_cleaned.tsv` |
| 整合脚本 | `scripts/integrate_outputs.py` |
| 坐标提取 | `Z_archive/extract_genomic_features.py` |
| 序列提取 | `scripts/extract_cds_pep.py` |
| ID映射 | `scripts/generate_mapping.py` |
| 蛋白性质 | `scripts/calc_protein_properties.py` |
| 功能注释 | `Z_archive/run_eggnog_nested.sh` |

### 9.2 输出列详解

参见 `docs/submission/file_format_spec.md`