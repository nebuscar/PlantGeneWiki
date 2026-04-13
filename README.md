# PlantsDB - Plant Standard Genome Database / 植物标准基因组库

[English](#english) | [中文](#chinese)

---

<a id="english"></a>

## English

PlantsDB is a bioinformatics pipeline for building a standardized plant genome resource. It curates a species list, batch-downloads genome assemblies and annotations from NCBI, processes and standardizes the data, and enables comparative genomics analysis.

### Features

- **Batch genome downloading** from NCBI via the `datasets` CLI, with filtering by assembly level, source, version, date, and reference status
- **Automatic file organization** — unzips downloads, selects the best assembly accession (RefSeq/GCF prioritized over GenBank/GCA), renames files to the standardized `{SpeciesName}_{type}.{ext}` format, and cleans up NCBI directory artifacts
- **Taxonomy ID enrichment** — adds NCBI taxonomy IDs to species lists using `taxonkit`
- **Species list deduplication** — keeps only the first occurrence of each species name
- **Species statistics** — counts species by Order, Family, or Genus with ranked output
- **Protein property computation** — calculates isoelectric point (pI), molecular weight (MW), and protein length; supports CSV/TSV/XLSX export
- **Comparative genomics** — GeneTribe integration for homologous gene identification, with BED files generated from GFF annotations via JCVI
- **Resumable downloads** — skips species with existing genome files; maintains detailed success/fail/skip logs
- **Download provenance** — generates `README_SOURCES.txt` per species documenting accession, data source, and download timestamp

### Prerequisites

**System tools:**

- Bash
- [NCBI datasets CLI](https://www.ncbi.nlm.nih.gov/datasets/docs/command-line-data-download/) — for downloading genome assemblies
- [taxonkit](https://github.com/shenwei356/taxonkit) — for taxonomy ID lookups
- `unzip`
- Standard Unix tools: `awk`, `sed`, `cut`, `find`

**Python 3 packages:**

```bash
pip install biopython pandas openpyxl
```

**Optional tools:**

- [JCVI](https://github.com/tanghaibao/jcvi) (`pip install jcvi`) — for GFF-to-BED conversion
- [GeneTribe](https://github.com/GeneTribe/GeneTribe) — for homologous gene analysis
- `ssconvert` (from [gnumeric](https://github.com/GNOME/gnumeric)) — for XLSX export in `add_taxid.sh`

### Project Structure

```
plantsdb/
├── data/
│   └── meta/
│       ├── species_list.txt                  # Species list (7 columns)
│       ├── species_list_with_taxid.txt       # Species list with Taxonomy ID (8 columns)
│       ├── species_list_unique_with_taxid.txt # Deduplicated: 2010 unique species
│       └── species_list.xlsx                 # Excel version
├── downloads/                                # Downloaded genome data (git-ignored)
│   └── logs/
│       ├── total.log
│       ├── success.log
│       ├── fail.log
│       └── skip.log
├── sample/                                   # Example species data (git-ignored)
├── scripts/
│   ├── download_genomes.sh                   # Batch download genomes from NCBI
│   ├── add_taxid.sh                          # Add Taxonomy IDs to species list
│   ├── deduplicate_species_list.sh           # Deduplicate species by name
│   ├── calc_species_stats.sh                 # Species count statistics
│   ├── make_bed_chrlist.sh                   # Generate BED + chr.list from GFF
│   ├── run_genetribe.sh                      # Run GeneTribe homologous gene analysis
│   ├── calc_protein_properties.py            # Compute protein pI, MW, length
│   └── batch_pi_mw.py                        # Alternative protein property calculator
└── tmp/                                      # Temporary files
```

### Usage

#### Add Taxonomy IDs to the species list

```bash
bash scripts/add_taxid.sh -i data/meta/species_list.txt -o data/meta/species_list_with_taxid.txt
```

#### Deduplicate species list

```bash
bash scripts/deduplicate_species_list.sh -i data/meta/species_list_with_taxid.txt \
  -o data/meta/species_list_unique_with_taxid.txt -s
```

#### Download genomes from NCBI

```bash
# By genus
bash scripts/download_genomes.sh genus Oryza

# By family
bash scripts/download_genomes.sh family Fabaceae

# By order
bash scripts/download_genomes.sh order Brassicales

# All species
bash scripts/download_genomes.sh all

# Test single species
bash scripts/download_genomes.sh -t "Arabidopsis thaliana"

# With filters (reference genomes only, chromosome-level assemblies)
bash scripts/download_genomes.sh genus Oryza --reference --assembly-level chromosome

# List available groups
bash scripts/download_genomes.sh -l family

# Custom output directory
bash scripts/download_genomes.sh genus Oryza -o /path/to/output
```

#### Generate BED and chr.list files

```bash
bash scripts/make_bed_chrlist.sh
```

#### Calculate species statistics

```bash
bash scripts/calc_species_stats.sh -i species_list.txt -o stats_order.txt -g order
bash scripts/calc_species_stats.sh -i species_list.txt -o stats_family.txt -g family
bash scripts/calc_species_stats.sh -i species_list.txt -o stats_genus.txt -g genus
```

#### Compute protein physicochemical properties

```bash
python scripts/calc_protein_properties.py -i ./sample -f csv
# With custom output directory
python scripts/calc_protein_properties.py -i ./sample -o ./output -f xlsx
```

#### Run GeneTribe (homologous gene analysis)

```bash
bash scripts/run_genetribe.sh
```

### Species List Format

The species list (`species_list.txt`) is a TSV file with the following columns:

| Column | Field | Example |
|--------|-------|---------|
| 1 | No. species | 1 |
| 2 | Species | Abeliophyllum distichum |
| 3 | Ploidy | diploid |
| 4 | Accession name | cultivar 'Wufu' |
| 5 | Order | Lamiales |
| 6 | Family | Oleaceae |
| 7 | Clade (Genus) | Abeliophyllum |

The `species_list_with_taxid.txt` adds a `Taxonomy ID` column between Species and Ploidy.

### License

This project is provided as-is for research purposes.

---

<a id="chinese"></a>

## 中文

PlantsDB 是一个用于构建标准化植物基因组资源的生物信息学流程。它管理物种列表、从 NCBI 批量下载基因组组装和注释数据、对数据进行处理和标准化，并支持比较基因组学分析。

### 功能特点

- **批量基因组下载** — 通过 NCBI `datasets` 命令行工具下载，支持按组装水平、数据来源、版本、日期和参考基因组状态进行过滤
- **自动文件整理** — 解压下载文件，优先选择 RefSeq/GCA 登录号（优于 GenBank/GCA），将文件重命名为标准化的 `{物种名}_{类型}.{扩展名}` 格式，并清理 NCBI 目录残留文件
- **分类学 ID 补充** — 使用 `taxonkit` 为物种列表添加 NCBI 分类学 ID
- **物种列表去重** — 仅保留每个物种名的首次出现
- **物种统计** — 按目、科或属统计物种数量并排序输出
- **蛋白质性质计算** — 计算等电点 (pI)、分子量 (MW) 和蛋白质长度；支持 CSV/TSV/XLSX 格式导出
- **比较基因组学** — 集成 GeneTribe 进行同源基因鉴定，通过 JCVI 从 GFF 注释生成 BED 文件
- **断点续传下载** — 自动跳过已有基因组文件的物种；维护详细的成功/失败/跳过日志
- **下载溯源** — 为每个物种生成 `README_SOURCES.txt`，记录登录号、数据来源和下载时间戳

### 环境要求

**系统工具：**

- Bash
- [NCBI datasets 命令行工具](https://www.ncbi.nlm.nih.gov/datasets/docs/command-line-data-download/) — 用于下载基因组组装数据
- [taxonkit](https://github.com/shenwei356/taxonkit) — 用于分类学 ID 查询
- `unzip`
- 标准 Unix 工具：`awk`、`sed`、`cut`、`find`

**Python 3 依赖包：**

```bash
pip install biopython pandas openpyxl
```

**可选工具：**

- [JCVI](https://github.com/tanghaibao/jcvi)（`pip install jcvi`）— 用于 GFF 转 BED
- [GeneTribe](https://github.com/GeneTribe/GeneTribe) — 用于同源基因分析
- `ssconvert`（来自 [gnumeric](https://github.com/GNOME/gnumeric)）— 用于 `add_taxid.sh` 中的 XLSX 导出

### 项目结构

```
plantsdb/
├── data/
│   └── meta/
│       ├── species_list.txt                  # 物种列表（7 列）
│       ├── species_list_with_taxid.txt       # 含分类学 ID 的物种列表（8 列）
│       ├── species_list_unique_with_taxid.txt # 去重后：2010 个唯一物种
│       └── species_list.xlsx                 # Excel 格式
├── downloads/                                # 下载的基因组数据（已加入 .gitignore）
│   └── logs/
│       ├── total.log
│       ├── success.log
│       ├── fail.log
│       └── skip.log
├── sample/                                   # 示例物种数据（已加入 .gitignore）
├── scripts/
│   ├── download_genomes.sh                   # 从 NCBI 批量下载基因组
│   ├── add_taxid.sh                          # 为物种列表添加分类学 ID
│   ├── deduplicate_species_list.sh           # 按物种名去重
│   ├── calc_species_stats.sh                 # 物种数量统计
│   ├── make_bed_chrlist.sh                   # 从 GFF 生成 BED 和 chr.list
│   ├── run_genetribe.sh                      # 运行 GeneTribe 同源基因分析
│   ├── calc_protein_properties.py            # 计算蛋白质 pI、MW、长度
│   └── batch_pi_mw.py                        # 备用蛋白质性质计算脚本
└── tmp/                                      # 临时文件
```

### 使用方法

#### 为物种列表添加分类学 ID

```bash
bash scripts/add_taxid.sh -i data/meta/species_list.txt -o data/meta/species_list_with_taxid.txt
```

#### 物种列表去重

```bash
bash scripts/deduplicate_species_list.sh -i data/meta/species_list_with_taxid.txt \
  -o data/meta/species_list_unique_with_taxid.txt -s
```

#### 从 NCBI 下载基因组

```bash
# 按属下载
bash scripts/download_genomes.sh genus Oryza

# 按科下载
bash scripts/download_genomes.sh family Fabaceae

# 按目下载
bash scripts/download_genomes.sh order Brassicales

# 下载所有物种
bash scripts/download_genomes.sh all

# 测试单个物种
bash scripts/download_genomes.sh -t "Arabidopsis thaliana"

# 带过滤条件（仅参考基因组，染色体水平组装）
bash scripts/download_genomes.sh genus Oryza --reference --assembly-level chromosome

# 列出可用分组
bash scripts/download_genomes.sh -l family

# 自定义输出目录
bash scripts/download_genomes.sh genus Oryza -o /path/to/output
```

#### 生成 BED 和 chr.list 文件

```bash
bash scripts/make_bed_chrlist.sh
```

#### 计算物种统计

```bash
bash scripts/calc_species_stats.sh -i species_list.txt -o stats_order.txt -g order
bash scripts/calc_species_stats.sh -i species_list.txt -o stats_family.txt -g family
bash scripts/calc_species_stats.sh -i species_list.txt -o stats_genus.txt -g genus
```

#### 计算蛋白质理化性质

```bash
python scripts/calc_protein_properties.py -i ./sample -f csv
# 自定义输出目录
python scripts/calc_protein_properties.py -i ./sample -o ./output -f xlsx
```

#### 运行 GeneTribe（同源基因分析）

```bash
bash scripts/run_genetribe.sh
```

### 物种列表格式

物种列表（`species_list.txt`）为 TSV 格式，包含以下列：

| 列号 | 字段 | 示例 |
|------|------|------|
| 1 | 序号 | 1 |
| 2 | 物种名 | Abeliophyllum distichum |
| 3 | 倍性 | diploid |
| 4 | 登录名 | cultivar 'Wufu' |
| 5 | 目 | Lamiales |
| 6 | 科 | Oleaceae |
| 7 | 分支（属） | Abeliophyllum |

`species_list_with_taxid.txt` 在物种名和倍性之间增加了一列 `Taxonomy ID`。

### 许可证

本项目仅供研究使用。
