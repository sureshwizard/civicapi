# backend/main.py
import os
import re
import json
import logging
import hashlib
import hmac
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db, insert_bill, list_bills, get_bill, update_status, DB_PATH
from .models import BillIn, Bill, NotifyIn

# ----------------------------
# Env & API-key guard
# ----------------------------
load_dotenv()

API_KEY        = os.getenv("CIVICAPI_API_KEY", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:4051")
DEBUG_MODE     = os.getenv("CIVICAPI_DEBUG", "0") == "1"

def verify_key(x_api_key: str = Header(default="")):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ----------------------------
# App bootstrap (docs toggle)
# ----------------------------
docs_enabled = os.getenv("CIVICAPI_DOCS", "0") == "1"
docs_url     = "/docs" if docs_enabled else None
openapi_url  = "/openapi.json" if docs_enabled else None

app = FastAPI(
    title="CivicAPI — API+Cloud+Data Demo",
    version="0.1.0",
    docs_url=docs_url,
    redoc_url=None,
    openapi_url=openapi_url,
)

# Static UI (served at /ui)
UI_DIR = (Path(__file__).resolve().parent.parent / "ui")
if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")

# CORS
allowed_origins = [o for o in os.getenv("CIVICAPI_CORS", "").split(",") if o]
if allowed_origins:
    # Credentials + explicit origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        allow_credentials=True,
    )
else:
    # No credentials when wildcard origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        allow_credentials=False,
    )

# Logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("civicapi")

# ----------------------------
# Lifecycle
# ----------------------------
@app.on_event("startup")
def _startup():
    init_db()
    logger.info("CivicAPI startup: DB_PATH=%s", DB_PATH)
    logger.info(
        "Config: PUBLIC_BASE_URL=%s CIVICAPI_DOCS=%s",
        os.getenv("PUBLIC_BASE_URL", ""),
        os.getenv("CIVICAPI_DOCS", "0"),
    )

# ----------------------------
# Utilities
# ----------------------------
def mock_parse_text(text: str) -> BillIn:
    vendor = re.search(r"Vendor:\s*(.+)", text)
    amount = re.search(r"Amount:\s*\$?([0-9]+(?:\.[0-9]{1,2})?)", text)
    due    = re.search(r"Due:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text)

    vendor_val = vendor.group(1).strip() if vendor else "Unknown Vendor"
    amount_val = float(amount.group(1)) if amount else 0.0
    due_val    = due.group(1) if due else datetime.utcnow().date().isoformat()

    return BillIn(vendor=vendor_val, amount=amount_val, due_date=due_val, note="parsed-from-text")

def send_notification(msg: str, channel: str = "auto", to: Optional[str] = None) -> dict:
    V_API_KEY   = os.getenv("VONAGE_API_KEY")
    V_API_SECRET= os.getenv("VONAGE_API_SECRET")
    V_FROM      = os.getenv("VONAGE_FROM", "CIVICAPI")

    if (channel in ("auto", "sms")) and V_API_KEY and V_API_SECRET and to:
        try:
            import requests
            resp = requests.post(
                "https://rest.nexmo.com/sms/json",
                data={
                    "api_key": V_API_KEY,
                    "api_secret": V_API_SECRET,
                    "to": to,
                    "from": V_FROM,
                    "text": msg,
                },
                timeout=10,
            )
            return {"channel": "sms", "status": resp.status_code, "response": resp.text}
        except Exception as e:
            return {"channel": "sms", "status": "error", "error": str(e)}

    print(f"[NOTIFY console] to={to or 'demo'} :: {msg}")
    return {"channel": "console", "status": "ok"}

def sign_token(bill_id: str) -> str:
    msg = bill_id.encode("utf-8")
    key = WEBHOOK_SECRET.encode("utf-8")
    sig = hmac.new(key, msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")

def verify_token(bill_id: str, token: str) -> bool:
    try:
        padding = "=" * ((4 - len(token) % 4) % 4)
        raw = base64.urlsafe_b64decode((token + padding).encode("utf-8"))
        expected = hmac.new(WEBHOOK_SECRET.encode("utf-8"), bill_id.encode("utf-8"), hashlib.sha256).digest()
        return hmac.compare_digest(raw, expected)
    except Exception:
        return False

def verify_webhook_signature(bill_id: str, signature: str) -> bool:
    return verify_token(bill_id, signature)

# ----------------------------
# Public endpoints (no API key)
# ----------------------------
@app.get("/", summary="Health (root)")
def root_health():
    payload = {
        "ok": True,
        "service": app.title,
        "time": datetime.utcnow().isoformat(),
    }
    if DEBUG_MODE:
        payload["db_path"] = DB_PATH
    return payload

@app.get("/health", summary="Health")
def health():
    # Alias for convenience
    return root_health()

# ----------------------------
# Protected endpoints (require X-API-KEY)
# ----------------------------
@app.post("/upload", response_model=Bill, summary="Upload a bill (file or JSON)", dependencies=[Depends(verify_key)])
async def upload_bill(
    file: Optional[UploadFile] = File(None),
    vendor: Optional[str] = Form(None),
    amount: Optional[float] = Form(None),
    due_date: Optional[str] = Form(None),
    note: Optional[str] = Form(None),
    payload: Optional[str] = Form(None),
):
    if payload:
        try:
            data = json.loads(payload)
            bill_in = BillIn(**data)
        except Exception as e:
            raise HTTPException(400, f"Invalid payload JSON: {e}")
    elif file:
        text = (await file.read()).decode("utf-8", errors="ignore")
        bill_in = mock_parse_text(text)
    elif vendor and amount is not None and due_date:
        bill_in = BillIn(vendor=vendor, amount=amount, due_date=due_date, note=note)
    else:
        raise HTTPException(400, "Provide either a file, form fields (vendor, amount, due_date), or JSON payload")

    bill = Bill(**bill_in.model_dump())
    insert_bill(bill.model_dump())
    return bill

@app.get("/bills", summary="List bills", dependencies=[Depends(verify_key)])
def get_bills(status: Optional[str] = Query(None, pattern="^(unpaid|paid|canceled)$")):
    return {"items": list_bills(status)}

@app.post("/notify", summary="Notify about a bill", dependencies=[Depends(verify_key)])
def notify(n: NotifyIn):
    b = get_bill(n.bill_id)
    if not b:
        raise HTTPException(404, "Bill not found")
    token = sign_token(b["id"])
    link = f"{PUBLIC_BASE_URL}/pay/{b['id']}?t={token}"
    msg = f"Reminder: Unpaid bill from {b['vendor']} amount ${b['amount']} due {b['due_date']}. Pay/review: {link}"
    result = send_notification(msg, channel=n.channel, to=n.to)
    return {"ok": True, "sent_via": result, "link": link}

@app.post("/bills/{bill_id}/mark_paid", summary="Mark a bill as paid", dependencies=[Depends(verify_key)])
def mark_paid(bill_id: str):
    ok = update_status(bill_id, "paid")
    if not ok:
        raise HTTPException(404, "Bill not found")
    return {"ok": True, "bill_id": bill_id, "status": "paid"}

# ----------------------------
# Payment flow (public pages + webhook)
# ----------------------------
@app.get("/pay/{bill_id}")
def pay_page(bill_id: str, t: str):
    if not verify_token(bill_id, t):
        raise HTTPException(403, "Invalid token")
    b = get_bill(bill_id)
    if not b:
        raise HTTPException(404, "Bill not found")
    return HTMLResponse(f"""
      <html><body style="font-family:system-ui">
        <h2>Pay Bill</h2>
        <p><b>Vendor:</b> {b['vendor']}<br/>
           <b>Amount:</b> ${b['amount']}<br/>
           <b>Due:</b> {b['due_date']}<br/>
           <b>Status:</b> {b['status']}</p>
        <p>This is a demo page. In production, redirect to a real gateway and configure its webhook to call <code>/webhooks/payment</code>.</p>
        <form method="post" action="/webhooks/payment">
          <input type="hidden" name="bill_id" value="{b['id']}" />
          <input type="hidden" name="status" value="paid" />
          <input type="hidden" name="external_ref" value="demo-{datetime.utcnow().timestamp()}" />
          <input type="hidden" name="signature" value="{sign_token(b['id'])}" />
          <button type="submit">Simulate Payment (Demo)</button>
        </form>
      </body></html>
    """)

@app.post("/webhooks/payment")
async def webhook_payment(request: Request):
    try:
        data = await request.json()
    except Exception:
        form = await request.form()
        data = dict(form)

    bill_id     = data.get("bill_id")
    status      = (data.get("status") or "").lower()
    signature   = data.get("signature") or ""
    external_ref= data.get("external_ref")

    if not bill_id or not status:
        raise HTTPException(400, "Missing bill_id or status")

    if not verify_webhook_signature(bill_id, signature):
        raise HTTPException(403, "Invalid signature")

    b = get_bill(bill_id)
    if not b:
        return {"ok": True, "ignored": True, "reason": "unknown bill"}

    if b["status"] == "paid":
        return {"ok": True, "idempotent": True}

    if status == "paid":
        update_status(bill_id, "paid")
        return {"ok": True, "bill_id": bill_id, "new_status": "paid", "external_ref": external_ref}
    else:
        return {"ok": True, "bill_id": bill_id, "status": status}

