# Set up for system version (all users on ubuntu) rather than following INSTALL_REQ:
```bash
umask 022
sudo pip install psycopg2-binary numpy astropy astroquery scipy flask
```

## Database setup
Once postgresql is installed, set a password for the postgres user, modify /etc/postgres/12/main/pg_hba.conf 
to allow md5 method (instead of peer) for the postges user, and edit the password set in the files in the 
chad-main/modules directory.

## point postgres to external drive (optional)
 - we have a 10TB volume mounted at /mnt/db/
```bash
sudo systemctl stop postgresql
sudo rsync -av /var/lib/postgresql /mnt/db
sudo mv /var/lib/postgresql/12/main /var/lib/postgresql/12/main.bak
```
 - edit /etc/postgresql/12/main/postgresql.conf:
```bash
data_directory = '/mnt/db/postgresql/12/main'
```
 - Restart db:
```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

 - change to chad-main directory and run:
```python
python3 build_chad.py --rebuild
```

## Create startup script /etc/chad/chad.sh:

```bash
#!/bin/bash
export FLASK_APP=/home/ubuntu/chad/chad-main/frontend/chad
export FLASK_DEBUG=1
/usr/local/bin/flask run -h `ip -o route get to 8.8.8.8 | sed -n 's/.*src \([0-9.]\+\).*/\1/p' ` -p 80
```

 - set user permissions:
```bash
sudo chmod a+x /etc/chad/chad.sh
```

 - Create systemd script /etc/systemd/system/chad.service:
```bash
[Unit]
Description= CHAD database frontend service
After=multi-user.target

[Service]
Type=simple
Restart=always
ExecStart=/etc/chad/chad.sh

[Install]
WantedBy=multi-user.target
```


## Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable chad.service
sudo systemctl start chad.service
```
