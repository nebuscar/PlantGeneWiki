project_dir="/home/nizhu/Projects/plantsdb"
meta_dir="/home/nizhu/Projects/plantsdb/data/meta/species_list_with_taxid.txt"
out_dir="$project_dir/downloads/genomes"
include_types="genome,protein,gff3,gbff"

mkdir -p $out_dir

head $meta_dir -n 5
awk -F'\t' 'NR>1 {print $2 "\t" $3}' $meta_dir | sort -u | wc -l
awk -F'\t' 'NR>1 {print $2 "\t" $4}' $meta_dir | sort -u | wc -l
awk -F'\t' 'NR>1 {print $2"|"$2"-"$6"-"$7"-"$8}' $meta_dir | sort -u | wc -l

species=$(awk -F'\t' 'NR>1 {print $2}' $meta_dir | sort -u)

awk -F'\t' 'NR>1 {print $2 "\t" $3}' $meta_dir | sort -u |
    # head -1 |
    while IFS=$'\t' read -r species taxid; do
        species_name=$(echo "$species" | tr ' ' '_')
        species_dir="${out_dir}/${species_name}"
        zip_file="${out_dir}/${species_name}.zip"

        echo "============================="
        echo "下载: $species (TaxID: $taxid)"
        echo "输出路径：$zip_file"
        echo "============================="
        mkdir -p $species_dir
        datasets download genome taxon "$taxid" \
            --include $include_types \
            --filename "${species_dir}.zip" 2>&1 | grep -v "New version"
        if unzip -t $zip_file; then
            echo "解压: $species (TaxID: $taxid)"
            unzip -o $zip_file -d $species_dir
        else
            echo "ZIP文件无效： $species (TaxID: $taxid) "
        fi
    done
