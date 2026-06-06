# run_genetribe.sh 问题排查指南

本文记录了运行 `run_genetribe.sh` 过程中遇到的问题及其根因和解决方案。

---

## 问题 1：BED 列数不匹配 — ValueError: Length mismatch

### 错误信息

```
ValueError: Length mismatch: Expected axis has 10 elements, new values have 6 elements
```

### 根因

`gff2bed` 将 GFF 转换为 BED 时保留了 GFF 的全部字段，输出 10 列 BED。但 GeneTribe 的 `coreCBS.py` 中 `bed2pd()` 函数硬编码只赋 6 列名：

```python
# coreCBS.py:67
bedtmp.columns = ["chr","start","end","id","score","strand"]
```

pandas 在 10 列 DataFrame 上赋 6 个列名时报错。

### 解决

在 `run_bed()` 的 gff2bed 管道末尾加 `cut -f1-6`，只输出标准 BED 6 列：

```bash
# 修改前
awk ... | gff2bed 2>/dev/null | awk '$8=="gene"' OFS="\t" >"$OUTPUT_DIR/${sp}.bed"

# 修改后
awk ... | gff2bed 2>/dev/null | awk '$8=="gene"' OFS="\t" | cut -f1-6 >"$OUTPUT_DIR/${sp}.bed"
```

---

## 问题 2：jcvi 未运行 — genetribe core 删除 genetribe_output

### 错误现象

genetribe core 运行完成后，jcvi 共线性分析未执行，无 `.anchors`、`.lifted.anchors`、`.pdf` 输出。

### 根因

GeneTribe 的 `core.sh` 在完成时会执行 `rm -rf genetribe_output`（第 338 行），删除整个工作目录。原脚本中 jcvi 是在 genetribe core 之后运行的：

```bash
genetribe core ... || true
if [[ -d "genetribe_output" ]]; then   # 目录已被删除，条件为 false
    cd genetribe_output
    python -m jcvi.compara.catalog ortholog ...
fi
```

由于 `genetribe_output/` 已被删除，jcvi 被直接跳过。

但实际上 `core.sh` 第 166 行**内部已经调用了 jcvi**：

```bash
python -m jcvi.compara.catalog ortholog --no_strip_names ${key1} ${key2}
```

因此脚本中的 jcvi 调用是多余的，真正的问题是 genetribe core 内部的 jcvi 调用失败了（见问题 3）。

### 解决

1. 移除脚本中重复的 jcvi 调用
2. 在 genetribe core 运行前，将 jcvi 所需的 `.cds`、`.bed`、`.pep` 文件链接到 `genetribe_output/` 目录
3. 确保脚本中 `genetribe core` 之前的文件链接逻辑正确

```bash
mkdir -p genetribe_output
for species in "$ref_sp" "$q"; do
    ln -s "$(pwd)/${species}.cds" "genetribe_output/${species}.cds"
    ln -s "$(pwd)/${species}.bed" "genetribe_output/${species}.bed"
    ln -s "$(pwd)/${species}.faa" "genetribe_output/${species}.pep"
done
genetribe core -l "$ref_sp" -f "$q" -d "$out" || true
```

---

## 问题 3：jcvi 导入失败 — ModuleNotFoundError: No module named 'jcvi'

### 错误信息

```
/home/nizhu/.local/bin/python: Error while finding module specification for 'jcvi.compara.catalog' (ModuleNotFoundError: No module named 'jcvi')
```

### 根因

虽然脚本执行了 `conda activate genetribe`，但 `~/.local/bin` 在 PATH 中优先级高于 conda 环境的 bin 目录。genetribe core 内部调用 `python -m jcvi` 时，`python` 解析到了 `~/.local/bin/python`（系统 Python 3.8），而 jcvi 只安装在 conda `genetribe` 环境的 Python 3.12 中。

```bash
$ which python
/home/nizhu/.local/bin/python    # 错误的 python
$ /path/to/genetribe/env/bin/python -c "import jcvi"  # 正常
```

### 解决

在 `conda activate` 后，强制将 conda 环境的 bin 目录置于 PATH 最前：

```bash
eval "$(conda shell.bash hook 2>/dev/null)"
conda activate genetribe
CONDA_ENV_DIR="$(conda info --base 2>/dev/null)/envs/genetribe"
if [[ -d "$CONDA_ENV_DIR/bin" ]]; then
    export PATH="$CONDA_ENV_DIR/bin:$PATH"
fi
```

---

## 问题 4：jcvi 报文件不存在 — AssertionError: The specified infile does not exist

### 错误信息

```
AssertionError: The specified infile `Acer_negundo.cds` does not exist
```

### 根因

jcvi 的 `ortholog` 命令在 `genetribe_output/` 目录下工作（因为 genetribe core 先 `cd` 到该目录）。jcvi 需要三种文件：

| 文件 | jcvi 用途 | 是否在 genetribe_output/ 中 |
|------|----------|---------------------------|
| `{Species}.bed` | 基因位置信息 | 否（在父目录） |
| `{Species}.cds` | 核酸序列（nucl 模式） | 否（在父目录） |
| `{Species}.pep` | 蛋白序列（prot 模式，默认） | 否（只有 .faa） |

genetribe core 的 `corelns.py` 会自动链接 `.bed` 和创建 `.last` 符号链接，但不会创建 `.cds` 和 `.pep` 链接。

### 解决

在 genetribe core 运行前预创建所有必需的符号链接：

```bash
mkdir -p genetribe_output
for species in "$ref_sp" "$q"; do
    [[ -f "${species}.cds" ]] && ln -s "$(pwd)/${species}.cds" "genetribe_output/${species}.cds"
    [[ -f "${species}.bed" ]] && ln -s "$(pwd)/${species}.bed" "genetribe_output/${species}.bed"
    # jcvi prot 模式默认查找 .pep，但我们的文件是 .faa
    [[ -f "${species}.faa" ]] && ln -s "$(pwd)/${species}.faa" "genetribe_output/${species}.pep"
done
```

> **注意**：jcvi 默认使用 prot 模式（`--dbtype=prot`），查找 `{Species}.pep` 文件。如果只有 `.faa` 文件，必须创建 `.pep → .faa` 符号链接。

---

## 问题 5：RBH 第四列为 "unknown"

### 错误现象

```
LWI29_000001    LWI28_008214    RBH    unknown
LWI29_000002    LWI28_005291    RBH    unknown
```

第四列应为基因所在的染色体名，但全部显示为 "unknown"。

### 根因

GeneTribe 的 `coreCorrectTotal.py` 在第 44-46 行执行染色体分组匹配：

```python
CHR = re.sub('[0-9][0-9]|[0-9]','N', beddc[i[1]])  # CM059866.1 → CMNNNNNN.N
if not re.search(rawCHR, CHR):
    i[3] = "unknown"
```

它将染色体名中的数字替换为 `N`，然后与 `.chrinfo` 文件中的正则模式匹配。`.chrinfo` 的模式由 `coreCalculateScore.py` 的 `printchr()` 函数生成，该函数将 chrlist 中染色体名的 `N` 替换为 `[0-9]` 或 `[0-9][0-9]` 作为正则。

问题在于 NCBI RefSeq 染色体命名（如 `CM059866.1`）中不含 `N` 字符，`printchr()` 生成的模式就是原样字符串，而 `coreCorrectTotal.py` 将数字替换为 `N` 后的字符串与之无法匹配，导致所有基因对都标为 "unknown"。

简单来说：
- chrlist 内容：`CM059866.1`（无 `N`）
- `printchr()` 生成模式：`CM059866.1`（原样，无正则通配）
- `coreCorrectTotal` 将 `CM059866.1` 替换为 `CMNNNNNN.N`
- 匹配 `CMNNNNNN.N` ≠ `CM059866.1` → "unknown"

### 解决

修改 GeneTribe 源码 `coreCorrectTotal.py`，匹配失败时保留 BED 中的实际染色体名而非标 "unknown"：

```python
# 修改前（coreCorrectTotal.py:46）
i[3] = "unknown"

# 修改后
i[3] = beddc[i[1]]    # 保留实际的染色体名
```

---

## 问题 6：genetribe_result 目录为空

### 错误现象

`genetribe_result/{Ref}_vs_{Query}/` 目录存在但为空，结果文件散落在 `$OUTPUT_DIR` 中。

### 根因

GeneTribe 的 `core.sh` 将结果文件（`.one2one`、`.RBH` 等）通过 `mv` 移到 `genetribe_output/` 的父目录（即 `$OUTPUT_DIR`），而非 `-d` 参数指定的目录。`-d` 参数实际含义是"预计算的 BLAST 文件所在目录"，不是输出目录。

### 解决

在 genetribe core 完成后，将结果文件从 `$OUTPUT_DIR` 移到 `genetribe_result/` 子目录：

```bash
genetribe core -l "$ref_sp" -f "$q" -d "$out" || true
result_dir="$out"
for ext in one2one one2many RBH SBH singleton block_pos collinearity_info; do
    for f in "${ref_sp}_${q}.${ext}" "${q}_${ref_sp}.${ext}"; do
        [[ -f "$f" ]] && mv "$f" "$result_dir/"
    done
done
```

---

## 修改清单

以下是本次排查中涉及的所有文件修改：

| 文件 | 修改内容 |
|------|----------|
| `scripts/ncbi/homolog/run_genetribe.sh` | BED 输出限制 6 列；conda PATH 优先级修复；genetribe core 前预链接 .cds/.bed/.pep；移除重复 jcvi 调用；结果整理到 genetribe_result/ |
| `genetribe/src/coreCorrectTotal.py` | 匹配失败时输出实际染色体名而非 "unknown"（第 46 行） |
