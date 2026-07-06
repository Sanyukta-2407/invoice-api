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
    return float(m.group()) if m else None


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/extract")
def extract(req: InvoiceRequest):

    text = req.invoice_text

    invoice_no = None
    date = None
    vendor = None
    amount = None
    tax = None
    currency = None

    # ---------------- Invoice Number ----------------
    patterns = [
        r"Invoice\s*(?:No|Number)?\s*[:#]?\s*([A-Za-z0-9\-/]+)",
        r"Invoice\s*#\s*[: ]?\s*([A-Za-z0-9\-/]+)",
        r"Ref\s*:\s*([A-Za-z0-9\-/]+)"
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            invoice_no = m.group(1).strip()
            break

    # ---------------- Vendor ----------------
    for label in ["Vendor", "Seller"]:
        m = re.search(rf"{label}\s*:\s*(.+)", text, re.IGNORECASE)
        if m:
            vendor = m.group(1).splitlines()[0].strip()
            break

    # ---------------- Date ----------------
    for label in ["Date", "Issued"]:
        m = re.search(rf"{label}\s*:\s*(.+)", text, re.IGNORECASE)
        if m:
            try:
                date = dateparser.parse(
                    m.group(1).splitlines()[0],
                    dayfirst=True
                ).date().isoformat()
            except Exception:
                pass
            break

    # ---------------- Subtotal ----------------
    m = re.search(
        r"Subtotal\s*:\s*(?:Rs\.?|INR|USD|EUR|GBP|₹)?\s*([0-9,]+(?:\.[0-9]+)?)",
        text,
        re.IGNORECASE,
    )

    if m:
        amount = extract_amount(m.group(1))

    # ---------------- Tax ----------------
    for line in text.splitlines():
        if re.search(r"\b(GST|IGST|CGST|SGST|VAT|Tax)\b", line, re.IGNORECASE):
            nums = re.findall(r"[0-9,]+(?:\.[0-9]+)?", line)
            if nums:
                tax = float(nums[-1].replace(",", ""))
            break

    # ---------------- Currency ----------------
    m = re.search(
        r"Currency\s*:\s*(INR|USD|EUR|GBP|AED|JPY|AUD|CAD)",
        text,
        re.IGNORECASE,
    )

    if m:
        currency = m.group(1).upper()
    elif "₹" in text or "Rs." in text or "Rs " in text:
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
        "currency": currency,
    }