import re

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
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
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
        .replace("₹", "")
        .replace("INR", "")
        .replace("$", "")
        .replace("USD", "")
        .replace("EUR", "")
        .replace("€", "")
        .strip()
    )

    try:
        return float(value)
    except:
        return None


@app.get("/")
def root():
    return {"message": "Invoice Extractor API is running"}


@app.post("/extract")
def extract(req: InvoiceRequest):
    text = req.invoice_text

    # Invoice Number
    invoice_no = find([
        r"Invoice\s*No\.?\s*[:\-]\s*(.+)",
        r"Invoice\s*#\s*[:\-]\s*(.+)",
        r"Invoice\s*Number\s*[:\-]\s*(.+)",
        r"Inv\s*No\.?\s*[:\-]\s*(.+)"
    ], text)

    if invoice_no:
        invoice_no = invoice_no.split("\n")[0].strip()

    # Vendor
    vendor = find([
        r"Vendor\s*[:\-]\s*(.+)",
        r"Supplier\s*[:\-]\s*(.+)",
        r"Sold\s*By\s*[:\-]\s*(.+)",
        r"Seller\s*[:\-]\s*(.+)",
        r"Company\s*[:\-]\s*(.+)",
        r"Business\s*Name\s*[:\-]\s*(.+)",
        r"Bill\s*From\s*[:\-]\s*(.+)",
        r"From\s*[:\-]\s*(.+)"
    ], text)

    # Fallback: first meaningful line
    if vendor is None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if not re.search(
                r"invoice|date|subtotal|total|gst|tax|amount|bill|receipt",
                line,
                re.IGNORECASE,
            ):
                vendor = line
                break

    if vendor:
        vendor = vendor.split("\n")[0].strip()

    # Date
    date_text = find([
        r"Invoice\s*Date\s*[:\-]\s*(.+)",
        r"Date\s*[:\-]\s*(.+)"
    ], text)

    date = None
    if date_text:
        try:
            date = parser.parse(date_text, dayfirst=True).date().isoformat()
        except Exception:
            date = None

    # Amount (Subtotal before tax)
    amount = parse_amount(find([
        r"Subtotal\s*[:\-]\s*(Rs\.?\s*[\d,]+(?:\.\d+)?)",
        r"Sub\s*Total\s*[:\-]\s*(Rs\.?\s*[\d,]+(?:\.\d+)?)",
        r"Amount\s*Before\s*Tax\s*[:\-]\s*(Rs\.?\s*[\d,]+(?:\.\d+)?)"
    ], text))

    # Tax
    tax = parse_amount(find([
        r"GST.*?[:\-]\s*(Rs\.?\s*[\d,]+(?:\.\d+)?)",
        r"Tax.*?[:\-]\s*(Rs\.?\s*[\d,]+(?:\.\d+)?)",
        r"VAT.*?[:\-]\s*(Rs\.?\s*[\d,]+(?:\.\d+)?)"
    ], text))

    # Currency
    currency = None

    if re.search(r"₹|Rs\.?|INR", text, re.IGNORECASE):
        currency = "INR"
    elif re.search(r"\$", text):
        currency = "USD"
    elif re.search(r"USD", text, re.IGNORECASE):
        currency = "USD"
    elif re.search(r"€", text):
        currency = "EUR"
    elif re.search(r"EUR", text, re.IGNORECASE):
        currency = "EUR"

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": currency
    }