#!/bin/bash

# user's home directory
FHOME=/home/flash/src/FLASH

cd $FHOME/django/flashdb

# Production ssl server using uWSGI: Use route and sed to determine ip address of external-facing interface:
#sudo uwsgi --https `ip -o route get to $IPCHECK | sed -n 's/.*src \([0-9.]\+\).*/\1/p' `:443,$FHOME/django/flashdb/certs/fullchain.pem,$FHOME/django/flashdb/certs/privkey.pem service/flashdb.ini >> service/flashgui.log 2>&1
sudo uwsgi --https :443,$FHOME/django/flashdb/certs/fullchain.pem,$FHOME/django/flashdb/certs/privkey.pem service/flashdb.ini >> service/flashgui.log 2>&1
