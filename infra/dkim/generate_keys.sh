#!/usr/bin/env sh
set -eu

DOMAIN="${1:?domain required}"
OUT_DIR="$(dirname "$0")"
PRIVATE_KEY="$OUT_DIR/private.key"
PUBLIC_KEY="$OUT_DIR/public.key"

openssl genrsa -out "$PRIVATE_KEY" 2048
openssl rsa -in "$PRIVATE_KEY" -pubout -out "$PUBLIC_KEY"
echo "DKIM keys written to $PRIVATE_KEY and $PUBLIC_KEY for $DOMAIN"
