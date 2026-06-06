# eggNOG-mapper 安装配置说明

## 环境信息

| 项目 | 说明 |
|------|------|
| eggNOG-mapper 版本 | 2.1.13 |
| eggNOG 数据库版本 | 5.0.2 |
| Python 版本 | >= 3.6 |
| 安装方式 | pip install --user |

## 一、安装 eggNOG-mapper

### 1.1 pip 安装到用户本地目录

```bash
pip install --user eggnog-mapper
```

安装后可执行文件位于 `~/.local/bin/`，Python 包位于 `~/.local/lib/python3.x/site-packages/`。

> **注意：** 如果 `~/.local/bin` 不在 `PATH` 中，需手动添加：
> ```bash
> echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
> source ~/.bashrc
> ```

### 1.2 验证安装

```bash
emapper.py --version
# 输出: eggnog-mapper 2.1.13
```

### 1.3 Python 依赖

eggnog-mapper 会自动安装以下依赖：

- biopython
- psutil
- xlsxwriter

## 二、安装序列比对工具

eggNOG-mapper 支持三种比对模式，需至少安装其中一种：

### 2.1 DIAMOND（推荐，速度最快）

```bash
# conda 安装
conda install -c bioconda diamond

# 或从源码编译
wget https://github.com/bbuchfink/diamond/releases/latest/download/diamond-linux64.tar.gz
tar xzf diamond-linux64.tar.gz
cp diamond ~/.local/bin/
```

### 2.2 MMseqs2

```bash
# conda 安装
conda install -c conda-forge -c bioconda mmseqs2
```

### 2.3 HMMER

```bash
# conda 安装
conda install -c bioconda hmmer
```

## 三、下载 eggNOG 数据库

### 3.1 使用自带脚本下载

eggnog-mapper 提供了 `download_eggnog_data.py` 脚本：

```bash
# 下载完整数据库（约 50GB 磁盘空间）
download_eggnog_data.py

# 指定数据存放目录
download_eggnog_data.py -d /path/to/data_dir
```

### 3.2 手动下载

若自动下载脚本速度不理想，可手动下载所需文件：

```bash
# 创建数据目录
mkdir -p /path/to/emapperdb-5.0.2
cd /path/to/emapperdb-5.0.2

# 下载核心数据库文件（从 http://eggnogdb.embl.de/download/emapperdb-5.0.2/）
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/eggnog.db
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/eggnog.taxa.db
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/eggnog.taxa.db.traverse.pkl

# 下载 DIAMOND 数据库
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/eggnog_proteins.dmnd

# 下载 MMseqs2 数据库（如使用 mmseqs 模式）
mkdir mmseqs
cd mmseqs
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/mmseqs/mmseqs.db
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/mmseqs/mmseqs.db.dbtype
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/mmseqs/mmseqs.db_h
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/mmseqs/mmseqs.db_h.dbtype
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/mmseqs/mmseqs.db_h.index
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/mmseqs/mmseqs.db.index
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/mmseqs/mmseqs.db.lookup
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/mmseqs/mmseqs.db.source

# 下载 Pfam 数据库（用于 pfam_realign 模式）
cd /path/to/emapperdb-5.0.2
mkdir pfam
cd pfam
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/pfam/Pfam-A.clans.tsv.gz
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/pfam/Pfam-A.hmm
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/pfam/Pfam-A.hmm.h3f
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/pfam/Pfam-A.hmm.h3i
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/pfam/Pfam-A.hmm.h3m
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/pfam/Pfam-A.hmm.h3m.ssi
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/pfam/Pfam-A.hmm.h3p
wget http://eggnogdb.embl.de/download/emapperdb-5.0.2/pfam/Pfam-A.hmm.idmap
```

### 3.3 数据库文件说明与磁盘需求

| 文件/目录 | 说明 | 大小（约） |
|-----------|------|------------|
| `eggnog.db` | 核心注释数据库 | 39 GB |
| `eggnog.taxa.db` | 分类信息数据库 | 266 MB |
| `eggnog.taxa.db.traverse.pkl` | 分类遍历索引 | 6.4 MB |
| `eggnog_proteins.dmnd` | DIAMOND 比对数据库 | 8.7 GB |
| `mmseqs/` | MMseqs2 比对数据库 | 11 GB |
| `pfam/` | Pfam 结构域数据库 | 2.8 GB |
| **合计** | | **~62 GB** |

> **提示：** 最小安装只需 `eggnog.db` + `eggnog.taxa.db` + `eggnog.taxa.db.traverse.pkl` + 一种比对数据库（diamond 或 mmseqs），约 48-50 GB。

## 四、配置数据目录

### 4.1 指定数据目录

运行时通过 `--data_dir` 参数指定数据库路径：

```bash
emapper.py -i input.fasta -o output --data_dir /path/to/emapperdb-5.0.2
```

### 4.2 设置默认数据目录（可选）

可通过环境变量避免每次都指定 `--data_dir`：

```bash
# 在 ~/.bashrc 中添加
export EGGNOG_DATA_DIR=/path/to/emapperdb-5.0.2

source ~/.bashrc
```

设置后可直接运行：

```bash
emapper.py -i input.fasta -o output
```

## 五、使用示例

### 5.1 DIAMOND 模式（蛋白质序列，默认）

```bash
emapper.py -i proteins.fasta -o result \
    --data_dir /path/to/emapperdb-5.0.2 \
    -m diamond \
    --cpu 8
```

### 5.2 DIAMOND 模式（核酸序列，自动翻译）

```bash
emapper.py -i cds.fasta -o result \
    --data_dir /path/to/emapperdb-5.0.2 \
    -m diamond \
    --itype CDS \
    --cpu 8
```

### 5.3 MMseqs2 模式

```bash
emapper.py -i proteins.fasta -o result \
    --data_dir /path/to/emapperdb-5.0.2 \
    -m mmseqs \
    --cpu 8
```

### 5.4 HMMER 模式

```bash
emapper.py -i proteins.fasta -o result \
    --data_dir /path/to/emapperdb-5.0.2 \
    -m hmmer \
    --cpu 8
```

## 六、常用参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i` | 输入 FASTA 文件 | 必需 |
| `-o` | 输出文件前缀 | 必需 |
| `-m` | 比对模式：diamond/mmseqs/hmmer | diamond |
| `--itype` | 输入类型：CDS/proteins/genome/metagenome | proteins |
| `--data_dir` | 数据库目录 | 自动检测 |
| `--cpu` | CPU 线程数 | 2 |
| `--evalue` | E-value 阈值 | 0.001 |
| `--score` | 最低比分阈值 | 20 |
| `--pident` | 最低序列一致性百分比 | 0 |
| `--query_cover` | 最低 query 覆盖度百分比 | 0 |
| `--subject_cover` | 最低 subject 覆盖度百分比 | 0 |
| `--go_evidence` | GO 注释证据等级：experimental/non-electronic/all | non-electronic |
| `--pfam_realign` | Pfam 重比对：none/realign/denovo | none |
| `--annotate_hits_table` | 跳过搜索步骤，仅注释已有比对结果 | - |
| `--resume` | 从中断处继续运行 | - |
| `--override` | 覆盖已有输出 | - |

## 七、输出文件说明

| 文件 | 说明 |
|------|------|
| `*.emapper.annotations` | 主要注释结果（TSV 格式） |
| `*.emapper.hits` | 比对命中结果 |
| `*.emapper.seed_orthologs` | 种子直系同源结果 |
| `*.emapper.gene_hits` | 基因预测结果（genome/metagenome 模式） |

## 八、常见问题

### 8.1 命令找不到

```
bash: emapper.py: command not found
```

确保 `~/.local/bin` 在 `PATH` 中：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 8.2 数据库路径错误

```
ERROR: eggnog database not found at /path/to/emapperdb-5.0.2
```

检查 `--data_dir` 路径是否正确，确保目录下存在 `eggnog.db` 等必要文件。

### 8.3 DIAMOLD 未安装

```
ERROR: diamond not found in PATH
```

安装 DIAMOND 并确保其在 `PATH` 中，或改用 `-m mmseqs` / `-m hmmer` 模式。

### 8.4 内存不足

核心数据库 `eggnog.db` 约 39 GB，运行时需要较大内存。可通过以下方式降低内存使用：

- 使用 `--dbmem` 参数将数据库加载到内存（需要足够 RAM）
- 减少 `--cpu` 线程数
- 分批处理输入文件

### 8.5 pip 安装权限问题

若系统 Python 无写权限，使用 `--user` 参数安装到用户目录：

```bash
pip install --user eggnog-mapper
```

或使用虚拟环境：

```bash
python3 -m venv ~/eggnog-env
source ~/eggnog-env/bin/activate
pip install eggnog-mapper
```
