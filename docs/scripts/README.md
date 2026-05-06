# Scripts Documentation

本目录集中管理 `scripts/` 下所有脚本的详细使用说明。

## 目录结构

```
scripts/
├── imp/                        # IMP 数据库流程
│   ├── run_imp_pipeline.sh     # IMP 主流程脚本（structure/sequence/properties/eggnog/homolog）
│   ├── imp_download.sh         # IMP 数据下载
│   └── imp_crawler/            # IMP 网站爬虫
│       ├── species_crawler.py  # 爬取物种列表
│       ├── download_manager.py # 下载管理器
│       ├── api_discover.py     # API 端点发现
│       └── excel_writer.py     # 生成 xlsx 报表
│
└── ncbi/                       # NCBI 数据库流程
    ├── annotation/             # 功能注释模块
    │   ├── calc_protein_properties.py   # 蛋白理化性质计算
    │   ├── extract_cds_pep.py           # CDS/PEP序列提取
    │   ├── extract_genomic_features.py  # 基因组结构信息提取
    │   ├── generate_mapping.py          # 基因ID-蛋白ID映射
    │   ├── integrate_outputs.py         # 整合各模块输出
    │   └── Management_system.py         # Flask管理界面
    ├── download/
    │   └── download_genomes.sh          # NCBI基因组下载
    ├── homolog/
    │   ├── run_eggnog_nested.sh         # eggNOG功能注释
    │   └── run_genetribe.sh             # 同源基因鉴定
    └── preprocess/
        ├── add_taxid.sh                 # 添加TaxID
        ├── check_missing.sh             # 检查缺失文件
        ├── clean_species_spaces.sh      # 清理物种名空格
        └── deduplicate_species_list.sh  # 去重物种列表
```

## 索引

### IMP 脚本

| 文档 | 脚本 | 功能简述 |
|------|------|---------|
| [imp_download.md](imp_download.md) | `imp/imp_download.sh` | 从 IMP 数据库批量下载植物基因组数据 |

### NCBI 脚本

| 文档 | 脚本 | 功能简述 |
|------|------|---------|
| [add_taxid.md](add_taxid.md) | `ncbi/preprocess/add_taxid.sh` | 使用 Taxonkit 批量为物种列表添加 Taxonomy ID |
| [calc_protein_properties.md](calc_protein_properties.md) | `ncbi/annotation/calc_protein_properties.py` | 批量计算蛋白序列理化性质 |
| [deduplicate_species_list.md](deduplicate_species_list.md) | `ncbi/preprocess/deduplicate_species_list.sh` | 按物种名去重 |
| [download_genomes.md](download_genomes.md) | `ncbi/download/download_genomes.sh` | 从 NCBI 批量下载基因组数据 |
| [run_genetribe.md](run_genetribe.md) | `ncbi/homolog/run_genetribe.sh` | 植物基因组同源基因鉴定流水线 |

## 补充文档

| 文档 | 说明 |
|------|------|
| [run_genetribe_debug.md](run_genetribe_debug.md) | run_genetribe.sh 问题排查指南 |
| [run_genetribe_report.md](run_genetribe_report.md) | run_genetribe.sh 测试报告与全量数据耗时推演 |

## 相关目录

- [guides/](../guides/) - 安装指南
- [submission/](../submission/) - 数据提交规范
- [imp_pipeline_plan.md](../imp_pipeline_plan.md) - IMP 流程计划与进度
