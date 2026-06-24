#!/bin/bash
# Batch homolog for A-prefix genera — ordered by species count (small first)
# Skips already-completed genera (tsv > 10 lines)

LOG=/home/nizhu/Projects/plantsdb/logs/A_homolog_batch_v2.log
PIPELINE=/home/nizhu/Projects/plantsdb/scripts/imp/run_imp_pipeline.sh

# Ordered: 2-species genera → 3-species → 5-species → Aegilops (6, last)
GENERA_REPS=(
    # Already done (will be skipped automatically)
    Acorus_americanus
    Adansonia_digitata
    Arachis_cardenasii
    Arabidopsis_arenosa
    Avena_atlantica

    # 2-species genera
    Ajuga_chamaepitys
    Albizia_julibrissin
    Andropogon_gerardi_hap1
    Annona_cherimola_Booth
    Aquilegia_coerulea
    Arabis_alpina
    Arctium_lappa
    Aristolochia_contorta
    Asparagus_officinalis

    # 3-species genera
    Allium_cepa
    Amaranthus_cruentus
    Amborella_trichopoda
    Ambrosia_artemisiifolia
    Artemisia_annua

    # 5-species genera
    Acer_campestre
    Actinidia_arguta

    # 6-species (large genomes, last)
    Aegilops_bicornis
)

total=${#GENERA_REPS[@]}
done_count=0

echo "[$(date +%H:%M:%S)] Start on $(hostname), PID $$" | tee -a "$LOG"

for rep in "${GENERA_REPS[@]}"; do
    genus=$(echo "$rep" | sed 's/^\([A-Za-z]*\)_.*/\1/')
    tsv="/home/nizhu/Projects/plantsdb/result/result_imp/homolog/${genus}/${genus}_homolog_1v1.tsv"

    if [ -f "$tsv" ] && [ "$(wc -l < "$tsv")" -gt 10 ]; then
        echo "[$(date +%H:%M:%S)] SKIP $genus (already done, $(wc -l < "$tsv") lines)" | tee -a "$LOG"
        done_count=$((done_count+1))
        continue
    fi

    echo "[$(date +%H:%M:%S)] [$((done_count+1))/$total] Homolog: $genus (rep: $rep)" | tee -a "$LOG"
    bash "$PIPELINE" -m homolog -g -s "$rep" >> "$LOG" 2>&1
    echo "[$(date +%H:%M:%S)] Done: $genus" | tee -a "$LOG"
    done_count=$((done_count+1))
done

echo "[$(date +%H:%M:%S)] All done. $done_count/$total" | tee -a "$LOG"
