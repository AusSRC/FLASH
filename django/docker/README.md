# Before building:
1. Ensure your in the checked out FLASH/django directory when building (contains the Dockerfile). 
2. Copy your real certs to FLASH/django/docker/certs/
3. Copy your real DJANGO flashdb.sh and flashdb.ini to FLASH/django/docker/service/
4. Copy your real DJANGO settings.py to FLASH/django/docker/
5. Build with 'sudo docker build -t flashgui .

