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


def extract_first(patterns, text):
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

    # ---------------- Invoice Number ----------------

    invoice_no = extract_first([
        r"Invoice\s*(?:No|Number|#)?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-/]*)",
        r"Invoice\s+([A-Za-z0-9][A-Za-z0-9\-/]*)",
        r"Inv\s*(?:No|#)?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-/]*)",
        r"Bill\s*No\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-/]*)",
    ])

    # ---------------- Vendor ----------------

    vendor = extract_first([
        r"Vendor\s*:\s*(.+)",
        r"Supplier\s*:\s*(.+)",
        r"Sold\s*By\s*:\s*(.+)",
        r"Bill\s*From\s*:\s*(.+)",
        r"Seller\s*:\s*(.+)",
        r"Company\s*:\s*(.+)",
        r"From\s*:\s*(.+)",
    ], text)

    if vendor:
        vendor = vendor.split("\n")[0].strip()

    # ---------------- Date ----------------

    date_text = extract_first([
        r"Invoice\s*Date\s*:\s*(.+)",
        r"Date\s*:\s*(.+)",
        r"Dated\s*:\s*(.+)",
        r"Order\s*Date\s*:\s*(.+)",
    ], text)

    date = None

    if date_text:
        try:
            date = parser.parse(date_text, dayfirst=True).date().isoformat()
        except Exception:
            pass

    # ---------------- Amount ----------------

    amount = None

    amount_patterns = [
        r"Subtotal\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Sub\s*Total\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Amount\s*Before\s*Tax\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
    ]

    for p in amount_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            amount = float(m.group(1).replace(",", ""))
            break

    # ---------------- Tax ----------------

    tax = None

    tax_patterns = [
        r"GST\s*\(\d+%?\)\s*:\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"GST\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Tax\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"VAT\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
    ]

    for p in tax_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            tax = float(m.group(1).replace(",", ""))
            break

    # ---------------- Currency ----------------

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
```
