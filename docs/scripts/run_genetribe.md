# run_genetribe.sh 使用说明

## 概述

植物基因组同源基因鉴定流水线脚本。从 NCBI 下载的基因组数据出发，完成蛋白 ID 统一、GFF 转 BED、染色体列表生成，并运行 [GeneTribe](https://github.com/YulongSong/GeneTribe) + [jcvi](https://github.com/tanghaibao/jcvi) 进行同源基因鉴定和共线性分析。

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

每个物种子目录需包含 `.faa` 和 `.gff` 文件。`.cds.fna` 文件可选，用于 jcvi 共线性分析。

---

## 命令行参数

```
Usage: ./run_genetribe.sh [OPTIONS]

Options:
  -i, --input DIR      输入目录（包含物种子文件夹）
  -o, --output DIR     输出目录
  -q, --query SPEC     待比对物种（逗号分隔，不指定则自动选所有非参考物种）
  -m, --mode MODE      运行模式（逗号分隔组合）
  -t, --threads N      BLAST 线程数 [默认: 36]
  -p, --cpus N         jcvi CPU 数，0=不限制 [默认: 0]
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

---

## 使用示例

```bash
# 完整流水线（全部模式）
./scripts/run_genetribe.sh -i /DATA/data2/downloads/genomes

# 仅运行预处理步骤
./scripts/run_genetribe.sh -i ./sample -m stat,faa,bed,chr

# 仅运行同源分析（需先完成预处理）
./scripts/run_genetribe.sh -i ./sample -m genetribe

# 指定待比对物种
./scripts/run_genetribe.sh -m genetribe -q Acer_saccharum

# 指定多个待比对物种
./scripts/run_genetribe.sh -m genetribe -q "Acer_saccharum,Acer_rubrum"

# 自定义线程数
./scripts/run_genetribe.sh -m genetribe -t 16 -p 4

# 查看单个参数帮助
./scripts/run_genetribe.sh -m -h
```

---

## 流水线步骤

### 1. stat — 序列统计与参考物种选择

- 使用 `seqkit stats` 统计各物种蛋白序列数量
- 选择蛋白序列数最多的物种作为参考物种
- 输出：`seqkit_faa_stats.txt`、`reference_species.txt`

### 2. faa — 统一蛋白 ID

- 从 GFF 中提取 protein_id → locus_tag 映射
- 替换 FAA 和 CDS 文件中的序列标题，将 protein_id 替换为 locus_tag
- 解决 NCBI 数据中 protein_id 与 locus_tag 不一致的问题
- 输出：`{Species}.faa`、`{Species}.cds`、`id_mapping/{Species}.map.txt`

### 3. bed — GFF 转 BED

- 使用 `gff2bed` 将 GFF 转为标准 6 列 BED 格式
- 自动去除 `gene-` 前缀，确保 BED 基因 ID 与 FAA 一致
- 过滤坐标异常行（end < start）
- gff2bed 失败时自动回退到 awk 直接转换
- 输出：`{Species}.bed`

### 4. chr — 生成 chrlist

- 从 BED 文件提取染色体/contig 名称列表
- 输出：`{Species}.chrlist`

### 5. genetribe — 同源基因鉴定

- 自动激活 `genetribe` conda 环境
- 为每个待比对物种与参考物种运行 GeneTribe core
- GeneTribe 内部调用 jcvi 进行共线性分析
- 结果自动整理到 `genetribe_result/` 子目录
- 输出：见下方"输出文件"

---

## 输出文件

### 目录结构

```
result/homolog/
├── seqkit_faa_stats.txt              # 各物种蛋白序列统计
├── reference_species.txt             # 参考物种信息
├── {Species}.faa                     # 统一ID后的蛋白序列
├── {Species}.cds                     # 统一ID后的CDS序列
├── {Species}.bed                     # BED 文件（6列）
├── {Species}.chrlist                 # 染色体列表
├── {Species}.fa -> {Species}.faa     # GeneTribe 需要的符号链接
├── id_mapping/
│   └── {Species}.map.txt            # protein_id → locus_tag 映射
└── genetribe_result/
    └── {Ref}_vs_{Query}/
        ├── {Ref}_{Query}.RBH         # 互为最佳匹配
        ├── {Ref}_{Query}.SBH         # 单向最佳匹配
        ├── {Ref}_{Query}.one2one     # 一对一同源
        ├── {Ref}_{Query}.one2many    # 一对多同源
        ├── {Ref}_{Query}.singleton   # 孤儿基因
        ├── {Ref}_{Query}.block_pos   # 共线性区块位置
        └── {Ref}_{Query}.collinearity_info  # 共线性信息
```

### 结果文件格式

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

## 注意事项

1. **conda 环境**：脚本要求存在名为 `genetribe` 的 conda 环境，且 jcvi 安装在该环境中
2. **PATH 优先级**：脚本自动将 conda 环境的 bin 目录置于 PATH 最前，避免 `~/.local/bin/python` 覆盖
3. **参考物种**：自动选择蛋白序列数最多的物种，如需指定可通过调整 `reference_species.txt` 实现
4. **CDS 文件**：jcvi 共线性分析需要 CDS 文件，如无则仅运行蛋白水平的同源鉴定
5. **NCBI 数据**：`faa` 模式专门处理 NCBI 格式的 protein_id/locus_tag 不一致问题，非 NCBI 数据可跳过此步
