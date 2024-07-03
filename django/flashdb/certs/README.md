## HTTPS certs
If running https, create the self-signed certs as normal and move to appropriate directories:

```bash
openssl req -newkey rsa:2048 -nodes -keyout flash.aussrc.org.key -out flash.aussrc.org.csr
openssl x509 -signkey flash.aussrc.org.key -in flash.aussrc.org.csr -req -days 365 -out flash.aussrc.org.crt
sudo cp flash.aussrc.org.crt /etc/ssl/certs/
sudo cp flash.aussrc.org.key flash.aussrc.org.csr /etc/ssl/private/
sudo chown -R root. /etc/ssl/certs /etc/ssl/private
sudo chmod -R 0600 /etc/ssl/certs /etc/ssl/private


## Get CA certificates via LetsEncrypt
sudo snap install --classic certbot

# Run the certbot:
sudo certbot certonly --standalone

# This will produce the files:
# Cert: /etc/letsencrypt/live/flash.aussrc.org/fullchain.pem
# Key: /etc/letsencrypt/live/flash.aussrc.org/privkey.pem

## Install package django-runsslserver
sudo pip install django-sslserver

## open the settings.py file in your code editor and add sslserver the INSTALLED_APPS list

# Run server:
sudo python3 manage.py runsslserver 146.118.64.208:443 --certificate /etc/letsencrypt/live/flash.aussrc.org/fullchain.pem --key /etc/letsencrypt/live/flash.aussrc.org/privkey.pem

# Run server disconnected from terminal:
sudo setsid python3 manage.py runsslserver 146.118.64.208:443 --certificate /etc/letsencrypt/live/flash.aussrc.org/fullchain.pem --key /etc/letsencrypt/live/flash.aussrc.org/privkey.pem


