# PlantsDB AI Agent — 使用场景设计文档

## 数据概览

PlantsDB 目前收录以下数据类型，Agent 的对话问答与分析均基于这些数据：

| 数据类型 | 内容 | 来源 |
|---------|------|------|
| 基因结构 | 染色体坐标、链方向、基因 / 外显子长度 | 基因组注释 |
| 蛋白理化性质 | 等电点（pI）、分子量、氨基酸长度 | 序列计算 |
| 功能注释 | GO term、KEGG 通路、Pfam 结构域 | EggNOG-mapper |
| 属内同源关系 | BSR / RBH 一对一直系同源（GeneTribe） | GeneTribe |
| 序列文件 | 基因组（genome）、基因（gene）、编码序列（CDS）、蛋白（pep） | 基因组注释 |
| RNA-seq 表达量 | TPM 矩阵，覆盖 81 个物种，含部分处理实验样本 | 公共数据库整合 |
| 植物研究文献 | PDF 全文，支持语义检索与综述摘要 | 管理员上传 |

---

## 1. 用户权限分层

### 1.1 权限总览

| 功能 | 游客 (guest) | 普通用户 (user) | 管理员 (admin) |
|--------|:---:|:---:|:---:|
| 基因查询 / 注释检索 | ✅ | ✅ | ✅ |
| 同源分析 | ✅ | ✅ | ✅ |
| 表达量查询 | ✅ | ✅ | ✅ |
| GO/KEGG 富集分析 | ✅ | ✅ | ✅ |
| 序列相似性搜索（BLAST） | ❌ | ✅ | ✅ |
| 文献语义检索 | ✅ | ✅ | ✅ |
| 文献综述摘要 | ✅ | ✅ | ✅ |
| 序列文件下载 | ❌ | ✅ | ✅ |
| 分析结果导出 | ❌ | ✅ | ✅ |
| 会话历史回溯 | ❌ | ✅ | ✅ |
| 查看数据原始文件路径 | ❌ | ❌ | ✅ |
| 文献上传 / 管理 | ❌ | ❌ | ✅ |

### 1.2 数据来源引用

AI 的每条回答末尾都会附上**参考来源**，就像论文的引用列表。用户可以点击链接，直接跳转到数据库对应模块，亲自查询同一条数据，确认 AI 的回答有据可查、不是凭空生成。

**来源链接对照表**

| 数据类型 | 显示名称 | 点击跳转 |
|---------|---------|---------|
| 基因结构 / 蛋白理化 | 基因详情 | `/query/#gene` |
| 功能注释（GO/KEGG/Pfam） | 功能注释搜索 | `/query/#annotation` |
| 属内同源基因 | 同源基因 | `/query/#homolog` |
| RNA-seq 表达量 | 表达量 | `/query/#expression` |
| GO/KEGG 富集结果 | GO/KEGG 富集 | `/query/#enrichment` |
| 上传文献 | 文献检索 | `/query/#literature` |
| 序列文件 | 序列下载 | `/download/#sequence` |

**普通用户 / 游客**在回答末尾看到模块链接：

```
> **参考来源**
> [基因详情](/query/#gene) · [功能注释搜索](/query/#annotation)
```

**管理员**在模块链接基础上，还可展开查看服务器原始文件路径：

```
> **参考来源**
> [基因详情](/query/#gene) · [功能注释搜索](/query/#annotation)
> <details><summary>原始文件路径</summary>
> - `[structure]`    `/result/result_imp/species/Arabidopsis_thaliana/gene_structure.tsv`
> - `[annotation]`   `/result/result_imp/species/Arabidopsis_thaliana/Arabidopsis_thaliana.eggnog.tsv`
> </details>
```

---

## 2. 预设 Skills 设计

### 2.1 意图识别流程

```text
用户输入
   │
   ├─ 包含 DNA / 蛋白序列？
   │     └─ 是 → blast_search（需登录）
   │
   ├─ 匹配 Skill 触发词？
   │     ├─ 「分析/介绍某基因」「基因概览」          → gene_report
   │     ├─ 「找同源基因」「属内保守性」              → homolog_compare
   │     ├─ 「基因家族成员」「含某结构域」            → family_survey
   │     ├─ 「表达谱数据」「哪个组织最高」       → expression_profile
   │     ├─ 「富集分析」「GO/KEGG 通路」             → enrichment_report
   │     └─ 「获取/下载序列」「CDS」「pep 文件」      → sequence_fetch
   │           → 直接调用对应 Skill（单次工具调用，结果完整）
   │
   ├─ 未匹配 Skill → 分析所需数据维度
   │     ├─ 单维度 → 调用对应基础工具
   │     │   ├─ 仅坐标/注释     → get_gene_info
   │     │   ├─ 仅同源          → query_homolog
   │     │   ├─ 仅关键词搜索    → search_by_annotation
   │     │   ├─ 仅表达量        → expression_query
   │     │   ├─ 仅富集          → go_kegg_enrichment
   │     │   ├─ 仅文献检索      → search_literature
   │     │   └─ 仅综述摘要      → get_lit_summary
   │     └─ 多维度 → 并行调用多个基础工具
   │
   └─ 权限不足？ → 提示登录或联系管理员
```

### 2.2 Skills 速查表

| Skill | 触发提示词 |
|-------|-----------|
| `gene_report` | 「分析/介绍某基因」「基因概览」「给我一份基因报告」 |
| `homolog_compare` | 「找同源基因」「属内保守性」「跨物种保守性分析」 |
| `family_survey` | 「基因家族成员」「含某结构域的基因」「某通路的基因成员」 |
| `expression_profile` | 「表达谱数据」「哪个组织最高」「组织特异性」 |
| `enrichment_report` | 「富集分析」「GO/KEGG 通路」「这些基因参与哪些通路」 |
| `blast_search` | 「序列比对」「BLAST 搜索」「找与此序列相似的基因」 |
| `sequence_fetch` | 「获取/下载序列」「CDS」「pep 文件」「基因组 FASTA」 |

---

### 2.3 单基因综合报告（gene_report）

**用途**：单基因全景分析入口，一次调用整合结构、理化、注释、表达、文献五类信息，是研究任何基因的第一步。

**使用场景**
- 「分析基因 AT1G01010」「介绍一下这个基因」「全面了解基因 X」
- 「这个基因是做什么的」「基因 X 的基本信息」「给我一份基因报告」

**产出**
返回基因结构坐标（染色体位置、链方向、外显子数）、蛋白理化性质（pI / 分子量 / 氨基酸长度）、GO / KEGG / Pfam 功能注释、各组织 TPM 均值，以及相关文献列表（含作者、年份、DOI）。

---

### 2.4 属内同源比较分析（homolog_compare）

**用途**：检索一个属内所有物种的 1v1 直系同源基因（GeneTribe BSR/RBH），并对比各同源蛋白的理化性质，揭示基因在属内的保守性与分化程度。

**使用场景**
- 「FLC 在 Brassica 属各物种的同源基因是哪些」
- 「比较 Arabidopsis 属各物种 AT5G10140 的同源蛋白」
- 「这个基因在属内有多少物种有同源」「跨物种保守性分析」

**产出**
返回属内同源基因列表（物种、基因 ID、BSR 值、RBH 标记），各同源蛋白理化性质对比（pI / 分子量 / 氨基酸长度），以及参考基因的组织表达背景。

---

### 2.5 基因家族调查（family_survey）

**用途**：在指定物种中按注释条件（关键词 / Pfam / GO / KEGG）检索家族成员，统计规模，并输出功能富集和代表基因的表达概览。

**使用场景**
- 「拟南芥中所有 NAC 转录因子家族基因」
- 「大豆中含 FAD 结构域（PF00175）的基因有哪些」
- 「参与光合作用的基因家族」「某通路的基因成员」

**产出**
返回家族成员基因列表（含功能注释描述）、GO / KEGG 富集结果（按 BP / MF / CC / KEGG 各 top 3 展示），以及前 5 个代表基因的最高表达组织。

---

### 2.6 表达谱分析（expression_profile）

**用途**：为一组基因生成组织 / 条件维度的 TPM 表达矩阵，识别各基因的最高表达组织，支持可视化数据输出。

**使用场景**
- 「分析 AT1G01010、AT2G22840、AT3G18780 的表达谱」
- 「这批基因在哪些组织表达最高」「比较这几个基因的组织特异性」
- 「胁迫处理下这些基因的表达变化」

**产出**
返回基因 × 组织 TPM 均值矩阵、每个基因的最高表达组织标注；若包含处理样本，额外输出基因 × 处理条件的表达对比矩阵。

---

### 2.7 GO/KEGG 富集报告（enrichment_report）

**用途**：对基因列表做全套 GO（BP/MF/CC）+ KEGG 富集分析（Fisher 精确检验 + Benjamini-Hochberg FDR 校正），每类别返回 top 10 显著条目，用于解读基因集的功能方向。

**使用场景**
- 「对这批差异表达基因做 GO/KEGG 富集」「这些基因参与哪些通路」
- 「功能富集分析」「GO 分析」「KEGG 通路分析」
- 通常在 `family_survey` 之后用于子集的独立富集

**产出**
按 GO-BP / GO-MF / GO-CC / KEGG 四类分别输出显著富集条目（FDR 升序，每类 top 10），含条目名称、FDR 值、命中基因数 / 背景总数，并附 1–2 句生物学结论概括。

---

### 2.8 序列相似性搜索（blast_search）

**用途**：接受用户提交的核酸或蛋白序列，在指定物种的基因组 / 蛋白组中执行 BLAST 比对，返回相似性最高的命中基因列表，支持后续基因分析衔接。序列类型自动判断（ACGT 占比 ≥ 90% 用 blastn，否则用 blastp）。

**使用场景**
- 「用这段序列在拟南芥中做 BLAST 比对」「找与此序列相似的基因」
- 「这段蛋白序列在大豆里有没有同源」「帮我鉴定这个序列是什么基因」

**产出**
返回命中基因列表（物种、基因 ID、相似度、E-value、覆盖度），自动标注相似度 ≥ 80% 的强匹配，并推荐对 top 1 命中进行后续分析（gene_report / homolog_compare）。

---

### 2.9 序列获取（sequence_fetch）

**用途**：按物种和序列类型检索并返回 FASTA 格式序列，支持单基因查询和全物种批量下载，覆盖基因组、基因、CDS、蛋白四类文件。

**使用场景**
- 「给我 AT1G01010 的 CDS 序列」「获取这个基因的蛋白序列」
- 「下载拟南芥基因组 FASTA」「导出大豆所有基因的 pep 文件」

**产出**
单基因直接在对话中展示 FASTA 序列；多基因（≤ 100 条）合并后提供下载链接；超过 100 条或基因组文件仅返回服务器端下载链接。

---

## 3. 对话场景与输入输出示例

> 场景按复杂程度由低到高排列：权限提示 → 基础单点查询 → 多工具并行 → Skill 链式调用 → 跨维度联动分析。

---

### 场景 1：访问受限提示

> 仅在未登录用户访问需要登录的功能时触发（如 BLAST 搜索、序列下载、结果导出）。

**输入**
```
帮我把这批差异基因的富集分析结果导出为 Excel
```

**输出**
```
分析结果导出功能需要登录后使用。

请点击右上角登录，注册账户后可使用：
- 序列相似性搜索（BLAST）
- 序列文件下载
- 分析结果导出（CSV / TSV / XLSX / PNG / PDF 等多种格式）
- 会话历史保存与回溯
```

---

### 场景 2：基因查询

**输入**
```
AT1G01010 是什么基因？
```

**意图** → `get_gene_info`（单工具）

**输出**
```
AT1G01010（Arabidopsis thaliana）是 NAC domain-containing protein 1（NAC001）。

**基因结构**
- 染色体：Chr1，3631–5899 bp，正链
- 基因长度：2269 bp，5 个外显子

**蛋白理化性质**
- 氨基酸长度：429 aa
- 分子量：48.3 kDa
- 等电点（pI）：6.21

**功能注释**
- Pfam：PF01849（NAC 结构域）
- GO：GO:0003700（转录因子活性）、GO:0006355（转录调控）
- KEGG：—

> **参考来源**
> [基因详情](/query/#gene) · [功能注释搜索](/query/#annotation)
```

> ⚙️ **管理员额外可见**：参考来源下方展开原始文件路径（gene_structure.tsv / protein_properties.tsv / eggnog.tsv）

---

### 场景 3：单基因表达模式

**输入**
```
AT1G01010 在拟南芥各组织的表达量是多少？
```

**意图** → `expression_query`

**输出**
```
**AT1G01010 组织表达量（Arabidopsis thaliana）**

| 组织 | 均值 TPM | 样本数 |
|------|---------|-------|
| 花   | 48.2    | 3     |
| 根   | 24.8    | 9     |
| 叶片 | 12.1    | 6     |
| 茎   | 8.7     | 3     |
| 角果 | 1.9     | 3     |

花和根中相对高表达，具有一定组织偏好性。

> **参考来源**
> [表达量](/query/#expression)
```

**用户追问**
```
在盐胁迫处理下表达量有变化吗？
```

**输出**
```
**AT1G01010 盐胁迫处理条件对比**

| 条件           | 均值 TPM | 对照 TPM | 变化倍数 |
|----------------|---------|---------|---------|
| NaCl 150mM 6h  | 89.4    | 12.1    | ↑ 7.4×  |
| NaCl 150mM 24h | 67.3    | 12.1    | ↑ 5.6×  |
| 对照（mock）   | 12.1    | —       | —       |

盐胁迫下显著上调，提示参与盐胁迫响应的转录调控。

📊 [下载条件表达量 CSV]

> **参考来源**
> [表达量](/query/#expression)
```

---

### 场景 4：序列获取

**输入**
```
获取 AT1G01010、AT2G29980、AT3G18780 的 CDS 序列
```

**意图** → `sequence_fetch` Skill

**输出**
```
**CDS 序列（3 个基因，Arabidopsis thaliana）**

>AT1G01010 | CDS | 1290 bp
ATGAGTGAGAGCAGCGATCCAGAAAATCAATTTACGGAGGAGTTTAG...

>AT2G29980 | CDS | 1152 bp
ATGGGGCTTATAATTGTAATTATGTCTTGTGTGATGCCTTTAGATAAG...

>AT3G18780 | CDS | 876 bp
ATGGAGCTTCTTAAAGATAAATCACAGACCAATATGAGTGGACAACAA...

📥 [下载 FASTA 文件]

> **参考来源**
> [序列下载](/download/#sequence)
```

---

### 场景 5：多基因功能对比

**输入**
```
AT1G01010 和 AT1G01020 功能上有什么区别？
```

**意图** → `get_gene_info`（两个基因并行查询）

**输出**
```
**AT1G01010 vs AT1G01020 功能对比**

| 维度         | AT1G01010             | AT1G01020             |
|------------|----------------------|----------------------|
| Pfam 结构域 | NAC domain (PF02365) | WRKY domain (PF03106) |
| GO 功能     | 转录调控              | 防御响应              |
| KEGG        | 植物激素信号通路       | 植物–病原互作         |
| pI          | 6.52                 | 8.31                  |
| 分子量      | 41.8 kDa             | 36.2 kDa              |

两者均为转录因子，调控通路不同：AT1G01010 参与激素信号，AT1G01020 偏向免疫防御。
AT1G01020 pI 偏碱性（8.31），蛋白电荷性质差异明显。

> **参考来源**
> [基因详情](/query/#gene) · [功能注释搜索](/query/#annotation)
```

---

### 场景 6：文献问答

**输入**
```
FLC 基因在开花时间调控中的研究进展如何？
```

**意图** → `search_literature` + `get_lit_summary`（并行）

**输出**
```
**FLC 研究进展（基于已上传文献）**

FLC（FLOWERING LOCUS C）编码 MADS-box 转录因子，通过抑制 FT 和 SOC1
的表达来阻止植物提前开花，是春化途径的核心调控因子。

**主要研究结论**
- 春化处理通过 PRC2 介导的 H3K27me3 修饰使 FLC 稳定沉默（Bastow 2004, DOI:10.xxxx）
- FLC 自然变异影响拟南芥生态型的开花时间适应性（Shindo 2006, DOI:10.xxxx）
- CRISPR 编辑 BnaFLC 可有效调控油菜开花期（Wang 2022, DOI:10.xxxx）

[仅基于已上传文献，不代表全部研究进展]

> **参考来源**
> [文献检索](/query/#literature)
```

---

### 场景 7：基因表达谱分析

**输入**
```
分析 AT1G01010、AT2G22840、AT3G18780 在各组织的表达谱，可视化
```

**意图** → `expression_profile` Skill

**输出**
```
**表达谱分析（3 个基因，组织模式）**

| 基因       | 根   | 叶   | 花   | 种子 | 茎  | 最高表达组织      |
|------------|------|------|------|------|-----|-----------------|
| AT1G01010  | 12.3 | 45.6 | 8.1  | 3.2  | 6.7 | 叶（45.6 TPM）  |
| AT2G22840  | 33.1 | 12.4 | 56.7 | 89.3 | 4.1 | 种子（89.3 TPM）|
| AT3G18780  | 8.7  | 7.2  | 91.4 | 5.6  | 3.3 | 花（91.4 TPM）  |

**结论**：三个基因表达模式各异，AT3G18780 花特异性最强，AT2G22840 在种子中高表达，AT1G01010 呈叶片偏好性表达。

📊 [下载 PNG] [下载 PDF] [下载数据 CSV]

> **参考来源**
> [表达量](/query/#expression)
```

---

### 场景 8：序列相似性搜索（BLAST）

**输入**
```
MWRWLIFWLALVVAISGLTTFISTHCVMPLDKISDDISGQNQFTEEFRLALQFPAVR...
用这段蛋白序列在 Arabidopsis thaliana 和 Glycine max 中做 BLAST 比对
```

**意图** → `blast_search` Skill

**输出**
```
**BLAST 搜索结果**
序列类型：protein（blastp）· 查询长度：383 aa · 搜索物种：A. thaliana、G. max

| 物种          | 基因 ID          | 相似度 | E-value   | 覆盖度 |
|--------------|-----------------|-------|----------|-------|
| A. thaliana  | AT2G29980       | 97.4% | 2.1e-198 | 100%  |
| G. max       | Glyma.10G048200 | 84.1% | 3.7e-152 | 98%   |
| A. thaliana  | AT3G12120       | 42.3% | 8.2e-41  | 76%   |
| G. max       | Glyma.19G211000 | 38.7% | 2.4e-35  | 71%   |

最优命中：**AT2G29980**（相似度 97.4%，E-value 2.1e-198），覆盖度 100%，为强匹配。

可进一步分析：
→ 「分析 AT2G29980 的基因信息」→ `gene_report`
→ 「AT2G29980 在 Arabidopsis 属内的同源分布」→ `homolog_compare`

📊 [下载比对结果 CSV]

> **参考来源**
> [基因详情](/query/#gene)
```

---

### 场景 9：属内同源基因全景

**输入**
```
FLC 在 Brassica 属各物种的同源基因是哪些？
```

**意图** → `homolog_compare` Skill

**输出**
```
**Brassica 属 FLC 同源基因（参考物种：napus · BnaFLC）**

| 物种      | 同源基因 ID   | BSR  |
|-----------|--------------|------|
| rapa      | BrFLC1       | 0.91 |
| oleracea  | BoFLC        | 0.88 |
| juncea    | BjuFLC       | 0.85 |
| carinata  | BcaFLC       | 0.83 |
| nigra     | BniFLC       | 0.79 |

属内 5/6 个物种检测到直系同源，BSR 均 > 0.75，FLC 在 Brassica 属内较为保守。

📊 [下载同源列表 CSV] [下载理化对比表 PDF]

> **参考来源**
> [同源基因](/query/#homolog) · [基因详情](/query/#gene)
```

---

### 场景 10：跨物种蛋白理化对比

**输入**
```
比较 Arabidopsis 属各物种 FLC 同源蛋白的 pI 和分子量
```

**意图** → `homolog_compare` Skill（侧重蛋白性质对比）

**输出**
```
**Arabidopsis 属 FLC 同源蛋白理化性质对比**

| 物种      | 基因 ID     | pI   | 分子量 (kDa) | 长度 (aa) |
|-----------|------------|------|-------------|----------|
| thaliana  | AT5G10140  | 8.82 | 22.5        | 196      |
| lyrata    | AlyrFLC    | 8.74 | 22.3        | 194      |
| halleri   | AhalFLC    | 9.12 | 22.8        | 198      |

pI 范围 8.74–9.12，分子量差异 < 0.5 kDa，属内理化性质高度保守。

📊 [下载对比表 CSV] [下载对比图 PNG]

> **参考来源**
> [同源基因](/query/#homolog) · [基因详情](/query/#gene)
```

---

### 场景 11：GO/KEGG 富集分析

**输入**
```
对这批差异表达基因做 GO/KEGG 富集：AT1G01010, AT2G22840, AT3G18780, AT4G16780, AT5G20240
```

**意图** → `enrichment_report` Skill

**输出**
```
**GO/KEGG 富集分析（5 个基因，Arabidopsis thaliana）**
共 12 个显著富集条目（FDR < 0.05）

**GO 生物过程（BP）** ⭐ 高度显著
| Term       | 名称                       | FDR    | 基因数/背景 |
|------------|---------------------------|--------|-----------|
| GO:0009908 | flower development         | 0.0021 | 3/280     |
| GO:0006355 | transcription regulation   | 0.0087 | 4/1203    |
| GO:0009414 | drought stress response    | 0.0312 | 2/98      |

**GO 分子功能（MF）**
| Term       | 名称                          | FDR    | 基因数/背景 |
|------------|------------------------------|--------|-----------|
| GO:0003700 | transcription factor activity | 0.0034 | 3/412     |

**KEGG 通路**
| KO      | 通路                                  | FDR    | 基因数/背景 |
|---------|--------------------------------------|--------|-----------|
| ko04075 | Plant hormone signal transduction    | 0.0156 | 2/87      |

**结论**：基因集在花发育和转录调控方向高度富集，提示可能参与开花相关的转录调控网络。

📊 [下载气泡图 PNG] [下载结果 PDF] [下载完整表格 CSV]

> **参考来源**
> [GO/KEGG 富集](/query/#enrichment) · [功能注释搜索](/query/#annotation)
```

---

### 场景 12：基因家族调查

**输入**
```
拟南芥中所有 NAC 转录因子家族基因有哪些？
```

**意图** → `family_survey` Skill

**输出**
```
**NAC 转录因子家族（Arabidopsis thaliana）**
共检索到 109 个家族成员。

**代表基因（前 10）**
AT1G01010 · AT1G52890 · AT2G17040 · AT3G15510 · AT3G29035 ...

**功能富集 Top 通路**
- GO:0009908 flower development（FDR 1.2e-8）
- GO:0003700 transcription factor activity（FDR 3.4e-7）
- GO:0006355 transcription regulation（FDR 8.1e-7）

**表达概览**（前 5 个基因，最高表达组织）
AT1G01010 叶最高 · AT1G52890 种子最高 · AT2G17040 根最高 ...

📊 [下载成员列表 CSV] [下载富集气泡图 PNG]

> **参考来源**
> [功能注释搜索](/query/#annotation) · [GO/KEGG 富集](/query/#enrichment) · [表达量](/query/#expression)
```

---

### 场景 13：文献结论与数据库交叉验证

**输入**
```
文献说 FLC 在春化前叶片中高表达，我们数据库里能验证吗？
```

**意图** → `search_literature` → `expression_query`（顺序：先找文献依据，再查本库）

**输出**
```
**文献 vs 本库数据对比**

文献依据（Bastow 2004）：拟南芥叶片 FLC TPM ≈ 120（春化前），根 ≈ 18

本库数据（Brassica napus BnaFLC）：
| 组织 | 均值 TPM | 与文献规律 |
|------|---------|-----------|
| 叶片 | 98.4    | ✅ 一致   |
| 茎   | 34.2    | ✅ 一致   |
| 根   | 15.7    | ✅ 一致   |
| 花   | 3.1     | ✅ 一致   |

本库油菜数据支持 FLC 叶片优势表达的结论，与拟南芥规律一致。

📊 [下载表达量 CSV]

> **参考来源**
> [文献检索](/query/#literature) · [表达量](/query/#expression)
```

---

### 场景 14：开放知识问答（文献 + 数据联动）

**输入**
```
NAC 转录因子在植物抗旱中有什么作用？
```

**意图** → `search_literature` + `search_by_annotation`（并行）

**输出**
```
**NAC 转录因子与植物抗旱**

**文献综述**
NAC 家族通过 ABA 信号通路调控气孔开闭和渗透胁迫响应。
ANAC055 和 ANAC019 在干旱处理下显著上调，过表达可增强耐旱性
（Zhang 2022, DOI:10.xxxx）。

**本库数据**
拟南芥含 NAC 结构域基因 105 个，其中 12 个具有
GO:0009414（水分胁迫响应）注释。

可进一步分析：
→ 「查看这 12 个基因的表达谱」→ expression_profile Skill
→ 「对这批基因做富集分析」→ enrichment_report Skill

> **参考来源**
> [文献检索](/query/#literature) · [功能注释搜索](/query/#annotation)
```

---

## 4. 分析结果导出设计

### 4.1 支持格式

导出功能支持多种常用文件格式，不按分析功能单独限定，所有常规后缀均可使用：

| 格式 | 说明 |
|------|------|
| CSV | 逗号分隔表格，适合进一步脚本处理 |
| TSV | 制表符分隔表格，适合导入 R / Excel / 其他工具 |
| TXT | 纯文本，适合基因列表或序列输出 |
| Excel | 电子表格，适合直接查看与编辑 |
| PNG | 图表图像，适合报告插图 |
| PDF | 综合报告，含图表与表格 |

### 4.2 导出触发方式

- 对话中自动附加导出按钮（Chainlit Action Button），显示常用格式图标供用户点击
- 用户明确要求：「导出为 Excel」「下载 TSV」→ 意图识别后生成对应格式

---
