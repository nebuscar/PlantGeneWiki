#!/bin/bash
# Run fixable genera: Amborella and Andropogon

LOG=/home/nizhu/Projects/plantsdb/logs/fixable_genera.log
PIPELINE=/home/nizhu/Projects/plantsdb/scripts/imp/run_imp_pipeline.sh

echo "[$(date +%H:%M:%S)] Start: Amborella + Andropogon on $(hostname), PID $$" | tee -a "$LOG"

# Amborella: HAP1(27chr,50K) as ref; HAP2(24chr,50K) and trichopoda(1268scaffold,27K) as queries
echo "[$(date +%H:%M:%S)] [1/2] Running Amborella..." | tee -a "$LOG"
bash "$PIPELINE" -m homolog -g -s Amborella_trichopoda >> "$LOG" 2>&1
echo "[$(date +%H:%M:%S)] Amborella done" | tee -a "$LOG"

# Check result
tsv="/home/nizhu/Projects/plantsdb/result/result_imp/homolog/Amborella/Amborella_homolog_1v1.tsv"
if [ -f "$tsv" ]; then
    echo "[$(date +%H:%M:%S)] Amborella TSV: $(wc -l < "$tsv") lines" | tee -a "$LOG"
fi

# Andropogon: hap1(44chr,145K) as ref; hap2(38chr,144K) as query
echo "[$(date +%H:%M:%S)] [2/2] Running Andropogon..." | tee -a "$LOG"
bash "$PIPELINE" -m homolog -g -s Andropogon_gerardi_hap1 >> "$LOG" 2>&1
echo "[$(date +%H:%M:%S)] Andropogon done" | tee -a "$LOG"

tsv="/home/nizhu/Projects/plantsdb/result/result_imp/homolog/Andropogon/Andropogon_homolog_1v1.tsv"
if [ -f "$tsv" ]; then
    echo "[$(date +%H:%M:%S)] Andropogon TSV: $(wc -l < "$tsv") lines" | tee -a "$LOG"
fi

echo "[$(date +%H:%M:%S)] All done." | tee -a "$LOG"
