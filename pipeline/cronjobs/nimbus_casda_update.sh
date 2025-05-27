#!/bin/bash
ssh ger063@setonix.pawsey.org.au "cd ~/src/cronjobs; ./casda_updates.sh aussrc &> spectral.log;" 
scp ger063@setonix.pawsey.org.au:~/src/cronjobs/spectral.log /home/ubuntu/cronjobs/
