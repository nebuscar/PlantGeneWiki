# PlantsDB AI Agent 设计规范

> 面向开发者，记录 Agent 模块的架构决策、用户场景与工具接口规范。
> 最后更新：2026-05-08

---

## 一、架构概览

### 设计原则

- **单 Orchestrator + 工具调用**：一个 LLM 实例持有所有工具，通过 tool_use 原生路由，无多 Agent 跳转
- **意图识别由 Orchestrator 负责**：工具层只接收参数并执行，不包含任何业务判断逻辑
- **文献人工上传**：不做自动抓取，管理员批量上传后系统自动处理、分类、预生成摘要

```
用户输入（自然语言）
        │
        ▼
┌───────────────────────────────────────────────────────┐
│                     Orchestrator                       │
│  · 理解用户意图                                        │
│  · 决定调用哪些工具及参数（含模式选择、过滤条件）        │
│  · 整合工具返回值，生成最终回答                         │
│  · 维护会话上下文（最近 20 条消息滑动窗口）              │
└──────────────────────────┬────────────────────────────┘
                           │ 选择性调用（可并行）
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ── DB 工具 ──      ── 文献工具 ──     ── 分析工具 ──
   get_gene_info      search_literature   go_kegg_enrichment
   query_homolog      get_lit_summary     expression_query
   search_by_anno
   compare_props
```

### 用户权限分层

```
guest（游客）              user（注册用户）           admin（管理员）
──────────────             ──────────────             ──────────────
✓ 知识问答（限次）         ✓ 全部聊天功能             ✓ 全部用户功能
✓ 基因信息查询             ✓ 会话历史保存             ✓ 文献上传 / 管理
✗ 会话历史保存             ✓ 文献问答（含引用）        ✓ 标签管理 / 修正
✗ 文献内容访问             ✗ 文献上传                 ✓ 用户管理
✗ 导出功能                 ✗ 用户管理                 ✓ 处理状态监控
```

---

## 二、用户场景

### 场景 1：单基因全景查询

**触发**：「告诉我这个基因」「查一下 XX」「这个基因是做什么的」

```
用户：告诉我拟南芥 AT1G01010 的基本信息

Orchestrator 调用（并行）：
  get_gene_info(species="Arabidopsis_thaliana", gene_id="AT1G01010")
  query_homolog(genus="Arabidopsis", gene_id="AT1G01010")
  search_literature(query="AT1G01010 NAC transcription factor")

输出：
  基因概况    AT1G01010 · Chr1:3631-5899 · 正链 · 2268 bp
  蛋白性质    pI 6.52 · MW 41.8 kDa · 383 aa
  功能注释    NAC 结构域转录因子 · GO:0003700 · PF02365
  同属同源    Arabidopsis 属 8 个物种均有直系同源基因
  文献支撑    3 篇文献，主要研究叶片发育与衰老调控
```

---

### 场景 2：基因家族检索

**触发**：「含 XX 结构域的基因」「XX 基因家族有哪些成员」「参与 XX 通路的基因」

```
用户：找大豆中所有含 FAD 结构域的基因，主要功能是什么？

Orchestrator 先做 term 扩展：
  pfam_ids=["PF00175"]，keywords=["fatty acid desaturase", "FAD binding"]

Orchestrator 调用：
  search_by_annotation(species="Glycine_max",
                       pfam_ids=["PF00175"],
                       keywords=["fatty acid desaturase"])

输出：
  共 23 个基因，分布于 12 条染色体
  主要功能：脂肪酸去饱和、氧化还原反应
  [基因列表 + 各基因 GO/KEGG 摘要]
```

---

### 场景 3：同源基因全景（属内）

**触发**：「XX 基因在这个属里各物种有没有」「找同源基因」「哪些物种有对应基因」

```
用户：FAD2 在 Aegilops 属各物种的同源基因是哪些？

Orchestrator 调用：
  query_homolog(genus="Aegilops", gene_id="AeShar_FAD2")

输出：
  参考物种    sharonensis · AeShar_g12345
  ─────────────────────────────────────
  bicornis    AeBicor_g67890   BSR 0.94
  tauschii    AeTausc_g11111   BSR 0.91
  speltoides  AeSpelt_g22222   BSR 0.87
  longissima  AeLong_g33333    BSR 0.89
  searsii     AeSear_g44444    BSR 0.85
  （共 6 个物种）
```

---

### 场景 4：跨物种理化性质对比

**触发**：「比较这几个物种的」「哪个物种 pI 最高」「蛋白质大小差异」

```
用户：比较 Arabidopsis 属各物种 FAD2 同源蛋白的 pI 和分子量

Orchestrator 调用（顺序）：
  ① query_homolog(genus="Arabidopsis", gene_id="AT2G29980")   # 先拿同源列表
  ② compare_protein_props(targets=[...])                      # 再比较理化

输出：
  物种           pI      MW(kDa)   长度(aa)
  ─────────────────────────────────────────
  thaliana      6.52    41.8      383
  lyrata        6.48    41.6      381
  halleri       6.71    42.1      385
  各物种 pI 差异 < 0.3，提示该蛋白在属内高度保守
```

---

### 场景 5：文献问答

**触发**：「文献里怎么说」「研究现状如何」「有没有相关研究」「做过什么实验」

```
用户：FAD2 基因在油脂合成中的功能研究到什么程度了？

Orchestrator 调用（并行）：
  search_literature(query="FAD2 fatty acid desaturation function mechanism")
  get_lit_summary(topic="FAD2")

输出（标注来源）：
  · FAD2 编码 ω-6 脂肪酸脱氢酶，催化油酸→亚油酸（Smith 2020, DOI:...）
  · fad2 突变体种子油酸含量升高 40%（Liu 2021, DOI:...）
  · CRISPR 编辑 FAD2 已在大豆实现高油酸育种（Zhang 2023, DOI:...）

  [仅基于已上传文献，不代表全部研究进展]
```

---

### 场景 6：文献与数据交叉验证

**触发**：「文献说的在我们数据里能看到吗」「能验证吗」「数据库里有没有支撑」

```
用户：这篇文章说 FAD2 在种子中高表达，我们数据库里能看到这个规律吗？

Orchestrator 判断：用户想核对文献结论 vs 本库数据
  → 需要先找文献原始依据，再查对应物种表达量

Orchestrator 调用（顺序）：
  ① search_literature(query="FAD2 seed high expression")
  ② expression_query(species="Arachis_hypogaea",
                     gene_ids=["AhFAD2"],
                     mode="tissue",
                     include_treatment=False)    # 只看正常组织

输出：
  文献依据（Liu 2021）：拟南芥种子 FAD2 TPM ≈ 180，叶片 ≈ 12
  本库数据（花生 AhFAD2）：
    种子     TPM 156.3   ✓ 与文献规律一致
    叶片      TPM   8.7
    根        TPM   3.2
  结论：本库花生数据支持 FAD2 种子特异性表达的结论
```

---

### 场景 7：基因列表功能富集

**触发**：「这批基因是干什么的」「富集分析」「功能方向」「共同功能」

```
用户：我有 20 个差异表达基因，帮我分析主要功能方向

Orchestrator 调用：
  go_kegg_enrichment(species="Arabidopsis_thaliana",
                     gene_ids=["AT1G01010", ...],
                     types=["go_bp", "kegg"])

输出：
  GO 富集（p < 0.05）：
    脂肪酸生物合成   GO:0006631   8/20 基因   富集倍数 4.2
    非生物胁迫响应   GO:0006950   6/20 基因   富集倍数 3.1
  KEGG 通路：
    脂肪酸代谢       ath01212     命中 7 个基因
  主要功能方向：脂质代谢 + 非生物胁迫响应
```

---

### 场景 8：表达模式查询

**触发**：「在哪个组织表达」「表达量多少」「组织特异性」「哪里最高表达」

```
用户：AT1G01010 在拟南芥各组织的表达量？

Orchestrator 判断：普通组织分布查询 → mode="tissue", include_treatment=False

Orchestrator 调用：
  expression_query(species="Arabidopsis_thaliana",
                   gene_ids=["AT1G01010"],
                   mode="tissue",
                   include_treatment=False)

输出：
  组织       均值 TPM   样本数
  ───────────────────────────
  花          48.2       3
  叶片        12.1       6
  根          24.8       9
  茎           8.7       3
  角果         1.9       3
  → 花和根中相对高表达

追问：「在盐胁迫处理下呢？」
Orchestrator 判断：想看处理条件对比 → mode="condition", include_treatment=True
  expression_query(..., mode="condition", include_treatment=True)
```

---

### 场景 9：多基因对比

**触发**：「这几个基因有什么区别」「功能相同吗」「比较一下」

```
用户：AT1G01010 和 AT1G01020 功能上有什么区别？

Orchestrator 调用（并行）：
  get_gene_info(species="Arabidopsis_thaliana", gene_id="AT1G01010")
  get_gene_info(species="Arabidopsis_thaliana", gene_id="AT1G01020")

输出：
  对比维度     AT1G01010           AT1G01020
  ──────────────────────────────────────────
  Pfam 结构域  NAC domain          WRKY domain
  GO 功能      转录调控             防御响应
  KEGG 通路    植物激素信号          植物-病原互作
  pI           6.52                8.31
  同源分布     属内 8/8 物种        属内 5/8 物种
  → 均为转录因子，调控通路不同；AT1G01020 跨物种保守性较低
```

---

### 场景 10：开放知识问答

**触发**：任意植物基因相关问题

```
用户：NAC 转录因子在植物抗旱中有什么作用？

Orchestrator 判断：需要结合文献和数据库注释
Orchestrator 调用（并行）：
  search_literature(query="NAC transcription factor drought stress ABA")
  search_by_annotation(species="Arabidopsis_thaliana",
                       go_terms=["GO:0009414"],
                       pfam_ids=["PF02365"])

输出：
  基于库内文献：NAC 家族参与 ABA 信号通路，ANAC055 / ANAC019 在干旱下上调...
  本库数据：拟南芥含 NAC 结构域基因 105 个，其中 12 个有水分胁迫响应 GO 注释
  [文献引用标注]
```

---

## 三、工具接口规范

### 设计原则

- 工具层**只接收参数并执行**，不包含意图判断、模式选择等业务逻辑
- 所有判断（调用哪个工具、传什么参数、什么模式）由 **Orchestrator** 决定
- 工具返回值应包含足够的元信息，便于 Orchestrator 向用户解释来源

---

### DB 工具

#### `get_gene_info`

```python
def get_gene_info(
    species: str,           # "Arabidopsis_thaliana"
    gene_id: str,           # "AT1G01010"
    fields: list = ["structure", "properties", "annotation"]
) -> {
    "gene_id":     str,
    "species":     str,
    "structure": {
        "chromosome":  str,
        "start":       int,
        "end":         int,
        "strand":      str,   # "+" | "-"
        "gene_length": int
    },
    "properties": {
        "pi":          float,
        "mol_weight":  float,
        "prot_length": int
    },
    "annotation": {
        "description": str,
        "go_terms":  [{"id": str, "name": str, "category": str}],
        "kegg_ko":   [{"id": str, "name": str}],
        "pfam_ids":  [{"id": str, "name": str}]
    },
    "not_found": bool       # True 时其余字段为 null，由 Orchestrator 告知用户
}
```

---

#### `query_homolog`

```python
def query_homolog(
    genus:       str,           # "Aegilops"
    gene_id:     str  = None,   # 指定参考基因，可选
    ref_species: str  = None,   # 指定参考物种，可选
    min_bsr:     float = 0.3
) -> {
    "genus":        str,
    "ref_species":  str,
    "ref_gene":     str,
    "homologs": [{
        "query_species": str,
        "query_gene":    str,
        "bsr":           float
    }],
    "species_count": int,       # 属内物种总数
    "hit_count":     int        # 找到同源的物种数
}
```

---

#### `search_by_annotation`

```python
# Orchestrator 负责将用户自然语言转为具体 term，工具只做过滤匹配

def search_by_annotation(
    species:    str,
    pfam_ids:   list[str] = None,   # ["PF00175"]
    go_terms:   list[str] = None,   # ["GO:0006631"]
    kegg_kos:   list[str] = None,   # ["K00507"]
    keywords:   list[str] = None,   # description 字段模糊匹配
    match_mode: str = "any",        # "any"=命中任一 / "all"=全部命中
    limit:      int = 100
) -> {
    "results": [{
        "gene_id":     str,
        "description": str,
        "matched_via": [str],       # ["pfam:PF00175", "go:GO:0006631"]
        "hit_count":   int          # 命中 term 数，排序依据
    }],
    "total":      int,
    "terms_used": {                 # 实际使用的 term，供 Orchestrator 向用户说明
        "pfam":     [str],
        "go":       [str],
        "kegg":     [str],
        "keywords": [str]
    }
}
```

**Orchestrator term 扩展参考**（system prompt 内置）：

```
自然语言 → term 扩展示例
脂肪酸    → pfam:["PF00175"], go:["GO:0006631","GO:0006636"], keywords:["fatty acid"]
转录因子  → pfam:["PF00847","PF02183"], go:["GO:0003700"], keywords:["transcription factor"]
抗病      → go:["GO:0042742","GO:0045087"], keywords:["disease resistance","NBS-LRR"]
胁迫响应  → go:["GO:0006950","GO:0009414"], keywords:["stress response"]
```

---

#### `compare_protein_props`

```python
def compare_protein_props(
    targets: [{"species": str, "gene_id": str}],
    sort_by: str = "pi"     # "pi" | "mol_weight" | "prot_length"
) -> {
    "table": [{
        "species":    str,
        "gene_id":    str,
        "pi":         float,
        "mol_weight": float,
        "prot_length":int
    }],
    "stats": {
        "pi_range":  [float, float],
        "mw_range":  [float, float],
        "len_range": [int, int]
    }
}
```

---

#### `expression_query`

```python
# Orchestrator 决定 mode 和 include_treatment，工具只按参数过滤

def expression_query(
    species:           str,
    gene_ids:          list[str],
    mode:              str  = "tissue",     # "tissue" | "condition"
    tissues:           list[str] = None,    # None=全部，["root","leaf"]=过滤
    include_treatment: bool = False         # False=仅对照组，True=含处理实验
) -> {
    "species":  str,
    "mode":     str,
    "data": {
        "<gene_id>": {
            "<tissue_or_condition>": {
                "mean_tpm":  float,
                "std_tpm":   float,
                "n_samples": int
            }
        }
    },
    "tissues_available": [str],     # 该物种有数据的组织列表
    "warning": str | None           # "该物种仅 1 个样本，无法计算标准差" 等
}
```

**Orchestrator 决策规则（expression_query）**：

| 用户意图 | mode | include_treatment |
|---------|------|------------------|
| 「在哪个组织表达最高」| tissue | False |
| 「各组织的表达量」| tissue | False |
| 「种子/叶片/根中的表达」| tissue | False，tissues=[指定] |
| 「胁迫/处理下的变化」| condition | True |
| 「对照组 vs 处理组」| condition | True |
| 「验证文献的组织特异性结论」| tissue | False |

---

### 文献工具

#### `search_literature`

```python
def search_literature(
    query:   str,           # 自然语言，直接做向量检索
    filters: dict = None,   # {"gene": "FAD2", "species": "Arabidopsis",
                            #  "year_from": 2020, "year_to": 2024}
    top_k:   int = 5
) -> [{
    "content":   str,       # 相关段落原文
    "paper_id":  str,
    "title":     str,
    "authors":   [str],
    "year":      int,
    "doi":       str,
    "relevance": float      # 向量相似度分数 0~1
}]
```

---

#### `get_lit_summary`

```python
# 优先返回预生成缓存，缓存失效时实时生成

def get_lit_summary(
    topic:   str,           # 基因名 / 物种 / 研究主题，如 "FAD2" / "CRISPR drought"
    filters: dict = None    # 同 search_literature 的 filters
) -> {
    "summary":      str,            # 综合摘要
    "key_findings": [str],          # 要点列表
    "papers_cited": [{
        "title":  str,
        "doi":    str,
        "year":   int
    }],
    "cache_hit":    bool,           # True=预生成缓存，False=实时生成
    "generated_at": str             # ISO 时间戳
}
```

**缓存生命周期**：

```
文献上传完成
    → classify_literature() 打标签
    → 按 tag 生成/更新对应 cache_key 的摘要
    → 新文献上传时，只重算命中相同 tag 的 cache_key（非全量重算）
    → cache_hit=False 时实时生成，结果写入缓存供下次使用
```

---

### 分析工具

#### `go_kegg_enrichment`

```python
def go_kegg_enrichment(
    species:     str,
    gene_ids:    list[str],
    types:       list = ["go_bp", "go_mf", "go_cc", "kegg"],
    p_threshold: float = 0.05
) -> {
    "go_bp": [{
        "term_id":        str,
        "term_name":      str,
        "gene_count":     int,
        "fold_enrichment":float,
        "p_value":        float,
        "genes":          [str]     # 命中基因列表
    }],
    "go_mf": [...],
    "go_cc": [...],
    "kegg":  [{
        "pathway_id":  str,
        "pathway_name":str,
        "gene_count":  int,
        "p_value":     float,
        "genes":       [str]
    }],
    "background_size": int          # 背景基因集大小（该物种全基因组）
}
```

---

## 四、工具-场景映射

```
场景                  主工具                        辅助工具（并行）
──────────────────────────────────────────────────────────────────────
单基因全景            get_gene_info                 query_homolog
                                                    search_literature
基因家族检索          search_by_annotation          get_gene_info（批量）
同源基因全景          query_homolog                 —
跨物种理化对比        query_homolog                 compare_protein_props
                      （顺序：先拿同源列表）
文献问答              search_literature             get_lit_summary
文献×数据验证         search_literature             expression_query
                                                    get_gene_info
基因列表富集          go_kegg_enrichment            —
表达模式              expression_query              —
多基因对比            get_gene_info × N（并行）     query_homolog
开放知识问答          search_literature             search_by_annotation
```

---

## 五、Orchestrator System Prompt 框架

```
你是 PlantsDB 植物基因数据库的 AI 分析助手。

【数据范围】
本库收录 IMP 数据库植物基因组数据，包含：
  - 基因结构（染色体坐标）
  - 蛋白理化性质（pI、分子量、长度）
  - 功能注释（GO、KEGG、Pfam，来自 EggNOG）
  - 属内同源关系（GeneTribe BSR/RBH）
  - RNA-seq 表达量（TPM，81 个物种，部分包含处理实验）
  - 人工上传的研究文献

【行为规则】
1. 数据库信息与文献信息必须明确区分来源标注
2. 文献引用必须包含作者、年份、DOI
3. 数据库无记录时，明确告知而非推测
4. 可并行调用多个工具，合并后再回答
5. 表达量查询：默认 mode="tissue", include_treatment=False
   用户明确问胁迫/处理时，切换为 mode="condition", include_treatment=True
6. 模糊注释查询：先将用户输入扩展为 pfam_ids/go_terms/keywords，再调用工具

【不在范围内】
  - 自动抓取外部文献（文献需管理员上传）
  - 蛋白质结构预测、CRISPR 靶点设计、启动子分析（待后续版本）
```

---

## 六、数据覆盖说明

| 数据类型 | 来源 | 覆盖范围 |
|---------|------|---------|
| 基因结构 / 理化性质 / 功能注释 | IMP + 本库流程 | 已完成 ETL 的物种 |
| 属内同源 | GeneTribe（BSR+RBH） | A 字头属基本完成，其余待补 |
| RNA-seq TPM | IMP 原始数据 | 81 个物种，样本数 1~60 不等 |
| 研究文献 | 管理员手动上传 | 按批次累积，每批约 100 篇 |
