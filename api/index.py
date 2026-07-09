import os
import json
import re

from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI()

client = OpenAI(
    api_key=os.getenv("AIPIPE_TOKEN"),
    base_url="https://aipipe.org/openrouter/v1"
)


class InvoiceRequest(BaseModel):
    document_id: str
    text: str
    schema: dict


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/")
def extract_invoice(req: InvoiceRequest):

    prompt = f"""
Extract the invoice information from the document below.

Rules:
- Return ONLY valid JSON.
- Follow the supplied JSON schema exactly.
- Copy values exactly as they appear in the document.
- Never invent or correct text.
- Email addresses must be copied exactly from the document.

Document:
{req.text}
"""

    response = client.chat.completions.create(
        model="openai/gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an invoice extraction assistant. "
                    "Return only valid JSON matching the provided schema. "
                    "Copy values exactly as written. "
                    "Do not guess or correct spelling."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "invoice",
                "schema": req.schema,
            },
        },
    )

    result = json.loads(response.choices[0].message.content)

    # Extract email directly from original text
    email_match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        req.text
    )

    if email_match:
        result["contact_email"] = email_match.group(0).lower()
    elif result.get("contact_email"):
        result["contact_email"] = result["contact_email"].strip().lower()

    # Ensure item_count is correct
    if "line_items" in result:
        result["item_count"] = len(result["line_items"])

    return result