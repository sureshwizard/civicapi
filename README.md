# CivicAPI — Bills (API + Cloud + Data Demo)

**Live UI:** https://civic.admnwizard.com  
**API Base:** `https://civic.admnwizard.com/api`

A tiny end-to-end demo to ingest bills (file or fields), list/filter them, mark them paid, and send a notification (console/SMS). Built to be simple, auditable, and demo-friendly.

---

## ✨ Features

- **Upload bills**
  - **File** (`.txt`/`.pdf`) → extracted to fields *(basic parser; graceful fallbacks)*
  - **Manual fields** → `vendor`, `amount`, `due_date`, `note`
- **List + filter** bills (`all`, `unpaid`, `paid`, `canceled`)
- **Mark paid** with one click
- **Notify** (auto / sms) — convenient for reminders / proof-of-concept
- **Secure by default**: supports `x-api-key` or `Authorization: Bearer <token>`

---

## 🏗️ Architecture

- **Frontend:** Vanilla HTML + a small `app.js`
- **Backend:** FastAPI (Python)
- **Proxy + TLS + CSP:** Nginx (Let’s Encrypt / Certbot)
- **Storage:** SQLite (`civicapi.db`)
- **Domain:** `civic.admnwizard.com` (subdomain of `admnwizard.com`)

Browser ──HTTPS──► Nginx (/api) ──► FastAPI ──► SQLite
▲ │
static UI └────────────► /ui (static)


---

## 🚀 Quick Start (Judges)

Open **https://civic.admnwizard.com**

1. In the **Connection** card:
   - **Base URL:** `https://civic.admnwizard.com/api`
   - **API Key (x-api-key):** *provided during demo*  
     *(enter just the key value — no `x-api-key:` prefix; or enter `Bearer <token>` to use bearer auth)*
2. Click **Save**, then **Ping /** — health JSON should appear.
3. **Upload** a bill (fields or file).
4. Click **Load Bills** → filter, **Mark Paid**, and **Notify**.

---

## 🔐 Authentication

Send one of the following on protected endpoints:

- **x-api-key**
x-api-key: <YOUR_KEY>

- **Authorization (Bearer)**
Authorization: Bearer <YOUR_TOKEN>


---

## 📚 API Endpoints

**Base:** `https://civic.admnwizard.com/api`

### Health
GET /
→ 200 { "ok": true, "service": "...", "time": "...", "db_path": "..." }


### List bills
GET /bills
GET /bills?status=unpaid|paid|canceled


### Upload bill
- **Form-data (fields):** `vendor`, `amount`, `due_date (YYYY-MM-DD)`, `note?`
- **Form-data (file):** `file` = .txt/.pdf
POST /upload
→ 200 { id, vendor, amount, due_date, status, note }



### Mark paid
POST /bills/{id}/mark_paid
→ 200 { ok: true, bill_id, status: "paid" }


### Notify
POST /notify
body:
{ "bill_id":"<id>", "channel":"auto" }
or { "bill_id":"<id>", "channel":"sms", "to":"+911234567890" }

→ 200 { "ok": true, "sent_via": { "channel": "...", ... } }


---

## 🧪 Testing

### Option A — Judge script (easiest)

We ship **`judge-test.sh`** for a one-shot, interactive test:

```bash
chmod +x judge-test.sh
./judge-test.sh
t prompts for Base URL and API key, then runs:
health → list → upload → filter unpaid → mark paid → notify → final list, printing ✅ / ❌ markers and JSON output (pretty if jq is installed).

##-----------------------------------------------------------------------------------------------------------------------------------------------------

Option B — Copy & paste (curl)

Set variables:

BASE="https://civic.admnwizard.com/api"
API_KEY="PASTE-YOUR-KEY-HERE"
1. Health

curl -sS "$BASE/" | jq .


2. List 
curl -sS -H "x-api-key: $API_KEY" "$BASE/bills" | jq .

3. Upload

curl -sS -X POST -H "x-api-key: $API_KEY" \
  -F "vendor=Judge Demo Co" \
  -F "amount=123.45" \
  -F "due_date=2025-09-15" \
  -F "note=from README judge test" \
  "$BASE/upload" | tee /tmp/new-bill.json | jq .
NEW_ID=$(sed -n 's#.*"id":"\([^"]*\)".*#\1#p' /tmp/new-bill.json); echo "NEW_ID=$NEW_ID"

4. List Unpaid
 curl -sS -H "x-api-key: $API_KEY" "$BASE/bills?status=unpaid" | jq .


5. Mark paid
curl -sS -X POST -H "x-api-key: $API_KEY" "$BASE/bills/$NEW_ID/mark_paid" | jq .


6. Notify(auto)

curl -sS -X POST -H "x-api-key: $API_KEY" -H "Content-Type: application/json" \
  -d "{\"bill_id\":\"$NEW_ID\",\"channel\":\"auto\"}" \
  "$BASE/notify" | jq .

7. Final list

curl -sS -H "x-api-key: $API_KEY" "$BASE/bills" | jq .

📸 Screenshots (included in repo)

Place images under docs/screenshots/:
ui-connection.png — Connection card with Base URL + successful Ping /
ui-upload.png — Upload Bill form filled (before clicking Upload)
ui-bills.png — Bills table showing a newly added row (unpaid)
ui-notify.png — After clicking Notify (success message or Network response)
In this README we reference them like:

🔒 Security Notes

CSP (Nginx) — recommended production policy:


default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src https://fonts.gstatic.com;
img-src 'self' data:;
connect-src 'self' https://civic.admnwizard.com;


TTPS via Let’s Encrypt, auto-renewed by Certbot
Nginx blocks suspicious agents/hidden files/unsafe methods
Frontend uses external JS (no inline scripts), compatible with strict CSP

🎬 Demo flow (2–3 min live)

1. Health check in UI → JSON status
2. Paste API key → Save → Load Bills
3. Upload (fields) → see new row
4. Filter unpaid → Mark Paid
5. Notify (auto) → show response
6. Wrap: architecture + security notes

🧭 Troubleshooting

401 Unauthorized
UI field expects just the key (no x-api-key: prefix)

Network tab → confirm request includes x-api-key or Authorization: Bearer
curl -i -H 'x-api-key: KEY' "$BASE/bills" should return 200

Date rejected
Use YYYY-MM-DD (use the date picker)

CSP error (inline script blocked)
Ensure index.html uses <script src="/js/app.js" defer></script> and no inline <script>

📄 License / Credits

Built by Suresh Kumar Thulasi Ram for hackathon demo
FastAPI, Nginx, Let’s Encrypt — ❤️ open source

