# PlantsDB - 植物标准基因组库 / Plant Standard Genome Database

---

## 中文

PlantsDB 是一个用于构建标准化植物基因组资源的生物信息学流程。它管理物种列表、从 NCBI 批量下载基因组组装和注释数据、对数据进行处理和标准化，并支持比较基因组学分析。

### 功能特点

- **批量基因组下载** — 通过 NCBI `datasets` 命令行工具下载，支持按组装水平、数据来源、版本、日期和参考基因组状态进行过滤
- **IMP 数据库集成** — 从 IMP 网站爬取物种列表，批量下载 7 种基因组数据（基因组、注释、基因、CDS、蛋白、启动子、TPM 矩阵）
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
- [NCBI datasets 命令行工具](https://www.ncbi.nih.gov/datasets/docs/command-line-data-download/) — 用于下载基因组组装数据
- [taxonkit](https://github.com/shenwei356/taxonkit) — 用于分类学 ID 查询
- `unzip`
- 标准 Unix 工具：`awk`、`sed`、`cut`、`find`

**Python 3 依赖包：**

```bash
pip install biopython pandas openpyxl playwright requests selenium
python -m playwright install chromium
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
│   ├── genomes/                             # NCBI 基因组
│   └── IMP/                                 # IMP 数据库基因组
│       └── logs/
├── sample/                                   # 示例物种数据（已加入 .gitignore）
├── docs/                                    # 详细文档
│   ├── README.md                            # 文档索引（英文）
│   ├── README-zh.md                        # 文档索引（中文）
│   ├── scripts/                            # 脚本使用说明
│   ├── pipelines/                          # 数据流程
│   ├── guides/                             # 安装指南
│   └── SKILLS/                             # 技能手册
├── scripts/
│   ├── download_genomes.sh                   # 从 NCBI 批量下载基因组
│   ├── add_taxid.sh                          # 为物种列表添加分类学 ID
│   ├── deduplicate_species_list.sh           # 按物种名去重
│   ├── calc_species_stats.sh                 # 物种数量统计
│   ├── make_bed_chrlist.sh                   # 从 GFF 生成 BED 和 chr.list
│   ├── run_genetribe.sh                      # 运行 GeneTribe 同源基因分析
│   ├── calc_protein_properties.py            # 计算蛋白质 pI、MW、长度
│   └── batch_pi_mw.py                        # 备用蛋白质性质计算脚本
├── scripts/imp_crawler/                      # IMP 数据爬虫
│   ├── species_crawler.py                   # 物种列表爬虫
│   ├── download_manager.py                  # 下载管理器
│   └── excel_writer.py                      # Excel 报表生成
├── tmp/                                      # 临时文件
└── Z_archive/                                # 归档文件
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

#### 从 IMP 数据库下载基因组

```bash
# 爬取IMP物种列表
python scripts/imp_crawler/species_crawler.py

# 批量下载（全部物种）
./scripts/imp_download.sh

# 后台运行
nohup ./scripts/imp_download.sh > downloads/IMP/logs/download.log 2>&1 &

# 查看进度
tail -f downloads/IMP/logs/download.log
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

### 详细文档

各脚本的详细使用说明见：
- [`docs/`](docs/) - 文档索引
- [`docs/scripts/README.md`](docs/scripts/README.md) - 脚本文档
- [`docs/pipelines/`](docs/pipelines/) - 数据流程
- [`docs/guides/`](docs/guides/) - 安装指南
- [`docs/SKILLS/`](docs/SKILLS/) - 技能手册

### 许可证

本项目仅供研究使用。

---

## English

PlantsDB is a bioinformatics pipeline for building a standardized plant genome resource. See [`README.md`](README.md) for details.
