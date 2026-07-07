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

    # Invoice Number
    invoice_patterns = [
    r"Invoice\s*(?:No|Number|#)?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-\/]*)",
    r"Invoice\s+([A-Za-z0-9][A-Za-z0-9\-\/]*)",
]

invoice_no = None
for pattern in invoice_patterns:
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        value = m.group(1)
        if value.lower() != "invoice":
            invoice_no = value
            break

    # Vendor
    vendor = search(
        r"(?:Vendor|Supplier|From)\s*:\s*(.+)",
        text,
    )

    # Date
    date_text = search(
        r"(?:Date)\s*:\s*(.+)",
        text,
    )

    date = None
    if date_text:
        try:
            date = parser.parse(date_text, dayfirst=True).date().isoformat()
        except Exception:
            pass

    # Subtotal (amount before tax)
    subtotal_match = re.search(
        r"(?:Subtotal|Sub\s*Total)\s*[:\-]?\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )

    amount = (
        float(subtotal_match.group(1).replace(",", ""))
        if subtotal_match
        else None
    )

    # Tax amount (NOT GST percentage)
    tax_match = re.search(
        r"(?:GST|Tax).*?:\s*(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )

    tax = (
        float(tax_match.group(1).replace(",", ""))
        if tax_match
        else None
    )

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