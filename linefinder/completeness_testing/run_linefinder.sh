#!/bin/bash

START=1
END=9
for ((i=$START;i<=$END;i++));

do
 jid=$(sbatch ~/slurm_run_job.sh $i)
 j1=$(echo $jid | awk '{print $4}')
 echo "Submitted" $j1
done

