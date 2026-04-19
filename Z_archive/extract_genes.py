from Bio import SeqIO
import re

# 文件名配置
cds_file = "cds_from_genomic.fna"
pep_file = "protein.faa"
output_file = "final_result_table.tsv"

def parse_header(header):
    """
    通用解析函数，提取 gene_id, species, genome 等信息
    """
    info = {
        "gene_name": None,
        "species": "Unknown",
        "genome": "Unknown", # 染色体号
        "accession": None    # 原始ID (如 KAL25610.1)
    }

    # 1. 提取 Gene Name (关键连接点)
    # 匹配 gene=XXXX
    m = re.search(r"gene=([^ ]+)", header)
    if m:
        info["gene_name"] = m.group(1)

    # 2. 提取 Species (物种)
    # 匹配 [Arabidopsis thaliana]
    m = re.search(r"\[([^\]]+)\]", header)
    if m:
        info["species"] = m.group(1)

    # 3. 提取 Genome (染色体号) - 重点在这里
    # 针对 NCBI 格式: lcl|CM091602.1_cds_KAL...
    # 我们想要提取 CM091602.1
    m = re.search(r"lcl\|([^\|_]+)", header)
    if m:
        info["genome"] = m.group(1)

    # 4. 提取 Accession ID (如 KAL25610.1)
    # 匹配 cds= 或 ref= 后面的 ID，或者直接取第一个词
    m = re.search(r"cds=([^ ]+)", header)
    if m:
        info["accession"] = m.group(1)
    else:
        # 如果没有 cds=，尝试取标题的第一个部分作为ID
        info["accession"] = header.split()[0]

    return info

# --- 主程序 ---

# 1. 读取 CDS 文件，建立一个以 gene_name 为 key 的字典
cds_dict = {}
print(f"正在读取 CDS 文件: {cds_file} ...")
for record in SeqIO.parse(cds_file, "fasta"):
    info = parse_header(record.description)
    gene_name = info["gene_name"]

    if gene_name:
        # 保存信息：染色体、原始ID、序列
        cds_dict[gene_name] = {
            "genome": info["genome"],
            "cds_id": info["accession"],
            "seq": str(record.seq)
        }

print(f"共找到 {len(cds_dict)} 个基因的 CDS 信息。")

# 2. 读取 PEP 文件，并与 CDS 字典合并
print(f"正在读取 PEP 文件: {pep_file} ...")
with open(output_file, "w") as f:
    # 写入表头
    f.write("gene_id\tspecies\tgenome\tcds_id\tcds_seq\tpep_id\tpep_seq\n")

    count = 0
    for record in SeqIO.parse(pep_file, "fasta"):
        info = parse_header(record.description)
        gene_name = info["gene_name"]

        if gene_name:
            # 获取物种信息 (通常 PEP 文件里的物种信息更准)
            species = info["species"]
            pep_id = info["accession"]
            pep_seq = str(record.seq)

            # 尝试从 CDS 字典中获取对应信息
            if gene_name in cds_dict:
                cds_info = cds_dict[gene_name]
                genome = cds_info["genome"]
                cds_id = cds_info["cds_id"]
                cds_seq = cds_info["seq"]
            else:
                # 如果没找到对应的 CDS (理论上不应该，除非文件不匹配)
                genome = "Unknown"
                cds_id = "No_CDS_Found"
                cds_seq = "Unknown"

            # 写入一行
            f.write(f"{gene_name}\t{species}\t{genome}\t{cds_id}\t{cds_seq}\t{pep_id}\t{pep_seq}\n")
            count += 1

print(f"完成！共合并 {count} 条记录。")
print(f"结果已保存至: {output_file}")
