# Running FLASH as a Service

## 1. Install nginx + gunicorn

```bash
sudo apt update
sudo apt install -y nginx gunicorn
```

---

## 2. Remove default nginx site

```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

---

## 3. Remove old flashdb service

```bash
sudo systemctl stop flashdb
sudo systemctl disable flashdb
sudo rm -f /etc/systemd/system/flashdb.service
```

---

## 4. Reload systemd

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
```

---

## 5. Install new flashdb.service

```bash
sudo nano /etc/systemd/system/flashdb.service
```

Paste the contents of:

```text
flashdb.service
```

Then reload systemd again:

```bash
sudo systemctl daemon-reload
```

---

## 6. Configure nginx

### 6.1 Copy nginx config

Copy contents of:

```text
nginx_config.txt
```

into:

```text
/etc/nginx/sites-available/flashdb
```

Example:

```bash
sudo nano /etc/nginx/sites-available/flashdb
```

---

### 6.2 Enable nginx site config

```bash
sudo ln -sf /etc/nginx/sites-available/flashdb /etc/nginx/sites-enabled/flashdb
```

---

## 7. Test nginx config

```bash
sudo nginx -t
```

---

## 8. Enable + start services

```bash
sudo systemctl enable nginx flashdb
sudo systemctl restart nginx
sudo systemctl restart flashdb
```

---

## 9. Verify services healthy

```bash
sudo systemctl status nginx
sudo systemctl status flashdb
```

---

## 10. Verify site + static files

```bash
curl -I https://flash.aussrc.org
curl -I https://flash.aussrc.org/static/db_query/flash.jpeg
```

---

# Logs (rotation is now automatic)
sudo systemctl status flashdb
sudo systemctl status nginx
journalctl -u flashdb -f
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log