import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser

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


def find(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
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
        .replace("USD", "")
        .replace("EUR", "")
        .replace("$", "")
        .replace("€", "")
        .strip()
    )

    try:
        return float(value)
    except Exception:
        return None


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/extract")
def extract(req: InvoiceRequest):

    text = req.invoice_text

    # Invoice Number
    invoice_no = find([
        r"Invoice\s*No\.?\s*[:#-]?\s*([A-Za-z0-9\-/]+)",
        r"Invoice\s*#\s*[:#-]?\s*([A-Za-z0-9\-/]+)",
        r"Invoice\s*Number\s*[:#-]?\s*([A-Za-z0-9\-/]+)",
        r"Inv\s*No\.?\s*[:#-]?\s*([A-Za-z0-9\-/]+)",
        r"Bill\s*No\.?\s*[:#-]?\s*([A-Za-z0-9\-/]+)",
        r"Ref\s*[:#-]?\s*([A-Za-z0-9\-/]+)",
        r"Reference\s*[:#-]?\s*([A-Za-z0-9\-/]+)"
    ], text)

    # Vendor
    vendor = find([
        r"Vendor\s*:\s*(.+)",
        r"Seller\s*:\s*(.+)",
        r"Supplier\s*:\s*(.+)",
        r"Sold\s*By\s*:\s*(.+)",
        r"Company\s*:\s*(.+)",
        r"Business\s*Name\s*:\s*(.+)",
        r"Bill\s*From\s*:\s*(.+)",
        r"From\s*:\s*(.+)"
    ], text)

    if vendor is None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if not re.search(
                r"invoice|bill|date|issued|subtotal|total|tax|gst|vat|amount|currency|client|description",
                line,
                re.IGNORECASE,
            ):
                vendor = line
                break

    # Date
    date_text = find([
        r"Issued\s*:\s*(.+)",
        r"Invoice\s*Date\s*:\s*(.+)",
        r"Date\s*:\s*(.+)"
    ], text)

    date = None
    if date_text:
        try:
            date = parser.parse(date_text, dayfirst=True).date().isoformat()
        except Exception:
            date = None

    # Amount
    amount = parse_amount(find([
        r"Subtotal\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"Sub\s*Total\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"Amount\s*Before\s*Tax\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"Taxable\s*Amount\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"Base\s*Amount\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"Net\s*Amount\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"Total\s*Before\s*Tax\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)"
    ], text))

    # Tax
    tax = parse_amount(find([
        r"IGST\s*\([^)]*\)\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"CGST\s*\([^)]*\)\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"SGST\s*\([^)]*\)\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"GST\s*\([^)]*\)\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"VAT\s*\([^)]*\)\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"Tax\s*\([^)]*\)\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"IGST\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"CGST\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"SGST\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"GST\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"VAT\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)",
        r"Tax\s*:\s*(?:Rs\.?|₹|INR|USD|EUR)?\s*([\d,]+(?:\.\d+)?)"
    ], text))

    # Currency
    currency = find([
        r"Currency\s*:\s*(INR|USD|EUR)"
    ], text)

    if currency is None:
        if re.search(r"₹|Rs\.?|INR", text, re.IGNORECASE):
            currency = "INR"
        elif re.search(r"\$|USD", text, re.IGNORECASE):
            currency = "USD"
        elif re.search(r"€|EUR", text, re.IGNORECASE):
            currency = "EUR"

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": currency
    }