#!/bin/bash

cd /home/ubuntu/django/flashdb

# Production ssl server using uWSGI: Use route and sed to determine ip address of external-facing interface:
sudo uwsgi --https `ip -o route get to 150.229.69.37 | sed -n 's/.*src \([0-9.]\+\).*/\1/p' `:443,/etc/letsencrypt/live/flash.aussrc.org/fullchain.pem,/etc/letsencrypt/live/flash.aussrc.org/privkey.pem service/flashdb.ini >> service/flashgui.log 2>&1
