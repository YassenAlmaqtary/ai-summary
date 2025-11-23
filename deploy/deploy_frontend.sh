#!/usr/bin/env bash
set -e

APP_DIR="/opt/ai-summary/front-end"
DIST_DIR="/var/www/ai-summary"

echo "[*] Building frontend..."
cd "$APP_DIR"
npm install --no-audit --no-fund
npm run build

echo "[*] Sync dist -> $DIST_DIR"
sudo mkdir -p "$DIST_DIR"
sudo rsync -a --delete dist/ "$DIST_DIR"/
sudo chown -R www-data:www-data "$DIST_DIR"
echo "[+] Done."
