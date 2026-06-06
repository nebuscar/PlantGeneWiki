#!/bin/bash
# Batch homolog analysis for all A-prefix genera with >=2 species

LOG=/home/nizhu/Projects/plantsdb/logs/A_homolog_batch.log
PIPELINE=/home/nizhu/Projects/plantsdb/scripts/imp/run_imp_pipeline.sh

GENERA_REPS=(
    Adansonia_digitata
    Arachis_cardenasii
    Arabidopsis_arenosa
    Avena_atlantica
    Aegilops_bicornis
    Actinidia_arguta
    Acer_campestre
    Artemisia_annua
    Ambrosia_artemisiifolia
    Amborella_trichopoda
    Amaranthus_cruentus
    Allium_cepa
    Asparagus_officinalis
    Aristolochia_contorta
    Arctium_lappa
    Arabis_alpina
    Aquilegia_coerulea
    Annona_cherimola_Booth
    Andropogon_gerardi_hap1
    Albizia_julibrissin
    Ajuga_chamaepitys
)

total=${#GENERA_REPS[@]}
done_count=0

for rep in "${GENERA_REPS[@]}"; do
    genus=$(echo "$rep" | sed 's/^\([A-Za-z]*\)_.*/\1/')
    tsv="/home/nizhu/Projects/plantsdb/result/result_imp/homolog/${genus}/${genus}_homolog_1v1.tsv"

    # Skip if already completed (>10 lines means real data)
    if [ -f "$tsv" ] && [ $(wc -l < "$tsv") -gt 10 ]; then
        echo "[$(date +%H:%M:%S)] SKIP $genus (already done)" | tee -a "$LOG"
        done_count=$((done_count+1))
        continue
    fi

    echo "[$(date +%H:%M:%S)] [$((done_count+1))/$total] Homolog: $genus (rep: $rep)" | tee -a "$LOG"
    bash "$PIPELINE" -m homolog -g -s "$rep" >> "$LOG" 2>&1
    echo "[$(date +%H:%M:%S)] Done: $genus" | tee -a "$LOG"
    done_count=$((done_count+1))
done

echo "[$(date +%H:%M:%S)] All A-prefix homolog done." | tee -a "$LOG"
