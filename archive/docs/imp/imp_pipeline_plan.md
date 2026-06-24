# IMP 数据整合分析 — 处理计划

最后更新：2026-05-06（第二次）

---

## 当前进度

| 阶段 | 状态 | 说明 |
|------|------|------|
| 数据下载（A 开头） | ✅ 完成 | 129 物种目录，部分 partial/unavailable |
| 数据下载（B-Z） | 🔄 待执行 | 按字母分批运行 |
| 物种注释 structure/sequence/properties | ✅ 完成 | 115 物种，structure/sequence 各 112，properties 111 |
| 物种注释 eggnog | ⚠️ 基本完成 | 110/115 有效；5 物种缺失（见下） |
| 同属同源 A-prefix | ⚠️ 基本完成 | 13 属成功；Aegilops/Amborella 待运行；7 属不可用 |
| 同属同源 B-Z prefix | 🔄 待执行 | A-prefix 完成后启动 |

### A-prefix 同源结果详情

| 状态 | 属 |
|------|----|
| ✅ 成功（13 属） | Acer、Acorus、Actinidia、Adansonia、Ajuga、Albizia、Amaranthus、Annona、Aquilegia、Arabidopsis、Arabis、Arachis、Avena |
| ⏳ 待运行 | Aegilops（6 物种，bed/chrlist/faa 已准备，大基因组，每对 blast ~15h）；Amborella（dot-sanitization 修复后重运行，进程已结束但无 TSV 产出，需重新触发） |
| ❌ 数据不可用（6 属） | Arctium（lappa gff3 无 gene features）、Artemisia（gff3 无 gene features）、Asparagus（仅 1 个有效物种）、Allium（无 gff3/prot）、Ambrosia（无 gff3）、Aristolochia（contorta prot 下载失败，仅 1 有效物种） |
| ❌ 无法修复 | Andropogon（hap1 蛋白 ID 格式与 GFF3 不一致，需完整重下基因组） |

**备注：** Arachis 的 monticola_PI_263393 在当前 TSV 中列缺失（BSR 失败），可单独补跑该物种对。

### eggnog 缺失物种（5 个，需补跑）

| 物种 | 备注 |
|------|------|
| Amaranthus_cruentus | eggnog.tsv 文件不存在 |
| Arachis_monticola_PI_263393 | eggnog.tsv 文件不存在 |
| Arctium_lappa | eggnog.tsv 文件不存在 |
| Aristolochia_contorta | eggnog.tsv 文件不存在 |
| Artemisia_argyi | eggnog.tsv 文件不存在 |

### 下一步

1. 补跑 5 个物种的 eggnog 注释
2. 重新触发 Amborella 同源分析（dot-sanitization 已修复）
3. 启动 Aegilops 同源分析（bed/chrlist/faa 已就绪）
4. 启动 B-Z 字母数据下载
5. 新下载物种补跑 structure/sequence/properties/eggnog
6. 按字母批量运行 B-Z 同源分析

---

## 输出目录结构

```
result/result_imp/
├── species/
│   └── <Species_Full_Name>/
│       ├── <Species>.structure.tsv      # 基因坐标
│       ├── <Species>.protein.fa         # 蛋白序列（>gene_id|mRNA_id）
│       ├── <Species>.cds.fa             # CDS 序列
│       ├── <Species>.gene.fa            # 基因组序列
│       ├── <Species>.properties.tsv     # 蛋白理化性质
│       └── <Species>.eggnog.tsv         # 功能注释
└── homolog/
    └── <Genus>/
        └── <Genus>_homolog_1v1.tsv      # 属内 one2one 同源对
```

---

## 输入数据结构（/DATA/data2/downloads/IMP）

每个物种目录使用**物种全名**命名，文件也使用全名前缀：

```
Arabidopsis_thaliana/
├── Arabidopsis_thaliana.fa.gz
├── Arabidopsis_thaliana.gff3.gz
├── Arabidopsis_thaliana.gene.fasta
├── Arabidopsis_thaliana.CDS.fasta
├── Arabidopsis_thaliana.prot.fasta
├── Arabidopsis_thaliana.promoter2k.fasta
└── Arabidopsis_thaliana.all.rnaseq.TPM.txt
```

**ID 映射关系（GFF3）：**
- `prot.fasta` 序列 ID = mRNA ID（如 `IMPATA1M00000009943`）
- GFF3 mRNA 记录的 `Parent=` = gene ID（如 `IMPATA1G00000050244`）
- 所有输出统一用 `gene_id`，mRNA_id 作为附属键

---

## 各模块输出格式

### structure.tsv
```
gene_id    chromosome    start    end    strand
```

### protein.fa / cds.fa
```
>gene_id|mRNA_id
序列...
```

### gene.fa
```
>gene_id
序列...
```

### properties.tsv
```
gene_id    mRNA_id    protein_length    isoelectric_point    molecular_weight
```

### eggnog.tsv
```
gene_id    mRNA_id    GO    KEGG    Pfam    Description
```

### homolog/{Genus}_homolog_1v1.tsv
```
gene_id_ref    gene_id_query    type
...            ...              one2one
```

---

## 主脚本：run_imp_pipeline.sh

```
scripts/importers/imp/run_imp_pipeline.sh

-i DIR       输入目录（默认 /DATA/data2/downloads/IMP）
-o DIR       输出目录（默认 result/result_imp）
-m MODE      模式：structure / sequence / properties / eggnog / homolog / all
-g           启用同属同源分析
-s NAME      仅处理指定物种目录名
```

**关键设计：**
- eggnog 模块检测 `.eggnog.tsv` 已存在则跳过（增量友好）
- sequence 模块检测源文件非空才生成对应输出（缺失文件不产生空文件）
- 所有模块从 GFF3 构建 mRNA→gene 映射，输出统一使用 gene_id
- genetribe 在 `/tmp` 本地目录运行，避免 NFS silly-rename 问题
- eggnog 参数：mmseqs + `--dbmem`（39GB DB 加载入 RAM）+ `--tax_scope Viridiplantae`

---

## 数据下载：imp_download.sh

```
scripts/importers/imp/imp_download.sh

-p PREFIX    按 dir_name 前缀分批（-p A 只处理 A 开头物种）
-t THREADS   并行线程数（默认 4）
-d           预览模式
--list       仅爬取物种列表
```

**分批下载计划（1068 个物种）：**
```bash
for prefix in A B C D E F G H I J K L M N O P Q R S T U V W X Y Z; do
    bash scripts/importers/imp/imp_download.sh -p "$prefix" -t 4
done
```

**可用性标记文件：** `data/meta/imp/species_availability.tsv`

| Status | 含义 |
|--------|------|
| `available` | 全部文件正常 |
| `partial` | 部分文件 404（通常 tpm，不影响 pipeline） |
| `unavailable` | 全部 404，IMP 无该物种数据 |

增量运行时自动合并已有记录，不重置。

---

## 环境依赖

| 模块 | conda 环境 | 工具 |
|------|-----------|------|
| structure / sequence / properties | 系统 | awk, python3 + biopython |
| eggnog | biotools | emapper.py v2.1.12, mmseqs2 |
| homolog | genetribe | genetribe, jcvi |

---

## 变更历史

| 日期 | 内容 |
|------|------|
| 2026-05-06 | 校准各模块物种数（eggnog 110/115，structure/sequence 112，properties 111）；确认 5 个 eggnog 缺失物种；Amborella 进程结束但无产出需重新触发；第一批数据（result_imp + downloads/IMP）上传百度网盘 |
| 2026-05-05 | 完成 13 属同源分析；run_homolog() 增加 dot-sanitization 修复；尝试 Amborella 重跑 |
| 2026-04-30 | 拆分输出目录为 species/ 和 homolog/；修复下载脚本 URL/文件名映射；完成 A 开头物种下载；完成全部物种 structure/sequence/properties/eggnog 注释 |
| 2026-04-29 | 初始计划（见 imp_pipeline_plan_20260429.md） |
