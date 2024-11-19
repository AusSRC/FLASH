#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Treat unset variables as an error and exit immediately
set -u

# Ensure the script exits if any command in a pipeline fails
set -o pipefail

# Replace these variables
DOMAIN="chad-dev.aussrc.org"
EMAIL="operations@aussrc.org"
STAGING=1 # Set to 1 if you're testing your setup to avoid hitting request limits

# Create letsencrypt and www directories in certs if they don't exist
mkdir -p ./certs/letsencrypt
mkdir -p ./certs/www

# Determine whether to use the staging environment
if [ "$STAGING" -ne 0 ]; then
    STAGING_ARG="--staging"
else
    STAGING_ARG=""
fi

# Request the certificate
docker run --rm -p 80:80 -v "./letsencrypt:/etc/letsencrypt" \
    certbot/certbot certonly --standalone -d "$DOMAIN" \
    --email "$EMAIL" --agree-tos --non-interactive
