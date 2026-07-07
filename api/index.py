```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
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


def first_match(patterns, text):
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/extract")
def extract(req: InvoiceRequest):
    text = req.invoice_text

    # Invoice Number
    invoice_no = first_match([
        r"Invoice\s*(?:No|Number|#)?\s*[:\-]?\s*([A-Za-z0-9\-\/]+)",
        r"Invoice\s+([A-Za-z0-9\-\/]+)",
        r"Bill\s*No\.?\s*[:\-]?\s*([A-Za-z0-9\-\/]+)",
        r"Inv\s*#?\s*[:\-]?\s*([A-Za-z0-9\-\/]+)"
    ], text)

    if invoice_no and invoice_no.lower() == "invoice":
        invoice_no = None

    # Vendor
    vendor = first_match([
        r"Vendor\s*:\s*(.+)",
        r"Supplier\s*:\s*(.+)",
        r"Sold\s*By\s*:\s*(.+)",
        r"Seller\s*:\s*(.+)",
        r"Bill\s*From\s*:\s*(.+)",
        r"Company\s*:\s*(.+)",
        r"From\s*:\s*(.+)"
    ], text)

    if vendor:
        vendor = vendor.splitlines()[0].strip()

    # Date
    date_text = first_match([
        r"Invoice\s*Date\s*:\s*(.+)",
        r"Date\s*:\s*(.+)",
        r"Dated\s*:\s*(.+)"
    ], text)

    date = None
    if date_text:
        try:
            date = parser.parse(date_text, dayfirst=True).date().isoformat()
        except Exception:
            date = None

    # Amount (Subtotal)
    amount = None
    m = re.search(
        r"(?:Subtotal|Sub\s*Total|Amount\s*Before\s*Tax)\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )
    if m:
        amount = float(m.group(1).replace(",", ""))

    # Tax
    tax = None
    for pattern in [
        r"GST\s*\(\d+%?\)\s*:\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"GST\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Tax\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"VAT\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            tax = float(m.group(1).replace(",", ""))
            break

    # Currency
    if "₹" in text or "Rs." in text or "Rs " in text or "INR" in text:
        currency = "INR"
    elif "$" in text:
        currency = "USD"
    elif "€" in text:
        currency = "EUR"
    elif "£" in text:
        currency = "GBP"
    else:
        currency = None

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": currency,
    }

