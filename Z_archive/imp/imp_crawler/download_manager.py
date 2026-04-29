#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMP 下载管理器
使用wget批量下载IMP基因组数据，支持增量更新
"""

import os
import argparse
import subprocess
import time
import json
from datetime import datetime

BASE_DIR = "/home/nizhu/Projects/plantsdb"
DOWNLOAD_DIR = f"{BASE_DIR}/downloads/IMP"

# IMP下载链接基础URL
IMP_DATA_BASE = "https://www.bic.ac.cn/data2t/html/IMP/public/data"

# 文件类型配置 - 对应下载链接
FILE_TYPES = {
    "genome": {
        "path": "igv/{code}/{code}.fa.gz",
        "desc": "Genome sequences"
    },
    "annotation": {
        "path": "igv/{code}/{code}.gff3.gz",
        "desc": "Genome annotation"
    },
    "gene": {
        "path": "blast/{code}.gene.fasta",
        "desc": "Gene sequences"
    },
    "cds": {
        "path": "blast/{code}.CDS.fasta",
        "desc": "CDS sequences"
    },
    "protein": {
        "path": "blast/{code}.prot.fasta",
        "desc": "Protein sequences"
    },
    "promoter": {
        "path": "blast/{code}.promoter2k.fasta",
        "desc": "Promoter sequences"
    },
    "tpm": {
        "path": "expr_matrix/{code}.all.rnaseq.TPM.txt",
        "desc": "Gene expression TPM matrix"
    },
}


def get_species_from_manifest(manifest_file):
    """从manifest文件读取物种列表"""
    species_list = []
    if not os.path.exists(manifest_file):
        return species_list

    # 支持TSV和JSON格式
    if manifest_file.endswith('.json'):
        with open(manifest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data.get('species', []):
                if isinstance(item, dict):
                    species_list.append({
                        'code': item.get('code', ''),
                        'name': item.get('name', item.get('code', '')),
                        'dir': item.get('dir', item.get('name', item.get('code', '')).replace(' ', '_'))
                    })
                else:
                    code = str(item)
                    species_list.append({'code': code, 'name': code, 'dir': code})
        return species_list

    with open(manifest_file, "r", encoding="utf-8") as f:
        header = f.readline()
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                code = parts[0].strip()
                name = parts[1].strip() if len(parts) > 1 else code
                dir_name = parts[2].strip() if len(parts) > 2 else name.replace(' ', '_')
                if code:
                    species_list.append({'code': code, 'name': name, 'dir': dir_name})
    return species_list


def get_species_directories(base_dir):
    """获取已存在的物种目录"""
    species_dirs = []
    if not os.path.exists(base_dir):
        return species_dirs

    # 排除特殊目录
    skip_dirs = {'logs', 'static', 'data', 'api', '.', '..'}

    for item in os.listdir(base_dir):
        if item in skip_dirs:
            continue
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            species_dirs.append(item)
    return species_dirs


def is_valid_file(filepath):
    """检查文件是否有效（存在且大小>0）"""
    return os.path.exists(filepath) and os.path.getsize(filepath) > 0


def check_species_files(species_dir):
    """检查物种目录下的文件情况"""
    file_status = {
        "genome": False,
        "annotation": False,
        "gene": False,
        "cds": False,
        "protein": False,
        "promoter": False,
        "tpm": False,
    }

    if not os.path.exists(species_dir):
        return file_status

    for filename in os.listdir(species_dir):
        filepath = os.path.join(species_dir, filename)
        if not os.path.isfile(filepath):
            continue

        # 检查文件是否有效（大小>0）
        if os.path.getsize(filepath) == 0:
            continue

        # 根据扩展名判断文件类型
        if filename.endswith('.fa.gz') or filename.endswith('_genome.fa'):
            file_status["genome"] = True
        elif filename.endswith('.gff3.gz') or filename.endswith('_annotation.gff3'):
            file_status["annotation"] = True
        elif 'gene' in filename.lower() and filename.endswith('.fasta'):
            file_status["gene"] = True
        elif 'cds' in filename.lower() and filename.endswith('.fasta'):
            file_status["cds"] = True
        elif 'prot' in filename.lower() and filename.endswith('.fasta'):
            file_status["protein"] = True
        elif 'promoter' in filename.lower():
            file_status["promoter"] = True
        elif 'tpm' in filename.lower() or 'rnaseq' in filename.lower():
            file_status["tpm"] = True

    return file_status


def build_download_url(species_code, file_type):
    """构建下载链接"""
    config = FILE_TYPES.get(file_type, {})
    path_template = config.get("path", "")
    return f"{IMP_DATA_BASE}/{path_template.format(code=species_code)}"


def rename_files_to_fullname(species_dir, species_name, species_code):
    """将下载的文件重命名为物种全称格式"""
    # 文件名映射：短码格式 -> 全称格式
    rename_map = {
        f"{species_code}.fa.gz": f"{species_name}_genome.fa.gz",
        f"{species_code}.gff3.gz": f"{species_name}_annotation.gff3.gz",
        f"{species_code}.gene.fasta": f"{species_name}_gene.fasta",
        f"{species_code}.CDS.fasta": f"{species_name}_cds.fasta",
        f"{species_code}.prot.fasta": f"{species_name}_protein.fasta",
        f"{species_code}.promoter2k.fasta": f"{species_name}_promoter.fasta",
        f"{species_code}.all.rnaseq.TPM.txt": f"{species_name}_expression_TPM.txt",
    }

    renamed = []
    for old_name, new_name in rename_map.items():
        old_path = os.path.join(species_dir, old_name)
        new_path = os.path.join(species_dir, new_name)
        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)
            renamed.append((old_name, new_name))

    return renamed


def cleanup_empty_files(species_dir):
    """清理目录中的空文件（大小为0）"""
    cleaned = []
    for filename in os.listdir(species_dir):
        filepath = os.path.join(species_dir, filename)
        if os.path.isfile(filepath) and os.path.getsize(filepath) == 0:
            os.remove(filepath)
            cleaned.append(filename)
    return cleaned


def download_species(species_code, output_dir, dry_run=False, skip_existing=True, species_name=None, dir_name=None):
    """下载单个物种的数据"""
    # 目录名：使用物种全称（清理特殊字符）
    folder_name = dir_name if dir_name else species_code
    species_dir = os.path.join(output_dir, folder_name)

    if not dry_run:
        os.makedirs(species_dir, exist_ok=True)

    display_name = species_name if species_name else species_code
    print(f"\n处理物种: {display_name} ({species_code})")
    print(f"目录: {species_dir}")

    # 检查是否已存在完整数据
    file_status = check_species_files(species_dir)
    complete_count = sum(file_status.values())
    total_count = len(file_status)

    if skip_existing and complete_count == total_count:
        print(f"  ✅ 数据已完整 ({complete_count}/{total_count})，跳过")
        return True, "skipped", file_status
    elif complete_count > 0:
        print(f"  ⚠️ 部分数据存在 ({complete_count}/{total_count})，继续下载缺失部分")
    else:
        print(f"  📥 开始下载...")

    download_results = {}
    success_count = 0

    for file_type, config in FILE_TYPES.items():
        # 跳过已存在的文件
        if skip_existing and file_status[file_type]:
            print(f"  ⏭️ {file_type}: 已存在，跳过")
            download_results[file_type] = "skipped"
            continue

        url = build_download_url(species_code, file_type)
        output_file = os.path.join(species_dir, os.path.basename(url))

        if dry_run:
            print(f"  📥 {file_type}: {url}")
            download_results[file_type] = "dry_run"
            continue

        # 使用wget下载
        print(f"  📥 {file_type}: {url}")
        result = wget_download(url, output_file)
        download_results[file_type] = result

        if result == "success":
            success_count += 1
            print(f"  ✅ {file_type}: 下载成功")
        else:
            print(f"  ❌ {file_type}: 下载失败 ({result})")

        # 限速避免请求过快
        time.sleep(0.5)

    # 清理空文件（下载失败的文件）
    if not dry_run:
        cleaned = cleanup_empty_files(species_dir)
        if cleaned:
            print(f"  🗑️ 清理空文件: {', '.join(cleaned)}")

    # 总体状态
    if dry_run:
        status = "dry_run"
    elif success_count == total_count:
        status = "completed"
    elif success_count > 0:
        status = "partial"
    else:
        status = "failed"

    return True, status, download_results


def wget_download(url, output_file):
    """使用wget下载文件"""
    try:
        # -q: 安静模式
        # --timeout: 超时时间
        # -O: 输出文件
        # --span-opts: 支持重定向
        result = subprocess.run(
            ["wget", "-q", "--timeout=60", "-O", output_file, url],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and os.path.exists(output_file):
            return "success"
        else:
            return "failed"
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception as e:
        return f"error: {e}"


def write_log(log_file, message):
    """写入日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def main():
    parser = argparse.ArgumentParser(description="IMP下载管理器")
    parser.add_argument("--manifest", type=str, help="物种清单TSV/JSON文件路径")
    parser.add_argument("--outdir", type=str, default=DOWNLOAD_DIR, help="输出目录")
    parser.add_argument("--logdir", type=str, default=f"{DOWNLOAD_DIR}/logs", help="日志目录")
    parser.add_argument("--species", type=str, help="指定单个物种代码（测试用）")
    parser.add_argument("--dry-run", action="store_true", help="仅显示，不实际下载")
    parser.add_argument("--limit", type=int, help="限制下载数量")
    parser.add_argument("--no-skip", action="store_true", help="跳过增量检测，重新下载已存在的文件")
    args = parser.parse_args()

    # 创建目录
    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(args.logdir, exist_ok=True)

    # 日志文件
    log_file = os.path.join(args.logdir, "imp_download.log")
    success_log = os.path.join(args.logdir, "imp_success.log")
    fail_log = os.path.join(args.logdir, "imp_fail.log")
    skip_log = os.path.join(args.logdir, "imp_skip.log")

    print("=" * 60)
    print("IMP 下载管理器")
    print("=" * 60)
    print(f"输出目录: {args.outdir}")
    print(f"日志目录: {args.logdir}")

    # 确定要下载的物种列表
    species_to_download = []

    # 优先使用manifest文件（物种列表爬取后会自动生成）
    default_manifest = f"{BASE_DIR}/downloads/IMP/species_manifest.tsv"
    default_json = f"{BASE_DIR}/downloads/IMP/species_list.json"

    if args.species:
        species_to_download = [{'code': args.species, 'name': args.species, 'dir': args.species}]
    elif args.manifest and os.path.exists(args.manifest):
        species_to_download = get_species_from_manifest(args.manifest)
    elif os.path.exists(default_json):
        species_to_download = get_species_from_manifest(default_json)
    elif os.path.exists(default_manifest):
        species_to_download = get_species_from_manifest(default_manifest)
    else:
        # 获取已存在的物种目录
        dirs = get_species_directories(args.outdir)
        species_to_download = [{'code': d, 'name': d, 'dir': d} for d in dirs]

    if args.limit:
        species_to_download = species_to_download[:args.limit]

    print(f"待处理物种数: {len(species_to_download)}")

    if args.dry_run:
        print("\n⚠️ Dry Run模式 - 仅显示，不实际下载")

    skip_existing = not args.no_skip

    # 统计
    success_count = 0
    fail_count = 0
    skip_count = 0
    partial_count = 0

    # 逐个处理物种
    for i, sp_info in enumerate(species_to_download, 1):
        species_code = sp_info.get('code', '')
        species_name = sp_info.get('name', species_code)
        dir_name = sp_info.get('dir', species_code)
        print(f"\n[{i}/{len(species_to_download)}] 处理中...")

        try:
            success, status, details = download_species(
                species_code, args.outdir,
                dry_run=args.dry_run,
                skip_existing=skip_existing,
                species_name=species_name,
                dir_name=dir_name
            )

            if status == "skipped":
                skip_count += 1
                write_log(log_file, f"{species_code} - 已跳过（数据完整）")
                write_log(skip_log, species_code)
            elif status == "completed":
                success_count += 1
                write_log(log_file, f"{species_code} - 成功")
                write_log(success_log, species_code)
            elif status == "partial":
                partial_count += 1
                write_log(log_file, f"{species_code} - 部分成功")
                write_log(success_log, species_code)
            else:
                fail_count += 1
                write_log(log_file, f"{species_code} - 失败")
                write_log(fail_log, species_code)

        except Exception as e:
            fail_count += 1
            write_log(log_file, f"{species_code} - 异常: {e}")
            write_log(fail_log, f"{species_code}\t{e}")

    # 打印统计
    print("\n" + "=" * 60)
    print("下载完成!")
    print(f"成功: {success_count} 个")
    print(f"部分成功: {partial_count} 个")
    print(f"跳过: {skip_count} 个")
    print(f"失败: {fail_count} 个")
    print("=" * 60)
    print(f"\n日志文件:")
    print(f"  总日志: {log_file}")
    print(f"  成功: {success_log}")
    print(f"  失败: {fail_log}")
    print(f"  跳过: {skip_log}")


if __name__ == "__main__":
    main()
