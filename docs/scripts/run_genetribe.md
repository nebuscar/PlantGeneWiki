# run_genetribe.sh 使用说明

## 概述

运行 [GeneTribe](https://github.com/YulongSong/GeneTribe) 对两个物种进行同源基因鉴定。自动从 `sample/` 目录查找蛋白序列和 BED 文件，执行 RBH（Reciprocal Best Hit）分析。

---

## 依赖

- [GeneTribe](https://github.com/YulongSong/GeneTribe)（`genetribe` 命令）
- 两个物种的蛋白序列文件（`.faa`）和 BED 文件（`.bed`）

---

## 输入数据

### 目录结构要求

```
./sample/
├── Hopea_chinensis/
│   ├── *_protein*.faa
│   └── *.bed
└── Hopea_hainanensis/
    ├── *_protein*.faa
    └── *.bed
```

### 配置（脚本内硬编码）

脚本顶部需修改以下变量：

| 变量       | 默认值                  | 说明                     |
|-----------|------------------------|--------------------------|
| `SP1`     | `Hopea_chinensis`      | 物种 1 目录名             |
| `SP2`     | `Hopea_hainanensis`    | 物种 2 目录名             |
| `OUT_DIR` | `./genetribe_final`    | 输出目录                  |

---

## 输出数据

### 输出目录

`./genetribe_final/`

### 主要输出文件

| 文件              | 说明                            |
|-------------------|---------------------------------|
| `*.RBH`           | RBH 同源基因对结果               |
| `{SP1}.fa`        | 物种 1 蛋白序列（副本）           |
| `{SP2}.fa`        | 物种 2 蛋白序列（副本）           |
| `{SP1}.bed`       | 物种 1 BED 文件（副本）           |
| `{SP2}.bed`       | 物种 2 BED 文件（副本）           |

---

## 使用方法

```bash
# 1. 修改脚本顶部的 SP1、SP2 变量为目标物种
# 2. 确保 sample/ 下对应目录包含蛋白和 BED 文件
# 3. 运行
./scripts/run_genetribe.sh
```

脚本无命令行参数，物种配置需直接编辑脚本。

---

## 方法细节

1. **工作目录**：脚本强制切换到项目根目录（`cd "$(dirname "$0")/.."`）。
2. **文件查找**：使用 `find sample/$SP -name "*protein*" | head -1` 和 `find sample/$SP -name "*.bed" | head -1` 自动定位蛋白序列和 BED 文件，取匹配的第一个。
3. **文件准备**：将蛋白序列和 BED 文件复制到输出目录，重命名为 `{Species}.fa` 和 `{Species}.bed`（GeneTribe 要求简洁命名）。
4. **运行 GeneTribe**：`genetribe core -l "$SP1" -f "$SP2"`，`-l` 指定局部物种，`-f` 指定远端物种，执行 RBH 同源分析。
