# PlantGeneWiki — 植物标准基因组库

---

PlantGeneWiki 是一个用于构建标准化植物基因组资源的生物信息学流程。项目对接多个数据来源（PGCP、IMP 和 NCBI），完成物种列表管理、基因组批量下载、数据标准化处理和比较基因组学分析。

## 数据来源

| 来源 | 物种范围 | 状态 |
|------|---------|------|
| **PGCP**（Plant Genome Comparison Platform） | 706 个植物物种 | 已完成，数据量 240.82 GB |
| **IMP**（Integrated Multi-omics Plant database） | ~1,068 个植物物种 | A 字母批次已完成；B–Z 待处理 |
| **NCBI** | 用户自定义物种列表 | 流程已归档（暂不使用） |

### PGCP 数据说明

PGCP 提供完整的基因组注释文件下载，包含：
- **Assembly** — 基因组序列（`.genomic.fa.gz`）
- **Annotation** — 基因/转录本注释（`.gff.gz`）
- **Protein** — 蛋白质序列（`.pep.fa.gz`）
- **Transcript** — 转录本序列（`.cds.fa.gz`）
- **Function** — 功能注释（InterPro）
- **Repeat Region** — 重复区域注释

数据位置：`data/meta/pgcp/`

## 功能特点

### IMP 流程

- **物种列表爬取** — 从 IMP 网站抓取完整物种清单
- **批量下载** — 每个物种下载 7 类文件：基因组（`.fa.gz`）、注释（`.gff3.gz`）、基因/CDS/蛋白序列、2 kb 启动子 FASTA、RNA-seq TPM 矩阵
- **标准化注释** — 提取基因结构（坐标、链方向）、蛋白理化性质（pI、MW、长度）和功能注释（GO、KEGG、Pfam，通过 EggNOG-mapper）
- **属内同源分析** — 使用 GeneTribe（blastp + BSR + RBH）鉴定属内 1-vs-1 直系同源对
- **增量处理** — 各模块检测已有输出文件后跳过，支持断点续算

### PGCP 流程

- **数据爬取** — 从 BioBigData PGCP 网站抓取完整物种文件列表
- **文件清单** — 按物种分类整理下载元信息（文件名、类型、大小、下载链接）
- **批量下载** — 通过 API 接口批量下载基因组和注释文件
- **数据统计** — 生成物种汇总表和文件类型分布统计

### NCBI 流程 _（已归档，暂不使用）_

- **批量基因组下载** — 通过 `datasets` 命令行工具，支持按组装水平、数据来源、版本、日期和参考基因组状态过滤
- **自动文件整理** — 解压后优先选取 RefSeq/GCF 登录号，文件重命名为 `{物种名}_{类型}.{扩展名}` 标准格式
- **分类学 ID 补充** — 使用 `taxonkit` 为物种列表添加 NCBI 分类学 ID
- **物种列表去重** — 保留每个物种名的首次出现
- **物种统计** — 按目、科或属统计物种数量并排序输出
- **蛋白理化性质计算** — 计算等电点（pI）、分子量（MW）和蛋白质长度；支持 CSV/TSV/XLSX 导出
- **比较基因组学** — 集成 EggNOG + GeneTribe 进行功能注释和同源基因鉴定
- **下载溯源** — 为每个物种生成 `README_SOURCES.txt`，记录登录号、数据来源和下载时间戳

## IMP 当前数据状态（A 字母批次，2026-05-06）

第一批覆盖全部 A 字母开头物种（约 115 个物种，处理结果约 32 GB，原始数据约 55 GB）。

| 模块 | 覆盖情况 |
|------|---------|
| 原始下载 | 129 个物种 |
| structure / gene / protein / cds | 112 / 115 个物种 |
| properties | 111 / 115 个物种 |
| eggnog 功能注释 | 110 / 115 个物种 |
| 属内同源分析（已完成） | 13 个属 |

同源分析：13 个属已完成，Aegilops 和 Amborella 待运行，6 个属因数据不可用跳过，Andropogon 因上游数据格式不一致无法修复。

## 环境依赖

**系统工具：**

- Bash
- [NCBI datasets 命令行工具](https://www.ncbi.nlm.nih.gov/datasets/docs/command-line-data-download/)
- [taxonkit](https://github.com/shenwei356/taxonkit)
- `unzip`
- 标准 Unix 工具：`awk`、`sed`、`cut`、`find`

**Python 3 依赖包：**

```bash
pip install biopython pandas openpyxl playwright requests selenium
python -m playwright install chromium
```

**生物信息学工具：**

- [EggNOG-mapper](https://github.com/eggnogdb/eggnog-mapper) v2.1+ — 功能注释（`biotools` conda 环境）
- [JCVI](https://github.com/tanghaibao/jcvi)（`pip install jcvi`）— GFF 转 BED
- [GeneTribe](https://github.com/GeneTribe/GeneTribe) — 同源基因鉴定（`genetribe` conda 环境）
- `ssconvert`（gnumeric）— `add_taxid.sh` 中的 XLSX 导出

## 项目结构

```
plantsdb/
├── data/
│   └── meta/
│       ├── pgcp/                             # PGCP 数据（706 物种，240.82 GB）
│       │   ├── biobigdata_downloads.tsv     # 完整文件清单
│       │   ├── biobigdata_summary.tsv        # 物种汇总表
│       │   ├── biobigdata_downloads.json     # JSON 格式完整数据
│       │   └── biobigdata_species/           # 按物种分类的文件
│       ├── imp/
│       │   ├── species_manifest.tsv          # IMP 完整物种清单
│       │   ├── species_list_cleaned.tsv      # 清洗后物种列表
│       │   ├── species_availability.tsv      # 下载状态（available/partial/unavailable）
│       │   ├── species_missing.tsv           # 缺失文件物种
│       │   ├── species_list.json             # 爬取原始数据
│       │   └── species_list.xlsx             # Excel 格式
│       └── ncbi/                             # NCBI 物种元数据
├── downloads/                                # 原始下载（已加入 .gitignore）
│   ├── genomes/                              # NCBI 基因组下载
│   └── IMP/                                  # IMP 原始下载（约 55 GB，A 字母批次）
│       └── logs/
├── result/
│   ├── result_imp/                           # IMP 流程输出（约 32 GB，A 字母批次）
│   │   ├── species/
│   │   │   └── {Species}/
│   │   │       ├── {Species}.structure.tsv   # 基因坐标
│   │   │       ├── {Species}.properties.tsv  # pI、MW、蛋白长度
│   │   │       ├── {Species}.eggnog.tsv     # GO、KEGG、Pfam、描述
│   │   │       ├── {Species}.gene.fa
│   │   │       ├── {Species}.protein.fa
│   │   │       └── {Species}.cds.fa
│   │   └── homolog/
│   │       └── {Genus}_homolog_1v1.tsv      # 属内 1-vs-1 直系同源对
│   └── result_ncbi/                          # NCBI 流程输出
├── scripts/
│   ├── pgcp/                                # PGCP 数据工具
│   │   ├── scrape_biobigdata.py             # 数据爬取
│   │   └── download_api.py                  # 下载工具
│   ├── imp/
│   │   ├── imp_crawler/                     # IMP 网站爬虫
│   │   ├── imp_download.sh                  # IMP 批量下载
│   │   └── run_imp_pipeline.sh             # IMP 注释流程
│   ├── ncbi/                                # NCBI 流程（已归档）
│   ├── esmfold/                             # 蛋白质结构预测
│   └── msa/                                 # 多序列比对工具包
├── utils/                                   # 通用工具
│   ├── species_filter.py
│   ├── species_filter.sh
│   └── visualization/
└── docs/                                    # 文档（已归档）
```

## 快速开始

### PGCP 流程

```bash
# 1. 查看数据概览
head data/meta/pgcp/biobigdata_summary.tsv

# 2. 列出所有物种
python scripts/pgcp/download_api.py list

# 3. 下载指定物种文件
python scripts/pgcp/download_api.py species abies_alba
python scripts/pgcp/download_api.py species abies_alba --pattern "*.genomic.fa.gz"
```

### IMP 流程

```bash
# 1. 爬取 IMP 物种列表
python scripts/imp/imp_crawler/species_crawler.py

# 2. 批量下载（按首字母分批，推荐）
bash scripts/imp/imp_download.sh -p A -t 4

# 后台运行
nohup bash scripts/imp/imp_download.sh -p A -t 4 \
  > downloads/IMP/logs/download_A.log 2>&1 &

# 3. 运行注释流程
#    MODE: structure / sequence / properties / eggnog / homolog / all
bash scripts/imp/run_imp_pipeline.sh -m all

# 仅处理单个物种
bash scripts/imp/run_imp_pipeline.sh -m all -s Arabidopsis_thaliana
```

### NCBI 流程 _（已归档，脚本文档见 `docs/archive/ncbi/`）_

```bash
# 1. 补充分类学 ID
bash scripts/ncbi/preprocess/add_taxid.sh \
  -i data/meta/ncbi/species_list.txt \
  -o data/meta/ncbi/species_list_with_taxid.txt

# 2. 去重
bash scripts/ncbi/preprocess/deduplicate_species_list.sh \
  -i data/meta/ncbi/species_list_with_taxid.txt \
  -o data/meta/ncbi/species_list_unique.txt -s

# 3. 下载基因组
bash scripts/ncbi/download/download_genomes.sh genus Oryza
bash scripts/ncbi/download/download_genomes.sh all

# 4. 功能注释与蛋白性质计算
python scripts/ncbi/annotation/calc_protein_properties.py -i ./sample -f csv

# 5. 同源基因分析
bash scripts/ncbi/homolog/run_genetribe.sh
```

## IMP 脚本参数

```
scripts/imp/run_imp_pipeline.sh

  -i DIR    输入目录（默认：/DATA/data2/downloads/IMP）
  -o DIR    输出目录（默认：result/result_imp）
  -m MODE   模块：structure / sequence / properties / eggnog / homolog / all
  -s NAME   仅处理指定物种目录
```

```
scripts/imp/imp_download.sh

  -p PREFIX   仅下载目录名以 PREFIX 开头的物种
  -t THREADS  并行线程数（默认：4）
  -d          预览模式（不实际下载）
  --list      仅爬取物种列表
```

## NCBI 下载参数 _（已归档）_

> NCBI 流程脚本已归档至 `docs/archive/ncbi/`，以下命令仅供参考。

```bash
# 按分类级别下载
bash scripts/ncbi/download/download_genomes.sh genus Oryza
bash scripts/ncbi/download/download_genomes.sh family Fabaceae
bash scripts/ncbi/download/download_genomes.sh order Brassicales

# 下载所有物种
bash scripts/ncbi/download/download_genomes.sh all

# 带过滤条件
bash scripts/ncbi/download/download_genomes.sh genus Oryza \
  --reference --assembly-level chromosome

# 列出可用分组
bash scripts/ncbi/download/download_genomes.sh -l family

# 自定义输出目录
bash scripts/ncbi/download/download_genomes.sh genus Oryza -o /path/to/output
```

## 输出格式说明

### IMP `species/` 输出

| 文件 | 列名 |
|------|------|
| `*.structure.tsv` | `gene_id`、`chromosome`、`start`、`end`、`strand` |
| `*.properties.tsv` | `gene_id`、`mRNA_id`、`protein_length`、`isoelectric_point`、`molecular_weight` |
| `*.eggnog.tsv` | `gene_id`、`mRNA_id`、`GO`、`KEGG`、`Pfam`、`Description` |
| `*.gene.fa` | `>gene_id` |
| `*.protein.fa` / `*.cds.fa` | `>gene_id\|mRNA_id` |

### IMP `homolog/` 输出

`{属名}_homolog_1v1.tsv` — 列名为属内各物种名，每行为一个直系同源基因簇，缺失成员用 `-` 表示。

## 相关文档

- [`docs/imp/imp_pipeline_plan.md`](docs/imp/imp_pipeline_plan.md) — IMP 流程进度与计划
- [`docs/imp/scripts/imp_download.md`](docs/imp/scripts/imp_download.md) — IMP 下载脚本说明
- [`docs/imp/guides/eggnog_mapper_install_guide.md`](docs/imp/guides/eggnog_mapper_install_guide.md) — EggNOG-mapper 安装指南
- [`docs/agent/agent_design.md`](docs/agent/agent_design.md) — AI Agent 使用场景设计
- [`docs/agent/ai_agent_user_guide.md`](docs/agent/ai_agent_user_guide.md) — AI Agent 用户指南
- [`docs/weekly/`](docs/weekly/) — 周任务分配记录
- [`docs/archive/ncbi/`](docs/archive/ncbi/) — NCBI 流程归档文档

## 许可证

本项目仅供研究使用。
