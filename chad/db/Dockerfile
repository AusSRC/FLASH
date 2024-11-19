# Use the official PostgreSQL image from the Docker library
FROM postgres:16.0

# Install necessary packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    postgresql-contrib \
    postgresql-16-postgis-3 \
    postgresql-16-pgsphere && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set locale
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen

# Copy initialization SQL scripts
COPY init.sql /docker-entrypoint-initdb.d/