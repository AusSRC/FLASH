# 1. Ensure you run from the checked out FLASH/django directory when building. 
# 2. Copy your real certs to FLASH/django/docker/certs/
# 3. Copy your real DJANGO flashdb.sh and flashdb.ini to FLASH/django/docker/service/
# 4. Copy your real DJANGO settings.py to FLASH/django/docker/
# 5. Edit the cron files in FLASH/django/docker/cron/
# 6. Build with 'sudo docker build -t flashgui .
FROM ubuntu:latest

RUN apt update && \
    apt upgrade -y && \
    apt install -y adduser \
    apt-utils \
    build-essential \
    git \
    iproute2 \
    libssl-dev \
    psmisc \
    python3-dev \
    python3-django \
    python3-pip \
    python3-psycopg2 \
    sudo \
    vim

# Add a flash user and give sudo permissions without password
    # This might already exist:
#RUN addgroup flash && \
RUN adduser --disabled-password --gecos "" flash \
    && echo 'flash ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

EXPOSE 443
WORKDIR /home/flash

# Build uwsgi
RUN git clone https://github.com/unbit/uwsgi.git \
    && cd uwsgi \
    && python3 uwsgiconfig.py --build \
    && cp uwsgi /usr/local/bin

# checkout the django part of the FLASH git repo and configure:
RUN cd /home/flash \
    && mkdir raw_django \
    && git clone -n --depth=1 --filter=tree:0 https://github.com/AusSRC/FLASH raw_django \
    && cd raw_django \
    && git sparse-checkout set --no-cone django \
    && git checkout \
    && cd /home/flash \
    && ln -s raw_django/django django

COPY docker/settings.py /home/flash/django/flashdb/flashdb/
COPY docker/service/*  /home/flash/django/flashdb/service/
COPY docker/certs/*  /home/flash/django/flashdb/certs/

RUN chown -R flash:flash /home/flash \
    && rm -R /home/flash/django/docker

COPY docker/service/flashdb.sh /usr/local/bin
RUN chmod a+x /usr/local/bin/flashdb.sh

USER flash
CMD [ "/usr/local/bin/flashdb.sh" ]
