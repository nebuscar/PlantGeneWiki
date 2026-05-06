#!/usr/bin/env python3
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests

BASE_DIR = "/home/nizhu/Projects/plantsdb"
DOWNLOAD_DIR = "/DATA/data2/downloads/IMP"
IMP_BASE = "https://www.bic.ac.cn/data2t/html/IMP/public/data"

# URL uses species code; local output filename uses full directory name (dir)
FILE_TYPES = {
    "genome":    {"url": "igv/{code}/{code}.fa.gz",               "out": "{dir}.fa.gz"},
    "annotation":{"url": "igv/{code}/{code}.gff3.gz",             "out": "{dir}.gff3.gz"},
    "gene":      {"url": "blast/{code}.gene.fasta",               "out": "{dir}.gene.fasta"},
    "cds":       {"url": "blast/{code}.CDS.fasta",                "out": "{dir}.CDS.fasta"},
    "protein":   {"url": "blast/{code}.prot.fasta",               "out": "{dir}.prot.fasta"},
    "promoter":  {"url": "blast/{code}.promoter2k.fasta",         "out": "{dir}.promoter2k.fasta"},
    "tpm":       {"url": "expr_matrix/{code}.all.rnaseq.TPM.txt", "out": "{dir}.all.rnaseq.TPM.txt"},
}


def load_manifest(path):
    """Load species list from TSV or JSON manifest."""
    species = []
    if not os.path.exists(path):
        return species
    if path.endswith('.json'):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        for item in data.get('species', []):
            code = item.get('code', '')
            name = item.get('name', code)
            dir_name = item.get('dir', name.replace(' ', '_'))
            if code:
                species.append({'code': code, 'name': name, 'dir': dir_name})
        return species
    with open(path, encoding='utf-8') as f:
        f.readline()  # skip header
        for line in f:
            parts = line.strip().split('\t')
            if not parts[0]:
                continue
            code = parts[0]
            name = parts[1] if len(parts) > 1 else code
            dir_name = parts[2] if len(parts) > 2 else name.replace(' ', '_')
            species.append({'code': code, 'name': name, 'dir': dir_name})
    return species


def is_valid(path):
    """Return True if file exists and is non-empty."""
    return os.path.isfile(path) and os.path.getsize(path) > 0


def out_filename(dir_name, ftype):
    return FILE_TYPES[ftype]['out'].format(dir=dir_name)


def check_files(species_dir, dir_name):
    """Return dict of file_type -> bool indicating whether local file is valid."""
    return {
        ftype: is_valid(os.path.join(species_dir, out_filename(dir_name, ftype)))
        for ftype in FILE_TYPES
    }


def build_url(code, ftype):
    return f"{IMP_BASE}/{FILE_TYPES[ftype]['url'].format(code=code)}"


def download_file(url, dest, timeout=120):
    """Download url to dest. Returns 'ok', '404', or error string."""
    try:
        r = requests.get(url, stream=True, timeout=timeout)
        if r.status_code == 404:
            return '404'
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        # guard against HTML error pages saved as file content
        if os.path.getsize(dest) < 200:
            snippet = open(dest, 'rb').read(200).lower()
            if b'<html' in snippet or b'forbidden' in snippet:
                os.remove(dest)
                return 'html-error'
        return 'ok'
    except Exception as e:
        return str(e)


def download_species(sp_info, output_dir, skip_existing=True, dry_run=False):
    """Download all file types for one species. Returns (dir_name, results_dict)."""
    code = sp_info['code']
    dir_name = sp_info['dir']
    species_dir = os.path.join(output_dir, dir_name)

    if not dry_run:
        os.makedirs(species_dir, exist_ok=True)

    file_status = check_files(species_dir, dir_name)
    results = {}

    for ftype in FILE_TYPES:
        if skip_existing and file_status[ftype]:
            results[ftype] = 'skip'
            continue

        url = build_url(code, ftype)
        dest = os.path.join(species_dir, out_filename(dir_name, ftype))

        if dry_run:
            results[ftype] = f'dry:{url}'
            continue

        results[ftype] = download_file(url, dest)

    return dir_name, results


def main():
    parser = argparse.ArgumentParser(description="IMP download manager")
    parser.add_argument('--manifest', help="species manifest TSV/JSON")
    parser.add_argument('--outdir', default=DOWNLOAD_DIR)
    parser.add_argument('--logdir', default=f"{DOWNLOAD_DIR}/logs")
    parser.add_argument('--species', help="single species code (for testing)")
    parser.add_argument('--prefix', help="only process species whose dir_name starts with this prefix")
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--no-skip', action='store_true', help="re-download existing files")
    parser.add_argument('--limit', type=int)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(args.logdir, exist_ok=True)

    if args.species:
        species_list = [{'code': args.species, 'name': args.species, 'dir': args.species}]
    else:
        json_path = f"{BASE_DIR}/data/meta/imp/species_list.json"
        tsv_path = f"{BASE_DIR}/data/meta/imp/species_manifest.tsv"
        manifest = args.manifest or (json_path if os.path.exists(json_path) else tsv_path)
        if not os.path.exists(manifest):
            print("ERROR: no manifest found", file=sys.stderr)
            sys.exit(1)
        species_list = load_manifest(manifest)

    if args.prefix:
        species_list = [s for s in species_list if s['dir'].startswith(args.prefix)]

    if args.limit:
        species_list = species_list[:args.limit]

    skip_existing = not args.no_skip
    print(f"species: {len(species_list)}, threads: {args.threads}, skip_existing: {skip_existing}")

    log_path = os.path.join(args.logdir, "imp_download.log")
    fail_path = os.path.join(args.logdir, "imp_fail.log")
    # availability: dir_name -> status string, persisted to species_availability.tsv
    avail_path = os.path.join(BASE_DIR, "data/meta/imp/species_availability.tsv")
    counts = {'ok': 0, 'skip': 0, 'fail': 0}
    total = len(species_list)

    # load existing availability records so incremental runs preserve prior results
    availability = {}
    if os.path.exists(avail_path):
        with open(avail_path, encoding='utf-8') as f:
            f.readline()
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    availability[parts[0]] = {'code': parts[1], 'status': parts[2]}

    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = {
            pool.submit(download_species, sp, args.outdir, skip_existing, args.dry_run): sp
            for sp in species_list
        }
        done = 0
        for future in as_completed(futures):
            done += 1
            sp = futures[future]
            try:
                dir_name, results = future.result()
            except Exception as e:
                print(f"[{done}/{total}] ERROR {sp['dir']}: {e}")
                counts['fail'] += 1
                continue

            ok = sum(1 for v in results.values() if v == 'ok')
            skipped = sum(1 for v in results.values() if v == 'skip')
            not_found = sum(1 for v in results.values() if v == '404')
            failed = {k: v for k, v in results.items()
                      if v not in ('ok', 'skip') and not v.startswith('dry:') and v != '404'}

            # determine availability status
            if not args.dry_run:
                total_files = len(FILE_TYPES)
                if not_found == total_files:
                    status = 'unavailable'
                elif not_found > 0:
                    status = 'partial'
                else:
                    status = 'available'
                availability[dir_name] = {'code': sp['code'], 'status': status}

            parts = []
            if ok:        parts.append(f"ok={ok}")
            if skipped:   parts.append(f"skip={skipped}")
            if not_found: parts.append(f"404={not_found}")
            if failed:    parts.append(f"fail={list(failed.keys())}")
            print(f"[{done}/{total}] {dir_name}: {' '.join(parts) or 'all-skipped'}")

            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(log_path, 'a') as f:
                f.write(f"[{ts}] {dir_name}: {results}\n")
            if failed:
                counts['fail'] += 1
                with open(fail_path, 'a') as f:
                    f.write(f"{dir_name}\t{failed}\n")
            elif ok:
                counts['ok'] += 1
            else:
                counts['skip'] += 1

    # write availability table (sorted by dir_name)
    if not args.dry_run and availability:
        with open(avail_path, 'w', encoding='utf-8') as f:
            f.write("Directory_Name\tSpecies_Code\tStatus\n")
            for dir_name in sorted(availability):
                rec = availability[dir_name]
                f.write(f"{dir_name}\t{rec['code']}\t{rec['status']}\n")
        unavail = sum(1 for r in availability.values() if r['status'] == 'unavailable')
        partial = sum(1 for r in availability.values() if r['status'] == 'partial')
        print(f"availability: {len(availability)} total, {unavail} unavailable, {partial} partial -> {avail_path}")

    print(f"done: ok={counts['ok']} skip={counts['skip']} fail={counts['fail']}")


if __name__ == '__main__':
    main()
