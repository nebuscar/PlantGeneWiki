# IMP 数据整合分析 - 实施计划

## 输出路径

```
/home/nizhu/Projects/plantsdb/result/result_imp/
├── <Species_Full_Name>/
│   └── <Species_Full_Name>.xlsx          # 4 sheets: structure, sequence, properties, eggnog
└── <Genus>/
    └── <Genus>_homolog_1v1.xlsx          # one2one homolog mapping within genus
```

---

## 数据格式 (IMP 文件结构，已完成重命名)

每个物种目录 (如 `Aegilops_bicornis/`):
```
Aegilops_bicornis.gff3.gz     # GFF3 注释 (gene/mRNA/exon/CDS)
Aegilops_bicornis.prot.fasta  # 蛋白序列 (ID = mRNA ID, 如 IMPTABI1N1_1)
Aegilops_bicornis.CDS.fasta   # CDS 序列 (ID = mRNA ID)
Aegilops_bicornis.gene.fasta  # 基因序列 (ID = gene ID, 如 IMPGABI1N1)
Aegilops_bicornis.fa.gz       # 基因组序列
```

**关键映射关系 (GFF3)**:
- `gene` ID: `IMPGABI1N1`
- `mRNA` ID: `IMPTABI1N1_1`, Parent = `IMPGABI1N1`
- prot.fasta 的序列 ID = mRNA ID

---

## Sheet 设计

### Sheet 1: structure
| gene_id | chromosome | start | end | strand |
|---------|------------|-------|-----|--------|
| IMPGABI1N1 | chr1 | 6184 | 6474 | - |

### Sheet 2: sequence
| gene_id | mRNA_id | protein_seq | cds_seq | gene_seq |
|---------|---------|-------------|---------|----------|
| IMPGABI1N1 | IMPTABI1N1_1 | MRLLLPS... | ATGAGG... | ATGAGG... |

### Sheet 3: properties
| gene_id | mRNA_id | protein_length | isoelectric_point | molecular_weight |
|---------|---------|----------------|-------------------|------------------|
| IMPGABI1N1 | IMPTABI1N1_1 | 142 | 8.52 | 15823.5 |

### Sheet 4: eggnog
| gene_id | mRNA_id | GO | KEGG | Pfam | Description |
|---------|---------|-----|------|------|-------------|
| IMPGABI1N1 | IMPTABI1N1_1 | GO:000... | ko:... | PF... | ... |

### Sheet 5 (homolog): per genus
| gene_id_ref | gene_id_query | type |
|-------------|---------------|------|
| IMPGABI1N1 | IMPGABI2N1 | one2one |

---

## ID 映射链

```
prot.fasta ID (mRNA ID) → GFF3 mRNA.Parent → gene ID
```
- prot.fasta ID = mRNA ID
- GFF3 中 mRNA 有 `Parent=gene_ID`，建立 mRNA → gene 映射
- 所有输出统一用 `gene_id`，mRNA_id 作为 secondary key

---

## 环境配置

| 模块 | 环境 | 工具 |
|------|------|------|
| 1-4 | biotools | awk, seqkit, python + Bio.SeqUtils.ProtParam, emapper.py |
| 5 (homolog) | genetribe | genetribe |

---

## 实施步骤

### Step 1: 主脚本 `run_imp_pipeline.sh`
统一入口，支持 `-m` 选择模块组合，支持 `-g` 属分组模式。
```
-i DIR       输入目录 (默认 /DATA/data2/downloads/IMP)
-o DIR       输出目录 (默认 ./result/result_imp)
-g           属分组模式 (启用同源分析)
-m MODE      运行模式: all/structure/sequence/properties/eggnog/homolog
-s NAME      仅处理指定物种
-h           帮助
```

### Step 2: 物种扫描
- 遍历 `/DATA/data2/downloads/IMP/*/`
- 识别有 `*.gff3.gz` + `*.prot.fasta` 的目录
- 提取物种前缀 (从 gff3.gz 文件名去掉 `.gff3.gz`)
- 构建 `mRNA_ID → gene_ID` 映射表

### Step 3: 模块 1 - structure
从 GFF3 gene 记录提取: `gene_id, chromosome, start, end, strand`

### Step 4: 模块 2 - sequence
- protein_seq: 从 `$PREFIX.prot.fasta` 按 mRNA_ID 提取
- cds_seq: 从 `$PREFIX.CDS.fasta` 按 mRNA_ID 提取
- gene_seq: 从 `$PREFIX.gene.fasta` 按 gene_ID 提取

### Step 5: 模块 3 - properties
Bio.SeqUtils.ProtParam 计算: protein_length, isoelectric_point, molecular_weight

### Step 6: 模块 4 - eggnog
emapper.py (biotools 环境)，输出 GO, KEGG, Pfam, Description

### Step 7: 模块 5 - homolog
同属物种两两比对 (genetribe 环境):
- 从 manifest Species_Name 提取属名
- 每属一个工作目录
- 生成 BED 和 chrlist
- 运行 `genetribe core -l <ref> -f <query>`
- 整合所有 one2one 映射

### Step 8: xlsx 整合输出
- 每个物种: `$OUTPUT_DIR/<Species>/<Species>.xlsx` (4 sheets)
- 每个属: `$OUTPUT_DIR/<Genus>/<Genus>_homolog_1v1.xlsx`

---

## 关键设计决策

1. **ID 统一**: 所有模块输出用 `gene_id`，mRNA_id 作为 secondary key
2. **物种名**: 目录名即为物种全称 (下划线分隔)
3. **文件前缀**: 从 gff3.gz 文件名提取 (如 `Aegilops_bicornis`)
4. **模块 1-4 整合**: 同一物种 4 个 sheet 共用 `gene_id` 键
5. **genetribe**: 直接用 prot.fasta (已支持 .faa/.fa/.fasta/.pep/.aa)

---

## 验证方案

1. 选取一个物种 (如 `Aegilops_bicornis`) 单独测试
2. 验证 gene_id/mRNA_id 映射正确
3. 验证 xlsx 4 个 sheet 数据关联正确
4. 选取一个属测试同源分析 (如 `Acer` 属)
5. 检查 one2one 映射表
