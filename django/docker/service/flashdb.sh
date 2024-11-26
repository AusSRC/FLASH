#!/bin/bash

# user's home directory
FHOME=/home/flash
cd $FHOME/django/flashdb || exit 1

# Production server using uWSGI: Use route and sed to determine ip address of external-facing interface:
sudo uwsgi --http `ip -o route get to 150.229.69.37 | sed -n 's/.*src \([0-9.]\+\).*/\1/p'`:8000 service/flashdb.ini