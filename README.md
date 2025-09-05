📄 README.md
# CivicAPI — Bills (API + Cloud + Data Demo)

**Live UI:** https://civic.admnwizard.com  
**API Base:** `https://civic.admnwizard.com/api`

A tiny end-to-end demo that ingests bills (file or fields), lists them, marks them paid, and can notify users (console/SMS). Built to be simple, auditable, and demo-friendly.

---

## ✨ Features

- **Upload bills**
  - **File** (`.txt`/`.pdf`) → extracted to fields *(basic parser; graceful fallbacks)*
  - **Manual fields** → `vendor`, `amount`, `due_date`, `note`
- **List + filter** bills (`all`, `unpaid`, `paid`, `canceled`)
- **Mark paid** with one click
- **Notify** (auto / sms) — convenient for reminders / proof-of-concept
- **Secure by default** (`x-api-key` or `Authorization: Bearer`)

---

## 🏗️ Architecture

- **Frontend:** Vanilla HTML + `app.js`
- **Backend:** FastAPI (Python)
- **Reverse proxy:** Nginx (SSL via Let’s Encrypt / Certbot)
- **Storage:** SQLite (`civicapi.db`)
- **Domain:** `civic.admnwizard.com` (subdomain under `admnwizard.com`)



Browser ──HTTPS──► Nginx (/api) ──► FastAPI ──► SQLite
▲ │
static UI └────────────► /ui (static)


---

## 🚀 Quick Start (for Judges)

**UI URL:** https://civic.admnwizard.com  

1. In **Connection**:
   - **Base URL:** `https://civic.admnwizard.com/api`
   - **API Key (x-api-key):** *provided during demo*  
     *(enter just the key value — no `x-api-key:` prefix; or enter `Bearer <token>` for bearer mode)*
2. Click **Save** → **Ping /** (should show JSON health).
3. **Upload** a bill using fields or file.
4. **Load Bills** → filter, **Mark Paid**, and **Notify**.

---

## 🔐 Authentication

Send either of the following with every protected request:

- **x-api-key** header:


x-api-key: <YOUR_KEY>

- **Authorization Bearer** (if using tokens):


Authorization: Bearer <YOUR_TOKEN>


---

## 📚 API Endpoints

Base: `https://civic.admnwizard.com/api`

### Health


GET /
→ 200 { "ok": true, "service": "...", "time": "...", "db_path": "..." }


### List bills


GET /bills
GET /bills?status=unpaid|paid|canceled


### Upload bill
- **Form-data** (fields): `vendor`, `amount`, `due_date (YYYY-MM-DD)`, `note?`
- **Form-data** (file): `file` = .txt/.pdf



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

### Option A — Judge Script (easiest)

We provide a ready script: **`judge-test.sh`**

```bash
chmod +x judge-test.sh
./judge-test.sh


Prompts for API base (default: https://civic.admnwizard.com/api)

Prompts for API key (paste the raw key, or Bearer <token> if using bearer)

Runs: health → list → upload → filter unpaid → mark paid → notify → final list

Prints ✅ / ❌ results and shows JSON output (pretty if jq is installed)

Option B — Judge Copy & Paste (README commands)

Set variables:

BASE="https://civic.admnwizard.com/api"
API_KEY="PASTE-YOUR-KEY-HERE"


1) Health

curl -sS "$BASE/" | jq .


2) List all bills

curl -sS -H "x-api-key: $API_KEY" "$BASE/bills" | jq .


3) Upload a bill

curl -sS -X POST -H "x-api-key: $API_KEY" \
  -F "vendor=Judge Demo Co" \
  -F "amount=123.45" \
  -F "due_date=2025-09-15" \
  -F "note=from README judge test" \
  "$BASE/upload" | tee /tmp/new-bill.json | jq .

NEW_ID=$(sed -n 's#.*"id":"\([^"]*\)".*#\1#p' /tmp/new-bill.json)
echo "NEW_ID=$NEW_ID"


4) List unpaid

curl -sS -H "x-api-key: $API_KEY" "$BASE/bills?status=unpaid" | jq .


5) Mark it paid

curl -sS -X POST -H "x-api-key: $API_KEY" "$BASE/bills/$NEW_ID/mark_paid" | jq .


6) Notify (auto)

curl -sS -X POST -H "x-api-key: $API_KEY" -H "Content-Type: application/json" \
  -d "{\"bill_id\":\"$NEW_ID\",\"channel\":\"auto\"}" \
  "$BASE/notify" | jq .


7) Final list

curl -sS -H "x-api-key: $API_KEY" "$BASE/bills" | jq .

🔒 Security Notes

CSP enforced at Nginx:

default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src https://fonts.gstatic.com;
img-src 'self' data:;
connect-src 'self' https://civic.admnwizard.com;


HTTPS enabled (Let’s Encrypt cert auto-renews)

Nginx blocks suspicious agents, hidden files, and unsafe methods

🎬 Demo Script (2–3 min live)

Health check in UI → JSON status

Paste API key → Save → Load Bills

Upload a bill → appears in table

Filter “unpaid”

Mark Paid → state change

Notify → console/SMS result

Wrap with architecture + security notes

📄 License / Credits

Built by Suresh Kumar Thulasi Ram for hackathon demo

FastAPI, Nginx, Let’s Encrypt — ❤️ open source
