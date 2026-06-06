# add_taxid.sh 使用说明

## 概述

使用 [Taxonkit](https://bioinf.shenwei.me/taxonkit/) 为物种列表批量添加 Taxonomy ID（TaxID）。自动对物种名去重查询，保持原文件行顺序和重复行。

---

## 依赖

- [Taxonkit](https://bioinf.shenwei.me/taxonkit/)（需已配置 NCBI taxonomy 数据库）
- `ssconvert`（可选，来自 gnumeric 包，用于导出 xlsx 格式）

---

## 输入数据

Tab 分隔的物种列表文件，表头及列要求如下：

| 列号 | 列名         | 说明               |
|------|-------------|--------------------|
| 1    | No.         | 序号               |
| 2    | Species     | 物种拉丁名（用于查询 TaxID） |
| 3    | Ploidy      | 倍性               |
| 4    | Accession   | 登录号             |
| 5    | Order       | 目                 |
| 6    | Family      | 科                 |
| 7    | Clade       | 进化支             |

示例：

```
No.	Species	Ploidy	Accession	name	Order	Family	Clade
1	Arabidopsis thaliana	2	GCF_000001735	Arabidopsis thaliana	Brassicales	Brassicaceae	Eudicots
```

---

## 输出数据

在输入列基础上，于第 2 列（Species）和第 3 列（Ploidy）之间**插入** `Taxonomy ID` 列：

| 列号 | 列名         | 说明                                   |
|------|-------------|----------------------------------------|
| 1    | No.         | 序号                                   |
| 2    | Species     | 物种拉丁名                             |
| 3    | **Taxonomy ID** | NCBI TaxID，未找到时为 `-`          |
| 4    | Ploidy      | 倍性                                   |
| 5    | Accession   | 登录号                                 |
| 6    | Order       | 目                                     |
| 7    | Family      | 科                                     |
| 8    | Clade       | 进化支                                 |

### 输出格式

根据输出文件扩展名自动选择格式：

| 扩展名   | 格式           | 说明                                       |
|----------|---------------|--------------------------------------------|
| `.txt` / `.tsv` | Tab 分隔文本 | 直接输出                                   |
| `.csv`   | 逗号分隔文本   | Tab 替换为逗号                              |
| `.xlsx`  | Excel          | 需安装 `ssconvert`，未安装则自动降级为 `.txt` |

---

## 使用方法

### 参数

| 参数           | 必需 | 说明                                       |
|----------------|------|-------------------------------------------|
| `-i, --input`  | 是   | 输入物种列表文件                           |
| `-o, --output` | 是   | 输出文件（扩展名决定格式）                  |
| `-h, --help`   | 否   | 显示帮助信息                               |

### 示例

```bash
# 输出为 tab 分隔文本
./add_taxid.sh -i data/meta/ncbi/species_list.txt -o result.txt

# 输出为 CSV
./add_taxid.sh -i data/meta/ncbi/species_list.txt -o result.csv

# 输出为 Excel（需 ssconvert）
./add_taxid.sh -i data/meta/ncbi/species_list.txt -o result.xlsx
```

---

## 方法细节

1. **去重查询**：提取输入文件第 2 列所有不重复的物种名，一次性调用 `taxonkit name2taxid` 查询，避免重复请求。
2. **查询命令**：`taxonkit name2taxid -s --show-rank`，`-s` 表示精确匹配学名，`--show-rank` 同时返回分类层级。
3. **构建映射表**：将查询结果读入关联数组 `taxid_map`，TaxID 为 0 或空视为未找到。
4. **逐行匹配**：遍历输入文件每一行，用物种名查找 TaxID；未找到时填入 `-`，并记录到失败列表。
5. **格式转换**：先统一输出为 TSV 临时文件，再根据输出扩展名转换格式。
6. **结果报告**：输出总行数、成功获取 TaxID 数、未找到 TaxID 数，并列出最多 20 个未匹配的物种名。

### 临时文件

脚本使用 `mktemp` 创建临时文件，正常结束后自动清理。
