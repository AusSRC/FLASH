#!/usr/bin/env bash
set -euo pipefail

# Prefer explicit argument if passed
TAG="${SSH_ORIGINAL_COMMAND##* }"

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

docker compose pull

#docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py collectstatic --noinput

docker compose up -d --remove-orphans