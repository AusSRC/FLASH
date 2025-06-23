#!/bin/bash
ssh ger063@setonix.pawsey.org.au "cd ~/src/cronjobs; ./casda_download_and_spectral.sh aussrc &> spectral.log;" 
scp ger063@setonix.pawsey.org.au:~/src/cronjobs/spectral.log /home/flash/src/cronjobs/
