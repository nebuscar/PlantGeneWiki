# PlantsDB 文档中心

本项目包含植物基因组同源分析相关的脚本、流程和技能文档。

---

## 文档索引

### 脚本使用 (`scripts/`)

| 文档 | 脚本 | 功能 |
|------|------|------|
| [scripts/README.md](scripts/README.md) | — | 脚本文档索引 |
| [download_genomes.md](scripts/download_genomes.md) | `download/download_genomes.sh` | 从 NCBI 批量下载基因组数据 |
| [imp_download.md](scripts/imp_download.md) | `download/imp_download.sh` | 从 IMP 数据库批量下载植物基因组数据 |
| [run_genetribe.md](scripts/run_genetribe.md) | `homolog/run_genetribe.sh` | 植物基因组同源基因鉴定流水线 |
| [add_taxid.md](scripts/add_taxid.md) | `preprocess/add_taxid.sh` | 使用 Taxonkit 批量添加 Taxonomy ID |
| [calc_protein_properties.md](scripts/calc_protein_properties.md) | `annotation/calc_protein_properties.py` | 批量计算蛋白序列理化性质 |
| [deduplicate_species_list.md](scripts/deduplicate_species_list.md) | `preprocess/deduplicate_species_list.sh` | 按物种名去重 |
| [calc_species_stats.md](scripts/calc_species_stats.md) | `preprocess/calc_species_stats.sh` | 按目/科/属分组统计物种数量 |

### 数据流程 (`pipelines/`)

| 文档 | 说明 |
|------|------|
| [genome_annotation_pipeline.md](pipelines/genome_annotation_pipeline.md) | 基因组结构注释完整流程 |

### 安装指南 (`guides/`)

| 文档 | 说明 |
|------|------|
| [eggnog_mapper_install_guide.md](guides/eggnog_mapper_install_guide.md) | EggNOG-Mapper 安装与使用 |

### 技能手册 (`SKILLS/`)

| 文档 | 说明 |
|------|------|
| [SKILLS/SKILLS.md](SKILLS/SKILLS.md) | 生物信息学技能手册（基因组注释、数据处理、比对分析） |

### 数据提交规范 (`submission/`)

| 文档 | 说明 |
|------|------|
| [submission/task_book.md](submission/task_book.md) | 第一批次数据整理与提交任务书 |
| [submission/file_format_spec.md](submission/file_format_spec.md) | 文件提交格式规范 |
| [submission/naming_convention.md](submission/naming_convention.md) | 文件命名规范 |

### 测试报告 (`reports/`)

| 文档 | 说明 |
|------|------|
| [scripts/run_genetribe_report.md](scripts/run_genetribe_report.md) | run_genetribe.sh 测试报告与耗时推演 |
| [scripts/run_genetribe_debug.md](scripts/run_genetribe_debug.md) | run_genetribe.sh 问题排查指南 |
| [scripts/calc_protein_properties_benchmark.md](scripts/calc_protein_properties_benchmark.md) | 蛋白性质计算资源消耗报告 |

---

## 快速开始

### 1. 准备物种列表

```bash
# 去重 → 添加TaxID
./scripts/preprocess/deduplicate_species_list.sh -i data/meta/species_list.xlsx -o data/meta/species_list_unique.tsv
./scripts/preprocess/add_taxid.sh -i data/meta/species_list_unique.tsv -o data/meta/species_list_with_taxid.txt
```

### 2. 下载基因组数据

**NCBI来源：**
```bash
./scripts/download/download_genomes.sh genus Oryza -i data/meta/species_list_with_taxid.txt
```

**IMP来源：**
```bash
python3 scripts/imp_crawler/species_crawler.py          # 爬取物种列表
./scripts/download/imp_download.sh                      # 批量下载
```

### 3. 同源基因鉴定

```bash
./scripts/homolog/run_genetribe.sh -m all -g -j 3 -t 18
```

### 4. 功能注释

```bash
# eggNOG功能注释
./scripts/homolog/run_eggnog_nested.sh -i /data/genomes -o /results/eggnog -c 30

# 蛋白理化性质
python3 scripts/annotation/calc_protein_properties.py -i /data/genomes -o /results/annotation -r -f xlsx
```

### 5. 整合结果

```bash
python3 scripts/annotation/integrate_outputs.py -i /results/annotation -o /results/integrated -f xlsx
```

---

## 目录结构

```
plantsdb/
├── scripts/                    # 脚本目录
│   ├── annotation/             # 基因组功能注释模块
│   │   ├── calc_protein_properties.py
│   │   ├── extract_cds_pep.py
│   │   ├── extract_genomic_features.py
│   │   ├── generate_mapping.py
│   │   ├── integrate_outputs.py
│   │   └── Management_system.py
│   ├── download/               # 数据下载
│   ├── homolog/               # 同源分析
│   ├── preprocess/            # 数据预处理
│   └── imp_crawler/           # IMP数据爬虫
│
├── utils/                     # 工具脚本
│   ├── visualization/          # 可视化工具
│   └── species_filter.py
│
├── data/                      # 数据目录
│
├── result/                    # 结果目录
│
├── docs/                      # 文档目录
│   ├── scripts/               # 脚本文档
│   ├── pipelines/             # 数据流程
│   ├── guides/                # 安装指南
│   ├── SKILLS/                # 技能手册
│   └── submission/            # 数据提交规范
│
└── Z_archive/                 # 归档文件
    └── legacy/
```

---

## 推荐工作流

```
物种列表准备
  preprocess/deduplicate_species_list.sh  →  preprocess/add_taxid.sh
                                              ↓
基因组下载
  download/download_genomes.sh (NCBI)       download/imp_download.sh (IMP)
                                              ↓
同源分析（属分组并行）            homolog/run_genetribe.sh -m all -g -j 3 -t 18
                                              ↓
功能注释
  homolog/run_eggnog_nested.sh              # eggNOG功能注释
  annotation/calc_protein_properties.py     # 蛋白理化性质
  annotation/extract_genomic_features.py    # 基因组结构信息
  annotation/extract_cds_pep.py              # CDS/PEP序列
  annotation/generate_mapping.py            # 基因ID-蛋白ID映射
                                              ↓
整合                                        annotation/integrate_outputs.py
```