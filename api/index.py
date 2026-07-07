from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
import re

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


def search(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


@app.get("/")
def root():
    return {"message": "Invoice Extraction API is running"}


@app.post("/extract")
def extract(req: InvoiceRequest):
    text = req.invoice_text

    # ---------------- Invoice Number ----------------
    invoice_patterns = [
        r"Invoice\s*(?:No|Number|#)?\s*[:\-]?\s*([A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)+)",
        r"Invoice\s+([A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)+)",
        r"Inv\s*(?:No|#)?\s*[:\-]?\s*([A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)+)",
    ]

    invoice_no = None
    for pattern in invoice_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            invoice_no = m.group(1).strip()
            break

    # ---------------- Vendor ----------------
    vendor_patterns = [
        r"Vendor\s*:\s*(.+)",
        r"Supplier\s*:\s*(.+)",
        r"From\s*:\s*(.+)",
    ]

    vendor = None
    for pattern in vendor_patterns:
        vendor = search(pattern, text)
        if vendor:
            break

    # ---------------- Date ----------------
    date_patterns = [
        r"Date\s*:\s*(.+)",
        r"Invoice\s*Date\s*:\s*(.+)",
        r"Dated\s*:\s*(.+)",
    ]

    date = None
    for pattern in date_patterns:
        date_text = search(pattern, text)
        if date_text:
            try:
                date = parser.parse(date_text, dayfirst=True).date().isoformat()
                break
            except Exception:
                pass

    # ---------------- Amount (Subtotal) ----------------
    subtotal_patterns = [
        r"Subtotal\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Sub\s*Total\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
    ]

    amount = None
    for pattern in subtotal_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            amount = float(m.group(1).replace(",", ""))
            break

    # ---------------- Tax ----------------
    tax_patterns = [
        r"GST\s*\(\d+%?\)\s*:\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"GST\s*:\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Tax\s*:\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
    ]

    tax = None
    for pattern in tax_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
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