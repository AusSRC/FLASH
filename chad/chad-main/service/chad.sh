#!/bin/bash

# Using Flask development server:
#export FLASK_APP=/home/ubuntu/FLASH/chad/chad-main/frontend/chad
#export FLASK_DEBUG=0
#/usr/local/bin/flask run --cert /etc/ssl/certs/chad.aussrc.org.crt --key /etc/ssl/private/chad.aussrc.org.key -h `ip -o route get to 8.8.8.8 | sed -n 's/.*src \([0-9.]\+\).*/\1/p' ` -p 443

# Using uwsgi production server:
cd /home/ubuntu/FLASH/chad/chad-main/frontend
uwsgi --shared-socket `ip -o route get to 8.8.8.8 | sed -n 's/.*src \([0-9.]\+\).*/\1/p'`:443 --uid ubuntu --https =0,/etc/ssl/certs/chad.aussrc.org.crt,/etc/ssl/private/chad.aussrc.org.key -p 4 -w chad:app

