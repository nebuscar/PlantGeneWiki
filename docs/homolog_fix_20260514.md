# Homolog模块修复记录 (2026-05-14)

## 问题描述

处理包含 `var._` 变种标记的物种名（如 `Amborella_trichopoda_var._SantaCruz_75_HAP1`）时，homolog模块无法正常输出RBH和`1v1.tsv`文件。

## 问题根因

### 问题1: jcvi文件名解析错误

**现象：** genetribe内部使用jcvi库解析文件名时，将`var._`识别为species/variant分隔符。

**示例：**
```
文件名: Amborella_trichopoda_var._SantaCruz_75_HAP1.bed
被解析为: species="Amborella_trichopoda_var", 后缀="_SantaCruz_75_HAP1.bed"
期望: species="Amborella_trichopoda_var._SantaCruz_75_HAP1"
```

**影响：** jcvi尝试读取不存在的文件`Amborella_trichopoda_var.bed`，导致后续步骤失败。

### 问题2: genetribe core静默失败

**现象：** genetribe core在处理完BLAST后，`coreCalculateScore`步骤抛出Python异常并退出（exit code 0），但RBH文件未生成。

**错误信息：**
```
FileNotFoundError: [Errno 2] No such file or directory: 'Amborella_trichopoda_var.bed'
```

**影响：** BLAST文件已成功生成，但RBH文件未创建，导致`ref genes with RBH: 0`。

## 修复方案

### 修复1: 文件名Sanitization

**原理：** 将物种名中的`.`替换为`__`（双下划线），避免jcvi将`._`识别为分隔符。

**修改位置：** `run_imp_pipeline.sh` 第511-526行

```bash
# 修复前
sanitize_gt() { echo "$1" | tr '.' '_'; }

# 修复后
sanitize_gt() { echo "$1" | sed 's/\./__/g'; }
```

**对比：**

| 物种名 | 修复前 | 修复后 |
|--------|--------|--------|
| `Amborella_trichopoda_var._SantaCruz_75_HAP1` | `Amborella_trichopoda_var__SantaCruz_75_HAP1` | `Amborella_trichopoda_var___SantaCruz_75_HAP1` |
| `Acer_campestre` | `Acer_campestre` | `Acer_campestre` |

**注意：** 只替换`.`为`__`，保持`_`不变，避免过度转义。

### 修复2: genetribe core失败回退

**原理：** 检测genetribe core是否异常退出，若是则手动执行`genetribe RBH`命令计算RBH。

**修改位置：** `run_imp_pipeline.sh` 第553-562行

```bash
for sp in "${query_species[@]}"; do
    local san_sp
    san_sp=$(sanitize_gt "$sp")
    pushd "$gt_tmp" >/dev/null
    rm -rf genetribe_output/

    # 尝试genetribe core，失败则回退到手动RBH
    if genetribe core -l "$san_ref_sp" -f "$san_sp" -n 80 2>&1 | grep -q "Traceback"; then
        local rbh_file="${san_ref_sp}_${san_sp}.RBH"
        if [[ -f genetribe_output/${san_ref_sp}_${san_sp}.blast && \
              -f genetribe_output/${san_sp}_${san_ref_sp}.blast ]]; then
            genetribe RBH -a "genetribe_output/${san_ref_sp}_${san_sp}.blast" \
                          -b "genetribe_output/${san_sp}_${san_ref_sp}.blast" \
                          > "$rbh_file" 2>/dev/null || true
        fi
    fi

    [[ -f "${san_ref_sp}_${san_sp}.RBH" ]] && \
        cp "${san_ref_sp}_${san_sp}.RBH" "${genus_dir}/${ref_sp}_${sp}.RBH"
    popd >/dev/null
done
```

## 验证结果

### 测试数据
- `Amborella_trichopoda` (200 proteins, 1268 chromosomes)
- `Amborella_trichopoda_var._SantaCruz_75_HAP1` (200 proteins, 27 chromosomes)

### 测试结果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| RBH配对数 | 0 | 12 |
| 1v1.tsv | 仅有header | 包含13行（header + 12个RBH配对） |
| genetribe执行 | 异常退出 | 正常完成 |

### 示例输出 (`Amborella_homolog_1v1.tsv`)

```
Amborella_trichopoda_var._SantaCruz_75_HAP1	Amborella_trichopoda
IMPATR6G00000000012	IMPATR3G00000000175
IMPATR6G00000000014	IMPATR3G00000000192
IMPATR6G00000000016	IMPATR3G00000000155
...
```

## 涉及文件

- **修改：** `/home/nizhu/Projects/plantsdb/scripts/imp/run_imp_pipeline.sh`

## 未修改的第三方工具

- jcvi: `/home/nizhu/software/genetribe/lib/python3.12/site-packages/jcvi/` — 源码未修改
- genetribe: `/home/nizhu/software/genetribe/` — 源码未修改

所有问题通过**绕过问题**而非**修改源码**解决。

## 相关日志

- 调试时发现genetribe core的BLAST文件生成正常，但`coreCalculateScore`阶段读取BED文件时使用错误的文件名
- 原始文件名（含`.`）不会被错误解析，问题出在sanitized文件名（`_`替代了`.`后产生`var_`与后续的`_HAP1`组合被误解）
