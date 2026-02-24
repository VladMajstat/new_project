import json
import re
import os
from pathlib import Path
from typing import Any, Dict
from openai import OpenAI
import logging


logger = logging.getLogger(__name__)

def _load_schema() -> Dict[str, Any]:
    p = Path(__file__).resolve().parent / "new_parser.json"
    return json.loads(p.read_text(encoding="utf-8"))


def parse_form_page_to_new_parser(page_png_base64: str, extra_images: list[str] | None = None, trip_hints: Dict[str, bool] | None = None) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    schema = _load_schema()
    client = OpenAI(api_key=api_key)
    system = """SYSTEM:
You are a document data extraction engine for German medical transport forms:
"Verordnung einer Krankenbefoerderung (Muster 4)".

You will receive:
1) IMAGE_1 containing the full scanned page
2) EXAMPLE JSON STRUCTURE (schema) below

Your job is:
A) extract fields into JSON strictly according to schema
B) run validation/business rules and return flags
C) NEVER invent missing data

====================================================
1) GENERAL RULES (ALWAYS)
====================================================

Extraction rules:
- Use ONLY clearly printed text. Ignore handwritten/pencil text, stamps over handwriting, and scribbles.
- Treat table borders, vertical separators, horizontal lines, and box frames as NON-CHARACTERS.
- If a border touches a character, ignore the border; read only the printed glyph.
- If a value is not clearly readable, return "" and add a warning flag.

Numeric fields:
- Read numeric codes digit-by-digit.
- kostentraegerkennung MUST be exactly 9 digits; if not, return "" + warning.
- betriebsstaetten_nr and arzt_nr MUST be exactly 9 digits; if not, return "" + warning.
- Arzt-Nr. appears on the same line as 'Betriebsstaetten-Nr.' and 'Datum'. Read ONLY printed digits from the Arzt-Nr. box; ignore any handwritten strokes crossing the line.
- If the Arzt-Nr. is partially overlapped by pen marks, still extract the full 9-digit printed number if all digits are visible.
- For Arzt-Nr. and Betriebsstaetten-Nr., distinguish 0 vs 3 carefully: 0 is a closed oval, 3 is open with two curves. Do not substitute 3 for 0.
- Do NOT take numbers from the doctor stamp (bottom-right box) for Arzt-Nr.
- status_number must be 7 digits; preserve exactly as printed. If unclear, return "" + warning.
- Insurance number (Versicherten-Nr.) is alphanumeric; keep letters and digits, no spaces.
  If leading letter ambiguous: prefer E over F, and Z over 2 only when the form shows a letter.
  If uncertain, return "" + warning.

Checkbox rules (strict):
- A checkbox is TRUE only if a clear X/cross is fully inside the box.
- If unclear or empty => false + warning.
- Do NOT infer from nearby text or pen strokes.

Specific mappings:
- Reasons (right block):
  Unfall, Unfallfolge -> reason_accident
  Arbeitsunfall, Berufskrankheit -> reason_work_accident
  Versorgungsleiden (z.B. BVG) -> reason_care_condition
- Trip direction:
  Hinfahrt -> transport_outbound
  Rueckfahrt -> transport_return
  If both are checked, set transport_outbound=true and transport_return=false + warning.
- Treatment type (Genehmigungsfreie Fahrten a/b/c only):
  a) voll-/teilstationaer -> reason_full_or_partial_inpatient
  a) vor-/nachstationaer -> reason_pre_post_inpatient
  b) ambulant... -> reason_ambulatory_with_marker
  c) anderer Grund -> reason_other
  IMPORTANT: Only read a/b/c from the Genehmigungsfreie Fahrten block. Do NOT use any checkboxes from d/e/f for treatment type.
  If you see a check in the mandatory trips block (d/e/f), set all treatment type fields to false.
  a) has two boxes: LEFT = voll-/teilstationaer, RIGHT = vor-/nachstationaer.
  If the LEFT box in a) is checked, reason_full_or_partial_inpatient must be true.
- Mandatory trips (d/e/f only):
  d) hochfrequente Behandlung -> reason_high_frequency
  e) dauerhafte Mobilitaetsbeeintraechtigung -> reason_mobility_impairment_6m
  f) anderer Grund f?r Fahrt mit KTW -> reason_other_ktw
  If d) or e) is checked, then f) must be false and ktw_reason_text must be empty.
  If f) is checked, set ktw_reason_text to the text on the f) line ONLY.
  Do NOT use clinic names, departments, addresses, or any other blocks for ktw_reason_text.
  If f) is not checked, ktw_reason_text must be empty.
- Transport position: if Tragestuhl is marked, do NOT mark liegend unless liegend box is clearly marked.
- Transport type checkboxes are ONLY in section '3. Art und Ausstattung der Befoerderung'. Do NOT set transport_taxi from any text in block 1 or other sections.
- If Taxi/Mietwagen appears or is marked, do NOT set transport_taxi (leave it false).
- Block 1 a) has two checkboxes on the same line: LEFT for 'voll-/teilstationaere Krankenhausbehandlung', RIGHT for 'vor-/nachstationaere Behandlung'. Look only at those two boxes on that line.
- Ordering party phone: extract ONLY the phone number labeled Tel/Telefon (ignore Fax). Do not include the word "Tel".

Validation rules (general):
- Do not change extracted values during validation. Validation only produces flags.
- Every flag must contain: code, severity, field, message, related_fields (optional).
- severity: "error" | "warning" | "info".

Strict schema rules:
- The output MUST contain only the keys defined in the EXAMPLE JSON STRUCTURE.
- Do NOT add any extra keys (no block* keys or any other top-level fields).

====================================================
2) INPUT
====================================================

IMAGE_1:

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
- (A1) If patient_birth_date is not a valid date -> set "" and add flag "INVALID_DATE".
- (A2) If insurance_number length is outside expected range -> add warning "INSURANCE_NUMBER_SUSPECT".

----------------------------------------------------

BLOCK B - TRANSPORT DIRECTION (Hinfahrt / Rueckfahrt)
Target fields:
- transport_outbound
- transport_return

Block rules to add:
- (B1) If neither outbound nor return is marked -> add warning "TRANSPORT_DIRECTION_NONE".

----------------------------------------------------

BLOCK C - REASON FOR TRANSPORT (section "1. Grund der Befoerderung")
Checkbox targets:
- reason_full_or_partial_inpatient
- reason_pre_post_inpatient
- reason_ambulatory_with_marker
- reason_other

Block rules to add:
- (C1) If none of the reason checkboxes are marked -> add warning "REASON_NONE_SELECTED".
- (C2) If the LEFT checkbox on line a) is marked, reason_full_or_partial_inpatient MUST be true.

----------------------------------------------------

BLOCK D - TREATMENT DETAILS (section "2. Behandlungstag/Behandlungsfrequenz ...")
Target fields:
- treatment_date_from
- treatment_frequency_per_week
- treatment_until
- treatment_location_name
- treatment_location_city

Block rules to add:
- (D1) If treatment_frequency_per_week exists but is not numeric -> set "" and add warning "FREQUENCY_NOT_NUMERIC".
- (D2) If treatment_date_from is present but treatment_location_name is missing -> warning "LOCATION_MISSING".

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
- (F1) Ordering party name is required; if missing -> warning "ORDERING_PARTY_NAME_MISSING".
- (F2) Ordering party phone: extract only the phone number. Ignore numbers that are part of names or addresses. Prefer a number labeled Tel/Telefon. If unclear, return "".

----------------------------------------------------

BLOCK G - MEDICAL JUSTIFICATION / NOTES (section "4. Begruendung/Sonstiges")
Target field:
- medical_reason_text

Block rules to add:

====================================================
4) OUTPUT JSON (STRICT)
====================================================

Return JSON in this exact shape:

{
  "data": {
    "insurance_name": "",
    "patient_last_name": "",
    "patient_first_name": "",
    "patient_birth_date": "YYYY-MM-DD",
    "patient_street": "",
    "patient_zip": "",
    "patient_city": "",
    "kostentraegerkennung": "",
    "insurance_number": "",
    "status_number": "",
    "betriebsstaetten_nr": "",
    "arzt_nr": "",
    "prescription_date": "YYYY-MM-DD",

    "transport_outbound": false,
    "transport_return": false,

    "reason_full_or_partial_inpatient": false,
    "reason_pre_post_inpatient": false,
    "reason_ambulatory_with_marker": false,
    "reason_other": false,

    "treatment_date_from": "YYYY-MM-DD",
    "treatment_frequency_per_week": "",
    "treatment_until": "YYYY-MM-DD",
    "treatment_location_name": "",
    "treatment_location_street": "",
    "treatment_location_zip": "",
    "treatment_location_city": "",

    "transport_taxi": false,
    "transport_ktw": false,
    "transport_rtw": false,
    "transport_naw_nef": false,
    "transport_other": false,
    "equipment_wheelchair": false,
    "equipment_transport_chair": false,
    "equipment_lying": false,

    "medical_reason_text": "",

    "ordering_party_name": "",
    "ordering_party_info": "",
    "ordering_party_zip": "",
    "ordering_party_city": "",
    "ordering_party_phone": ""
  },
  "flags": [
    {
      "code": "",
      "severity": "warning",
      "field": "",
      "related_fields": [],
      "message": ""
    }
  ]
}"""

    hints_text = ""
    if isinstance(trip_hints, dict) and trip_hints:
        hints_text += "TRIP_DIRECTION_HINTS: " + json.dumps(trip_hints, ensure_ascii=False) + "\n"
    user_text = hints_text + "EXAMPLE JSON STRUCTURE:" + json.dumps(schema, ensure_ascii=False)

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
    logger.info("Parsed data keys: %s", list(data.keys()) if isinstance(data, dict) else type(data))

    # Split clinic line into fields if merged
    def _split_clinic_line(line: str):
        if not line:
            return None
        # Try pattern: name, street, ZIP city
        m = re.search(r"^(?P<name>.*?),(?P<street>.*?),(?P<zip>\d{5})\s+(?P<city>.+)$", line)
        if not m:
            # Try pattern: name, street ZIP city
            m = re.search(r"^(?P<name>.*?),(?P<street>.*?)(?P<zip>\d{5})\s+(?P<city>.+)$", line)
        if not m:
            return None
        return {
            "name": m.group("name").strip(),
            "street": m.group("street").strip().strip(","),
            "zip": m.group("zip").strip(),
            "city": m.group("city").strip(),
        }

    # Enforce single trip direction: if both true, keep outbound and unset return
    # Apply trip direction hints if provided
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict) and isinstance(trip_hints, dict):
            out_h = bool(trip_hints.get("outbound"))
            ret_h = bool(trip_hints.get("return"))
            if out_h and ret_h:
                d["transport_outbound"] = True
                d["transport_return"] = False
            elif out_h and not ret_h:
                d["transport_outbound"] = True
                d["transport_return"] = False
            elif ret_h and not out_h:
                d["transport_outbound"] = False
                d["transport_return"] = True
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            if d.get("transport_outbound") and d.get("transport_return"):
                d["transport_return"] = False


    _enforce_no_lying = True

    # Fix insurance_number leading O vs 0 when 10 digits
    # Fix insurance_number leading E vs F when ambiguous
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            ins = (d.get("insurance_number") or "").strip()
            if re.fullmatch(r"F\d{9}", ins):
                d["insurance_number"] = "E" + ins[1:]

    # Fix insurance_number leading Z vs 2 when 10 digits
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            ins = (d.get("insurance_number") or "").strip()
            if re.fullmatch(r"2\d{9}", ins):
                d["insurance_number"] = "Z" + ins[1:]

    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            ins = (d.get("insurance_number") or "").strip()
            if re.fullmatch(r"0\d{9}", ins):
                d["insurance_number"] = "O" + ins[1:]
    # Validate insurance status: must be 7 digits and typically starts with '5'
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            status = (d.get("status_number") or "").strip()
            digits = re.sub(r"\D", "", status)
            if not (len(digits) == 7 and digits.startswith("5")):
                d["status_number"] = ""

    # Enforce 9-digit printed doctor identifiers
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            bsnr = re.sub(r"\D", "", (d.get("betriebsstaetten_nr") or ""))
            arzt = re.sub(r"\D", "", (d.get("arzt_nr") or ""))
            d["betriebsstaetten_nr"] = bsnr if len(bsnr) == 9 and bsnr != "000000000" else ""
            d["arzt_nr"] = arzt if len(arzt) == 9 and arzt != "000000000" else ""

    # Default insurance status if missing/invalid
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            status = (d.get("status_number") or "").strip()
            digits = re.sub(r"\D", "", status)
            if not (len(digits) == 7 and digits.startswith("5")):
                d["status_number"] = "5000000"

    # Enforce 9-digit cost carrier code, ignore handwritten-like noise
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            kc = (d.get("kostentraegerkennung") or "").strip()
            digits = re.sub(r"\D", "", kc)
            if digits:
                d["kostentraegerkennung"] = digits

    # Normalize ordering_party_phone: strip labels like Tel./Telefon/Fax
    # Keep only phone number before Fax, if present
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            phone = (d.get("ordering_party_phone") or "").strip()
            if phone:
                phone = re.sub(r"^(tel\.?|telefon|fax)[:\s]*", "", phone, flags=re.IGNORECASE).strip()
                phone = re.split(r"\bfax\b", phone, flags=re.IGNORECASE)[0].strip()
                d["ordering_party_phone"] = phone

    # Clean ordering_party_info: remove name and ZIP/city if present
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            info = (d.get("ordering_party_info") or "").strip()
            name = (d.get("ordering_party_name") or "").strip()
            zip_ = (d.get("ordering_party_zip") or "").strip()
            city = (d.get("ordering_party_city") or "").strip()
            if info:
                if name:
                    info = info.replace(name, "").strip(" ,")
                if zip_ and city:
                    info = info.replace(f"{zip_} {city}", "").strip(" ,")
                if zip_ and not city:
                    info = info.replace(zip_, "").strip(" ,")
                if city and not zip_:
                    info = info.replace(city, "").strip(" ,")
                d["ordering_party_info"] = info
    
    
    # Prevent 'lying' when carry chair is selected
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            if d.get("equipment_transport_chair") and d.get("equipment_lying"):
                d["equipment_lying"] = False

    # Fill clinic fields from merged line when missing
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            if not d.get("treatment_location_street") and not d.get("treatment_location_zip"):
                merged = d.get("treatment_location_name", "")
                parts = _split_clinic_line(merged)
                if parts:
                    d["treatment_location_name"] = parts["name"]
                    d["treatment_location_street"] = parts["street"]
                    d["treatment_location_zip"] = parts["zip"]
                    d["treatment_location_city"] = parts["city"]
    # Enforce single-checkbox selection for key groups
    if isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), dict) else None
        if isinstance(d, dict):
            # Reasons (Unfall/Arbeitsunfall/Versorgungsleiden)
            reasons = ["reason_accident", "reason_work_accident", "reason_care_condition"]
            if sum(bool(d.get(k)) for k in reasons) != 1:
                for k in reasons:
                    d[k] = False

            # Trip direction (Hinfahrt/Rueckfahrt)
            trips = ["transport_outbound", "transport_return"]
            if sum(bool(d.get(k)) for k in trips) == 2:
                d["transport_outbound"] = True
                d["transport_return"] = False
            elif sum(bool(d.get(k)) for k in trips) != 1:
                for k in trips:
                    d[k] = False

            # Block 1 (Genehmigungsfreie Fahrten) a/b/c
            block1 = ["reason_full_or_partial_inpatient", "reason_pre_post_inpatient", "reason_ambulatory_with_marker", "reason_other"]
            if sum(bool(d.get(k)) for k in block1) != 1:
                for k in block1:
                    d[k] = False

            # Mandatory trips (d/e/f)
            mandatory = ["reason_high_frequency", "reason_mobility_impairment_6m", "reason_other_ktw"]
            if sum(bool(d.get(k)) for k in mandatory) > 1:
                for k in mandatory:
                    d[k] = False

            # If any mandatory trip (d/e/f) is checked, treatment type a/b/c must be false
            if any(bool(d.get(k)) for k in mandatory):
                for k in block1:
                    d[k] = False

    return data