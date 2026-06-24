#!/bin/bash
LOG=/home/nizhu/Projects/plantsdb/logs/test_unavailable.log
PIPELINE=/home/nizhu/Projects/plantsdb/scripts/imp/run_imp_pipeline.sh

GENERA_REPS=(
    Arctium_lappa
    Artemisia_annua
    Asparagus_officinalis
    Allium_cepa
    Ambrosia_artemisiifolia
    Aristolochia_fimbriata
    Andropogon_gerardi_hap1
    Amborella_trichopoda
)

echo "[$(date +%H:%M:%S)] Start test on $(hostname), PID $$" | tee -a "$LOG"

for rep in "${GENERA_REPS[@]}"; do
    genus=$(echo "$rep" | sed 's/^\([A-Za-z]*\)_.*/\1/')
    tsv="/home/nizhu/Projects/plantsdb/result/result_imp/homolog/${genus}/${genus}_homolog_1v1.tsv"

    if [ -f "$tsv" ] && [ "$(wc -l < "$tsv")" -gt 10 ]; then
        echo "[$(date +%H:%M:%S)] SKIP $genus (already done)" | tee -a "$LOG"
        continue
    fi

    echo "[$(date +%H:%M:%S)] Testing $genus (rep: $rep)..." | tee -a "$LOG"
    bash "$PIPELINE" -m homolog -g -s "$rep" >> "$LOG" 2>&1
    rc=$?

    lines=0
    [ -f "$tsv" ] && lines=$(wc -l < "$tsv")
    echo "[$(date +%H:%M:%S)] Done $genus: exit=$rc, TSV=$lines lines" | tee -a "$LOG"
    echo "---" | tee -a "$LOG"
done

echo "[$(date +%H:%M:%S)] All tests complete." | tee -a "$LOG"
