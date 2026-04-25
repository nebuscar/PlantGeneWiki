# IMP 数据爬取与下载

## 概述

从 [IMP (Integrated Model Plant database)](https://www.bic.ac.cn/IMP/#/Download) 批量下载植物物种基因组数据。分为两个阶段：

1. **物种列表爬取** - 从IMP页面自动获取全部物种（短码 + 物种全称）
2. **数据批量下载** - 按物种分目录下载7种基因组文件

---

## 依赖

- Python 3.6+
- `playwright` - 用于浏览器自动化爬取
- `wget` - 文件下载
- `openpyxl` - 生成Excel报表

### 安装依赖

```bash
pip install playwright openpyxl requests selenium
python -m playwright install chromium
```

---

## 目录结构

```
downloads/IMP/
├── logs/                      # 下载日志
├── species_list.json          # 物种列表（JSON格式）
├── species_manifest.tsv       # 物种清单（TSV格式）
├── IMP_data_inventory.xlsx    # 数据清单报表
├── Anisodus_acutangulus/     # 按物种全称分目录
│   ├── Anisodus acutangulus_genome.fa.gz
│   ├── Anisodus acutangulus_annotation.gff3.gz
│   ├── Anisodus acutangulus_gene.fasta
│   ├── Anisodus acutangulus_cds.fasta
│   ├── Anisodus acutangulus_protein.fasta
│   ├── Anisodus acutangulus_promoter.fasta
│   └── Anisodus acutangulus_expression_TPM.txt
└── Arabis_alpina/
    └── ...
```

---

## 脚本说明

### 1. species_crawler.py - 物种列表爬虫

从IMP页面爬取物种列表（短码 + 物种全称）。

**使用方法：**

```bash
# 全量爬取（54页，约1068个物种）
python3 scripts/imp_crawler/species_crawler.py

# 查看帮助
python3 scripts/imp_crawler/species_crawler.py --help
```

**输出文件：**

- `downloads/IMP/species_list.json` - 物种列表（JSON）
- `downloads/IMP/species_manifest.tsv` - 物种清单（TSV）

**数据结构：**

```json
{
  "count": 1068,
  "species": [
    {
      "code": "Aac1",
      "name": "Anisodus acutangulus",
      "dir": "Anisodus_acutangulus"
    },
    ...
  ]
}
```

```
Species_Code    Species_Name           Directory_Name
Aac1            Anisodus acutangulus  Anisodus_acutangulus
Aaf1            Agapanthus africanus   Agapanthus_africanus
```

---

### 2. download_manager.py - 下载管理器

批量下载IMP基因组数据，支持增量更新。

**使用方法：**

```bash
# 使用species_list.json下载全部物种
python3 scripts/imp_crawler/download_manager.py

# 指定物种清单文件
python3 scripts/imp_crawler/download_manager.py --manifest downloads/IMP/species_manifest.tsv

# 下载单个物种测试
python3 scripts/imp_crawler/download_manager.py --species Aac1

# 限制数量（用于测试）
python3 scripts/imp_crawler/download_manager.py --limit 10

# Dry-run预览（不实际下载）
python3 scripts/imp_crawler/download_manager.py --dry-run

# 强制重新下载（跳过增量检测）
python3 scripts/imp_crawler/download_manager.py --no-skip
```

**下载链接格式：**

| 文件类型 | URL模式 |
|---------|---------|
| Genome | `https://www.bic.ac.cn/data2t/html/IMP/public/data/igv/{code}/{code}.fa.gz` |
| Annotation | `https://www.bic.ac.cn/data2t/html/IMP/public/data/igv/{code}/{code}.gff3.gz` |
| Gene | `https://www.bic.ac.cn/data2t/html/IMP/public/data/blast/{code}.gene.fasta` |
| CDS | `https://www.bic.ac.cn/data2t/html/IMP/public/data/blast/{code}.CDS.fasta` |
| Protein | `https://www.bic.ac.cn/data2t/html/IMP/public/data/blast/{code}.prot.fasta` |
| Promoter | `https://www.bic.ac.cn/data2t/html/IMP/public/data/blast/{code}.promoter2k.fasta` |
| TPM Matrix | `https://www.bic.ac.cn/data2t/html/IMP/public/data/expr_matrix/{code}.all.rnaseq.TPM.txt` |

**文件重命名：**

下载后自动重命名为物种全称格式：

| 原始文件名 | 重命名后 |
|-----------|---------|
| `{code}.fa.gz` | `{Species}_genome.fa.gz` |
| `{code}.gff3.gz` | `{Species}_annotation.gff3.gz` |
| `{code}.gene.fasta` | `{Species}_gene.fasta` |
| `{code}.CDS.fasta` | `{Species}_cds.fasta` |
| `{code}.prot.fasta` | `{Species}_protein.fasta` |
| `{code}.promoter2k.fasta` | `{Species}_promoter.fasta` |
| `{code}.all.rnaseq.TPM.txt` | `{Species}_expression_TPM.txt` |

**日志文件：**

- `downloads/IMP/logs/imp_download.log` - 总日志
- `downloads/IMP/logs/imp_success.log` - 成功列表
- `downloads/IMP/logs/imp_fail.log` - 失败列表
- `downloads/IMP/logs/imp_skip.log` - 跳过列表

---

### 3. imp_download.sh - 主入口脚本

串联各模块，一键执行。

**使用方法：**

```bash
# 全量下载（使用species_list.json）
./scripts/imp_download.sh

# 预览模式（不实际下载）
./scripts/imp_download.sh --dry-run

# 下载指定物种
./scripts/imp_download.sh --species Aac1

# 限制数量
./scripts/imp_download.sh --limit 10

# 仅获取物种列表
./scripts/imp_download.sh --list

# 后台运行
nohup ./scripts/imp_download.sh > downloads/IMP/logs/download_full.log 2>&1 &

# 查看进度
tail -f downloads/IMP/logs/download_full.log
```

---

### 4. excel_writer.py - 数据报表生成

扫描下载目录，生成Excel数据清单。

**使用方法：**

```bash
python3 scripts/imp_crawler/excel_writer.py \
    --indir downloads/IMP \
    --out downloads/IMP/IMP_data_inventory.xlsx
```

**输出格式（IMP_data_inventory.xlsx）：**

| Species | Genome_Sequence | Genome_Annotation | Gene_Sequence | CDS_Sequence | Protein_Sequence | Promoter_Sequence | Gene_Expression_TPM | Source |
|---------|-----------------|-------------------|---------------|--------------|-------------------|-------------------|---------------------|--------|
| Anisodus acutangulus | 1 | 1 | 1 | 1 | 1 | 1 | 1 | IMP |
| Agapanthus africanus | 1 | 1 | 1 | 1 | 1 | 1 | 0 | IMP |

- 有文件 = 1，无文件 = 0
- Source 列固定为 "IMP"

---

## 完整工作流程

### 步骤1：爬取物种列表

```bash
python3 scripts/imp_crawler/species_crawler.py
```

### 步骤2：批量下载

```bash
# 前台运行（测试）
./scripts/imp_download.sh --limit 3

# 后台运行（全量）
nohup ./scripts/imp_download.sh > downloads/IMP/logs/download_full.log 2>&1 &
```

### 步骤3：查看报表

下载完成后，查看 `downloads/IMP/IMP_data_inventory.xlsx`

---

## 常见问题

### 1. 下载超时

网络不稳定时会出现部分文件超时，脚本会自动重试。可以在 `download_manager.py` 中调整超时时间：

```python
# wget超时时间（秒）
wget --timeout=60
```

### 2. 部分文件下载失败

由于IMP服务器限制，某些物种的部分文件可能不存在。日志会记录失败的文件，后续可单独重试。

### 3. 空文件问题

下载失败产生的空文件会被自动清理，不会影响后续的增量检测。

### 4. 增量更新

脚本默认跳过已存在且完整的物种目录，重新运行会跳过已下载完成的物种。如需强制重下，使用 `--no-skip` 参数。

---

## 文件结构

```
scripts/imp_crawler/
├── __init__.py              # 包初始化
├── api_discover.py          # API发现脚本（调试用）
├── species_crawler.py       # 物种列表爬虫
├── download_manager.py      # 下载管理器
└── excel_writer.py         # Excel报表生成

scripts/imp_download.sh      # 主入口脚本
```

---

## 参考

- IMP官网：https://www.bic.ac.cn/IMP/#/Download
- Playwright文档：https://playwright.dev/python/
