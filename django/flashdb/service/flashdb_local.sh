#!/bin/bash

# user's home directory
FHOME=/home/ger063/src/FLASH

cd $FHOME/django/flashdb

# Production ssl server using uWSGI: Use route and sed to determine ip address of external-facing interface:
sudo uwsgi --https 127.0.0.1:443,$FHOME/django/flashdb/certs/fullchain.pem,$FHOME/django/flashdb/certs/privkey.pem service/flashdb_local.ini
