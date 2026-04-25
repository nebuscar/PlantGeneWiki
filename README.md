# PlantsDB - Plant Standard Genome Database

[English](README.md) | [中文](README-zh.md)

---

PlantsDB is a bioinformatics pipeline for building a standardized plant genome resource. It curates a species list, batch-downloads genome assemblies and annotations from NCBI, processes and standardizes the data, and enables comparative genomics analysis.

## Features

- **Batch genome downloading** from NCBI via the `datasets` CLI, with filtering by assembly level, source, version, date, and reference status
- **IMP database integration** — crawls species list from IMP website, batch-downloads 7 types of genome data (genome, annotation, gene, CDS, protein, promoter, TPM matrix)
- **Automatic file organization** — unzips downloads, selects the best assembly accession (RefSeq/GCF prioritized over GenBank/GCA), renames files to the standardized `{SpeciesName}_{type}.{ext}` format, and cleans up NCBI directory artifacts
- **Taxonomy ID enrichment** — adds NCBI taxonomy IDs to species lists using `taxonkit`
- **Species list deduplication** — keeps only the first occurrence of each species name
- **Species statistics** — counts species by Order, Family, or Genus with ranked output
- **Protein property computation** — calculates isoelectric point (pI), molecular weight (MW), and protein length; supports CSV/TSV/XLSX export
- **Comparative genomics** — GeneTribe integration for homologous gene identification, with BED files generated from GFF annotations via JCVI
- **Resumable downloads** — skips species with existing genome files; maintains detailed success/fail/skip logs
- **Download provenance** — generates `README_SOURCES.txt` per species documenting accession, data source, and download timestamp

## Prerequisites

**System tools:**

- Bash
- [NCBI datasets CLI](https://www.ncbi.nlm.nih.gov/datasets/docs/command-line-data-download/) — for downloading genome assemblies
- [taxonkit](https://github.com/shenwei356/taxonkit) — for taxonomy ID lookups
- `unzip`
- Standard Unix tools: `awk`, `sed`, `cut`, `find`

**Python 3 packages:**

```bash
pip install biopython pandas openpyxl playwright requests selenium
python -m playwright install chromium
```

**Optional tools:**

- [JCVI](https://github.com/tanghaibao/jcvi) (`pip install jcvi`) — for GFF-to-BED conversion
- [GeneTribe](https://github.com/GeneTribe/GeneTribe) — for homologous gene analysis
- `ssconvert` (from [gnumeric](https://github.com/GNOME/gnumeric)) — for XLSX export in `add_taxid.sh`

## Project Structure

```
plantsdb/
├── data/
│   └── meta/
│       ├── species_list.txt                  # Species list (7 columns)
│       ├── species_list_with_taxid.txt       # Species list with Taxonomy ID (8 columns)
│       ├── species_list_unique_with_taxid.txt # Deduplicated: 2010 unique species
│       └── species_list.xlsx                 # Excel version
├── downloads/                                # Downloaded genome data (git-ignored)
│   ├── genomes/                             # NCBI genomes
│   └── IMP/                                 # IMP database genomes
│       └── logs/
├── sample/                                   # Example species data (git-ignored)
├── docs/                                    # Detailed documentation
│   ├── README.md                            # Documentation index (English)
│   ├── README-zh.md                         # Documentation index (Chinese)
│   ├── scripts/                             # Script documentation
│   ├── pipelines/                           # Data pipelines
│   ├── guides/                              # Installation guides
│   └── SKILLS/                              # Skills handbook
├── scripts/
│   ├── download_genomes.sh                   # Batch download genomes from NCBI
│   ├── add_taxid.sh                          # Add Taxonomy IDs to species list
│   ├── deduplicate_species_list.sh           # Deduplicate species by name
│   ├── calc_species_stats.sh                 # Species count statistics
│   ├── make_bed_chrlist.sh                   # Generate BED + chr.list from GFF
│   ├── run_genetribe.sh                      # Run GeneTribe homologous gene analysis
│   ├── calc_protein_properties.py            # Compute protein pI, MW, length
│   └── batch_pi_mw.py                        # Alternative protein property calculator
├── scripts/imp_crawler/                      # IMP data crawler
│   ├── species_crawler.py                   # Species list crawler
│   ├── download_manager.py                  # Download manager
│   └── excel_writer.py                      # Excel report generator
├── tmp/                                      # Temporary files
└── Z_archive/                                # Archived files
```

## Quick Start

### 1. Add Taxonomy IDs

```bash
bash scripts/add_taxid.sh -i data/meta/species_list.txt -o data/meta/species_list_with_taxid.txt
```

### 2. Deduplicate species list

```bash
bash scripts/deduplicate_species_list.sh -i data/meta/species_list_with_taxid.txt \
  -o data/meta/species_list_unique_with_taxid.txt -s
```

### 3. Download genomes

**From NCBI:**

```bash
# By genus
bash scripts/download_genomes.sh genus Oryza

# All species
bash scripts/download_genomes.sh all

# Test single species
bash scripts/download_genomes.sh -t "Arabidopsis thaliana"
```

**From IMP database:**

```bash
# Crawl species list
python scripts/imp_crawler/species_crawler.py

# Batch download
./scripts/imp_download.sh

# Background download
nohup ./scripts/imp_download.sh > downloads/IMP/logs/download.log 2>&1 &
```

### 4. Run homologous gene analysis

```bash
bash scripts/run_genetribe.sh
```

## Usage

### Download genomes from NCBI

```bash
# By genus/family/order
bash scripts/download_genomes.sh genus Oryza
bash scripts/download_genomes.sh family Fabaceae
bash scripts/download_genomes.sh order Brassicales

# All species
bash scripts/download_genomes.sh all

# Test single species
bash scripts/download_genomes.sh -t "Arabidopsis thaliana"

# With filters
bash scripts/download_genomes.sh genus Oryza --reference --assembly-level chromosome

# List available groups
bash scripts/download_genomes.sh -l family

# Custom output directory
bash scripts/download_genomes.sh genus Oryza -o /path/to/output
```

### Generate BED and chr.list files

```bash
bash scripts/make_bed_chrlist.sh
```

### Calculate species statistics

```bash
bash scripts/calc_species_stats.sh -i species_list.txt -o stats_order.txt -g order
bash scripts/calc_species_stats.sh -i species_list.txt -o stats_family.txt -g family
bash scripts/calc_species_stats.sh -i species_list.txt -o stats_genus.txt -g genus
```

### Compute protein properties

```bash
python scripts/calc_protein_properties.py -i ./sample -f csv
python scripts/calc_protein_properties.py -i ./sample -o ./output -f xlsx
```

### Run GeneTribe

```bash
bash scripts/run_genetribe.sh
```

## Species List Format

The species list (`species_list.txt`) is a TSV file with the following columns:

| Column | Field | Example |
|--------|-------|---------|
| 1 | No. species | 1 |
| 2 | Species | Abeliophyllum distichum |
| 3 | Ploidy | diploid |
| 4 | Accession name | cultivar 'Wufu' |
| 5 | Order | Lamiales |
| 6 | Family | Oleaceae |
| 7 | Clade (Genus) | Abeliophyllum |

The `species_list_with_taxid.txt` adds a `Taxonomy ID` column between Species and Ploidy.

## Documentation

Detailed documentation:
- [`docs/`](docs/) - Documentation index
- [`docs/scripts/`](docs/scripts/README.md) - Script documentation
- [`docs/pipelines/`](docs/pipelines/) - Data pipelines
- [`docs/guides/`](docs/guides/) - Installation guides
- [`docs/SKILLS/`](docs/SKILLS/) - Skills handbook

## License

This project is provided as-is for research purposes.
