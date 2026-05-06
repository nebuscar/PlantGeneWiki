#!/bin/bash
# Rename IMP species directories and files from short code to full scientific name
set -uo pipefail

IMP_DIR="/DATA/data2/downloads/IMP"
MANIFEST="${HOME}/Projects/plantsdb/downloads/IMP/species_manifest.tsv"

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Rename IMP species directories and internal files from short code to full scientific name.

Options:
  -d, --dry-run   Show what would be renamed without doing it
  -h, --help      Show this help

Example:
  $0 --dry-run    # preview changes
  $0              # execute rename
EOF
}

DRY_RUN=false
while [[ $# -gt 0 ]]; do
    case "$1" in
    -d | --dry-run) DRY_RUN=true; shift ;;
    -h | --help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# Read manifest into associative array: code -> (full_name, directory_name)
declare -A CODE_TO_NAME
declare -A CODE_TO_DIR
while IFS=$'\t' read -r code name dir; do
    [[ "$code" == "Species_Code" ]] && continue
    [[ -z "$code" ]] && continue
    CODE_TO_NAME["$code"]="$(echo "$name" | tr ' ' '_')"
    CODE_TO_DIR["$code"]="$dir"
done < "$MANIFEST"

echo "Loaded ${#CODE_TO_NAME[@]} species mappings from manifest"
echo ""

renamed_dir=0
renamed_file=0
skipped=0

for code in "${!CODE_TO_NAME[@]}"; do
    full_name="${CODE_TO_NAME[$code]}"
    target_dir="${CODE_TO_DIR[$code]}"  # actual directory name from manifest
    old_dir="${IMP_DIR}/${code}"
    new_dir="${IMP_DIR}/${full_name}"

    # Case 1: directory exists with short code (e.g., Aar6/ exists)
    if [[ -d "$old_dir" && "$code" != "$target_dir" ]]; then
        if [[ -d "$new_dir" ]]; then
            echo "  [SKIP] ${code}/ → ${full_name}/ (target exists)"
            ((skipped++)) || true
        else
            if $DRY_RUN; then
                echo "  [DRY] ${code}/ → ${full_name}/"
            else
                mv "$old_dir" "$new_dir"
                ((renamed_dir++)) || true
                echo "  [RENAME] ${code}/ → ${full_name}/"
            fi
        fi
        old_prefix="${code}."
        new_prefix="${full_name}."
        work_dir="$new_dir"
    # Case 2: directory already named correctly (e.g., Abrus_pulchellus/ exists)
    elif [[ -d "$new_dir" && "$code" != "$target_dir" ]]; then
        work_dir="$new_dir"
        old_prefix="${code}."
        new_prefix="${full_name}."
        echo "  [FOUND] ${full_name}/ (needs file rename: ${code}.* → ${full_name}.*)"
    elif [[ "$code" == "$target_dir" ]]; then
        ((skipped++)) || true
        continue
    else
        ((skipped++)) || true
        continue
    fi

    # Rename internal files: replace short code prefix with full name prefix
    if [[ -d "$work_dir" ]] && [[ -n "${old_prefix}" ]]; then
        if ls "${work_dir}/${old_prefix}"* 1>/dev/null 2>&1; then
            for f in "${work_dir}/${old_prefix}"*; do
                [[ -f "$f" ]] || continue
                fname=$(basename "$f")
                new_fname="${fname//${old_prefix}/${new_prefix}}"
                if $DRY_RUN; then
                    echo "      [DRY] ${fname} → ${new_fname}"
                else
                    mv "$f" "${work_dir}/${new_fname}"
                    ((renamed_file++)) || true
                    echo "      [RENAME] ${fname} → ${new_fname}"
                fi
            done
        fi
    fi
done

echo ""
echo "Done. Directories: ${renamed_dir}, Files: ${renamed_file}, Skipped: ${skipped}"
