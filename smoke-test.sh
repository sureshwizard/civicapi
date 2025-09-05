#!/usr/bin/env bash
set -euo pipefail

# ------------------------------
# CONFIG
# ------------------------------
BASE="https://civic.admnwizard.com/api"
API_KEY="change-me-32chars"   # <- paste your real key here

hdr=(-H "x-api-key: ${API_KEY}")

# helper
say() { printf "\n\033[1m==> %s\033[0m\n" "$*"; }
jqok() { command -v jq >/dev/null 2>&1 && jq . || cat; }

# ------------------------------
# 0. show config
# ------------------------------
say "Using BASE=${BASE}"
say "Using x-api-key=<hidden>"

# ------------------------------
# 1. health check
# ------------------------------
say "HEALTH: GET ${BASE}/"
curl -sS "${BASE}/" | jqok

# ------------------------------
# 2. list all bills
# ------------------------------
say "LIST: GET ${BASE}/bills"
curl -sS "${hdr[@]}" "${BASE}/bills" | jqok

# ------------------------------
# 3. upload (manual fields)
# ------------------------------
VENDOR="Judge Demo Co"
AMOUNT="123.45"
DUE="2025-09-15"
NOTE="uploaded-from-smoke-test"

say "UPLOAD(FIELDS): POST ${BASE}/upload  vendor=${VENDOR}, amount=${AMOUNT}, due_date=${DUE}"
NEW_JSON=$(curl -sS -X POST "${hdr[@]}" -F "vendor=${VENDOR}" -F "amount=${AMOUNT}" -F "due_date=${DUE}" -F "note=${NOTE}" "${BASE}/upload")
echo "$NEW_JSON" | jqok
NEW_ID=$(echo "$NEW_JSON" | sed -n 's#.*"id":"\([^"]*\)".*#\1#p')
if [ -z "${NEW_ID:-}" ]; then
  echo "ERROR: Could not parse new bill id"; exit 1
fi
say "Created bill id: ${NEW_ID}"

# ------------------------------
# 4. list unpaid only
# ------------------------------
say "FILTER: GET ${BASE}/bills?status=unpaid"
curl -sS "${hdr[@]}" "${BASE}/bills?status=unpaid" | jqok

# ------------------------------
# 5. mark paid
# ------------------------------
say "MARK PAID: POST ${BASE}/bills/${NEW_ID}/mark_paid"
curl -sS -X POST "${hdr[@]}" "${BASE}/bills/${NEW_ID}/mark_paid" | jqok

# ------------------------------
# 6. notify (auto) - backend decides best channel/console
# ------------------------------
say "NOTIFY(auto): POST ${BASE}/notify { bill_id: ${NEW_ID}, channel: auto }"
curl -sS -X POST "${hdr[@]}" -H "Content-Type: application/json" \
  -d "{\"bill_id\":\"${NEW_ID}\",\"channel\":\"auto\"}" \
  "${BASE}/notify" | jqok

# ------------------------------
# 7. (optional) notify via SMS
# ------------------------------
#TO="+911234567890"
#if [ -n "${TO}" ]; then
#  say "NOTIFY(sms): POST ${BASE}/notify -> ${TO}"
#  curl -sS -X POST "${hdr[@]}" -H "Content-Type: application/json" \
#    -d "{\"bill_id\":\"${NEW_ID}\",\"channel\":\"sms\",\"to\":\"${TO}\"}" \
#    "${BASE}/notify" | jqok
#fi

# ------------------------------
# 8. final list
# ------------------------------
say "FINAL LIST: GET ${BASE}/bills"
curl -sS "${hdr[@]}" "${BASE}/bills" | jqok

say "Smoke test completed ✅"

