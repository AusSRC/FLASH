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

echo "FLASH_JOB_IMAGE_TAG=$TAG" > /srv/flash/jobs/.env

