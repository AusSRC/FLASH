#!/bin/bash
export FLASK_APP=/home/ubuntu/FLASH/chad/chad-main/frontend/chad
export FLASK_DEBUG=1
/usr/local/bin/flask run --cert /etc/ssl/certs/chad.aussrc.org.crt --key /etc/ssl/private/chad.aussrc.org.key -h `ip -o route get to 8.8.8.8 | sed -n 's/.*src \([0-9.]\+\).*/\1/p' ` -p 443

