#!/bin/bash

cd /home/flash/django/flashdb

# Production ssl server using uWSGI: Use route and sed to determine ip address of external-facing interface:
sudo uwsgi --https `ip -o route get to 150.229.69.37 | sed -n 's/.*src \([0-9.]\+\).*/\1/p' `:443,/home/flash/django/flashdb/certs/fullchain.pem,/home/flash/django/flashdbcerts/privkey.pem service/flashdb.ini >> service/flashgui.log 2>&1
