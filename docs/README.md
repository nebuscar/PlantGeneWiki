# PlantsDB 文档中心

本项目包含植物基因组同源分析相关的脚本、流程和技能文档。

---

## 文档索引

### 脚本使用 (`scripts/`)

| 文档 | 脚本 | 功能 |
|------|------|------|
| [scripts/README.md](scripts/README.md) | — | 脚本文档索引 |
| [scripts/download_genomes.md](scripts/download_genomes.md) | `download_genomes.sh` | 从 NCBI 批量下载基因组数据 |
| [scripts/imp_download.md](scripts/imp_download.md) | `imp_download.sh` | 从 IMP 数据库批量下载植物基因组数据 |
| [scripts/run_genetribe.md](scripts/run_genetribe.md) | `run_genetribe.sh` | 植物基因组同源基因鉴定流水线 |
| [scripts/add_taxid.md](scripts/add_taxid.md) | `add_taxid.sh` | 使用 Taxonkit 批量添加 Taxonomy ID |
| [scripts/calc_protein_properties.md](scripts/calc_protein_properties.md) | `calc_protein_properties.py` | 批量计算蛋白序列理化性质 |
| [scripts/make_bed_chrlist.md](scripts/make_bed_chrlist.md) | `make_bed_chrlist.sh` | 从 GFF 生成 BED 文件和染色体列表 |
| [scripts/deduplicate_species_list.md](scripts/deduplicate_species_list.md) | `deduplicate_species_list.sh` | 按物种名去重 |
| [scripts/calc_species_stats.md](scripts/calc_species_stats.md) | `calc_species_stats.sh` | 按目/科/属分组统计物种数量 |

### 数据流程 (`pipelines/`)

| 文档 | 说明 |
|------|------|
| [genome_annotation_pipeline.md](genome_annotation_pipeline.md) | 基因组结构注释完整流程 |

### 安装指南 (`guides/`)

| 文档 | 说明 |
|------|------|
| [eggnog_mapper_install_guide.md](eggnog_mapper_install_guide.md) | EggNOG-Mapper 安装与使用 |

### 技能手册 (`SKILLS/`)

| 文档 | 说明 |
|------|------|
| [SKILLS/SKILLS.md](SKILLS/SKILLS.md) | 生物信息学技能手册（基因组注释、数据处理、比分析） |

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
./scripts/deduplicate_species_list.sh -i data/meta/species_list.xlsx -o data/meta/species_list_unique.tsv
./scripts/add_taxid.sh -i data/meta/species_list_unique.tsv -o data/meta/species_list_with_taxid.txt
```

### 2. 下载基因组数据

**NCBI来源：**
```bash
./scripts/download_genomes.sh genus Oryza -i data/meta/species_list_with_taxid.txt
```

**IMP来源：**
```bash
python3 scripts/imp_crawler/species_crawler.py          # 爬取物种列表
./scripts/imp_download.sh                              # 批量下载
```

### 3. 同源基因鉴定

```bash
./scripts/run_genetribe.sh -m all -g -j 3 -t 18
```

---

## 目录结构

```
docs/
├── README.md              # 本文档（主索引）
│
├── scripts/               # 脚本使用说明
│   ├── README.md          # 脚本索引
│   ├── download_genomes.md
│   ├── imp_download.md
│   ├── run_genetribe.md
│   └── ...
│
├── pipelines/             # 数据流程
│   └── genome_annotation_pipeline.md
│
├── guides/               # 安装指南
│   └── eggnog_mapper_install_guide.md
│
└── SKILLS/               # 技能手册
    └── SKILLS.md
```

---

## 推荐工作流

```
物种列表准备
  deduplicate_species_list.sh  →  add_taxid.sh
                                    ↓
基因组下载
  download_genomes.sh (NCBI)     imp_download.sh (IMP)
                                    ↓
同源分析（属分组并行）            run_genetribe.sh -m all -g -j 3 -t 18
                                    ↓
蛋白性质计算                      calc_protein_properties.py
```
