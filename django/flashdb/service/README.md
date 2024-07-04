# Running FLASH as a service

## flashdb.sh
This script starts the uwsgi web server using ip and sed to determine the current external-facing ip address. It should live at `/etc/flashdb/`. 

 - Set permissions:
```bash
sudo chmod a+x /etc/flashdb/flashdb.sh
```

## flashdb.service
This is the daemon script to start / stop the flashdb service. It should live at `/etc/systemd/system/`. service is enabled with:

```bash
sudo systemctl daemon-reload
sudo systemctl enable flashdb.service
```

and can then be started or stopped as normal:

```bash
sudo systemctl start flashdb.service
```
## flash_rotate
This script rotates the logs and restarts the service daily. Copy this to /etc/logrotate.d/
