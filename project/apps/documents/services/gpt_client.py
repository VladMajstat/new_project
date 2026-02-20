import json
import os
from pathlib import Path
from typing import Any, Dict
from openai import OpenAI


def _load_schema() -> Dict[str, Any]:
    p = Path(__file__).resolve().parent / "new_parser.json"
    return json.loads(p.read_text(encoding="utf-8"))


def parse_form_page_to_new_parser(page_png_base64: str) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    schema = _load_schema()
    client = OpenAI(api_key=api_key)

    system = (
        "You extract data from a scanned German form 'Verordnung einer Krankenbefoerderung'. "
        "Return ONLY valid JSON, no markdown. "
        "The output MUST match exactly the keys and nesting of the example JSON. "
        "Do not invent. Unknown => \"\" for strings, false for booleans. "

        "Insurance status: ONLY take the numeric value from the line labeled 'Status' in the insurance block (near Versicherten-Nr./Kostentraegerkennung). "
        "Do NOT use any number from the Krankenkasse/insurer line as status. "
        "Status must be exactly 7 digits; if you cannot read a 7-digit status, return an empty string for status. Ignore handwritten/pencil notes outside printed boxes/fields (e.g., numbers written above the insurance block). "
        "Ordering party (block13): if a doctor name is present (e.g. with Dr./med/Dipl.-med), put the doctor name in auftraggeberName; otherwise use the full organization name. "
        "Put ALL department/specialty/address lines in auftraggeberInfo, each on a new line, in the same order as on the form. "
        "Keep specialty lines like 'FA ...', 'ZB ...', 'Facharztin fuer ...', '-Hausarztliche Versorgung-'. "
        "If ZIP/city/phone are present anywhere in that block, fill auftraggeberZip/auftraggeberCity/auftraggeberTelefon. "
        "Phone lines should go to auftraggeberTelefon; do not include the phone line in auftraggeberInfo. If a phone number appears in the doctor stamp (e.g., 'Telefon: ...'), put it in auftraggeberTelefon even if it is outside the block text. "
    )

    user_text = (
        "EXAMPLE JSON STRUCTURE:\n"
        + json.dumps(schema, ensure_ascii=False)
        + "\n\nFill this JSON by reading the attached scanned form page image."
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_png_base64}"}}
            ]},
        ],
        temperature=0,
        response_format={"type": "json_object"},
        timeout=120,
    )

    data = json.loads((resp.choices[0].message.content or "").strip())

    if set(data.keys()) != set(schema.keys()):
        raise RuntimeError("Wrong JSON structure: top-level keys do not match new_parser.json")

    return data







def parse_insurance_status(page_png_base64: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)

    system = (
        "You extract ONLY the insurance Status code from the printed field labeled 'Status' (the 7-digit code printed next to the word 'Status'; it usually starts with 5) "
        "in the insurance block of the German form 'Verordnung einer Krankenbefoerderung'. "
        "Return ONLY JSON with the single key 'status'. Locate the word 'Status' and read ONLY the digits in that printed box/row. "
        "Ignore handwritten/pencil notes and any numbers outside the printed Status box. "
        "If you cannot read a 7-digit status from the printed Status box, return an empty string."
    )

    user_text = "Return JSON like {\"status\": \"5000000\"} or empty string if not readable."

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_png_base64}"}},
            ]},
        ],
        temperature=0,
        response_format={"type": "json_object"},
        timeout=120,
    )

    data = json.loads((resp.choices[0].message.content or "").strip())
    return str(data.get("status", "") or "").strip()



def parse_ordering_party_phone(page_png_base64: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)

    system = (
        "You extract ONLY the phone number of the Ordering party (doctor stamp). "
        "Return ONLY JSON with the single key 'phone'. "
        "Ignore numbers that are part of names or addresses. "
        "Prefer a number labeled Tel/Telefon/Phone/Fax. "
        "If no phone is clearly labeled, return an empty string."
    )

    user_text = "Return JSON like {\"phone\": \"030/8255051\"} or empty string if not readable."

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_png_base64}"}},
            ]},
        ],
        temperature=0,
        response_format={"type": "json_object"},
        timeout=120,
    )

    data = json.loads((resp.choices[0].message.content or "").strip())
    return str(data.get("phone", "") or "").strip()



def parse_betriebsstaetten_nr(page_png_base64: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)

    system = (
        "You extract ONLY the Betriebsstaetten-Nr. (facility ID) from the printed field labeled 'Betriebsstaetten-Nr.' (the 9-digit number printed on the line under the label, immediately left of 'Arzt-Nr.' and above 'Datum'). "
        "on the German form 'Verordnung einer Krankenbefoerderung'. "
        "Return ONLY JSON with the single key 'betriebsstaetten_nr'. "
        "Ignore handwritten notes. Do NOT reorder digits. If you cannot read a 9-digit number from that printed field, return an empty string."
    )

    user_text = "Return JSON like {\"betriebsstaetten_nr\": \"727405500\"} or empty string if not readable."

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_png_base64}"}},
            ]},
        ],
        temperature=0,
        response_format={"type": "json_object"},
        timeout=120,
    )

    data = json.loads((resp.choices[0].message.content or "").strip())
    return str(data.get("betriebsstaetten_nr", "") or "").strip()
