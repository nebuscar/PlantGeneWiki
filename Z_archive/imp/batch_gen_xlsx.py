#!/usr/bin/env python3
"""批量生成 eggNOG 注释 xlsx 文件"""

import os
import re
import glob
import pandas as pd

DATA_DIR = "/home/nizhu/Projects/plantsdb/data/imp_eggnog"
RESULT_DIR = "/home/nizhu/Projects/plantsdb/result/imp_eggnog"

os.makedirs(RESULT_DIR, exist_ok=True)

for species_dir in glob.glob(f"{DATA_DIR}/*/"):
    species = os.path.basename(species_dir.rstrip('/'))
    full_annot_files = glob.glob(f"{species_dir}/*.full_annotations")

    if not full_annot_files:
        print(f"跳过: {species} (无 full_annotations)")
        continue

    annot_file = full_annot_files[0]
    output_xlsx = f"{RESULT_DIR}/{species}.eggnog_annotation.xlsx"

    print(f"处理: {species}")

    data = []
    with open(annot_file, 'r') as f:
        for line in f:
            if line.startswith('#') or line.startswith('query'):
                continue
            line = line.strip()
            if not line:
                continue
            fields = line.split('\t')
            if len(fields) < 12:
                continue

            query = fields[0]
            go_terms = fields[9] if len(fields) > 9 else ''
            kegg = fields[12] if len(fields) > 12 else ''
            pfam = fields[20] if len(fields) > 20 else ''
            description = fields[7] if len(fields) > 7 else ''

            go_terms_clean = re.sub(r'@.*', '', go_terms)
            kegg_clean = re.sub(r'@.*', '', kegg)

            data.append({
                'Gene_ID': query,
                'GO': go_terms_clean,
                'KEGG': kegg_clean,
                'Pfam': pfam,
                'Function_Description': description
            })

    if data:
        df = pd.DataFrame(data)
        df = df.sort_values('Gene_ID')
        df.to_excel(output_xlsx, sheet_name='eggnog_annotation', index=False)
        print(f"  -> {len(data)} 条记录: {output_xlsx}")
    else:
        print(f"  警告: 无数据")