# calc_species_stats.sh 使用说明

## 概述

对物种列表按目（Order）/科（Family）/属（Genus）分组统计唯一物种数量，输出标准 TSV 表格。

---

## 输入数据

Tab 分隔的物种列表文件，表头及列要求如下：

| 列号 | 列名     | 说明         |
|------|---------|--------------|
| 2    | Species | 物种拉丁名    |
| 6    | Order   | 目           |
| 7    | Family  | 科           |
| 8    | Genus   | 属           |

---

## 输出数据

Tab 分隔的统计结果，按物种数量降序排列：

### 按 Order 分组

```
Order	Species_Count
Brassicales	45
Poales	38
...
```

### 按 Family 分组

```
Family	Species_Count
Fabaceae	32
Poaceae	28
...
```

### 按 Genus 分组

```
Genus	Species_Count
Oryza	5
...
```

---

## 使用方法

### 参数

| 参数           | 必需 | 说明                                       |
|----------------|------|-------------------------------------------|
| `-i, --input`  | 是   | 输入物种列表文件                            |
| `-o, --output` | 是   | 输出统计文件                                |
| `-g, --group`  | 是   | 分组类型：`order` / `family` / `genus`      |
| `-h, --help`   | 否   | 显示帮助信息                                |

### 示例

```bash
# 按目统计
./calc_species_stats.sh -i species_list.txt -o stats_order.txt -g order

# 按科统计
./calc_species_stats.sh -i species_list.txt -o stats_family.txt -g family

# 按属统计
./calc_species_stats.sh -i species_list.txt -o stats_genus.txt -g genus
```

---

## 方法细节

1. **去重**：使用 `awk` 关联数组 `seen_species` 对第 2 列（Species）去重，确保每个物种只计一次。
2. **分组计数**：对去重后的物种，按指定分组列（Order=第6列，Family=第7列，Genus=第8列）累加计数到 `groups` 数组。
3. **跳过表头**：`NR == 1 { next }` 跳过第一行。
4. **排序**：`awk` 输出后经 `sort -k2,2nr` 按第 2 列（Species_Count）数值降序排列。
5. **运行后预览**：自动输出结果前 10 行到终端。
