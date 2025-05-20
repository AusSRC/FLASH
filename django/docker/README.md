# Before building:
1. Ensure your in the checked out FLASH/django directory when building (contains the Dockerfile). 
2. Copy your real certs to FLASH/django/docker/certs/
3. Copy your real DJANGO flashdb.sh and flashdb.ini to FLASH/django/docker/service/
4. Copy your real DJANGO settings.py to FLASH/django/docker/
5. Edit the cron files in FLASH/django/docker/cron/

# Building
Build with:
    sudo docker build -t flashgui .

# Test Run
Run and check image - you need to run it, to find the image for commit later:
    sudo docker run -u flash -it --entrypoint /bin/bash -p 443:443 flashgui

Commit the image:
    sudo docker ps -l
    sudo docker commit <container ID> aussrc/flashgui

# Certs
In the container, check the certificate:
    sudo certbot certificates
(if required):
    sudo certbot renew



# Production Run
Run with:
    sudo docker run -d -u flash -p 443:443 aussrc/flashgui
 

