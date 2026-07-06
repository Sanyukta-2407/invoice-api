from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser as dateparser
import re

app = FastAPI(title="Invoice Extractor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvoiceRequest(BaseModel):
    invoice_text: str


def extract_amount(value):
    if value is None:
        return None
    value = value.replace(",", "")
    m = re.search(r"\d+(?:\.\d+)?", value)
    if m:
        return float(m.group())
    return None


@app.get("/")
def home():
    return {"status": "Invoice Extractor API Running"}


@app.post("/extract")
def extract(req: InvoiceRequest):

    text = req.invoice_text

    invoice_no = None
    date = None
    vendor = None
    amount = None
    tax = None
    total = None
    currency = None

    # Invoice Number
    m = re.search(
        r"(?:Invoice\s*(?:No|Number)?|Inv\s*No)\s*[:#]?\s*([A-Za-z0-9\-\/]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        invoice_no = m.group(1).strip()

    # Vendor
    m = re.search(r"Vendor\s*:\s*(.+)", text, re.IGNORECASE)
    if m:
        vendor = m.group(1).splitlines()[0].strip()

    # Date
    m = re.search(r"Date\s*:\s*(.+)", text, re.IGNORECASE)
    if m:
        try:
            date = dateparser.parse(
                m.group(1).splitlines()[0],
                dayfirst=True
            ).date().isoformat()
        except Exception:
            date = None

    # Subtotal
    m = re.search(
        r"Subtotal\s*:\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)",
        text,
        re.IGNORECASE,
    )
    if m:
        amount = extract_amount(m.group(1))

    # Tax / GST / VAT
    m = re.search(
        r"(?:GST|Tax|VAT)[^0-9]*?(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)",
        text,
        re.IGNORECASE,
    )
    if m:
        tax = extract_amount(m.group(1))

    # Total
    totals = re.findall(
        r"Total\s*:\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)",
        text,
        re.IGNORECASE,
    )
    if totals:
        total = extract_amount(totals[-1])

    # Currency
    m = re.search(
        r"\b(INR|USD|EUR|GBP|JPY|AUD|CAD|AED)\b",
        text,
        re.IGNORECASE,
    )

    if m:
        currency = m.group(1).upper()
    elif "₹" in text or "Rs." in text or "Rs " in text or "INR" in text:
        currency = "INR"
    elif "$" in text:
        currency = "USD"
    elif "€" in text:
        currency = "EUR"
    elif "£" in text:
        currency = "GBP"

    return {
    "invoice_no": invoice_no,
    "date": date,
    "vendor": vendor,
    "amount": amount,
    "tax": tax,
    "currency": currency
}