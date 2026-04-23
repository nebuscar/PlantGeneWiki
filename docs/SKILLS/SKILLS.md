# SKILLS - 生物信息学技能手册

## 目录

- [基因组注释](#基因组注释)
- [数据处理](#数据处理)
- [比对分析](#比对分析)
- [植物基因组专题](#植物基因组专题)

---

## 基因组注释

### 1.1 基因组结构注释流程

**适用场景**：仅有fna序列，无RNA-seq和蛋白数据

```bash
# 核心工具安装
conda create -n annotation -c bioconda \
    augustus genemark-es snap exonerate evidence-modeler pasa repeatmasker

# 推荐流程
1. clean_genome.sh           # 基因组清洗
2. RepeatMasker              # 重复序列屏蔽
3. GeneMark-ES               # 自训练从头预测
4. AUGUSTUS --species=generic # 从头预测
5. EVM整合                    # 证据整合
```

**权重设置**（仅fna时）：
```
GeneMark      2
AUGUSTUS      2
SNAP          1
```

**相关文档**：[genome_annotation_pipeline.md](../genome_annotation_pipeline.md)

---

### 1.2 NCBI数据下载与清洗

#### 下载基因组数据

```bash
# 使用 NCBI datasets CLI
datasets download genome taxon <taxid> \
    --include genome,protein,cds,gff3,gbff \
    --filename genome.zip

# 解压并整理
unzip -o genome.zip -d species_dir/
```

#### 清洗fna文件

```bash
# 问题：大小写混用、Scaffold命名不统一、行长度不固定
# 解决：

bioawk -c fastx '
{
    name = $name
    sub(/ .*/, "", name)      # 统一accession
    seq = toupper($seq)       # 统一大写
    gsub(/[ \t\n\r]/, "", seq) # 移除空白
    if (length(seq) > 0) {
        print ">" name
        system("echo \"" seq "\" | fold -w 60")
    }
}' input.fna > output.fna
```

---

### 1.3 重复序列处理

#### RepeatMasker

```bash
# 植物基因组必须步骤
RepeatMasker \
    -species viridiplantae \
    -poly \
    -gff \
    -dir ./rm_out \
    -fasta genome.fna

# 输出
#   *.fna.masked    # 重复区用N替代
#   *.tbl           # 统计报告
```

---

### 1.4 基因预测工具

#### GeneMark-ES（推荐首先运行）

```bash
# 自训练，无需预先配置
gmes_petap.pl \
    --sequence genome_masked.fna \
    --ES \
    --soft masked \
    --cores 32
```

#### AUGUSTUS

```bash
# 通用模型
augustus --species=generic genome.fna > augustus.gff

# 查看可用物种模型
augustus --species=help | grep -i plant
```

#### SNAP

```bash
# 使用植物HMM模型
snap genome.fna Zmays.sgf -gff > snap.gff
```

---

### 1.5 证据整合 EVM

```bash
# 权重文件
cat > weights.txt << 'EOF'
AUGUSTUS      2
GeneMark      2
exonerate     5
EOF

# 整合
evidence_modeler \
    -S predictions.list \
    -w weights.txt \
    -G genome.fna \
    -o evm.gff3
```

---

### 1.6 PASA转录组校准

```bash
# 需要转录组数据
Launch_PASA_pipeline.pl \
    -c pasa.config \
    -R -C \
    -g genome.fna \
    -t transcripts.fasta
```

---

### 1.7 基因功能注释

#### InterProScan

```bash
interproscan.sh \
    -i proteins.faa \
    -f tsv \
    -o interpro.tsv \
    -dp --cpu 32
```

#### eggNOG-mapper

```bash
emapper.py \
    -i proteins.faa \
    -o eggnog_output \
    --cpu 32 \
    -m diamond
```

---

## 数据处理

### 2.1 FASTA/FASTQ操作

#### seqkit 常用命令

```bash
# 序列统计
seqkit stats *.fna

# 序列提取
seqkit seq -n my_ids.txt input.fna > output.fna

# 序列过滤（按长度）
seqkit seq -m 100 input.fna > output.fna

# fasta转tab
seqkit fx2tab -l -g input.fna
```

#### bioawk基本操作

```bash
# 序列统计
bioawk -c fastx '{print length($seq)}' input.fna | stats

# 序列反转
bioawk -c fastx '{print ">"$name"\n"$seq}' input.fna | rev

# 序列翻译
bioawk -c fastx '{print translate($seq)}' input.fna
```

---

### 2.2 GFF/GTF操作

#### gffread序列提取

```bash
# 提取蛋白序列
gffread annotation.gff3 -g genome.fna -y proteins.faa -p mRNA

# 提取CDS序列
gffread annotation.gff3 -g genome.fna -y cds.fna -p CDS

# GFF转GTF
gffread annotation.gff3 -T -o annotation.gtf
```

#### gff2bed转换

```bash
# GFF转BED
awk -F'\t' '$3=="gene"' annotation.gff3 | \
    gff2bed > genes.bed

# 直接转换（简化版）
awk -F'\t' '$3=="gene" && NF>=9 {
    attrs = ""; for(i=9;i<=NF;i++) attrs = attrs (i>9?" ":"") $i
    n = split(attrs, a, /;/); id=""
    for(i=1;i<=n;i++) {
        gsub(/^[ \t]+/, "", a[i])
        if(a[i] ~ /^ID=/) { id=substr(a[i],4); break }
    }
    if(id!="") print $1"\t"$4-1"\t"$5"\t"id"\t.\t"$7
}' annotation.gff3 > genes.bed
```

---

### 2.3 文本处理

#### awk常用模式

```bash
# 按列提取
awk -F'\t' '{print $1, $3}' file.tsv

# 按条件过滤
awk -F'\t' '$3>100 && $5=="A"' file.tsv

# 分组统计
awk -F'\t' '{count[$4]++} END {for(k in count) print k, count[k]}' file.tsv

# 多文件关联
awk 'NR==FNR {map[$1]=$2; next} {print $0, map[$3]}' map.txt data.txt
```

#### 合并文件

```bash
# 行方向合并
cat file1.txt file2.txt > merged.txt

# 列方向合并
paste file1.txt file2.txt > merged.txt

# join（按key列）
join -t'\t' -1 1 -2 1 file1.txt file2.txt
```

---

### 2.4 格式转换

#### CSV/TSV/Excel

```bash
# CSV转TSV
awk -F',' '{print}' file.csv | awk -F'\t' '{print}'

# TSV转CSV
awk -F'\t' -v OFS=',' '{print}' file.tsv

# Excel转TSV（需pandas）
python3 -c "import pandas as pd; df=pd.read_excel('file.xlsx'); df.to_csv('file.tsv', sep='\t', index=False)"
```

---

## 比对分析

### 3.1 序列比对

#### BLAST

```bash
# 构建数据库
makeblastdb -in proteins.faa -dbtype prot -out proteins_db

# 蛋白比对蛋白
blastp -query query.faa -db proteins_db -outfmt 6 -evalue 1e-5 > results.txt

# 核酸比对蛋白（6框架翻译）
blastx -query genome.fna -db proteins_db -outfmt 6 -evalue 1e-5 > results.txt

# 输出格式6列说明
# qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore
```

#### diamond（加速版BLAST）

```bash
# 构建索引
diamond makedb --in proteins.faa -d proteins_diamond

# 比对
diamond blastp -q query.faa -d proteins_diamond -o results.tsv -e 1e-5 --more-sensitive
```

---

### 3.2 多序列比对

#### MUSCLE

```bash
# 多序列比对
muscle -in sequences.faa -out aligned.faa

# 比对蛋白序列
muscle -in proteins.faa -out aligned.faa -maxiters 16
```

#### MAFFT

```bash
# 快速比对
mafft --auto input.faa > aligned.faa

# 高精度模式
mafft --maxseqlength 50000 --localpair --maxiterate 1000 input.faa > aligned.faa
```

---

### 3.3 RNA-seq比对

#### HISAT2

```bash
# 构建索引
hisat2-build genome.fna genome_index

# 比对（双端）
hisat2 -p 32 -x genome_index -1 rna_1.fq.gz -2 rna_2.fq.gz | \
    samtools sort -o aligned.bam

# 比对（单端）
hisat2 -p 32 -x genome_index -U reads.fq.gz | \
    samtools sort -o aligned.bam
```

#### STAR

```bash
# 构建索引
STAR --runMode genomeGenerate \
    --genomeDir genome_index \
    --genomeFastaFiles genome.fna \
    --runThreadN 32

# 比对
STAR --runMode alignReads \
    --genomeDir genome_index \
    --readFilesIn rna_1.fq.gz rna_2.fq.gz \
    --outSAMtype BAM SortedByCoordinate \
    --runThreadN 32
```

---

### 3.4 共线性分析

#### MCScanX

```bash
# 需要自己制备输入文件
cat gene.gff blastout.txt > input.txt

# 运行
 MCScanX input.txt

# 可视化
java -jar MCScanX_downstream.pl -i input.txt -c 1-10
```

---

## 植物基因组专题

### 4.1 植物特异性问题

#### 4.1.1 高重复序列

植物基因组常有>70%重复序列：

```bash
# 必须先做RepeatMasker
RepeatMasker -species viridiplantae -poly -gff genome.fna

# 仅用soft-masked序列做基因预测
# 不要用完全masked的序列做RNA-seq比对
```

#### 4.1.2 高倍性复杂基因组

```bash
# 分离同源染色体（需Hi-C数据）
juicer -d [directory] -p [site_file] -z [genome]
hicpro2juicebox
```

---

### 4.2 常用植物数据库

#### NCBI Taxonomy

```bash
# 查询TaxID
taxonkit name2taxid "Arabidopsis thaliana"

# 获取分类信息
taxonkit lineage 3702 | taxonkit reformat -r "; " -f "{k};{p};{c};{o};{f};{g};{s}"
```

#### 植物蛋白数据库

| 数据库 | 说明 |
|--------|------|
| UniProt Plants | 植物蛋白 |
| PLAZA | 植物比较基因组 |
| Phytozome | 植物基因组 |
| Ensembl Plants | 植物基因组 |

---

### 4.3 基因组版本选择

```bash
# 优先选择原则
1. RefSeq > GenBank (RefSeq经过更多审核)
2. Chromosome > Scaffold > Contig (完整度)
3. Annotated > Unannotated (有注释数据)
4. Latest version (最新版本)

# 查看可用版本
datasets summary genome taxon "<species>" --as-json | jq '.reports[].accession'
```

---

## 常用工具速查

### 5.1 核心工具安装

```bash
# conda生物信息学常用渠道
conda install -c bioconda \
    samtools bcftools bedtools \
    blast diamond muscle mafft \
    seqkit bioawk \
    augustus genemark-es snap exonerate \
    hisat2 stringtie gffread \
    interproscan eggnog-mapper

# Python生物信息学
pip install biopython pandas openpyxl jcvi
```

### 5.2 常见命令对照

| 操作 | 命令 |
|------|------|
| 序列计数 | `grep -c "^>" file.fna` |
| 序列统计 | `seqkit stats file.fna` |
| 长度过滤 | `seqkit seq -m 100 file.fna` |
| ID提取 | `cut -f1 file.bed` |
| 去重 | `sort -u file.txt` |
| 计数 | `wc -l file.txt` |
| 查找替换 | `sed 's/old/new/g' file` |

---

## 常见问题处理

### Q1: BLAST比对结果为空

**可能原因**：
1. E-value阈值过高
2. 序列方向相反（尝试`-strand minus`）
3. 数据库太小区段匹配不够

**解决**：
```bash
# 放宽阈值
blastp -evalue 10 -qcov_hsp_perc 50

# 检查序列方向
bioawk -c fastx '{print $name, length($seq)}' query.faa
```

---

### Q2: GFF格式错误

**检查GFF格式**：
```bash
# 必须是9列
awk -F'\t' 'NF!=9 {print NR": "$0}' file.gff3

# 第三列必须是标准feature type
awk -F'\t' '{print $3}' file.gff3 | sort | uniq -c | sort -rn
```

---

### Q3: 内存不足

**解决**：
```bash
# 分批处理大文件
split -l 10000 large_file.faa chunk_

# 使用samtools处理大BAM
samtools sort -@ 4 -m 4G input.bam -o output.bam

# 数据库分块索引
diamond makedb --in large.faa -d large --chunk 10
```

---

## 附录

### A. 文件格式说明

#### GFF3格式

```
# 9列：seqid source type start end score strand phase attributes
Chr1    AUGUSTUS    gene    1000    2000    .    +    .    ID=gene1;Name=gene1
Chr1    AUGUSTUS    mRNA    1000    2000    .    +    .    ID=transcript1;Parent=gene1
Chr1    AUGUSTUS    CDS     1100    1500    .    +    0    ID=cds1;Parent=transcript1
```

#### BED格式

```
# 6列：chrom start end name score strand
Chr1    999     2000    gene1   .       +
```

#### Chain格式（基因组比对）

用于liftover或基因组版本转换

---

### B. 参考资料

- [NCBI datasets CLI文档](https://www.ncbi.nlm.nih.gov/datasets/docs/command-line-data-download/)
- [UCSC基因组工具](https://hgdownload.soe.ucsc.edu/downloads.html)
- [Ensembl Plants](https://plants.ensembl.org/)
- [Braker2使用指南](https://github.com/Gaius-Augustus/BRAKER)
- [EVM官方文档](https://evidencemodeler.github.io/)
