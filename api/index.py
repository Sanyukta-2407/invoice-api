currency = None

m = re.search(r"\b(INR|USD|EUR|GBP)\b", text, re.I)
if m:
    currency = m.group(1).upper()
elif "₹" in text or "Rs" in text or "Rs." in text:
    currency = "INR"

return {
    "invoice_no": invoice_no,
    "date": date,
    "vendor": vendor,
    "amount": amount,
    "tax": tax,
    "total": total,
    "currency": currency
}