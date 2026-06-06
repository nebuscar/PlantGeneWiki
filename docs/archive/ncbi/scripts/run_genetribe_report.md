# run_genetribe.sh 测试报告

## 测试环境

| 项目 | 配置 |
|------|------|
| CPU | 104 核 |
| 内存 | 1 TB |
| GeneTribe 版本 | v1.2.1 |
| BLAST 线程数 (-t) | 36（默认） |
| jcvi CPU 数 (-p) | 0（不限制） |

## 测试数据

- 输入目录: `./sample`
- 有 .faa 的属: Acer (2 物种), Dendrobium (2 物种)
- Aegilops 仅 1 物种有 .faa，跳过

## 测试结果

**总耗时: 0h 44m 33s (2673s)**

| 属 | 参考物种 | 参考物种序列数 | 待比对物种 | 属耗时 |
|----|---------|--------------|-----------|--------|
| Acer | Acer_saccharum | 38,583 | Acer_negundo | 1811s (30m 11s) |
| Dendrobium | Dendrobium_nobile | 29,043 | Dendrobium_chrysotoxum | 861s (14m 21s) |

### 各步骤时间分布

| 步骤 | 说明 | 耗时占比 |
|------|------|---------|
| stat | 序列统计 + 选参考物种 | <1% |
| faa | 统一蛋白ID (protein_id → locus_tag) | ~1% |
| bed | GFF 转 BED | ~1% |
| chr | 生成 chrlist | <1% |
| genetribe | BLAST + jcvi 共线性分析 | **>90%** |
| merge | 合并 RBH 映射表 | ~1% |

### 输出文件

```
result/homolog/
├── Acer/
│   ├── Acer_RBH_merged.xlsx
│   ├── genetribe_result/Acer_saccharum_vs_Acer_negundo/
│   │   ├── Acer_saccharum_Acer_negundo.RBH
│   │   ├── Acer_saccharum_Acer_negundo.one2one
│   │   └── ...
│   └── ...
├── Dendrobium/
│   ├── Dendrobium_RBH_merged.xlsx
│   └── ...
└── seqkit_faa_stats.txt
```

---

## 全量数据推演

### 数据概况

- `/DATA/data2/downloads/NCBI/` 下共 **881** 个物种目录
- 其中 **98** 个物种有 .faa 文件，分布在 **69** 个属
- 可做属内同源比对的属（≥2 物种有 .faa）: **18** 个属
- 51 个单物种属将被自动跳过

### 多物种属分布

| 物种数 | 属数 | 属名 |
|--------|------|------|
| 8 | 1 | Gossypium |
| 4 | 2 | Arachis, Arabidopsis |
| 3 | 1 | Acer |
| 2 | 14 | Glycine, Fragaria, Euphorbia, Eucalyptus, Dipteronia, Dioscorea, Dendrobium, Cucurbita, Coffea, Camellia, Brassica, Anisodus, Amaranthus, Actinidia |
| 1 | 51 | （单物种属，无法做属内比对） |

### 耗时估算

**测算依据**: 2 物种属（~30K 蛋白 vs ~29K 蛋白）耗时约 861-1811s，取决于序列数量。

GeneTribe 耗时与物种蛋白序列数量正相关，主要受 BLAST 和 jcvi 共线性分析影响：
- 2 物种属（小基因组 ~30K seqs）: ~15 min
- 2 物种属（大基因组 ~40K seqs）: ~30 min
- 多物种属的耗时可按比对对数估算（参考物种与每个非参考物种各做一次比对）

| 属 | 物种数 | 比对对数 | 单对预估耗时 | 属预估总耗时 |
|----|--------|---------|------------|------------|
| Gossypium | 8 | 7 | ~25 min | ~3 h |
| Arachis | 4 | 3 | ~20 min | ~1 h |
| Arabidopsis | 4 | 3 | ~15 min | ~45 min |
| Acer | 3 | 2 | ~30 min | ~1 h |
| 其余14属(2物种) | 2 | 1 | ~15-30 min | ~15-30 min/属 |

### 并行方案

由于各属之间独立，可并行处理多个属：

| 方案 | 参数 | 并行度 | 预估总耗时 |
|------|------|--------|-----------|
| 串行 | `-j 1 -t 36` | 1 属 | ~11-12 h |
| 2 路并行 | `-j 2 -t 36` | 2 属 | ~6 h |
| 3 路并行 | `-j 3 -t 18` | 3 属 | ~3-4 h |
| 4 路并行 | `-j 4 -t 12` | 4 属 | ~2-3 h |

> 建议：`-j × -t` 不超过服务器总核数（104 核），保留部分核心给系统。

### 全量运行命令

```bash
# 3 属并行，每属 18 线程（推荐）
nohup bash scripts/run_genetribe.sh \
    -i /DATA/data2/downloads/NCBI \
    -m all -g -j 3 -t 18 \
    > result/homolog/run.log 2>&1 &
```

### 注意事项

1. 51 个单物种属无法做属内同源比对，将被自动跳过
2. Gossypium (8 物种) 是最耗时的属，7 对比对可能需 3 小时
3. jcvi 共线性分析在某些大基因组组合下可能卡住，建议设置 `-p 4` 限制 jcvi CPU
4. 磁盘空间: 每对比对产生 ~1-2 GB 中间文件，Gossypium 属约需 10-15 GB
5. 18 个属总计中间文件约 30-50 GB，完成后可保留 `genetribe_output/` 或手动清理
