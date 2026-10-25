#!/usr/bin/env bash
# One-time setup of the subscription secrets. You type the secret values; they go
# straight into Cloudflare and into ~/.config/canvass-and-analyze/notify.env (only you can read it).
set -euo pipefail
cd "$(dirname "$0")/.."

WORKER_URL=$(python3 -c "import json;print(json.load(open('subscribe/site.json'))['worker_url'])")
[ -n "$WORKER_URL" ] || { echo "Deploy the Worker first (subscribe/site.json has no worker_url)."; exit 1; }
GMAIL_ADDRESS="canvassandanalyze@gmail.com"

echo "Setting up email subscriptions for $WORKER_URL"
read -rp  "Turnstile SITE key (public, starts with 0x): " SITE_KEY
read -rsp "Turnstile SECRET key (hidden): " TURNSTILE_SECRET; echo
read -rsp "Gmail app password for $GMAIL_ADDRESS (16 letters, hidden): " GMAIL_APP_PASSWORD; echo
GMAIL_APP_PASSWORD=${GMAIL_APP_PASSWORD// /}
ADMIN_TOKEN=$(openssl rand -hex 32)

cd subscribe
printf '%s' "$GMAIL_APP_PASSWORD" | npx wrangler secret put GMAIL_APP_PASSWORD >/dev/null
printf '%s' "$TURNSTILE_SECRET"   | npx wrangler secret put TURNSTILE_SECRET >/dev/null
printf '%s' "$ADMIN_TOKEN"        | npx wrangler secret put ADMIN_TOKEN >/dev/null
cd ..

python3 - "$SITE_KEY" <<'PY'
import json, sys
p = "subscribe/site.json"; d = json.load(open(p)); d["turnstile_site_key"] = sys.argv[1].strip()
json.dump(d, open(p, "w"), indent=2); open(p, "a").write("\n")
PY

mkdir -p ~/.config/canvass-and-analyze
umask 077
cat > ~/.config/canvass-and-analyze/notify.env <<ENV
WORKER_URL=$WORKER_URL
ADMIN_TOKEN=$ADMIN_TOKEN
GMAIL_ADDRESS=$GMAIL_ADDRESS
GMAIL_APP_PASSWORD=$GMAIL_APP_PASSWORD
ENV
chmod 600 ~/.config/canvass-and-analyze/notify.env
echo "Done. Secrets are in Cloudflare and ~/.config/canvass-and-analyze/notify.env"
