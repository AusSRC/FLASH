#!/bin/bash
##########################################################
# This script will scp the outputs of the linefinder processing
# for an SBID to the Flash VM on Oracle, where it will be uploaded to the
# database. WARNING - it will delete any previous data for this
# SBID.
#########################################################

# Push Detection to Oracle & Push Spectral to Oracle are modified to move all
# relevant files for a run into a folder, make a metadata.txt containing the run
# info such as sbid, quality_flag, run type etc, zip it into a single zip for
# transfer, move it into the transfer folder and mark it as complete

# This script will:
# Check transfer folder on HPC for all zips marked complete
# For each Zip
# Copy the Zip to VM
# Unzip
# Figure out the run type, quality flag etc from the run meta data file
# Upload to DB
# Delete complete marker & zip from VM
# Move zip to scratch uploaded_results folder on HPC

remote="user@remote"
remote_dir="/remote/path"
local_dir="/local/path"

ssh "$remote" '
  cd "'"$remote_dir"'" &&
  for f in *.tar.gz.complete; do
    [ -e "$f" ] || continue
    printf "%s\n" "${f%.complete}"
  done
' | while IFS= read -r file; do
    echo "Copying $file..."

    scp "$remote:$remote_dir/$file" "$local_dir/" || continue

    remote_hash=$(ssh "$remote" "sha256sum '$remote_dir/$file' | cut -d' ' -f1")
    local_hash=$(sha256sum "$local_dir/$file" | cut -d' ' -f1)

    if [[ "$remote_hash" == "$local_hash" ]]; then
        echo "✓ Hash verified: $file"
        # Optional:
        # ssh "$remote" "rm '$remote_dir/$file' '$remote_dir/$file.complete'"
    else
        echo "✗ Hash mismatch: $file"
        rm -f "$local_dir/$file"
    fi
done



echo "Processing ${SBIDARRAY[@]}"

for SBID in "${SBIDARRAY[@]}"; do

    QUALITY=`cat "$DATA"/"$SBID"/data_quality.txt`
    if [ -z "$QUALITY" ]; then
        QUALITY="NOT_VALIDATED"
    fi

    echo "Uploading $SBID spectral plot results via Oracle to database"

    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR; rm -R $SBID/spectra_ascii* $SBID/spectra_plots* $TMPDIR/$SBID* $SBID/logs; mkdir -p $SBID/config $SBID/spectra_plots $SBID/spectra_ascii $SBID/SourceSpectra $SBID/logs;"
    scp -i $ORACLE_KEY $DATA/$SBID/*ascii_tarball.tar.gz flash@$CLIENT:$TMPDIR
    scp -i $ORACLE_KEY $DATA/$SBID/*plots_tarball.tar.gz flash@$CLIENT:$PARENTDIR/$SBID/spectra_plots/

    # Compare the size of the plot tarball with the original
    LOCAL_SIZE=$(stat -c %s $DATA/$SBID/${SBID}_plots_tarball.tar.gz)
    REMOTE_SIZE=$(ssh -i $ORACLE_KEY flash@$CLIENT "stat -c %s $PARENTDIR/$SBID/spectra_plots/${SBID}_plots_tarball.tar.gz")
    if [ "$LOCAL_SIZE" -eq "$REMOTE_SIZE" ]; then
        echo ""
    else
        echo "❌ Failure: plot sizes for $SBID do not match."
        continue
    fi
    echo "Marking spectral data as complete"
    touch $DATA/$SBID/SPECTRAL_COMPLETE.txt
#    scp -i $ORACLE_KEY $DATA/$SBID/config/* flash@$CLIENT:$PARENTDIR/$SBID/config/
#    ssh -i $ORACLE_KEY flash@$CLIENT "mkdir -p $PARENTDIR/$SBID/logs"
#    cat $DATA/$SBID/logs/plot_err*.log | ssh -i $ORACLE_KEY flash@$CLIENT "cat > $PARENTDIR/$SBID/logs/err.log"
#    cat $DATA/$SBID/logs/plot_out*.log | ssh -i $ORACLE_KEY flash@$CLIENT "cat > $PARENTDIR/$SBID/logs/out.log"
#    scp -i $ORACLE_KEY $DATA/catalogues/*$SBID*.xml flash@$CLIENT:$PARENTDIR/catalogues/
#    scp -i $ORACLE_KEY $DATA/$SBID/*Spectra-image*.tar flash@$CLIENT:$PARENTDIR/$SBID/
#    scp -i $ORACLE_KEY $DATA/$SBID/*sources_tarball.tar.gz flash@$CLIENT:$PARENTDIR/$SBID/SourceSpectra/
#    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID/spectra_plots; tar -zxvf *plots_tarball.tar.gz"
#    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID/SourceSpectra; tar -zxvf *sources_tarball.tar.gz"
#    echo "Starting upload to FLASH db"
#    ssh -i $ORACLE_KEY flash@$CLIENT "source ~/set_local_flash_env.sh; cd ~/src/FLASH/database; python3 db_upload.py -m SPECTRAL -q $QUALITY -s $SBID -t $TMPDIR -d $PARENTDIR -pw $FLASHPASS -cs config -C $COMMENT >> $PARENTDIR/$SBID/'$SBID'_spectral_db.log 2>&1"

done
echo "Completed data upload to FLASH db for ${SBIDARRAY[@]}"



    if [ "$MODE" = "STD" ]; then
         echo "Marking Linefinder STD run for $SBID complete"
         touch $DATA/$SBID/LINEFINDER_STD_COMPLETE.txt
#        echo "Uploading $SBID1 linefinder results via Oracle to database"
#
#        # set up directories on Oracle VM
#        ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR; rm -R $SBID1/outputs $SBID1/logs $SBID1/config $TMPDIR/$SBID1*; mkdir -p $SBID1/config $SBID1/logs $SBID1/outputs;"
#        # Copy data to Oracle
#        scp -i $ORACLE_KEY $DATA/$SBID1/linefinder.tar.gz flash@$CLIENT:$PARENTDIR/$SBID1/outputs/
#        scp -i $ORACLE_KEY $DATA/$SBID1/config/* flash@$CLIENT:$PARENTDIR/$SBID1/config/
#        scp -i $ORACLE_KEY $DATA/$SBID1/logs/* flash@$CLIENT:$PARENTDIR/$SBID1/logs/
#        ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID1/outputs; tar -zxvf linefinder.tar.gz; rm linefinder.tar.gz"
#        # Start a db_upload session at Oracle
#        ssh -i $ORACLE_KEY flash@$CLIENT "source ~/set_local_flash_env.sh;cd ~/src/FLASH/database; python3 db_upload.py -m DETECTION -s $SBID1 -t $TMPDIR -d $PARENTDIR -pw $FLASHPASS -cs config -C 'Linefinder_run' >> $PARENTDIR/$SBID1/'$SBID1'_std_detection_db.log 2>&1"
    elif [ "$MODE" = "INVERT" ]; then
        echo "Marking Linefinder INVERT run for $SBID complete"
        touch $DATA/$SBID/LINEFINDER_INVERT_COMPLETE.txt
#        echo "Uploading $SBID1 inverted linefinder results via Oracle to database"
#
#        # set up directories on Oracle VM
#        ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR; rm -R $SBID1/inverted_outputs $SBID1/logs $SBID1/config $TMPDIR/$SBID1*; mkdir -p $SBID1/config $SBID1/logs $SBID1/inverted_outputs;"
#        # Copy data to Oracle
#        scp -i $ORACLE_KEY $DATA/$SBID1/inverted_linefinder.tar.gz flash@$CLIENT:$PARENTDIR/$SBID1/inverted_outputs/
#        scp -i $ORACLE_KEY $DATA/$SBID1/config/* flash@$CLIENT:$PARENTDIR/$SBID1/config/
#        scp -i $ORACLE_KEY $DATA/$SBID1/logs/* flash@$CLIENT:$PARENTDIR/$SBID1/logs/
#        # Start a db_upload session at Oracle
#        ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID1/inverted_outputs; tar -zxvf inverted_linefinder.tar.gz; rm inverted_linefinder.tar.gz"
#        ssh -i $ORACLE_KEY flash@$CLIENT "source ~/set_local_flash_env.sh;cd ~/src/FLASH/database; python3 db_upload.py -m INVERTED -s $SBID1 -t $TMPDIR -d $PARENTDIR -pw $FLASHPASS -cs config -l out_inverted.log -e err_inverted.log -o inverted_outputs -C 'Inverted_linefinder_run' >> $PARENTDIR/$SBID1/'$SBID1'_invert_detection_db.log 2>&1"
    elif [ "$MODE" = "MASK" ]; then
        echo "Marking Linefinder MASK run for $SBID complete"
        touch $DATA/$SBID/LINEFINDER_MASK_COMPLETE.txt

#        echo "Uploading $SBID1 masked linefinder results via Oracle to database"
#
#        # set up directories on Oracle VM
#        ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR; rm -R $SBID1/masked_outputs $SBID1/logs $SBID1/config $TMPDIR/$SBID1*; mkdir -p $SBID1/config $SBID1/logs $SBID1/masked_outputs;"
#        # Copy data to Oracle
#        scp -i $ORACLE_KEY $DATA/$SBID1/masked_linefinder.tar.gz flash@$CLIENT:$PARENTDIR/$SBID1/masked_outputs/
#        scp -i $ORACLE_KEY $DATA/$SBID1/config/* flash@$CLIENT:$PARENTDIR/$SBID1/config/
#        scp -i $ORACLE_KEY $DATA/$SBID1/logs/* flash@$CLIENT:$PARENTDIR/$SBID1/logs/
#        # Start a db_upload session at Oracle
#        ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID1/masked_outputs; tar -zxvf masked_linefinder.tar.gz; rm masked_linefinder.tar.gz"
#        ssh -i $ORACLE_KEY flash@$CLIENT "source ~/set_local_flash_env.sh;cd ~/src/FLASH/database; python3 db_upload.py -m MASKED -s $SBID1 -t $TMPDIR -d $PARENTDIR -pw $FLASHPASS -cs config -l out_masked.log -e err_masked.log -o masked_outputs -C 'masked_linefinder_run' >> $PARENTDIR/$SBID1/'$SBID1'_mask_detection_db.log 2>&1"

    fi

    # Stash the SLURM logs
    mv slurm-*.out $DATA/tmp/
done
exit 0
