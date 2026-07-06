from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser as dateparser
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceRequest(BaseModel):
    invoice_text: str


def money(value):
    if value is None:
        return None
    value = value.replace(",", "")
    m = re.search(r"\d+(?:\.\d+)?", value)
    return float(m.group()) if m else None


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/extract")
def extract(req: InvoiceRequest):

    text = req.invoice_text

    invoice_no = None
    vendor = None
    date = None
    amount = None
    tax = None
    total = None

    m = re.search(r"(?:Invoice\s*(?:No|Number)?|Inv\s*No)\s*[:#]?\s*([A-Za-z0-9\-/]+)", text, re.I)
    if m:
        invoice_no = m.group(1)

    m = re.search(r"Vendor\s*:\s*(.+)", text, re.I)
    if m:
        vendor = m.group(1).splitlines()[0].strip()

    m = re.search(r"Date\s*:\s*(.+)", text, re.I)
    if m:
        try:
            date = dateparser.parse(
                m.group(1).splitlines()[0],
                dayfirst=True
            ).date().isoformat()
        except Exception:
            pass

    m = re.search(r"Subtotal\s*:\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.I)
    if m:
        amount = money(m.group(1))

    m = re.search(r"(?:GST|Tax|VAT)[^0-9]*?(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.I)
    if m:
        tax = money(m.group(1))

    totals = re.findall(r"Total\s*:\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.I)
    if totals:
        total = money(totals[-1])

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "total": total
    }

handler = app