# deduplicate_species_list.sh 使用说明

## 概述

按物种名（第 2 列 Species）对物种列表去重，每个物种仅保留第一次出现的记录。表头完整保留，行顺序不变。

---

## 输入数据

Tab 分隔的物种列表文件，表头格式：

```
No.	Species	Taxonomy ID	Ploidy	Accession name	Order	Family	Clade
```

---

## 输出数据

与输入格式完全相同的 Tab 分隔文件，仅去除 Species 列重复的行（保留首次出现），表头保留。

---

## 使用方法

### 参数

| 参数           | 必需 | 说明                       |
|----------------|------|---------------------------|
| `-i, --input`  | 是   | 输入物种列表文件            |
| `-o, --output` | 是   | 输出去重后的文件            |
| `-s, --stat`   | 否   | 显示去重统计信息            |
| `-h, --help`   | 否   | 显示帮助信息                |

### 示例

```bash
# 基本去重
./deduplicate_species_list.sh -i species_list.txt -o species_list_unique.txt

# 去重并显示统计
./deduplicate_species_list.sh -i list.txt -o unique_list.txt -s
```

---

## 方法细节

1. **核心逻辑**：使用 `awk` 逐行处理，以第 2 列（Species）为 key 维护 `seen` 关联数组。
2. **保留首次出现**：`if (!seen[species]++)` — 第一次遇到某物种名时 `seen` 为 0，取反为真，输出该行并递增计数器；后续再遇到同一物种名时 `seen` 已非零，取反为假，跳过。
3. **表头处理**：`NR == 1` 时直接输出，不参与去重逻辑。
4. **强制 Tab 分隔**：`FS = "\t"; OFS = "\t"` 确保以制表符分割和输出，避免物种名中空格导致列错位。
5. **统计信息**（`-s` 模式）：分别统计原始行数、去重后行数、移除的冗余条目数。
