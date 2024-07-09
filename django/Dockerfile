# 1. Ensure you run from the checked out FLASH/django directory when building. 
# 2. Copy your real certs to FLASH/django/docker/certs/
# 3. Copy your real DJANGO flashdb.sh and flashdb.ini to FLASH/django/docker/service/
# 4. Copy your real DJANGO settings.py to FLASH/django/docker/
# 5. Build with 'sudo docker build -t flashgui .
FROM ubuntu:latest

RUN apt update && \
    apt upgrade -y && \
    apt install -y adduser \
    apt-utils \
    build-essential \
    git \
    iproute2 \
    libssl-dev \
    python3-dev \
    python3-django \
    python3-pip \
    python3-psycopg2 \
    sudo \
    vim \
    && useradd -ms /bin/bash flash \
    #&& adduser flash sudo
    && usermod -aG sudo flash

EXPOSE 443
WORKDIR /home/flash

# Build uwsgi
RUN git clone https://github.com/unbit/uwsgi.git && \
    cd uwsgi && \
    python3 uwsgiconfig.py --build && \
    cp uwsgi /usr/local/bin

# checkout the django part of the FLASH git repo and configure:
RUN cd ~/ && \
    mkdir raw_django && \
    git clone -n --depth=1 --filter=tree:0 https://github.com/AusSRC/FLASH raw_django && \
    cd raw_django && \
    git sparse-checkout set --no-cone django && \
    git checkout && \
    cd ~/ && \
    ln -s raw_django/django django

COPY docker/settings.py /home/FLASH/django/flashdb/flashdb/
COPY docker/service/*  /home/flash/django/flashdb/service/
COPY docker/certs/*  /home/flash/django/flashdb/certs

RUN chown -R flash:flash /home/flash

USER flash
ENTRYPOINT [ "sudo uwsgi --https `ip -o route get to 150.229.69.37 | sed -n 's/.*src \([0-9.]\+\).*/\1/p' `:443,/home/flash/django/flashdb/certs/fullchain.pem,/home/flash/django/flashdb/certs/privkey.pem /home/flash/django/flashdb/service/flashdb.ini" ]
