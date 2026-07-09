import os
import json

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

Return ONLY valid JSON that exactly matches the supplied JSON Schema.

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
                    "Return only valid JSON. "
                    "Follow the provided schema exactly."
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

    # Normalize email to lowercase as required
    if result.get("contact_email"):
        result["contact_email"] = result["contact_email"].lower()

    # Ensure item_count matches the number of line items
    if "line_items" in result:
        result["item_count"] = len(result["line_items"])

    return result