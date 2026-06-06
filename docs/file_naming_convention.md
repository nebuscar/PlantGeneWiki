# Genomic Data File Naming Convention

## Overview

Standardized naming for genomic data files in the database.

Format: `{species}.{data_type}.{format}`

---

## Data Types

### Sequence Files (FASTA)

| Suffix | Description | Content |
|--------|-------------|---------|
| `genomic.fa` | Genome sequence | Complete genome assembly |
| `gene.fa` | Gene sequences | DNA sequence of coding genes |
| `transcript.fa` | All transcripts | All transcript sequences |
| `longest.fa` | Longest transcripts | One longest transcript per gene |
| `cds.fa` | CDS sequences | Coding sequence (nucleotides) |
| `pep.fa` | Protein sequences | Translated amino acids |
| `promoter2k.fa` | Promoter sequences | 2kb upstream of TSS |

### Annotation Files (GFF3)

| Suffix | Description | Content |
|--------|-------------|---------|
| `genomic.gff` | Structural annotation | All transcripts (alternative splicing) |
| `longest.gff` | Longest transcript annotation | One transcript per gene |
| `interpro.gff` | InterPro domain annotation | Protein domain predictions |
| `eggnog.gff` | eggNOG orthology annotation | Ortholog groups |
| `repeat.gff` | Repeat annotation | Transposable elements |
| `miRNA.gff` | miRNA annotation | microRNA genes |

### Expression Data

| Suffix | Description | Content |
|--------|-------------|---------|
| `rnaseq.TPM.txt` | Expression matrix (TPM) | Transcript expression levels |
| `rnaseq.counts.txt` | Expression matrix (counts) | Raw read counts |

---

## Format Specification

- **Compression**: All files are gzip-compressed (`.gz`)
- **Species name**: lowercase with underscores (e.g., `abies_alba`)
- **Separator**: `.` (period)

---

## Complete File清单

```
abies_alba.genomic.fa.gz           # 基因组序列
abies_alba.genomic.gff.gz         # 完整结构注释（所有转录本）
abies_alba.gene.fa.gz             # 基因序列（DNA）
abies_alba.transcript.fa.gz       # 所有转录本序列
abies_alba.longest.fa.gz          # 最长转录本序列
abies_alba.cds.fa.gz              # CDS序列
abies_alba.pep.fa.gz              # 蛋白序列
abies_alba.promoter2k.fa.gz       # 启动子序列
abies_alba.interpro.gff.gz        # InterPro功能域
abies_alba.eggnog.gff.gz         # eggNOG同源注释
abies_alba.repeat.gff.gz         # 重复序列
abies_alba.miRNA.gff.gz          # miRNA注释
abies_alba.rnaseq.TPM.txt.gz      # RNA-seq TPM矩阵
abies_alba.rnaseq.counts.txt.gz  # RNA-seq counts矩阵
```

---

## Relationships

```
genomic.gff.gz
    │
    ├──[extract longest per gene]──→ longest.gff.gz
    │                                  └──→ longest.fa.gz
    │
    ├──[extract all transcripts]──→ transcript.fa.gz
    │
    └──[extract CDS coordinates]──→ cds.fa.gz
                                       └──→ pep.fa.gz (translation)

genomic.fa.gz
    └──[extract gene sequences]──→ gene.fa.gz

promoter2k.fa.gz
    └──[from genomic, 2kb upstream of TSS]

functional annotation:
    ├── interpro.gff.gz  (protein domains)
    ├── eggnog.gff.gz    (orthology)
    └── repeat.gff.gz    (repeats)
```

---

## Essential Files

Minimum required for basic analysis:

1. `*.genomic.fa.gz` - Genome sequence
2. `*.genomic.gff.gz` - Structural annotation
3. `*.pep.fa.gz` - Protein sequences (for BLAST search)