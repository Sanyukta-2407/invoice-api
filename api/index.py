import re
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvoiceRequest(BaseModel):
    invoice_text: str


def find(patterns, text):
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def parse_amount(value):
    if value is None:
        return None

    value = (
        value.replace(",", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .replace("INR", "")
        .replace("₹", "")
        .strip()
    )

    try:
        return float(value)
    except:
        return None


@app.post("/extract")
def extract(req: InvoiceRequest):
    text = req.invoice_text

    invoice_no = find([
        r"Invoice\s*No\.?\s*[:\-]\s*(.+)",
        r"Invoice\s*#\s*[:\-]\s*(.+)",
        r"Invoice\s*Number\s*[:\-]\s*(.+)"
    ], text)

    vendor = find([
        r"Vendor\s*[:\-]\s*(.+)",
        r"Supplier\s*[:\-]\s*(.+)",
        r"Sold\s*By\s*[:\-]\s*(.+)"
    ], text)

    date_text = find([
        r"Date\s*[:\-]\s*(.+)",
        r"Invoice\s*Date\s*[:\-]\s*(.+)"
    ], text)

    date = None
    if date_text:
        try:
            date = parser.parse(date_text, dayfirst=True).date().isoformat()
        except:
            pass

    amount = parse_amount(find([
        r"Subtotal\s*[:\-]\s*(Rs\.?\s*[\d,]+\.\d+)",
        r"Sub\s*Total\s*[:\-]\s*(Rs\.?\s*[\d,]+\.\d+)"
    ], text))

    tax = parse_amount(find([
        r"GST.*?[:\-]\s*(Rs\.?\s*[\d,]+\.\d+)",
        r"Tax.*?[:\-]\s*(Rs\.?\s*[\d,]+\.\d+)",
        r"VAT.*?[:\-]\s*(Rs\.?\s*[\d,]+\.\d+)"
    ], text))

    currency = None

    if re.search(r"\bINR\b|Rs\.?|₹", text, re.I):
        currency = "INR"
    elif re.search(r"\bUSD\b|\$", text):
        currency = "USD"
    elif re.search(r"\bEUR\b|€", text):
        currency = "EUR"

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": currency,
    }