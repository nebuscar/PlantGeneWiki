# IMP 数据爬取与下载

## 概述

从 [IMP (Integrated Model Plant database)](https://www.bic.ac.cn/IMP/#/Download) 批量下载植物物种基因组数据。分为两个阶段：

1. **物种列表爬取** — 从 IMP 页面自动获取全部物种（代码 + 全称）
2. **数据批量下载** — 按物种分目录下载 7 种基因组文件，本地文件名统一使用物种全称

---

## 依赖

- Python 3.6+
- `playwright` — 浏览器自动化爬取
- `requests` — 文件下载

```bash
pip install playwright requests
python -m playwright install chromium
```

---

## 目录结构

```
downloads/IMP/
├── logs/                          # 下载日志
├── species_list.json              # 物种列表（JSON）
├── species_manifest.tsv           # 物种清单（TSV）
├── species_availability.tsv       # 物种可用性标记（下载后生成）
└── Arabidopsis_thaliana/
    ├── Arabidopsis_thaliana.fa.gz
    ├── Arabidopsis_thaliana.gff3.gz
    ├── Arabidopsis_thaliana.gene.fasta
    ├── Arabidopsis_thaliana.CDS.fasta
    ├── Arabidopsis_thaliana.prot.fasta
    ├── Arabidopsis_thaliana.promoter2k.fasta
    └── Arabidopsis_thaliana.all.rnaseq.TPM.txt
```

---

## 下载 URL 与本地文件名映射

URL 使用物种**代码**（如 `Ath1`），本地保存使用**物种全名**（如 `Arabidopsis_thaliana`）：

| 文件类型 | URL（使用代码） | 本地文件名（使用全名） |
|---------|--------------|-------------------|
| Genome | `igv/{code}/{code}.fa.gz` | `{dir}.fa.gz` |
| Annotation | `igv/{code}/{code}.gff3.gz` | `{dir}.gff3.gz` |
| Gene | `blast/{code}.gene.fasta` | `{dir}.gene.fasta` |
| CDS | `blast/{code}.CDS.fasta` | `{dir}.CDS.fasta` |
| Protein | `blast/{code}.prot.fasta` | `{dir}.prot.fasta` |
| Promoter | `blast/{code}.promoter2k.fasta` | `{dir}.promoter2k.fasta` |
| TPM | `expr_matrix/{code}.all.rnaseq.TPM.txt` | `{dir}.all.rnaseq.TPM.txt` |

Base URL: `https://www.bic.ac.cn/data2t/html/IMP/public/data/`

---

## 脚本说明

### scripts/imp/imp_crawler/species_crawler.py

从 IMP 页面爬取物种列表。自动翻页，检测末页；对 name == code 的条目打印警告（全称未提取）。

```bash
python3 scripts/imp/imp_crawler/species_crawler.py
```

输出：`downloads/IMP/species_manifest.tsv`、`downloads/IMP/species_list.json`

---

### scripts/imp/imp_crawler/download_manager.py

批量下载，支持增量更新和并发。

```bash
# 全量下载
python3 -u scripts/imp/imp_crawler/download_manager.py \
    --manifest downloads/IMP/species_manifest.tsv \
    --outdir /DATA/data2/downloads/IMP \
    --threads 4

# 按首字母分批
python3 -u scripts/imp/imp_crawler/download_manager.py \
    --manifest downloads/IMP/species_manifest.tsv \
    --outdir /DATA/data2/downloads/IMP \
    --prefix B --threads 4

# 单物种测试（传入代码）
python3 -u scripts/imp/imp_crawler/download_manager.py \
    --species Ath1

# 预览 URL（不下载）
python3 -u scripts/imp/imp_crawler/download_manager.py \
    --dry-run --limit 5
```

**参数：**

| 参数 | 说明 |
|------|------|
| `--manifest` | 物种清单 TSV/JSON |
| `--outdir` | 下载输出目录 |
| `--prefix` | 只处理 dir_name 以该前缀开头的物种（分批下载用） |
| `--threads` | 并行线程数（默认 4） |
| `--no-skip` | 强制重下已存在文件 |
| `--dry-run` | 仅打印 URL，不下载 |
| `--limit` | 限制处理数量 |

**完成后生成 `downloads/IMP/species_availability.tsv`：**

```
Directory_Name          Species_Code    Status
Arabidopsis_thaliana    Ath1            available
Agapanthus_africanus    Aaf1            unavailable
Acorus_americanus       Aame1           partial
```

- `available` — 全部文件下载成功
- `partial` — 部分文件 404（通常是 tpm）
- `unavailable` — 全部 404，IMP 无该物种数据

增量运行时会合并已有记录，不覆盖。

---

### scripts/imp/imp_download.sh

主入口，封装 download_manager.py。

```bash
# 全量下载（后台）
nohup bash scripts/imp/imp_download.sh -t 4 \
    > logs/imp_download.log 2>&1 &

# 按字母分批
bash scripts/imp/imp_download.sh -p A
bash scripts/imp/imp_download.sh -p B

# 仅爬取物种列表
bash scripts/imp/imp_download.sh --list

# 预览
bash scripts/imp/imp_download.sh -d --limit 5
```

**参数：**

| 参数 | 说明 |
|------|------|
| `-o, --outdir` | 下载目录（默认 `/DATA/data2/downloads/IMP`） |
| `-m, --manifest` | 指定清单文件 |
| `-s, --species` | 单个物种代码 |
| `-p, --prefix` | 按 dir_name 前缀过滤 |
| `-t, --threads` | 并行线程数（默认 4） |
| `-l, --limit` | 限制处理数量 |
| `-d, --dry-run` | 预览模式 |
| `--no-skip` | 强制重下 |
| `--list` | 仅爬取物种列表 |

---

## 日志文件

| 文件 | 内容 |
|------|------|
| `logs/imp_download.log` | 详细下载记录 |
| `logs/imp_fail.log` | 下载异常记录 |
| `downloads/IMP/logs/imp_download.log` | 服务端下载日志 |
| `downloads/IMP/species_availability.tsv` | 物种可用性标记 |

---

## 分批下载策略

manifest 共约 1068 个物种，建议按首字母分批：

```bash
for prefix in A B C D E F G H I J K L M N O P Q R S T U V W X Y Z; do
    bash scripts/imp/imp_download.sh -p "$prefix" -t 4
done
```

---

## 文件结构

```
scripts/imp/
├── imp_download.sh              # 主入口
└── imp_crawler/
    ├── __init__.py
    ├── api_discover.py          # API 发现（调试用）
    ├── species_crawler.py       # 物种列表爬虫
    └── download_manager.py      # 下载管理器
```
