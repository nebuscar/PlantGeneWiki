# download_genomes.sh 使用说明

## 概述

从 NCBI 批量下载植物基因组数据。基于物种列表（含 TaxID），调用 `datasets`（NCBI Datasets CLI）按目/科/属分批下载，自动解压、整理文件并生成下载日志。

---

## 依赖

- [NCBI Datasets CLI](https://www.ncbi.nlm.nih.gov/datasets/docs/command-line/)（`datasets` 命令）
- `unzip`
- `ssconvert`（可选，仅 xlsx 日志需要）

---

## 输入数据

### 物种列表文件

硬编码路径：`data/meta/ncbi/species_list_with_taxid.txt`，Tab 分隔，关键列：

| 列号 | 列名     | 说明                       |
|------|---------|----------------------------|
| 2    | Species | 物种拉丁名                  |
| 3    | TaxID   | NCBI Taxonomy ID            |
| 6    | Order   | 目                          |
| 7    | Family  | 科                          |
| 8    | Genus   | 属                          |

### 目录结构要求

无需预先创建目录，脚本自动创建下载目录和日志目录。

---

## 输出数据

### 每个物种的下载目录

`{out_dir}/{Species_Name}/` 下生成标准化命名文件：

| 文件名                           | 来源 NCBI 文件                | 说明              |
|----------------------------------|-------------------------------|-------------------|
| `{Species}_genome.fna`           | `GCA/GCF*_genomic.fna`       | 基因组序列         |
| `{Species}_cds.fna`              | `cds_from_genomic.fna`        | CDS 序列          |
| `{Species}_protein.faa`          | `protein.faa`                 | 蛋白序列           |
| `{Species}_annotation.gff`       | `genomic.gff`                 | GFF 注释           |
| `{Species}_annotation.gbff`      | `genomic.gbff`                | GenBank 注释       |
| `README_SOURCES.txt`             | 自动生成                      | 数据来源说明       |

### 日志文件

保存在 `downloads/logs/` 目录：

| 文件          | 内容                                   |
|---------------|----------------------------------------|
| `total.log`   | 全部记录（成功 + 失败 + 跳过）           |
| `success.log` | 下载成功的物种                          |
| `fail.log`    | 下载失败的物种                          |
| `skip.log`    | 跳过的物种（无 TaxID 或已存在）          |

---

## 使用方法

### 模式

| 模式      | 说明                                   |
|-----------|----------------------------------------|
| `genus`   | 按属分批下载（默认）                     |
| `family`  | 按科分批下载                             |
| `order`   | 按目分批下载                             |
| `all`     | 下载全部物种                             |

### 参数

| 参数                        | 说明                                                       |
|-----------------------------|-----------------------------------------------------------|
| `[模式]`                    | order / family / genus / all（默认 genus）                  |
| `-h, --help`                | 显示帮助信息                                                |
| `-l, --list`                | 列出当前模式下可用的批次                                     |
| `-t, --test "物种名"`       | 测试模式，只下载单个物种                                     |
| `-o, --outdir DIR`          | 指定下载保存目录（默认 `/DATA/data2/downloads/genomes`）      |
| `--include <types>`         | 下载的数据类型（默认 `genome,protein,cds,gff3,gbff`）        |
| `--assembly-level <lvls>`   | 限制组装级别（chromosome,complete,contig,scaffold）          |
| `--assembly-source <src>`   | 限制来源：RefSeq / GenBank / all                           |
| `--assembly-version <v>`    | 限制版本：latest / all                                     |
| `--annotated`               | 限制为有注释的基因组                                        |
| `--reference`               | 限制为参考基因组                                            |
| `--exclude-atypical`        | 排除非典型组装（默认开启）                                   |
| `--exclude-multi-isolate`   | 排除多分离株组装（默认开启）                                 |
| `--mag <val>`               | MAG 限制：only / exclude / all                             |
| `--released-after <date>`   | 限制发布日期下界（YYYY-MM-DD）                              |
| `--released-before <date>`  | 限制发布日期上界（YYYY-MM-DD）                              |

### 筛选参数

位置参数可传入属名/科名/目名，或包含名称列表的文件（每行一个），脚本自动判断是文件还是名称。

### 示例

```bash
# 查看可用的科列表
./download_genomes.sh -l family

# 下载 Brassicales 目
./download_genomes.sh order Brassicales

# 下载 Fabaceae 科
./download_genomes.sh family Fabaceae

# 下载 Oryza 和 Acer 两个属
./download_genomes.sh genus Oryza Acer

# 从文件读取属名列表
./download_genomes.sh genus genus_list.txt

# 测试单个物种
./download_genomes.sh -t "Arabidopsis thaliana"

# 只下载有注释的染色体级别基因组
./download_genomes.sh all --annotated --assembly-level chromosome

# 下载全部物种到指定目录
./download_genomes.sh all -o /path/to/output
```

---

## 方法细节

### 下载流程

1. **跳过检查**：无 TaxID 的物种直接跳过；若目标目录已存在 `{Species}_genome.fna` 则视为已下载。
2. **调用 NCBI Datasets**：`datasets download genome taxon <TaxID>` 按指定参数下载 zip 包。
3. **完整性验证**：检查 zip 文件是否存在且非空，`unzip -t` 验证 zip 完整性。
4. **解压整理**：解压后遍历 `ncbi_dataset/data/GCF_*` 和 `GCA_*` 子目录，按完整性评分选择最优版本（RefSeq GCF 优先于 GenBank GCA），复制文件到物种根目录。
5. **重命名**：将 NCBI 原始文件名统一为 `{Species}_{type}.ext` 格式。
6. **清理**：删除 `ncbi_dataset/` 目录、zip 包及原始命名残留文件。
7. **生成来源说明**：写入 `README_SOURCES.txt`，包含物种名、TaxID、Accession、数据来源（RefSeq/GenBank）、下载时间。
8. **文件完整性检查**：检查是否同时存在 genome、cds、protein 和 gff/gbff 文件，标记为"完整"或"不完整"。

### 组装版本选择评分

对每个 accession 目录内文件类型计分：

| 文件类型   | 分值 |
|-----------|------|
| `.fna`    | 1    |
| `.cds.fna`| 1    |
| `.faa`    | 1    |
| `.gff`    | 2    |
| `.gbff`   | 1    |

分数高者优先；分数相同时 GCF（RefSeq）优先于 GCA（GenBank）。
