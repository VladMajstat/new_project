import re
import logging
from typing import Any, Dict


logger = logging.getLogger(__name__)

_PHONE_RE = re.compile(r"(\+?\d[\d\s/()\-]{5,}\d)")
_ZIP_CITY_RE = re.compile(r"\b(\d{5})\s+([A-Za-z\-\.]+(?:\s+[A-Za-z\-\.]+)*)")
_DOCTOR_RE = re.compile(r"\b(?:Dr\.?|Prof\.?|med\.?|Herr|Frau)\b", re.IGNORECASE)
_ORG_HINTS = (
    "Universitaetsmedizin",
    "Klinik",
    "Krankenhaus",
    "MVZ",
    "GmbH",
    "Charit",
    "Praxis",
    "Zentrum",
    "Ambulanz",
    "Hochschulambulanz",
)



_DEPT_KEYWORDS = (
    "Hochschulambulanz",
    "Ambulanz",
    "Zentrum",
    "Klinik",
    "Praxis",
)


def _split_name_department(name: str) -> tuple[str, str]:
    for kw in _DEPT_KEYWORDS:
        idx = name.find(kw)
        if idx > 0:
            head = name[:idx].strip()
            tail = name[idx:].strip()
            if head and tail:
                return head, tail
    return name, ""


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]






def _extract_person_name_line(lines: list[str]) -> tuple[str, list[str]]:
    for i, line in enumerate(list(lines)):
        if _looks_like_person_name(line) and not _looks_like_address_line(line) and not _is_specialty_info_line(line) and not _is_phone_line(line):
            new_lines = lines[:i] + lines[i+1:]
            return line, new_lines
    return "", lines


def _extract_doctor_line(lines: list[str]) -> tuple[str, list[str]]:
    for i, line in enumerate(list(lines)):
        if _is_doctor_line(line):
            new_lines = lines[:i] + lines[i+1:]
            return line, new_lines
    return "", lines


def _is_doctor_line(line: str) -> bool:
    return bool(_DOCTOR_RE.search(line))


def _looks_like_person_name(line: str) -> bool:
    parts = [p for p in re.split(r"\s+", line) if p]
    if len(parts) < 2 or len(parts) > 5:
        return False
    if any(k in line for k in _ORG_HINTS):
        return False
    if line.upper().startswith("FA ") or line.upper().startswith("ZB "):
        return False
    if "Facharzt" in line:
        return False
    return all(p[:1].isupper() for p in parts)


def _is_phone_line(line: str) -> bool:
    return "telefon" in line.lower() or bool(_PHONE_RE.search(line))


def _normalize_name_token(text: str) -> str:
    # replace punctuation with spaces for name detection
    cleaned = re.sub(r"[()\./-]", " ", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _is_doctor_name_line(line: str) -> bool:
    l = _normalize_name_token(line).lower()
    if re.search(r"\bdr\b", l):
        return True
    if "dr med" in l or "drmed" in l:
        return True
    if "dipl med" in l or "diplmed" in l:
        return True
    return False


def _normalize_phone(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    # keep digits and slashes, optionally leading +
    lead_plus = value.startswith("+")
    filtered = "".join(ch for ch in value if ch.isdigit() or ch == "/")
    digits_only = "".join(ch for ch in filtered if ch.isdigit())

    # Collapse exact duplicate halves like 78623647862364
    if len(digits_only) % 2 == 0 and len(digits_only) > 0:
        half = len(digits_only) // 2
        if digits_only[:half] == digits_only[half:]:
            digits_only = digits_only[:half]
            return ("+" if lead_plus else "") + digits_only

    # If tel+fax got concatenated, keep the first part
    if len(digits_only) >= 14:
        if digits_only.startswith("0"):
            digits_only = digits_only[:10]
        else:
            digits_only = digits_only[:7]
        return ("+" if lead_plus else "") + digits_only

    # Otherwise keep slashes
    return ("+" if lead_plus else "") + filtered




def _extract_phone_from_text(text: str) -> str:
    if not text:
        return ""
    lines = _split_lines(text)
    # Only accept lines explicitly labeled as phone
    for line in lines:
        if re.search(r"\b(tel|telefon|phone|fax)\b", line, re.IGNORECASE):
            m = _PHONE_RE.search(line)
            if m:
                return m.group(1).strip()
    return ""




def _normalize_ocr(text: str) -> str:
    return (text or "").replace("\u00c5", "A").replace("\u00c4", "A").replace("\u00d6", "O").replace("\u00dc", "U").replace("\u00e4", "a").replace("\u00f6", "o").replace("\u00fc", "u").replace("\u00df", "ss")




def _is_specialty_info_line(line: str) -> bool:
    norm = _normalize_ocr(line)
    l = norm.lower()
    if norm.upper().startswith("FA ") or norm.upper().startswith("ZB "):
        return True
    if "facharzt" in l or "fachaerzt" in l:
        return True
    if "hausaerztliche versorgung" in l:
        return True
    if "zahnarzt" in l:
        return True
    return False






def _is_name_candidate(line: str) -> bool:
    if _is_phone_line(line):
        return False
    if _looks_like_address_line(line):
        return False
    if _is_specialty_info_line(line):
        return False
    if any(k in line for k in _ORG_HINTS):
        return False
    return _is_doctor_name_line(line) or _looks_like_person_name(line)


def _looks_like_address_line(line: str) -> bool:
    l = _normalize_ocr(line).lower()
    if any(k in l for k in ("str", "str.", "strasse", "allee", "platz", "weg", "ring", "gasse")):
        return True
    if _ZIP_CITY_RE.search(line):
        return True
    return False


def _is_allowed_info_line(line: str) -> bool:
    norm = _normalize_ocr(line)
    l = norm.lower()
    if _is_specialty_info_line(line):
        return True
    if any(k in l for k in ("str", "str.", "strasse", "allee", "platz", "weg", "ring", "gasse")):
        return True
    if any(k in l for k in ("standort", "abteilung", "bereich", "zentrum")):
        return True
    if any(k in norm for k in _ORG_HINTS):
        return True
    if any(ch.isdigit() for ch in line):
        return True
    return False




def _digits_only(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _normalize_insurance_status(value: str) -> str:
    if not value:
        return ""
    import re as _re
    # Accept only 7 digits starting with 5 (printed Status codes are 5xxxxxx)
    m = _re.search(r"5\d{6}", value)
    return m.group(0) if m else ""


def normalize_insurance_block(data: Dict[str, Any]) -> Dict[str, Any]:
    block1 = dict(data.get("block1_insurance", {}) or {})
    block2 = dict(data.get("block2_patient", {}) or {})

    # Only trust status from block2 (printed Status line near Versicherten-Nr./Kostentraegerkennung)
    p_status = (block2.get("status") or "").strip()
    p_status_norm = _normalize_insurance_status(p_status)

    # If status is 6 digits, pad with trailing 0 (common OCR miss)
    if not p_status_norm:
        import re as _re
        m6 = _re.fullmatch(r"\d{6}", p_status)
        if m6:
            p_status_norm = m6.group(0) + "0"

    # Reject status if it matches or overlaps other IDs (handwritten notes often repeat them)
    vnr = _digits_only(block2.get("versichertennr") or "")
    ktk = _digits_only(block2.get("kostentraegerkennung") or "")
    if p_status_norm:
        if vnr and (p_status_norm.startswith(vnr) or vnr in p_status_norm):
            p_status_norm = ""
        if ktk and (p_status_norm.startswith(ktk) or ktk in p_status_norm):
            p_status_norm = ""

    # Never use block1 status (it often captures insurer line)
    block1["status"] = ""
    data["block1_insurance"] = block1

    block2["status"] = p_status_norm
    data["block2_patient"] = block2

    # Normalize kostentraegerkennung to 9 digits if present in block2
    ktk_raw = (block2.get("kostentraegerkennung") or "").strip()
    if ktk_raw:
        import re as _re
        m9 = _re.search(r"\d{9}", ktk_raw)
        if m9:
            block2["kostentraegerkennung"] = m9.group(0)
            data["block2_patient"] = block2

    return data

def normalize_block13_doctor_contact(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Ordering Party fields to reduce GPT variability.
    - fill missing phone/zip/city from info lines
    - merge short name with org line from info
    - move first info line to name when name is empty
    """
    try:
        logger.info("Ordering party BEFORE: %s", (data or {}).get("block13_doctor_contact", {}))
    except Exception:
        pass
    block = dict(data.get("block13_doctor_contact", {}) or {})

    name = (block.get("auftraggeberName") or "").strip()
    original_name = name
    info = (block.get("auftraggeberInfo") or "").strip()
    zip_code = (block.get("auftraggeberZip") or "").strip()
    city = (block.get("auftraggeberCity") or "").strip()
    phone = (block.get("auftraggeberTelefon") or "").strip()

    raw_info = info
    lines = _split_lines(info)

    has_doctor_name = False
    doctor_line, lines = _extract_doctor_line(lines)
    if doctor_line and _is_name_candidate(doctor_line):
        name = doctor_line
        has_doctor_name = True

    if not phone and raw_info:
        phone = _extract_phone_from_text(raw_info)

    if not name and lines:
        name = lines.pop(0)

    if name and _looks_like_address_line(name):
        lines.insert(0, name)
        name = name

    # If department was concatenated into name, move it to info
    name, dept = _split_name_department(name)
    if dept:
        lines.insert(0, dept)

    # If name is actually a specialty line, move it back to info
    if name and _is_specialty_info_line(name):
        lines.insert(0, name)
        name = name

    if name and lines:
        first = lines[0]
        short_name = len(name.split()) <= 1
        has_hint = any(h in first for h in _ORG_HINTS)
        if short_name and has_hint and name not in first:
            name = f"{name} {first}".strip()
            lines.pop(0)

    # If name was not a doctor/person, try to replace with a better line
    if name and _is_name_candidate(name) and not has_doctor_name:
        for line in lines:
            if not _is_phone_line(line) and not _looks_like_person_name(line) and not _is_specialty_info_line(line) and not _looks_like_address_line(line):
                name = line
                lines.remove(line)
                break

    # If name is still empty, try to take a doctor line from info
    if not name:
        for line in list(lines):
            if _is_name_candidate(line):
                name = line
                lines.remove(line)
                break

    if lines:
        for line in lines:
            m = _ZIP_CITY_RE.search(line)
            if m:
                zip_code = m.group(1)
                city = m.group(2).strip()
                break

    if (not zip_code or not city):
        clinic = data.get("block10_clinic", {}) or {}
        if not zip_code:
            zip_code = (clinic.get("clinic_zip") or "").strip()
        if not city:
            city = (clinic.get("clinic_city") or "").strip()

    # Keep only allowed info lines (specialty/address), drop phones and person names
    lines = [line for line in lines if _is_allowed_info_line(line) and not _is_phone_line(line) and not _looks_like_person_name(line)]

    # Keep name exactly as provided by GPT when available
    if original_name:
        name = original_name
    elif has_doctor_name and doctor_line and _is_name_candidate(doctor_line):
        name = doctor_line

    # If name still looks like an address, move it into info
    if name and _looks_like_address_line(name):
        lines.insert(0, name)
        name = name

    # Ensure ZIP/City line is present in info when available
    if zip_code and city:
        zip_city = f"{zip_code} {city}".strip()
        has_zip_city = any(zip_code in line or city in line for line in lines)
        if not has_zip_city:
            lines.append(zip_city)

    # Keep name exactly as provided by GPT when available
    if original_name:
        name = original_name
    elif has_doctor_name and doctor_line and _is_name_candidate(doctor_line):
        name = doctor_line

    block["auftraggeberName"] = name
    block["auftraggeberInfo"] = "\n".join(lines)
    block["auftraggeberZip"] = zip_code
    block["auftraggeberCity"] = city
    phone = _normalize_phone(phone)
    block["auftraggeberTelefon"] = phone

    data["block13_doctor_contact"] = block
    try:
        logger.info("Ordering party AFTER: %s", block)
    except Exception:
        pass
    return data
