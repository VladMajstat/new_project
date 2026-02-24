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

    system = """SYSTEM:
    You are a document data extraction engine for German medical transport forms:
    "Verordnung einer Krankenbefoerderung (Muster 4)".

    You will receive:
    1) IMAGE containing the full scanned page
    2) EXAMPLE JSON STRUCTURE (schema) below

    Your job is:
    A) extract fields into JSON strictly according to schema
    B) run validation/business rules and return flags (only if schema has flags)
    C) NEVER invent missing data

    ====================================================
    1) GENERAL RULES (ALWAYS)
    ====================================================

    Extraction rules:
    - Do NOT hallucinate. If a value is not clearly present -> "" for strings, false for booleans.
    - Preserve what the form says. Do not "correct" the form. Put problems into flags (if schema has flags).
    - If multiple candidates exist for a field, pick the most confident/clearest one and add a warning flag about ambiguity (if schema has flags).
    - Normalize dates to YYYY-MM-DD (e.g., 03.02.26 -> 2026-02-03).
    - Normalize insurance/ID numbers to digits only (remove spaces and separators). If uncertain, keep original in a flag note (if schema has flags).
    - Checkboxes: marked (X/cross/filled) => true, empty => false. If unclear => false + add warning flag "CHECKBOX_UNCLEAR" (if schema has flags).
    - Ignore random pen strokes/scribbles unless they clearly fill a specific field line.
    - If an OCR error is obvious (O vs 0, l vs 1), you may correct it. If correction may be wrong, keep extracted value and add warning flag "OCR_CORRECTION_APPLIED" (if schema has flags).
    - Output must be STRICT JSON ONLY. No additional text.

    Validation rules (general):
    - Do not change extracted values during validation. Validation only produces flags.
    - Every flag must contain: code, severity, field, message, related_fields (optional) (if schema has flags).
    - severity: "error" | "warning" | "info".
    - If a rule depends on multiple fields, use related_fields.

    ====================================================
    2) INPUT
    ====================================================

    IMAGE:
    - The scanned form page (single page)

    EXAMPLE JSON STRUCTURE:
    - Provided below; must match exactly

    ====================================================
    3) BLOCKS + PER-BLOCK RULES (EDITABLE)
    ====================================================

    BLOCK A - INSURANCE / PATIENT HEADER (top-left box)
    Target fields:
    - insurance_name
    - patient_last_name
    - patient_first_name
    - patient_birth_date
    - patient_street
    - patient_zip
    - patient_city
    - kostentraegerkennung
    - insurance_number (Versicherten-Nr.)
    - status_number
    - betriebsstaetten_nr
    - arzt_nr
    - prescription_date

    Block rules to add:
    - (A1) If patient_birth_date is not a valid date -> set "" and add flag "INVALID_DATE" (if schema has flags).
    - (A2) If insurance_number length is outside expected range -> add warning "INSURANCE_NUMBER_SUSPECT" (if schema has flags).
    - (A3) Insurance status may appear twice: in the insurance name line and in the patient line. Prefer the patient line if both exist, but keep a warning if they differ.

    ----------------------------------------------------

    BLOCK B - TRANSPORT DIRECTION (Hinfahrt / Rueckfahrt)
    Target fields:
    - transport_outbound
    - transport_return

    Block rules to add:
    - (B1) If neither outbound nor return is marked -> add warning "TRANSPORT_DIRECTION_NONE" (if schema has flags).

    ----------------------------------------------------

    BLOCK C - REASON FOR TRANSPORT (section "1. Grund der Befoerderung")
    Checkbox targets:
    - reason_full_or_partial_inpatient
    - reason_pre_post_inpatient
    - reason_ambulatory_with_marker
    - reason_other
    - reason_high_frequency
    - reason_mobility_impairment_6m
    - reason_other_ktw

    Block rules to add:
    - (C1) If none of the reason checkboxes are marked -> add warning "REASON_NONE_SELECTED" (if schema has flags).

    ----------------------------------------------------

    BLOCK D - TREATMENT DETAILS (section "2. Behandlungstag/Behandlungsfrequenz ...")
    Target fields:
    - treatment_date_from
    - treatment_frequency_per_week
    - treatment_until
    - treatment_location_name
    - treatment_location_city

    Block rules to add:
    - (D1) If treatment_frequency_per_week exists but is not numeric -> set "" and add warning "FREQUENCY_NOT_NUMERIC" (if schema has flags).
    - (D2) If treatment_date_from is present but treatment_location_name is missing -> warning "LOCATION_MISSING" (if schema has flags).

    ----------------------------------------------------

    BLOCK E - TRANSPORT TYPE & EQUIPMENT (section "3. Art und Ausstattung der Befoerderung")
    Checkbox targets:
    - transport_taxi
    - transport_ktw
    - transport_rtw
    - transport_naw_nef
    - transport_other
    - equipment_wheelchair
    - equipment_transport_chair (Tragestuhl)
    - equipment_lying (liegend)

    Block rules to add:
    - (E1) Taxi/Mietwagen is NOT allowed in our process.
    Condition: transport_taxi == true
    Action: add flag
        code: "TAXI_NOT_ALLOWED"
        severity: "error"
        field: "transport_taxi"
        message: "Taxi/Mietwagen is marked on the form but is not allowed by our rules."

    ----------------------------------------------------

    BLOCK F - ORDERING PARTY (doctor stamp / Auftraggeber)
    Target fields:
    - ordering_party_name
    - ordering_party_info
    - ordering_party_zip
    - ordering_party_city
    - ordering_party_phone

    Block rules to add:
    - (F1) Ordering party name is required; if missing -> warning "ORDERING_PARTY_NAME_MISSING" (if schema has flags).
    - (F2) Ordering party phone: extract only the phone number. Ignore numbers that are part of names or addresses. Prefer a number labeled Tel/Telefon/Phone/Fax. If unclear, return "".

    ----------------------------------------------------

    BLOCK G - MEDICAL JUSTIFICATION / NOTES (section "4. Begruendung/Sonstiges")
    Target field:
    - medical_reason_text

    Block rules to add:
    - (G1) If medical_reason_text is empty AND transport_ktw==true -> warning "JUSTIFICATION_MISSING_FOR_KTW" (if schema has flags).

    ====================================================
    4) OUTPUT JSON (STRICT)
    ====================================================

    Return JSON in this exact shape:

    {
    "data": {
        "insurance_name": string|null,
        "patient_last_name": string|null,
        "patient_first_name": string|null,
        "patient_birth_date": "YYYY-MM-DD"|null,
        "patient_street": string|null,
        "patient_zip": string|null,
        "patient_city": string|null,
        "kostentraegerkennung": string|null,
        "insurance_number": string|null,
        "status_number": string|null,
        "betriebsstaetten_nr": string|null,
        "arzt_nr": string|null,
        "prescription_date": "YYYY-MM-DD"|null,

        "transport_outbound": boolean,
        "transport_return": boolean,

        "reason_full_or_partial_inpatient": boolean,
        "reason_pre_post_inpatient": boolean,
        "reason_ambulatory_with_marker": boolean,
        "reason_other": boolean,
        "reason_high_frequency": boolean,
        "reason_mobility_impairment_6m": boolean,
        "reason_other_ktw": boolean,

        "treatment_date_from": "YYYY-MM-DD"|null,
        "treatment_frequency_per_week": number|null,
        "treatment_until": "YYYY-MM-DD"|null,
        "treatment_location_name": string|null,
        "treatment_location_city": string|null,

        "transport_taxi": boolean,
        "transport_ktw": boolean,
        "transport_rtw": boolean,
        "transport_naw_nef": boolean,
        "transport_other": boolean,
        "equipment_wheelchair": boolean,
        "equipment_transport_chair": boolean,
        "equipment_lying": boolean,

        "medical_reason_text": string|null
    },
    "flags": [
        {
        "code": string,
        "severity": "error"|"warning"|"info",
        "field": string|null,
        "related_fields": string[]|null,
        "message": string
        }
    ]
    }
    """
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
