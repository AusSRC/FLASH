# The above was replaced by Dockerfile July 2024. Prior to build, ensure all code changes are committed to the git repo. Build with:

# 1. Ensure you run from the checked out FLASH/django directory when building. 
# 2. Copy your real certs to FLASH/django/docker/certs/
# 3. Copy your real DJANGO flashdb.sh and flashdb.ini to FLASH/django/docker/service/
# 4. Copy your real DJANGO settings.py to FLASH/django/docker/
# 5. Edit Dockerfile as required (eg check the ENV values)
# 6. Build with 'sudo docker build -t flashgui .' (add "--no-cache" for complete rebuild).

# Run and check image - you need to run it, to find the image for commit later:
sudo docker run -u flash --entrypoint /bin/bash -p 443:443 -it flashgui

# Commit image:
sudo docker ps -l
sudo docker commit <container ID> aussrc/flashgui

# Push to DockerHub repo:
sudo docker login --username=gordonwh # passwd = dh#....2020
sudo docker push aussrc/flashgui


# Production run:

# Ensure container is not already running:
sudo docker container ls
# If so, kill it (eg container name = "great_engelbart"):
sudo docker rm -f great_engelbart
# Get latest image:
sudo docker pull aussrc/flashgui

# Run container:
sudo docker run -d -u flash -p 443:443 -t aussrc/flashgui
# NOTE if the entrypoint doesn't run, just pass the script to the run command 
# (this is the path to the script within the container):
sudo docker run -d -u flash -p 443:443 -t aussrc/flashgui /usr/local/bin/flashdb.sh

# Can log into running container:
sudo docker ps -l # get name
sudo docker exec -u flash -it <name> /bin/bash

# Ensure it restarts with docker daemon restart:
sudo docker update --restart=unless-stopped <container ID>
 

