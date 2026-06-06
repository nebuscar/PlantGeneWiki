# run_genetribe.sh 使用说明

## 概述

植物基因组同源基因鉴定流水线脚本。从 NCBI 下载的基因组数据出发，完成蛋白 ID 统一、GFF 转 BED、染色体列表生成，并运行 [GeneTribe](https://github.com/YulongSong/GeneTribe) + [jcvi](https://github.com/tanghaibao/jcvi) 进行同源基因鉴定和共线性分析。支持按属分组批处理、多格式输出。

---

## 依赖

| 工具 | 用途 | 安装方式 |
|------|------|----------|
| seqkit | 蛋白序列统计 | `conda install seqkit` |
| gff2bed | GFF 转 BED 格式 | `conda install bedops` |
| genetribe | 同源基因鉴定 | 参见 [GeneTribe](https://github.com/YulongSong/GeneTribe) |
| jcvi | 共线性分析 | `conda install -c bioconda jcvi`（需安装在 `genetribe` conda 环境中） |
| BLAST+ | 蛋白序列比对 | 随 genetribe 环境安装 |
| conda | 环境管理 | 需有名为 `genetribe` 的 conda 环境 |
| python3 + openpyxl | xlsx 输出 | 可选，缺失时回退到 csv |

---

## 输入数据

### 目录结构要求

```
input_dir/
├── Species_A/
│   ├── *.faa          # 蛋白序列（NCBI 格式）
│   ├── *.gff          # 基因注释（NCBI 格式）
│   └── *cds*.fna      # CDS 序列（可选，用于 jcvi 共线性分析）
├── Species_B/
│   ├── *.faa
│   ├── *.gff
│   └── *cds*.fna
└── ...
```

每个物种子目录需包含 `.faa` 和 `.gff` 文件。`.cds.fna` 文件可选，用于 jcvi 共线性分析。物种目录名遵循 `Genus_species` 格式（如 `Acer_saccharum`）。

---

## 命令行参数

```
Usage: ./run_genetribe.sh [OPTIONS]

Options:
  -i, --input DIR      输入目录（包含物种子文件夹）
  -o, --output DIR     输出目录
  -g, --genus          按属分组运行同源分析（自动批处理各属）
  -m, --mode MODE      运行模式（逗号分隔组合）
  -f, --format FMT     RBH合并表输出格式 [默认: xlsx]
  -h, --help           显示帮助
```

### 运行模式

| 模式 | 说明 |
|------|------|
| `all` | 全部运行（默认） |
| `stat` | 序列统计 + 选择参考物种 |
| `faa` | 统一蛋白 ID（protein_id → locus_tag） |
| `bed` | GFF 转 BED（标准 6 列格式） |
| `chr` | 从 BED 生成 chrlist |
| `genetribe` | 运行同源分析（含 jcvi 共线性） |
| `merge` | 合并 RBH 映射表 |

### 输出格式

| 格式 | 说明 |
|------|------|
| `xlsx` | 默认，需 python3 + openpyxl，缺失时回退到 csv |
| `csv` | 逗号分隔 |
| `tsv` | Tab 分隔 |
| `txt` | Tab 分隔（.txt 后缀） |

支持逗号分隔多格式组合，如 `-f xlsx,csv`。

---

## 使用示例

```bash
# 无参数运行显示帮助
./scripts/run_genetribe.sh

# 完整流水线（非属模式，所有物种互比）
./scripts/run_genetribe.sh -i /DATA/data2/downloads/NCBI

# 按属分组批处理（推荐）
./scripts/run_genetribe.sh -i /DATA/data2/downloads/NCBI -m all -g

# 仅运行预处理步骤
./scripts/run_genetribe.sh -i ./sample -m stat,faa,bed,chr -g

# 仅运行同源分析 + 合并
./scripts/run_genetribe.sh -i ./sample -m genetribe,merge -g

# 指定输出格式
./scripts/run_genetribe.sh -m merge -g -f csv
./scripts/run_genetribe.sh -m merge -g -f xlsx,tsv

# 查看单个参数帮助
./scripts/run_genetribe.sh -m -h
```

---

## 流水线步骤

### 1. stat — 序列统计与参考物种选择

- 使用 `seqkit stats` 统计各物种蛋白序列数量
- 选择蛋白序列数最多的物种作为参考物种
- `-g` 模式下：按属独立统计，每个属选自己的参考物种

### 2. faa — 统一蛋白 ID

- 从 GFF 中提取 protein_id → locus_tag 映射
- 替换 FAA 和 CDS 文件中的序列标题，将 protein_id 替换为 locus_tag
- 解决 NCBI 数据中 protein_id 与 locus_tag 不一致的问题

### 3. bed — GFF 转 BED

- 使用 `gff2bed` 将 GFF 转为标准 6 列 BED 格式
- 自动去除 `gene-` 前缀，确保 BED 基因 ID 与 FAA 一致
- 过滤坐标异常行（end < start）
- gff2bed 失败时自动回退到 awk 直接转换

### 4. chr — 生成 chrlist

- 从 BED 文件提取染色体/contig 名称列表

### 5. genetribe — 同源基因鉴定

- 自动激活 `genetribe` conda 环境
- `-g` 模式下：仅同属物种互相比对
- 为每个待比对物种与参考物种运行 GeneTribe core
- GeneTribe 内部调用 jcvi 进行共线性分析
- 结果自动整理到 `genetribe_result/` 子目录

### 6. merge — 合并 RBH 映射表

- 收集所有 RBH 文件，以参考物种基因 ID 为第一列合并
- 第一列列名为参考物种名（非 "Reference"）
- 默认输出 xlsx，tsv 仅作临时文件用完即删
- 输出文件名格式：`{Genus}_RBH_merged.{format}`

---

## 输出文件

### 目录结构（-g 模式）

```
result/homolog/
├── seqkit_faa_stats.txt                  # 全局蛋白序列统计
├── Acer/
│   ├── reference_species.txt             # 该属参考物种信息
│   ├── seqkit_faa_stats.txt              # 该属序列统计
│   ├── {Species}.faa / .cds / .bed / .chrlist / .fa  # 处理后的输入文件
│   ├── id_mapping/{Species}.map.txt      # protein_id → locus_tag 映射
│   ├── genetribe_result/
│   │   └── {Ref}_vs_{Query}/
│   │       ├── {Ref}_{Query}.RBH
│   │       ├── {Ref}_{Query}.SBH
│   │       ├── {Ref}_{Query}.one2one
│   │       ├── {Ref}_{Query}.one2many
│   │       ├── {Ref}_{Query}.singleton
│   │       ├── {Ref}_{Query}.block_pos
│   │       └── {Ref}_{Query}.collinearity_info
│   └── Acer_RBH_merged.xlsx              # 属内 RBH 合并表
├── Dendrobium/
│   ├── ...
│   └── Dendrobium_RBH_merged.xlsx
└── ...
```

### RBH 合并表格式

以参考物种基因 ID 为第一列，各比对物种基因 ID 为后续列：

| Acer_saccharum | Acer_negundo |
|----------------|--------------|
| LWI29_000001 | LWI28_008214 |
| LWI29_000002 | LWI28_005291 |

多物种时：

| Acer_saccharum | Acer_negundo | Acer_rubrum |
|----------------|--------------|-------------|
| LWI29_000001 | LWI28_008214 | - |
| LWI29_000002 | LWI28_005291 | LRQ78_000001 |

无同源基因时显示 `-`。

### 同源结果文件格式

所有同源结果为 tab 分隔，4 列：

```
基因A_ID    基因B_ID    同源类型    染色体名
LWI29_000001    LWI28_008214    RBH    CM046700.1
```

| 同源类型 | 说明 |
|----------|------|
| RBH | Reciprocal Best Hit，互为最佳匹配 |
| SBH | Single-side Best Hit，单向最佳匹配 |

---

## 属分组模式 (-g)

### 工作流程

1. 扫描输入目录，按属名（从 `Genus_species` 提取）分组
2. 每个属独立统计，选择该属蛋白序列最多的物种为参考
3. 跳过只有 0 或 1 个物种有 .faa 的属
4. 每个属的结果输出到独立的属名子目录
5. 各属串行处理

---

## 计时信息

脚本自动记录：
- 每个属的处理耗时
- 总耗时（时/分/秒格式）

输出示例：
```
  属 Acer 完成，耗时: 1811s
  属 Dendrobium 完成，耗时: 861s

========================================
✅ 运行完成，总耗时: 0h 44m 33s
========================================
```

---

## 注意事项

1. **conda 环境**：脚本要求存在名为 `genetribe` 的 conda 环境，且 jcvi 安装在该环境中
2. **PATH 优先级**：脚本自动将 conda 环境的 bin 目录置于 PATH 最前，避免 `~/.local/bin/python` 覆盖
3. **参考物种**：自动选择蛋白序列数最多的物种，如需指定可通过调整 `reference_species.txt` 实现
4. **CDS 文件**：jcvi 共线性分析需要 CDS 文件，如无则仅运行蛋白水平的同源鉴定
5. **NCBI 数据**：`faa` 模式专门处理 NCBI 格式的 protein_id/locus_tag 不一致问题，非 NCBI 数据可跳过此步
6. **xlsx 依赖**：输出 xlsx 需要 python3 和 openpyxl，缺失时自动回退到 csv
7. **属名提取**：物种目录名必须为 `Genus_species` 格式，属名取第一个 `_` 前的部分
