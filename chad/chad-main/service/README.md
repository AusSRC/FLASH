# Running Chad as a service

## chad.sh
This script starts the FLASK web server using ip and sed to determine the current external-facing ip address. It should live at `/etc/chad/`. 

 - Set permissions:
```bash
sudo chmod a+x /etc/chad/chad.sh
```

## chad.service
This is the daemon script to start / stop the chad service. It should live at `/etc/systemd/system/`. service is enabled with:

```bash
sudo systemctl daemon-reload
sudo systemctl enable chad.service
```

and can then be started or stopped as normal:

```bash
sudo systemctl start chad.service
```

## HTTPS certs
If running https, create the self-signed certs as normal and move to appropriate directories:

```bash
openssl req -newkey rsa:2048 -nodes -keyout chad.aussrc.org.key -out chad.aussrc.org.csr
openssl x509 -signkey chad.aussrc.org.key -in chad.aussrc.org.csr -req -days 365 -out chad.aussrc.org.crt
sudo cp chad.aussrc.org.crt /etc/ssl/certs/
sudo cp chad.aussrc.org.key chad.aussrc.org.csr /etc/ssl/private/
sudo chown -R root. /etc/ssl/certs /etc/ssl/private
sudo chmod -R 0600 /etc/ssl/certs /etc/ssl/private
```
Modify the chad.sh script to use the certificate:

```bash
...
/usr/local/bin/flask run --cert /etc/ssl/certs/chad.aussrc.org.crt --key /etc/ssl/private/chad.aussrc.org.key -h `ip -o route get to 8.8.8.8 | sed -n 's/.*src \([0-9.]\+\).*/\1/p' ` -p 443
```

