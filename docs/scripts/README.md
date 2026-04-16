# Scripts Documentation

本目录集中管理 `scripts/` 下所有脚本的详细使用说明。

## 索引

| 文档 | 脚本 | 功能简述 |
|------|------|---------|
| [add_taxid.md](add_taxid.md) | [`scripts/add_taxid.sh`](../../scripts/add_taxid.sh) | 使用 Taxonkit 批量为物种列表添加 Taxonomy ID |
| [calc_protein_properties.md](calc_protein_properties.md) | [`scripts/calc_protein_properties.py`](../../scripts/calc_protein_properties.py) | 批量计算蛋白序列理化性质（长度、等电点、分子量） |
| [calc_species_stats.md](calc_species_stats.md) | [`scripts/calc_species_stats.sh`](../../scripts/calc_species_stats.sh) | 按目/科/属分组统计物种数量 |
| [deduplicate_species_list.md](deduplicate_species_list.md) | [`scripts/deduplicate_species_list.sh`](../../scripts/deduplicate_species_list.sh) | 按物种名去重，每物种仅保留首条记录 |
| [download_genomes.md](download_genomes.md) | [`scripts/download_genomes.sh`](../../scripts/download_genomes.sh) | 从 NCBI 批量下载基因组数据（支持按目/科/属分批） |
| [make_bed_chrlist.md](make_bed_chrlist.md) | [`scripts/make_bed_chrlist.sh`](../../scripts/make_bed_chrlist.sh) | 从 GFF 生成 BED 文件和染色体列表 |
| [run_genetribe.md](run_genetribe.md) | [`scripts/run_genetribe.sh`](../../scripts/run_genetribe.sh) | 植物基因组同源基因鉴定流水线（faa统计+GFF转BED+GeneTribe+jcvi） |
| [run_genetribe_debug.md](run_genetribe_debug.md) | — | run_genetribe.sh 问题排查指南 |

## 推荐工作流

```
物种列表准备
  deduplicate_species_list.sh  →  add_taxid.sh
                                    ↓
基因组下载                       download_genomes.sh
                                    ↓
同源分析预处理                    run_genetribe.sh -m stat,faa,bed,chr
                                    ↓
同源基因鉴定                      run_genetribe.sh -m genetribe
                                    ↓
物种统计                          calc_species_stats.sh
```
