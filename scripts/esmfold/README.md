# ESMFold 蛋白结构预测使用文档

## 概述

本模块集成 Meta AI ESMFold v1（3.5B 参数），可从**单条氨基酸序列**直接预测三维蛋白结构，无需多序列比对（MSA）输入。输出标准 PDB 文件、pLDDT 置信度图及 JSON 元数据，适用于快速结构评估和无参考结构的新型蛋白分析。

## 依赖

- **conda 环境**：`esmfold`（使用前请执行 `conda activate esmfold`）
- **关键 Python 包**：
  - `fair-esm==2.0.0`
  - `torch==1.12.1+cu113`
  - `biopython`
  - `matplotlib`

## 系统要求

| 要求项 | 说明 |
|--------|------|
| GPU（推荐） | NVIDIA GPU，显存 >= 16GB；CPU 可用，但速度极慢 |
| GLIBC | GLIBC >= 2.34 时可直接使用 CUDA 扩展；**低版本系统已通过内置 mock patch 自动绕过，无需手动处理** |
| 模型权重 | 首次运行自动下载至 `~/.cache/torch/hub/checkpoints/esmfold_3B_v1.pt`（约 12 GB） |
| 磁盘空间 | 模型权重约 12 GB + 输出结果空间 |

## 目录结构

```
scripts/esmfold/
├── __init__.py           # 包入口，导出主要 API
├── esmfold_model.py      # 模型加载、推理、置信度分析
├── esmfold_predict.py    # CLI 入口脚本
└── test_data/            # 测试序列示例
    ├── AtTest.fasta      # 拟南芥测试蛋白（短序列，约 80aa）
    └── RealProtein.fasta # 真实植物蛋白示例（约 350aa）
```

## 功能说明

### `esmfold_model.py`

| 功能 | 说明 |
|------|------|
| 模型 singleton 加载 | 全局单例，避免重复加载（首次加载约 50s） |
| 序列验证 | 检查长度范围（6–800aa）、非标准字符自动去除 |
| 结构推理 | 调用 ESMFold 前向传播，返回 PDB 坐标和置信度分数 |
| pLDDT 图生成 | 使用 matplotlib 绘制每残基 pLDDT 置信度折线图 |

### `esmfold_predict.py`

CLI 入口，解析命令行参数后调用 `esmfold_model.py` 进行推理，支持单序列、FASTA 文件和批量模式。

## 输入格式

| 格式 | 说明 |
|------|------|
| 标准氨基酸 | 支持标准 20 种氨基酸（单字母编码） |
| 序列来源 | 接受 FASTA 文件（`-i`）或命令行直接输入（`-s`） |
| 长度限制 | 6–800 个氨基酸（在线模式建议 <= 400） |
| 非标准字符 | 自动去除（`B`、`J`、`O`、`U`、`X`、`Z` 等），并输出警告 |
| 多聚体 | 多条链使用 `:` 分隔，如 `MKTLL...ACDEF:GHILM...NPQRST` |

## 使用示例

### 单序列预测

```bash
conda activate esmfold

python -m scripts.esmfold.esmfold_predict \
  -s "MKTLLLTLVVVTIVCLDLGAVGNPCTGGVFDFMKTVCHPNIMSVFNLMCQLEKTLSDFPNISKLNALQKL" \
  -n MyProtein \
  -o output/esmfold_result/
```

### FASTA 文件输入

```bash
python -m scripts.esmfold.esmfold_predict \
  -i test_data/AtTest.fasta \
  -o output/esmfold_result/
```

### 批量模式（FASTA 含多条序列）

```bash
python -m scripts.esmfold.esmfold_predict \
  -i proteins.fasta \
  --batch \
  -o output/esmfold_result/
```

### 高精度模式（增加 recycling 次数）

```bash
python -m scripts.esmfold.esmfold_predict \
  -i test_data/RealProtein.fasta \
  --num-recycles 4 \
  -o output/esmfold_result/
```

## CLI 参数说明

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--sequence` | `-s` | — | 直接输入氨基酸序列字符串（与 `-i` 二选一） |
| `--input` | `-i` | — | 输入 FASTA 文件路径（与 `-s` 二选一） |
| `--name` | `-n` | FASTA header | 输出文件名前缀 |
| `--output` | `-o` | `./esmfold_output/` | 输出目录 |
| `--batch` | | `false` | 批量模式：对 FASTA 中每条序列分别预测 |
| `--num-recycles` | | `3` | ESMFold recycling 次数（越高精度越好，速度越慢） |
| `--chunk-size` | | `128` | 注意力分块大小，内存不足时减小（如 `64`） |
| `--no-plot` | | `false` | 禁用 pLDDT 图像生成 |
| `--force` | `-f` | `false` | 强制覆盖已存在的输出文件 |

## 输出文件格式

| 文件扩展名 | 内容 |
|-----------|------|
| `.pdb` | 标准 PDB 格式三维结构坐标，可用 PyMOL / ChimeraX 打开 |
| `.plddt.png` | 每残基 pLDDT 置信度折线图（matplotlib 生成） |
| `.json` | 元数据：序列长度、平均 pLDDT、pTM、置信度分级统计、推理耗时 |

## pLDDT 置信度解释

| pLDDT 范围 | 置信度等级 | 含义 |
|------------|-----------|------|
| > 90 | 极高（Very High） | 结构可信，接近实验精度 |
| 70 – 90 | 高（High） | 主链可信，侧链可能有偏差 |
| 50 – 70 | 低（Low） | 结构不可靠，可能为柔性区域 |
| < 50 | 极低（Very Low） | 高度无序区域，结构预测无参考价值 |

> pTM（predicted TM-score）< 0.5 表示整体拓扑置信度低，应谨慎使用该结构进行下游分析。

## 测试数据

`test_data/` 目录提供两个示例序列：

| 文件 | 蛋白名 | 序列长度 | 用途 |
|------|--------|----------|------|
| `AtTest.fasta` | AtTest | ~80 aa | 快速验证环境（CPU 约 5 min） |
| `RealProtein.fasta` | RealProtein | ~350 aa | 典型植物蛋白预测示例 |

## 性能参考

| 条件 | 性能 |
|------|------|
| 模型加载（首次） | ~50 秒（GPU/CPU 相同） |
| CPU 推理 | 每 100 残基约 3–5 分钟 |
| GPU 推理（A100） | 每 100 残基约 5–10 秒 |
| 建议上限（CPU） | 不建议预测超过 400 残基的序列 |

## 常见问题

**Q：运行时报 GLIBC 版本错误？**
已通过内置 mock patch 自动绕过 CUDA 扩展编译问题，无需手动处理。若仍报错，请确认使用 `conda activate esmfold` 激活了正确环境。

**Q：内存不足（OOM）？**
添加 `--chunk-size 64` 参数减小注意力计算的分块大小，可显著降低显存/内存占用，但会稍微增加推理时间。

**Q：模型权重下载失败？**
权重文件约 12 GB，存放于 `~/.cache/torch/hub/checkpoints/esmfold_3B_v1.pt`。如下载中断，删除该文件后重新运行即可触发重新下载。网络受限环境请联系管理员手动部署权重文件。

**Q：输入序列含有非标准字符？**
非标准氨基酸字符（如 `B`、`J`、`O`、`U`、`X`、`Z`）会被自动去除并输出警告信息。去除后若序列长度低于 6，将报错终止。
