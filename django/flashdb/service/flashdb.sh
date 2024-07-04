#!/bin/bash

# Using Django development server:
cd /home/ubuntu/django/flashdb

# Use route and sed to determine ip address of external-facing interface:
sudo uwsgi --https `ip -o route get to 150.229.69.37 | sed -n 's/.*src \([0-9.]\+\).*/\1/p' `:443,/etc/letsencrypt/live/flash.aussrc.org/fullchain.pem,/etc/letsencrypt/live/flash.aussrc.org/privkey.pem service/flashdb.ini

# Using Django development server disconnected from terminal (headless):
#cd /home/ubuntu/django/flashdb
#sudo setsid python3 manage.py runsslserver 146.118.64.208:443 --certificate /etc/letsencrypt/live/flash.aussrc.org/fullchain.pem --key /etc/letsencrypt/live/flash.aussrc.org/privkey.pem 1>out_server.log 2>err_server.log


# Using uwsgi production server:
#cd /home/ubuntu/FLASH/chad/chad-main/frontend
#uwsgi --shared-socket `ip -o route get to 8.8.8.8 | sed -n 's/.*src \([0-9.]\+\).*/\1/p'`:443 --uid ubuntu --https =0,/etc/ssl/certs/chad.aussrc.org.crt,/etc/ssl/private/chad.aussrc.org.key -p 4 -w chad:app
# Using Django dev server disconnected from terminal
