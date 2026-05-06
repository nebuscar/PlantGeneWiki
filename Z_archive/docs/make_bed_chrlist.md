# make_bed_chrlist.sh 使用说明

## 概述

遍历 `sample/` 目录下所有物种子目录，从 GFF 注释文件生成 BED 文件和染色体列表文件（chr.list），供 GeneTribe 等同源分析工具使用。

---

## 依赖

- [JCVI](https://github.com/tanghaibao/jcvi)（Python 包，提供 `jcvi.formats.gff` 模块）

---

## 输入数据

### 目录结构要求

```
./sample/
├── Species_A/
│   └── Species_A_annotation.gff
├── Species_B/
│   └── Species_B_annotation.gff
└── ...
```

每个物种子目录下需存在 `{Species}_annotation.gff` 文件。

---

## 输出数据

每个物种目录下生成两个文件：

| 文件                | 说明                                                   |
|---------------------|--------------------------------------------------------|
| `{Species}.bed`     | BED 格式基因坐标文件，4 列：chrom, start, end, gene_id  |
| `{Species}.chr.list`| 染色体/contig 名称列表，每行一个，已去重排序             |

### 目录结构（运行后）

```
./sample/
├── Species_A/
│   ├── Species_A_annotation.gff
│   ├── Species_A.bed
│   └── Species_A.chr.list
├── Species_B/
│   ├── Species_B_annotation.gff
│   ├── Species_B.bed
│   └── Species_B.chr.list
└── ...
```

---

## 使用方法

```bash
# 在项目根目录运行
./scripts/make_bed_chrlist.sh
```

脚本无参数，自动遍历 `./sample/` 下所有子目录。

---

## 方法细节

1. **遍历物种目录**：`for sp_dir in ./sample/*` 遍历所有子目录，取目录名作为物种名 `sp`。
2. **生成 BED 文件**：
   - 调用 `python -m jcvi.formats.gff bed --type=gene --key=ID`，从 GFF 中提取 `type=gene` 的记录，以 `ID` 属性作为 BED 第 4 列名称。
   - `sed -i 's/gene://g'` 去除基因 ID 前缀中的 `gene:`（JCVI 输出会在 ID 前加上 `gene:` 前缀）。
3. **生成 chr.list**：`cut -f1 $bed | sort | uniq` 提取 BED 文件第 1 列（染色体/contig 名），排序去重。
