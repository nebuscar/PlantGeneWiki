# Changelog

## [Unreleased]

### Fixed

- **IMP Pipeline**: `--tax_scope Viridiplantae` → `--tax_scope auto`
  - 修复非绿色植物物种（如红藻Cyanidioschyzon_merolae）eggnog注释为空的问题
  - 文件: `scripts/imp/run_imp_pipeline.sh:371`
  - 日期: 2026/05/17

- **Homolog分析**: 统一使用genetribe core流程
  - 移除了fallback到genetribe RBH的逻辑
  - 统一走BLAST + BSR过滤(75) + 共线性分析(MCScan) + RBH完整流程
  - 文件: `scripts/imp/run_imp_pipeline.sh:571-580`
  - 日期: 2026/05/17

- **Genetribe pipeline**: 修复物种名点号处理
  - 用`+`替代`__`来sanitize点号，避免`._`被jcvi/tribemath误解释为变体分隔符
  - 移除了genetribe core失败时回退到手动RBH计算的脆弱逻辑
  - 文件: `scripts/imp/run_imp_pipeline.sh`
  - 日期: 2026/05/18