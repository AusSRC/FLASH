# Set up for Production version (rather than following INSTALL_REQ):
```bash
umask 022
sudo pip install psycopg2-binary numpy astropy astroquery scipy flask
```
## VM setup at Oracle Cloud
A dedicated VM on AusSRC's Oracle infrastructure is set up to host CHAD and the accompanying database. The VM runs an Ubuntu 22.04 OS, and has both private and public subnet access. The VM is at 192.9.187.153, web access served via CLoudflare as chad.aussrc.org

There is a 1TB volume mounted to the VM at /mnt/db. This is an Oracle ISCSI volume, and needs to be made available to the VM instance when rebooted. Upon reboot of the VM, the volume will appear as "attached", and will have a line in /etc/fstab, but that doesn't necessarily mean that it is "available". 

Log into the VM to check (you should see the volume under /mnt/db with a "df- h" command). If it's not there, run the ISCSI commands found on the volume page at Oracle portal. They will look something like this:

sudo iscsiadm -m node -o new -T iqn.2015-12.com.oracleiaas:ee642ad2-4a70-4d18-af5e-7fa68dfb0967 -p 169.254.2.2:3260
sudo iscsiadm -m node -o update -T iqn.2015-12.com.oracleiaas:ee642ad2-4a70-4d18-af5e-7fa68dfb0967 -n node.startup -v automatic
sudo iscsiadm -m node -T iqn.2015-12.com.oracleiaas:ee642ad2-4a70-4d18-af5e-7fa68dfb0967 -p 169.254.2.2:3260 -l

You can now confirm the volume is mounted with:

df -h

## Database setup
Once postgresql is installed, set a password for the postgres user, modify /etc/postgres/12/main/pg_hba.conf 
to allow md5 method (instead of peer) for the postgres user, and edit the password set in: 
   1. files in the chad-main/modules directory.
   2. frontend/db.py

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

## Build chad database
 - change to chad-main directory and run:
```python
python3 build_chad.py --rebuild
```

## Create startup scripts 
 - /etc/chad/chad.sh:

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
