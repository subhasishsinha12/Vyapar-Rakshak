"""GPT-5.2 wrapper (text + vision) via emergentintegrations."""
import os
import json
import uuid
import base64
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("vyaparrakshak.ai")


def _key() -> str:
    return os.environ.get("EMERGENT_LLM_KEY", "")


async def _run_chat(system: str, user_text: str,
                    file_b64: Optional[str] = None,
                    file_mime: Optional[str] = None,
                    model: str = "gpt-5.2") -> str:
    """Send a single message (optionally with image) and collect full text."""
    try:
        from emergentintegrations.llm.chat import (
            LlmChat, UserMessage, ImageContent, TextDelta, StreamDone,
        )
    except Exception as e:
        logger.error(f"emergentintegrations import failed: {e}")
        return ""

    if not _key():
        logger.warning("EMERGENT_LLM_KEY missing; skipping AI call")
        return ""

    chat = LlmChat(
        api_key=_key(),
        session_id=str(uuid.uuid4()),
        system_message=system,
    ).with_model("openai", model)

    kwargs: Dict[str, Any] = {"text": user_text}
    if file_b64:
        kwargs["file_contents"] = [ImageContent(image_base64=file_b64)]

    msg = UserMessage(**kwargs)
    out_parts: List[str] = []
    try:
        async for ev in chat.stream_message(msg):
            if isinstance(ev, TextDelta):
                out_parts.append(ev.content)
            elif isinstance(ev, StreamDone):
                break
    except Exception as e:
        logger.error(f"GPT-5.2 call failed: {e}")
        return ""
    return "".join(out_parts).strip()


def _extract_json(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.startswith("json"):
            t = t[4:]
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(t[start:end + 1])
    except Exception:
        return {}


# --------------- Communication Fraud Analysis ---------------

COMM_SYSTEM = """You are an expert forensic analyst for Indian MSME payment fraud.
You classify emails, WhatsApp and SMS messages targeting finance / owner / vendor teams.
You detect: urgency, secrecy, authority impersonation, unusual payment instructions,
new beneficiary details, look-alike email domains, reply-to mismatch, changed writing style,
suspicious links, and requests to bypass approval controls.
Respond ONLY as compact JSON, no markdown, no prose."""


async def analyse_communication(text: str) -> Dict[str, Any]:
    prompt = (
        "Analyse the following message and return JSON with schema:\n"
        "{ \"score\": number(0-100), \"category\": \"low|moderate|high|critical|suspected_fraud\",\n"
        "  \"signals\": [ { \"category\": string, \"phrase\": string,\n"
        "                   \"severity\": \"low|moderate|high|critical\", \"reason\": string } ],\n"
        "  \"summary\": string }\n\n"
        f"MESSAGE:\n---\n{text}\n---"
    )
    raw = await _run_chat(COMM_SYSTEM, prompt)
    data = _extract_json(raw)
    if not data:
        return {"score": 0, "category": "low", "signals": [], "summary": "", "ai_available": False}
    data["ai_available"] = True
    return data


# --------------- Invoice Vision Extraction ---------------

INVOICE_SYSTEM = """You are a precise OCR + structured extraction engine for Indian tax invoices.
You read an invoice image and return strict JSON only, no markdown, no commentary.
Do NOT guess. Set missing fields to null."""


async def extract_invoice(image_bytes: bytes, mime: str = "image/png") -> Dict[str, Any]:
    b64 = base64.b64encode(image_bytes).decode()
    prompt = (
        "Extract these fields from the invoice image and return JSON:\n"
        "{ \"supplier_name\": string|null, \"gstin\": string|null, \"pan\": string|null,\n"
        "  \"invoice_number\": string|null, \"invoice_date\": string|null,\n"
        "  \"taxable_amount\": number|null, \"cgst\": number|null, \"sgst\": number|null,\n"
        "  \"igst\": number|null, \"total_amount\": number|null,\n"
        "  \"po_number\": string|null, \"bank_account\": string|null, \"ifsc\": string|null,\n"
        "  \"qr_data\": string|null,\n"
        "  \"line_items\": [ { \"description\": string, \"qty\": number|null,\n"
        "                     \"rate\": number|null, \"amount\": number|null } ],\n"
        "  \"observations\": [ string ] }\n"
        "Only respond with the JSON object."
    )
    raw = await _run_chat(INVOICE_SYSTEM, prompt, file_b64=b64, file_mime=mime)
    data = _extract_json(raw)
    if not data:
        return {"ai_available": False}
    data["ai_available"] = True
    return data


# --------------- Free-form fraud narrative ---------------

NARRATIVE_SYSTEM = """You are a payment-safety analyst summarising fraud risk for
Indian MSME owners. Explain findings crisply in plain English, 3-4 sentences max."""


async def generate_narrative(context: str) -> str:
    raw = await _run_chat(
        NARRATIVE_SYSTEM,
        f"Given these red flags, write a plain-English risk summary a business owner can act on:\n\n{context}",
    )
    return raw or ""
