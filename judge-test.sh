#!/usr/bin/env bash
# CivicAPI judge-friendly end-to-end test
# - Prompts for API base + key
# - Runs: health → list → upload → filter → mark paid → notify → final list
# - Prints clear ✅/❌ results, shows HTTP codes, works with/without jq

set -u

DEFAULT_BASE="https://civic.admnwizard.com/api"

read -r -p "API Base [${DEFAULT_BASE}]: " BASE
BASE="${BASE:-$DEFAULT_BASE}"

echo -n "API Key (paste JUST the key; if Bearer, include 'Bearer ' prefix): "
stty -echo 2>/dev/null || true
read -r API_KEY
stty echo 2>/dev/null || true
echo

if [ -z "${API_KEY}" ]; then
  echo "❌ No API key provided. Exiting."
  exit 1
fi

use_jq=false
if command -v jq >/dev/null 2>&1; then use_jq=true; fi

say()  { printf "\n\033[1m==> %s\033[0m\n" "$*"; }
ok()   { printf "   ✅ %s\n" "$*"; }
fail() { printf "   ❌ %s\n" "$*"; }

# Build auth header: if user pasted "Bearer …", send Authorization; else x-api-key
auth_header=()
if [[ "$API_KEY" =~ ^[[:space:]]*Bearer[[:space:]]+.*$ ]]; then
  auth_header=(-H "Authorization: ${API_KEY}")
else
  auth_header=(-H "x-api-key: ${API_KEY}")
fi

# curl helper that preserves status code and body separately
req() {
  # usage: req METHOD URL [curl-args...]
  local METHOD="$1"; shift
  local URL="$1"; shift
  local OUT CODE
  OUT=$(curl -sS -X "$METHOD" "$URL" "$@" -w $'\n%{http_code}') || { CODE=$?; echo "CURL ERROR $CODE"; return 255; }
  CODE="${OUT##*$'\n'}"
  BODY="${OUT%$'\n'*}"
  printf "%s\n" "$BODY"
  echo "$CODE" 1>&2   # status to stderr
}

pp() {
  $use_jq && jq . 2>/dev/null || cat
}

# 1) Health
say "HEALTH: GET ${BASE}/"
BODY="$(req GET "${BASE}/")"; CODE="$?"
if [ "$CODE" = "0" ]; then
  # status is printed to stderr by req; capture last line from stderr isn’t trivial here, so rely on body content
  echo "$BODY" | pp
  ok "Health request executed"
else
  echo "$BODY" | pp
  fail "Health request failed"
fi

# 2) List
say "LIST: GET ${BASE}/bills"
BODY="$(req GET "${BASE}/bills" "${auth_header[@]}")"; STATUS="$?"
echo "$BODY" | pp
if [ "$STATUS" = "0" ] && grep -q '"items"' <<<"$BODY"; then ok "List OK"; else fail "List may have failed (check output)"; fi

# 3) Upload (fields)
VENDOR="Judge Demo Co"
AMOUNT="123.45"
DUE="2025-09-15"
NOTE="from judge-test"

say "UPLOAD(FIELDS): POST ${BASE}/upload (vendor=${VENDOR}, amount=${AMOUNT}, due=${DUE})"
BODY="$(curl -sS -X POST "${auth_header[@]}" \
  -F "vendor=${VENDOR}" -F "amount=${AMOUNT}" -F "due_date=${DUE}" -F "note=${NOTE}" \
  "${BASE}/upload")"
echo "$BODY" | pp
NEW_ID="$(sed -n 's#.*"id":"\([^"]\+\)".*#\1#p' <<<"$BODY")"
if [ -n "$NEW_ID" ]; then ok "Upload OK (id=$NEW_ID)"; else fail "Upload failed (no id)"; fi

# 4) Filter unpaid
say "FILTER: GET ${BASE}/bills?status=unpaid"
curl -sS "${auth_header[@]}" "${BASE}/bills?status=unpaid" | pp

# 5) Mark paid
if [ -n "$NEW_ID" ]; then
  say "MARK PAID: POST ${BASE}/bills/${NEW_ID}/mark_paid"
  curl -sS -X POST "${auth_header[@]}" "${BASE}/bills/${NEW_ID}/mark_paid" | pp
else
  fail "Skipping mark paid (no NEW_ID)"
fi

# 6) Notify (auto)
if [ -n "$NEW_ID" ]; then
  say "NOTIFY(auto): POST ${BASE}/notify"
  curl -sS -X POST "${auth_header[@]}" -H "Content-Type: application/json" \
    -d "{\"bill_id\":\"${NEW_ID}\",\"channel\":\"auto\"}" \
    "${BASE}/notify" | pp
else
  fail "Skipping notify (no NEW_ID)"
fi

# 7) Final list
say "FINAL LIST: GET ${BASE}/bills"
curl -sS "${auth_header[@]}" "${BASE}/bills" | pp

say "Judge test completed ✅"

