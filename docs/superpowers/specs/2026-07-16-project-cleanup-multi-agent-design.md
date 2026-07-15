# PlantGeneWiki 项目清理与多 Agent 协作设计

## 1. 背景与目标

PlantGeneWiki 正在从单物种原型扩展为多物种、可持续更新的 Wiki 型植物知识库。当前仓库同时存在应用代码、标准化脚本、本地构建产物和约 31.6 GB 的中间数据；后续还需要并行推进数据治理、向量检索、结构化图谱和应用集成。

本轮工作的目标是：

1. 将大体量数据和可再生缓存移出代码仓库工作区。
2. 保留具有科研复用价值的数据，并建立可追踪的归档登记。
3. 配置职责清晰、相互隔离的 Codex 开发子 Agent。
4. 定义产品运行时 Agent 的角色和接口，但暂不实现运行框架。
5. 保持现有 FastAPI、SQLite 离线图谱快照和前端原型可继续运行。

## 2. 设计原则

- 代码仓库只保存代码、配置、Schema、测试、小型示例和文档。
- 原始数据、中间结果、索引和模型产物使用外部数据目录管理。
- 先登记、复制和验证，再删除仓库工作区中的原副本。
- 数据来源应记录在对象元数据和 Dataset Registry 中，不依赖目录名表达语义。
- 开发子 Agent 按职责分工，不以数据来源或单一脚本划分。
- 并行任务必须减少共享文件写入，最终由根任务统一审查和整合。
- 产品运行时 Agent 与 Codex 开发子 Agent 分开设计，避免概念混用。

## 3. 仓库清理范围

### 3.1 可直接清理的再生内容

以下目录均可由依赖安装或构建命令重新生成：

- `apps/web/node_modules/`
- `apps/web/dist/`
- `apps/web/.astro/`
- 各级 `__pycache__/`

项目根目录 `.venv/` 当前仍作为统一 Python 开发环境使用，本轮保留。

### 3.2 需要归档的数据

已确认需要迁出的主要目录：

- `data/meta/`，约 5.6 GB
- `data/pgcp_ortho/`，约 26 GB

归档目标：

```text
/DATA/data2/plantgenewiki/archive/meta/
/DATA/data2/plantgenewiki/archive/pgcp_ortho/
```

迁移采用“复制、验证、删除源目录”的流程：

1. 使用可断点续传方式复制目录。
2. 对比源端与目标端的文件数量和总大小。
3. 对清单文件及抽样大文件执行校验和比对。
4. 写入归档登记文件。
5. 验证通过后移除仓库工作区中的源目录。

### 3.3 归档登记

新增受 Git 跟踪的 `config/archives.yaml`，记录：

- `archive_id`
- `category`
- `source_path`
- `archive_path`
- `source_or_batch`
- `version`
- `file_count`
- `size_bytes`
- `checksum_manifest`
- `archived_at`
- `status`

该文件只记录逻辑位置和校验信息，不保存密码、令牌或个人环境配置。

### 3.4 暂不清理的内容

`scripts/analysis/`、`scripts/importers/`、`scripts/maintenance/` 等脚本暂不批量删除。后续由 `data-curator` 和 `reviewer` 逐项判断其输入、输出、测试覆盖和替代实现，再决定保留、迁移或归档。

`.gitignore` 中已经不存在的 `apps/agent/` 运行产物规则属于失效配置，本轮可删除。

## 4. Codex 开发子 Agent

### 4.1 协作拓扑

```text
Root Orchestrator
├── data-curator
├── vector-engineer
├── graph-engineer
├── application-engineer
└── reviewer
```

根任务负责拆分任务、设置边界、选择子 Agent、检查结果并决定是否合并。子 Agent 不直接承担最终发布责任。

### 4.2 角色职责

| Agent | 主要职责 | 明确边界 |
|---|---|---|
| `data-curator` | 数据盘点、归档、Schema、标准化、来源与版本追踪 | 不改前端视觉，不决定在线存储实现 |
| `vector-engineer` | KnowledgeChunk、嵌入生成、Qdrant 索引、语义检索评估 | 不修改结构化图谱语义模型 |
| `graph-engineer` | 知识对象、关系、EvidenceClaim、图谱导入与查询 | 不把向量相似度当作事实关系 |
| `application-engineer` | FastAPI、前端、API 契约和服务集成 | 不绕过标准化层直接读取原始数据 |
| `reviewer` | 测试、数据质量、回归、敏感信息和变更范围审查 | 默认只读，不代替实现者重写功能 |

### 4.3 并发与隔离

建议项目级配置：

```toml
[agents]
max_threads = 4
max_depth = 1
job_max_runtime_seconds = 1800
```

- 同一时间最多运行 4 个子 Agent，避免争用服务器资源。
- 需要写代码的并行任务使用独立 Git worktree。
- 只读审计任务可以直接并行执行。
- 两个 Agent 不应同时修改同一文件或同一迁移脚本。
- 子 Agent 输出必须包含变更文件、验证结果、未解决问题和风险。

### 4.4 配置结构

项目配置建议放置为：

```text
.codex/
├── config.toml
└── agents/
    ├── data-curator.toml
    ├── vector-engineer.toml
    ├── graph-engineer.toml
    ├── application-engineer.toml
    └── reviewer.toml
```

项目级 `config.toml` 注册角色、描述和角色配置文件。角色文件只定义职责、边界、验证要求和输出格式，不保存密钥或服务器密码。

当前 Codex CLI 已支持稳定版 `multi_agent`。本轮不启用仍处于开发状态的 `multi_agent_v2` 和 `child_agents_md`。

## 5. 产品运行时 Agent 边界

本轮只定义角色和接口，不创建运行时代码。

| Agent | 输入 | 输出 | 核心职责 |
|---|---|---|---|
| Data Ingestion Agent | 数据源登记、抓取策略 | Raw Dataset、采集日志 | 增量发现、下载、校验和版本登记 |
| Normalization Agent | Raw Dataset、目标 Schema | Knowledge Object、Relation、EvidenceClaim | 解析、标准化、实体对齐和质量检查 |
| Literature Curation Agent | 文献元数据、摘要或全文 | Literature、候选 EvidenceClaim | 收集、筛选、分类和知识抽取 |
| Evidence Evaluation Agent | 候选声明及来源 | 证据等级、置信度、审核状态 | 评估证据质量并触发人工复核 |
| Indexing Agent | 已审核知识对象和文本块 | 向量索引、图谱索引、检索清单 | 增量建立并更新检索组件 |
| User Task Agent | 用户问题、检索结果、权限上下文 | 回答、查询计划或分析任务 | 编排检索、推理和受控分析 |
| Archive Agent | 过期版本、运行产物、审计记录 | 可验证归档及恢复清单 | 生命周期管理、归档和恢复 |

所有运行时 Agent 应交换带有 `object_id`、`dataset_id`、`version`、`provenance`、`status` 和时间戳的结构化任务对象，不能仅依赖自然语言消息传递关键状态。

## 6. 实施顺序

1. 单独提交当前 MySQL 实验代码和依赖清理。
2. 清理可再生缓存和失效忽略规则。
3. 迁移 `data/meta/` 与 `data/pgcp_ortho/`，完成校验和归档登记。
4. 配置 Codex 项目级多 Agent 角色。
5. 验证 Codex 配置、Git 状态、API 测试和前端构建。
6. 另行规划向量数据库最小闭环，不在本轮直接部署 Qdrant。

## 7. 验收标准

- 仓库工作区不再承载 31.6 GB 的归档数据。
- 归档目标中的文件数量、大小和抽样校验与源目录一致。
- `config/archives.yaml` 能追踪归档来源、位置和状态。
- MySQL 实验代码及依赖完全从项目中移除。
- 项目级 Codex 配置可通过严格配置校验。
- 五个开发子 Agent 的职责、边界和验证输出明确。
- 产品运行时 Agent 只有设计文档，不引入未验证的框架代码。
- 现有 API 单元测试通过，前端可完成构建。
- Git 提交按“设计文档、MySQL 清理、数据清理与 Agent 配置”分开组织。

## 8. 非目标

本轮不完成以下工作：

- 部署生产向量数据库。
- 选择或部署正式图数据库。
- 实现产品运行时 Agent 编排框架。
- 批量删除尚未审计的科研分析脚本。
- 将大型原始数据或索引文件加入 Git。
