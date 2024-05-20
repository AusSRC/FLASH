#!/bin/bash
mkdir -p $1/summary
find $1 -type f -name "results*.dat" -exec awk 'NR==1 || FNR>1' {} + > $1/summary/results_all_$$.txt

