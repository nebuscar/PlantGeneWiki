# 基因组结构注释金标准方案 Pipeline

## 一、整体架构

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        基因组结构注释金标准 Pipeline                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  【第一阶段】数据准备                                                           │
│                                                                               │
│    NCBI下载的fna ─────────────────► 基因组清洗 ─────────────────► 清洁基因组     │
│                                      (去空白/标准化行长/统一accession)          │
│                                                                               │
│  【第二阶段】证据收集                                                           │
│                                                                               │
│    清洁基因组 ────────────────────► RepeatMasker ───────► 重复序列注释           │
│         │                                                                     
│         ├──────────────────► MAKER (可选)                                     │
│         │                          │                                         
│         │                    整合初始注释                                     
│         │                                                                     
│  【第三阶段】多证据预测                                                         │
│                                                                               │
│    清洁基因组 ────────────────────► AUGUSTUS (从头预测)                        │
│    清洁基因组 ────────────────────► GeneMark-ES (自训练)                        │
│    清洁基因组 ────────────────────► SNAP (HMM模型)                             │
│                                                                               
│    近缘物种蛋白 ─────────────────► Exonerate (同源预测)                        │
│    近缘物种蛋白 ─────────────────► Spaln (同源比对)                           │
│                                                                               
│    RNA-seq数据 ─────────────────► BRAKER (转录组指导预测)                     │
│                                                                               
│  【第四阶段】证据整合                                                           │
│                                                                               │
│    AUGUSTUS ─┐                                                                │
│    GeneMark ─┼──► EvidenceModeler (EVM) ──► PASA ──► 最终GFF3                │
│    SNAP ─────┤                                                                │
│    Exonerate ┘                                                                │
│                                                                               
│  【第五阶段】功能注释                                                           │
│                                                                               │
│    最终GFF3 ────────────────────► 蛋白序列提取 ───► InterProScan / eggNOG      │
│                                    最终GFF3 ───► GO/KEGG注释                   │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、分阶段详解

### 阶段 0：前提条件

#### 2.1 安装核心工具

```bash
# 使用 conda 创建专用环境
conda create -n annotation -c bioconda \
    augustus genemark-es snap exonerate spaln \
    evidence-modeler pasa braker2 repeatmasker \
    hisat2 stringtie gffread

# 激活环境
conda activate annotation
```

#### 2.2 工具说明

| 工具 | 用途 | 特点 |
|------|------|------|
| **RepeatMasker** | 重复序列屏蔽 | 植物基因组必需 |
| **AUGUSTUS** | 从头预测基因 | 需要物种训练模型 |
| **GeneMark-ES** | 从头预测基因 | 自训练，无需预先配置 |
| **SNAP** | HMM从头预测 | 通用模型可用 |
| **Exonerate** | 蛋白-基因组比对 | 同源预测 |
| **Spaln** | 高级同源比对 | 支持外显子边界 |
| **BRAKER** | RNA-seq指导预测 | 需要转录组数据 |
| **EVM** | 证据整合 | 多预测结果加权合并 |
| **PASA** | 转录组校准 | 最终注释优化 |

---

## 三、分阶段执行流程

### 阶段 1：数据清洗

#### 3.1.1 为什么需要清洗NCBI数据

NCBI下载的fna文件存在以下技术问题：

| 问题 | 原因 | 影响 |
|------|------|------|
| **大小写混用** | NCBI有意区分参考区和预测区 | 比对可能失败 |
| **Scaffold命名不统一** | RefSeq/GenBank命名体系不同 | 难以对应 |
| **行长度不固定** | 传输/解压导致 | 某些工具处理异常 |
| **空白行** | Windows/Unix换行符问题 | 序列解析错误 |

**大小说明**：NCBI官方标准
- **大写**：权威/参考区域（已验证的CDS等）
- **小写**：非权威/预测区域（内含子、预测基因等）

#### 3.1.2 清洗脚本

```bash
#!/bin/bash
# clean_genome.sh - 基因组fna清洗脚本

INPUT=$1
OUTPUT=$2

if [ -z "$INPUT" ] || [ -z "$OUTPUT" ]; then
    echo "用法: $0 <输入fna> <输出fna>"
    exit 1
fi

bioawk -c fastx '
{
    # 提取accession作为序列名（取第一个空格前的ID）
    name = $name
    sub(/ .*/, "", name)
    
    # 转为大写（做比对时用）
    seq = toupper($seq)
    
    # 移除所有空白字符
    gsub(/[ \t\n\r]/, "", seq)
    
    # 过滤空序列
    if (length(seq) > 0) {
        print ">" name
        # 标准化60列输出
        system("echo \"" seq "\" | fold -w 60")
    }
}
' "$INPUT" > "$OUTPUT"

echo "清洗完成: $OUTPUT"
```

#### 3.1.3 执行

```bash
# 单个文件
bash clean_genome.sh input.fna output_clean.fna

# 批量处理
for fna in */ *_genome.fna; do
    [ -f "$fna" ] && bash clean_genome.sh "$fna" "${fna%.fna}_clean.fna"
done
```

---

### 阶段 2：重复序列注释

#### 3.2.1 RepeatMasker

植物基因组重复序列可占70%以上，是注释准确性的关键。

```bash
# 构建输出目录
mkdir -p repeatmasker_out

# 运行RepeatMasker（植物物种库）
RepeatMasker \
    -species viridiplantae \
    -poly \
    -gff \
    -dir ./repeatmasker_out \
    -fasta ./genome_clean.fna

# 输出文件：
#   genome_clean.fna         - 原始序列（大小写保留）
#   genome_clean.fna.masked - 重复区用N替代
#   genome_clean.tbl         - 重复序列统计
#   genome_clean.fna.cat.gz - 重复分类详情
```

#### 3.2.2 常用参数

| 参数 | 说明 |
|------|------|
| `-species` | 指定物种库，如 viridiplantae, arabidopsis 等 |
| `-poly` | 识别_poly_A尾部 |
| `-gff` | 输出GFF格式注释 |
| `-dir` | 输出目录 |
| `-xsmall` | 用小写表示重复序列（而非N） |

#### 3.2.3 自定义重复库（可选）

```bash
# 使用RepBase数据库
wget https://www.girinst.org/server/RepBase/repeatmasker-libraries.tar.gz
tar -xzf repeatmasker-libraries.tar.gz -C $CONDA_PREFIX/share/RepeatMasker/

# 配置
perl $CONDA_PREFIX/scripts/RepeatMasker/configure假
```

---

### 阶段 3：同源蛋白数据准备

#### 3.3.1 近缘物种蛋白来源

```bash
# 方式1：从NCBI下载近缘物种protein.faa
datasets download genome taxon <taxid> --include protein

# 方式2：从本地数据库获取
# 建议：至少3-5个近缘物种
```

#### 3.3.2 构建蛋白数据库

```bash
# 合并多个物种的蛋白序列
cat species1_protein.faa species2_protein.faa ... > ref_proteins.faa

# 构建BLAST索引
makeblastdb -in ref_proteins.faa -dbtype prot -out ref_proteins
```

---

### 阶段 4：多证据从头预测

#### 3.4.1 GeneMark-ES（推荐首先运行）

**特点**：自训练模式，无需预先训练模型

```bash
# ES = Exon Separation，自训练模式
gmes_petap.pl \
    --sequence genome_clean.fna.masked \
    --ES \
    --soft masked \
    --min_contig 10 \
    --min_gene 100 \
    --cores 32

# 输出：
#   genemark.gtf - 基因预测结果
#   genemark.fasta.transdecoder.cds - 预测的CDS序列
```

#### 3.4.2 AUGUSTUS

**特点**：需要物种模型，可使用通用模型或训练

```bash
# 查看可用物种模型
augustus --species=help 2>&1 | grep -i plant

# 使用通用植物模型
augustus \
    --species=generic \
    --extrinsicCfgFile=$CONDA_PREFIX/config/extrinsic.cfg \
    --softmasking=on \
    --gff=off \
    --genome=genome_clean.fna.masked \
    > augustus.gff

# 或使用近缘物种模型
augustus --species=arabidopsis augustus --species=maize ...
```

#### 3.4.3 SNAP

**特点**：基于HMM，通用模型可用

```bash
# 使用植物HMM模型
snap genome_clean.fna.masked Zmays.sgf -gff -quiet > snap.gff

# 如需创建自定义模型
fathom -gene-stats genome.fna model.est
fathom -validate model.est
```

---

### 阶段 5：同源预测

#### 3.5.1 Exonerate（蛋白到基因组比对）

```bash
# 方法1：直接比对
exonerate \
    --protein genome_clean.fna.masked ref_protein.faa \
    --genome \
    --showtargetgff TRUE \
    --showcigar no \
    > exonerate_result.gff

# 方法2：批量比对（推荐）
for faa in ref_proteins/*.faa; do
    name=$(basename $faa .faa)
    exonerate \
        --protein genome_clean.fna.masked $faa \
        --genome \
        --showtargetgff TRUE \
        --showcigar no \
        > exonerate_${name}.gff
done

# 合并结果
cat exonerate_*.gff > homology_exonerate.gff
```

#### 3.5.2 Spaln（高级同源比对）

**优点**：更好的外显子边界处理

```bash
# 构建蛋白索引
spaln -O -M5000 -Q40 -H3 -d ref_proteins genome_clean.fna.masked -o spaln.gff
```

#### 3.5.3 GMAP（可選）

```bash
# 适合RNA-seq比对
gmap_build -d genome_index genome_clean.fna.masked
gmap -d genome_index -t 32 reads.fq -f gff3 > gmap.gff3
```

---

### 阶段 6：RNA-seq指导预测（BRAKER）

**注意**：此阶段需要RNA-seq数据

#### 3.6.1 RNA-seq比对

```bash
# 构建基因组索引
hisat2-build genome_clean.fna.masked genome_index

# 双端测序比对
hisat2 -p 32 -x genome_index \
    -1 rna_1.fq.gz -2 rna_2.fq.gz | \
    samtools sort -o aligned.bam

# 单端测序
hisat2 -p 32 -x genome_index -U reads.fq.gz | \
    samtools sort -o aligned.bam
```

#### 3.6.2 BRAKER注释

```bash
braker.pl \
    --species=your_species_name \
    --genome=genome_clean.fna.masked \
    --bam=aligned.bam \
    --threads 32 \
    --softmasking \
    --gff3
```

---

### 阶段 7：证据整合（EVM）

#### 3.7.1 准备权重文件

```bash
cat > weights.txt << 'EOF'
# 格式：来源类型  权重
AUGUSTUS      2
GeneMark      2
SNAP          1
exonerate     5
Spaln         5
BRAKER        8
EOF
```

#### 3.7.2 证据权重分配原则

| 证据来源 | 权重范围 | 说明 |
|----------|----------|------|
| RNA-seq (BRAKER) | 8-10 | 最高权重，直接证据 |
| 同源蛋白 (Exonerate/Spaln) | 5-8 | 高权重，近缘物种验证 |
| 转录组组装 (PASA) | 6-8 | 高权重，表达证据 |
| AUGUSTUS (训练后) | 3-5 | 中等权重 |
| GeneMark-ES | 3-5 | 中等权重 |
| SNAP | 1-3 | 较低权重 |

#### 3.7.3 准备GFF列表

```bash
cat > predictions.list << 'EOF'
AUGUSTUS	augustus.gff
GeneMark	genemark.gtf
SNAP	snap.gff
exonerate	homology_exonerate.gff
Spaln	spaln.gff
BRAKER	braker.gff3
EOF
```

#### 3.7.4 执行EVM

```bash
# 方法1：直接整合（简单基因组）
evidence_modeler \
    -S predictions.list \
    -w weights.txt \
    -G genome_clean.fna.masked \
    -o evm.gff3

# 方法2：分割基因组并行处理（大基因组）
# 创建分割文件
partition_genome.pl genome_clean.fna.masked 1000000 > genome.partitions

# 并行整合
evidence_modeler \
    -S predictions.list \
    -w weights.txt \
    -G genome_clean.fna.masked \
    -P genome.partitions \
    --CPU 32 \
    -o evm.gff3
```

---

### 阶段 8：PASA最终校准

#### 3.8.1 转录组组装

```bash
# 使用StringTie组装
hisat2 -p 32 -x genome_index -1 rna_1.fq.gz -2 rna_2.fq.gz | \
    samtools sort -o aligned.bam

stringtie -p 32 -o transcripts.gtf aligned.bam

# 转换为GFF3和FASTA
gffread transcripts.gtf -o transcripts.gff3 -g genome_clean.fna.masked
gffread transcripts.gtf -o transcripts.fasta -g genome_clean.fna.masked
```

#### 3.8.2 PASA校准

```bash
# 配置PASA
cat > pasa.config << 'EOF'
DATABASE,sqlite,annot_compare.sqlite,0
ALIGNER,hlatra,1,1
EOF

# 运行PASA
Launch_PASA_pipeline.pl \
    -c pasa.config \
    -R \
    -C \
    -g genome_clean.fna.masked \
    -t transcripts.fasta \
    --ALIGNERS hisat2 \
    --CPU 32

# 最终GFF
cp *.gff3.final final_annotation.gff3
```

---

### 阶段 9：蛋白序列提取与功能注释

#### 3.9.1 提取蛋白序列

```bash
gffread final_annotation.gff3 \
    -g genome_clean.fna.masked \
    -y final_proteins.faa \
    -p mRNA
```

#### 3.9.2 InterProScan功能注释

```bash
# 蛋白家族和功能域注释
interproscan.sh \
    -i final_proteins.faa \
    -f tsv \
    -o interpro_annotation.tsv \
    -dp \
    --cpu 32

# 输出包含：GO terms, Pfam domains, InterPro entries
```

#### 3.9.3 eggNOG-mapper

```bash
# 同源簇和功能注释
emapper.py \
    -i final_proteins.faa \
    -o eggnog_output \
    --cpu 32 \
    -m diamond

# 输出：KO, GO, KEGG, eggNOG orthologs
```

---

## 四、输出文件说明

| 文件后缀 | 说明 |
|----------|------|
| `*_clean.fna` | 清洗后的基因组序列 |
| `*_clean.fna.masked` | 重复序列被N替代的基因组 |
| `*.rm.gff` | RepeatMasker重复序列注释 |
| `augustus.gff` | AUGUSTUS从头预测结果 |
| `genemark.gtf` | GeneMark-ES预测结果 |
| `snap.gff` | SNAP预测结果 |
| `homology_exonerate.gff` | Exonerate同源预测结果 |
| `spaln.gff` | Spaln同源预测结果 |
| `braker.gff3` | BRAKER RNA-seq指导预测 |
| `evm.gff3` | EVM整合结果 |
| `final_annotation.gff3` | PASA校准后最终注释 |
| `final_proteins.faa` | 最终注释对应的蛋白序列 |
| `interpro_annotation.tsv` | InterProScan功能注释 |
| `eggnog_output.tsv` | eggNOG功能注释 |

---

## 五、快速简化版（仅fna可用时）

当**仅有fna序列，无RNA-seq和近缘蛋白数据**时：

```bash
#!/bin/bash
# minimal_annotation.sh - 仅fna的简化注释流程

GENOME=$1
OUTPUT_PREFIX=${2:-output}

echo "===== 步骤1: 清洗基因组 ====="
bash clean_genome.sh ${GENOME} ${OUTPUT_PREFIX}_clean.fna

echo "===== 步骤2: RepeatMasker重复序列屏蔽 ====="
RepeatMasker -species viridiplantae -poly -gff \
    -dir ./rm_out \
    ${OUTPUT_PREFIX}_clean.fna

echo "===== 步骤3: GeneMark-ES自训练预测 ====="
gmes_petap.pl --sequence ${OUTPUT_PREFIX}_clean.fna.masked \
    --ES --soft masked --cores 32

echo "===== 步骤4: AUGUSTUS从头预测 ====="
augustus --species=generic \
    --softmasking=on \
    ${OUTPUT_PREFIX}_clean.fna.masked > augustus.gff

echo "===== 步骤5: 合并GFF（取并集） ====="
cat augustus.gtf genemark.gtf > all_predictions.gff3

echo "===== 步骤6: 提取蛋白序列 ====="
gffread all_predictions.gff3 \
    -g ${OUTPUT_PREFIX}_clean.fna.masked \
    -y ${OUTPUT_PREFIX}_proteins.faa \
    -p mRNA

echo ""
echo "===== 注释完成 ====="
echo "最终注释: ${OUTPUT_PREFIX}_annotation.gff3"
echo "蛋白序列: ${OUTPUT_PREFIX}_proteins.faa"
```

**执行**：
```bash
bash minimal_annotation.sh genome.fna species_name
```

---

## 六、流程选择决策树

```
开始：仅fna序列可用？
        │
        ├── 是，无其他数据
        │         ↓
        │   GeneMark-ES + AUGUSTUS + SNAP
        │   （纯从头预测，权重设为1-2）
        │         ↓
        │   精度: 70-85%
        │   需人工抽检10-20个基因验证
        │
        └── 有同源蛋白数据？
                  │
                  └── Exonerate/Spaln 同源预测
                           权重提高至5-8
                           ↓
                     精度: 80-90%
                           │
                     有RNA-seq数据？
                           │
                     BRAKER + EVM + PASA
                           ↓
                     精度: 90-95%
                     （接近金标准）
```

---

## 七、时间估算

| 步骤 | 基因组大小 | 线程 | 时间 |
|------|-----------|------|------|
| 基因组清洗 | 500 Mb | 1 | 5-10 min |
| RepeatMasker | 500 Mb | 32 | 2-4 h |
| GeneMark-ES | 500 Mb | 32 | 4-8 h |
| AUGUSTUS | 500 Mb | 32 | 3-6 h |
| SNAP | 500 Mb | 32 | 1-2 h |
| Exonerate/Spaln | 500 Mb | 32 | 2-4 h |
| EVM整合 | 500 Mb | 16 | 1-2 h |
| PASA校准 | 500 Mb | 32 | 2-4 h |
| **总计（完整流程）** | | | **12-24 h** |
| **总计（简化流程）** | | | **6-12 h** |

---

## 八、注意事项

### 8.1 关键原则

1. **GeneMark-ES必须首先运行**（自训练需要干净的重复屏蔽序列）
2. **重复序列屏蔽是植物基因组注释的关键**（植物重复序列可占70%+）
3. **仅fna时**，AUGUSTUS使用`--species=generic`，精度有限
4. **建议至少用2个以上近缘物种蛋白**做同源预测
5. **最终结果必须人工抽检** 10-20 个基因验证

### 8.2 常见问题

| 问题 | 解决方案 |
|------|----------|
| AUGUSTUS运行缓慢 | 减小基因组或使用 `--progress=true` |
| GeneMark-ES内存不足 | 设置 `--min_contig` 过滤小contig |
| EVM报错 | 检查GFF格式是否一致（gtf vs gff3） |
| PASA无输出 | 确认转录本比对质量 |

### 8.3 质量评估

```bash
# BUSCO评估注释完整性
busco -i final_proteins.faa \
    -l viridiplantae_odb10 \
    -o busco_output \
    -m protein \
    --cpu 32

# 评估基因数目合理性
grep -c "^>" final_proteins.faa  # 总基因数
awk '{print $9}' final_annotation.gff3 | grep -c "gene"  # GFF中基因数
```

---

## 九、相关文档

- [NCBI数据下载流程](./scripts/download_genomes.md)
- [同源基因分析](./scripts/run_genetribe.md)
- [基因功能注释](./eggnog_mapper_install_guide.md)
