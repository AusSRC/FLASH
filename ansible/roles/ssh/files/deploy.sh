#!/usr/bin/env bash
set -euo pipefail
umask 0002

# Prefer explicit argument if passed
if [[ $# -ge 1 ]]; then
  TAG="$1"
else
  TAG="${SSH_ORIGINAL_COMMAND##* }"
fi

# Safety check for missing tag
if [[ -z "$TAG" ]]; then
  echo "Missing tag"
  exit 1
fi


#Validate tag
if [[ ! "$TAG" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Invalid tag: $TAG"
  exit 1
fi

export FLASH_IMAGE_TAG="$TAG"
echo "FLASH_JOB_IMAGE_TAG=$TAG" > /etc/flashdb/job_version.env

# Pull the docker image
docker compose pull

# Migrate database (once we start having it managed by django)
#docker compose run --rm web python manage.py migrate

# Tidy up any old staticfiles and media files
rm -rf /srv/flashdb/staticfiles/*
rm -rf /srv/flashdb/media/*

# Create new static files using the docker container
docker compose run --rm web python manage.py collectstatic --noinput

# Start up the nginx and django services and clear up old ones
docker compose up -d --remove-orphans