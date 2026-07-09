import os
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    api_key=os.getenv("AIPIPE_TOKEN"),
    base_url="https://aipipe.org/openrouter/v1"
)


class InvoiceRequest(BaseModel):
    invoice_text: str


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/extract")
def extract(req: InvoiceRequest):

    prompt = f"""
Extract the following fields from this invoice.

Return ONLY valid JSON.

Required keys:
invoice_no
date
vendor
amount
tax
currency

Rules:
- Return all six keys.
- Use null if missing.
- date must be YYYY-MM-DD.
- amount is subtotal BEFORE tax.
- tax is ONLY the tax amount.
- currency must be ISO code such as INR, USD, EUR.

Invoice:

{req.invoice_text}
"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )

        content = response.choices[0].message.content.strip()

        # Remove markdown if present
        content = content.replace("```json", "").replace("```", "").strip()

        result = json.loads(content)

    except Exception:
        result = {}

    return {
        "invoice_no": result.get("invoice_no"),
        "date": result.get("date"),
        "vendor": result.get("vendor"),
        "amount": result.get("amount"),
        "tax": result.get("tax"),
        "currency": result.get("currency")
    }