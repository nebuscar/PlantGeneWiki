# PlantsDB 文档中心

本项目包含植物基因组同源分析相关的脚本、流程和文档。

---

## 文档索引

### 脚本使用 (`scripts/`)

| 文档 | 脚本 | 功能 |
|------|------|------|
| [scripts/README.md](scripts/README.md) | — | 脚本文档索引 |
| [scripts/download_genomes.md](scripts/download_genomes.md) | `ncbi/download/download_genomes.sh` | 从 NCBI 批量下载基因组数据 |
| [scripts/imp_download.md](scripts/imp_download.md) | `imp/imp_download.sh` | 从 IMP 数据库批量下载植物基因组数据 |
| [scripts/run_genetribe.md](scripts/run_genetribe.md) | `ncbi/homolog/run_genetribe.sh` | NCBI 数据同源基因鉴定流水线 |
| [scripts/add_taxid.md](scripts/add_taxid.md) | `ncbi/preprocess/add_taxid.sh` | 使用 Taxonkit 批量添加 Taxonomy ID |
| [scripts/calc_protein_properties.md](scripts/calc_protein_properties.md) | `ncbi/annotation/calc_protein_properties.py` | 批量计算蛋白序列理化性质 |
| [scripts/deduplicate_species_list.md](scripts/deduplicate_species_list.md) | `ncbi/preprocess/deduplicate_species_list.sh` | 按物种名去重 |

### IMP 流程

| 文档 | 说明 |
|------|------|
| [imp_pipeline_plan.md](imp_pipeline_plan.md) | IMP 数据整合分析计划与进度 |

### 安装指南 (`guides/`)

| 文档 | 说明 |
|------|------|
| [guides/eggnog_mapper_install_guide.md](guides/eggnog_mapper_install_guide.md) | EggNOG-Mapper 安装与使用 |

### 数据提交规范 (`submission/`)

| 文档 | 说明 |
|------|------|
| [submission/task_book.md](submission/task_book.md) | 第一批次数据整理与提交任务书 |
| [submission/file_format_spec.md](submission/file_format_spec.md) | 文件提交格式规范 |
| [submission/naming_convention.md](submission/naming_convention.md) | 文件命名规范 |

### 补充文档

| 文档 | 说明 |
|------|------|
| [scripts/run_genetribe_report.md](scripts/run_genetribe_report.md) | run_genetribe.sh 测试报告与耗时推演 |
| [scripts/run_genetribe_debug.md](scripts/run_genetribe_debug.md) | run_genetribe.sh 问题排查指南 |

---

## 快速开始

### 1. 准备物种列表（NCBI）

```bash
./scripts/ncbi/preprocess/deduplicate_species_list.sh \
    -i data/meta/ncbi/species_list.xlsx \
    -o data/meta/ncbi/species_list_unique.tsv
./scripts/ncbi/preprocess/add_taxid.sh \
    -i data/meta/ncbi/species_list_unique.tsv \
    -o data/meta/ncbi/species_list_with_taxid.txt
```

### 2. 下载基因组数据

**NCBI 来源：**
```bash
./scripts/ncbi/download/download_genomes.sh genus Oryza \
    -i data/meta/ncbi/species_list_with_taxid.txt
```

**IMP 来源：**
```bash
python3 scripts/imp/imp_crawler/species_crawler.py   # 爬取物种列表
bash scripts/imp/imp_download.sh -p A -t 8           # 按前缀批量下载
```

### 3. IMP 数据处理（structure/sequence/properties/eggnog）

```bash
bash scripts/imp/run_imp_pipeline.sh -m all -s Arabidopsis_thaliana
```

### 4. 同源基因鉴定

**IMP 数据（按属）：**
```bash
bash scripts/imp/run_imp_pipeline.sh -m homolog -g -s Acer_campestre
```

**NCBI 数据：**
```bash
./scripts/ncbi/homolog/run_genetribe.sh -m all -g -j 3 -t 18
```

### 5. 功能注释（NCBI）

```bash
./scripts/ncbi/homolog/run_eggnog_nested.sh -i /DATA/data2/downloads/genomes -o result/eggnog -c 30
python3 scripts/ncbi/annotation/calc_protein_properties.py -i /data/genomes -o result/annotation -f xlsx
```

---

## 目录结构

```
plantsdb/
├── scripts/
│   ├── imp/                        # IMP 数据库流程
│   │   ├── run_imp_pipeline.sh     # IMP 主流程脚本
│   │   ├── imp_download.sh         # IMP 数据下载
│   │   └── imp_crawler/            # IMP 网站爬虫
│   └── ncbi/                       # NCBI 数据库流程
│       ├── annotation/             # 功能注释模块
│       ├── download/               # 基因组下载
│       ├── homolog/                # 同源分析
│       └── preprocess/             # 数据预处理
│
├── data/
│   └── meta/
│       ├── ncbi/                   # NCBI 物种元数据
│       └── imp/                    # IMP 物种元数据
│
├── result/
│   └── result_imp/
│       ├── species/                # 物种级注释结果
│       └── homolog/                # 属级同源结果（含 *_homolog_1v1.tsv）
│
├── docs/                           # 文档目录
│   ├── scripts/                    # 脚本使用文档
│   ├── guides/                     # 安装指南
│   └── submission/                 # 数据提交规范
│
├── utils/                          # 工具脚本
└── Z_archive/                      # 归档文件
```

---

## 推荐工作流

```
物种列表准备（NCBI）
  ncbi/preprocess/deduplicate_species_list.sh  →  ncbi/preprocess/add_taxid.sh
                                                    ↓
基因组下载
  ncbi/download/download_genomes.sh (NCBI)     imp/imp_download.sh (IMP)
                                                    ↓
IMP 数据处理                                   imp/run_imp_pipeline.sh -m all
                                                    ↓
同源分析（属分组）
  imp/run_imp_pipeline.sh -m homolog -g        ncbi/homolog/run_genetribe.sh -m all -g
                                                    ↓
功能注释（NCBI）
  ncbi/homolog/run_eggnog_nested.sh            ncbi/annotation/calc_protein_properties.py
                                                    ↓
整合                                           ncbi/annotation/integrate_outputs.py
```
