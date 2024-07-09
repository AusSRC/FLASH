#!/bin/bash
cd /home/flash/django/flashdb/db_query/static/db_query/plots
find . -name "*.*" -type f -mmin +3 -delete
cd /home/flash/django/flashdb/db_query/static/db_query/linefinder
find . -name "*.*" -type f -mmin +3 -delete
