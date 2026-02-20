"""
required* fields "custom/open-api/fahrberichte/add"
date *         Datum der Fahrt
endTime *      Zielzeit der Fahrt
provider *     Name zur Identifikation des Quellsystems. ACHTUNG: soll der Webhook ausgelГ¶st werden muss der Webhook im Feld Name den gleichen Wert erhalten
startCity *    Abholort Stadt
startStreet *  Abholort StraГџe
startTime *    Abholzeit des Patienten
startZip *     Abholort PLZ
targetCity *   Zielort Stadt
targetStreet * Zielort StraГџe
targetZip *    Zielort PLZ
"""

import json
import os
from typing import Dict, Any
from datetime import datetime
import logging
from .config import setup_logging
from .api_client import (
    get_institution,
    create_driver_report,
    create_institution,
    get_verordnungsart_by_name,
)
from .utils import (
    get_json,
    get_direction,
    get_transport_type,
    parse_date,
    get_or_create_institution,
)

setup_logging()

logger = logging.getLogger(__name__)

# Const and required* fields
DATE = None  # Will use current date if not parsed from document
START_TIME = "07:30"  # *
END_TIME = "09:30"  # *

# Zielort: fill all fields if needed
TARGET_STREET = ""
TARGET_ZIP = ""
TARGET_CITY = ""

# Data for new institution: fill all fields if needed
mandant_new_inst = int(os.getenv("DISPOLIVE_MANDANT", "0") or "0")

cost_status = "10"
check = (
    "0"  # 0 = РЅРµ РїСЂРѕРІРµСЂРµРЅРѕ, 1 = РіРѕС‚РѕРІРѕ Рє СЃС‡РµС‚Сѓ, 2 = СЃС‡РµС‚ РІС‹СЃС‚Р°РІР»РµРЅ, 3 = Р°СЂС…РёРІРёСЂРѕРІР°РЅРѕ
)
infection = 0
manuelle_anfahrt = 5
dauergenehmigung = "0"  # 0 = Nein, 1 = Ja  # Р•СЃС‚СЊ Р»Рё Сѓ РїР°С†РёРµРЅС‚Р° РґРѕР»РіРѕСЃСЂРѕС‡РЅРѕРµ СЂР°Р·СЂРµС€РµРЅРёРµ РѕС‚ СЃС‚СЂР°С…РѕРІРѕР№ РЅР° СЂРµРіСѓР»СЏСЂРЅС‹Рµ РїРѕРµР·РґРєРё (РЅР°РїСЂРёРјРµСЂ, РЅР° 6 РјРµСЃСЏС†РµРІ)
transportschein_vorhanden = "Ja"


def build_payload(prescription: Dict[str, Any]) -> Dict[str, Any]:
    """
    Р—Р°РїРѕР»РЅСЏРµС‚ payload РґР°РЅРЅС‹РјРё РёР· СЂРµС†РµРїС‚Р°

    """
    manual_override = {
        "targetCity": TARGET_CITY,
        "targetStreet": TARGET_STREET,
        "targetZip": TARGET_ZIP,
    }

    # Priority in Ziel selection
    pat = prescription.get("block2_patient", {})
    def norm_address(city: str = "", street: str = "", zip_: str = "") -> Dict[str, str]:
        return{
            "targetCity": (city or "").strip(),
            "targetStreet": (street or "").strip(),
            "targetZip": (zip_ or "").strip(),
        }
    def adress_is_full(a: Dict[str, str]) -> bool:
        return bool(a.get("targetCity") and a.get("targetStreet") and a.get("targetZip"))
    
    manual_target = norm_address(TARGET_CITY, TARGET_STREET, TARGET_ZIP)
    confirm = prescription.get("block15_patient_confirmation")
    confirm_target = norm_address()

    if isinstance(confirm, list) and confirm:
        c0 = confirm[0] or {}
        confirm_target = norm_address(c0.get("city", ""), c0.get("street", ""), c0.get("zip", ""))
    elif isinstance(confirm, dict):
        confirm_target = norm_address(
            confirm.get("city", ""), confirm.get("street", ""), confirm.get("zip", "")
        )
    
    patient_target = norm_address(
        pat.get("patiant_city", ""),
        pat.get("patiant_street", ""),
        pat.get("patiant_zip", ""),
    )

    if adress_is_full(manual_target):
        target_address = manual_target
        logger.info("Ziel: using MANUAL override")
    elif adress_is_full(confirm_target):
        target_address = confirm_target
        logger.info("Ziel: using BestГ¤tigung (patient confirmation)")
    else:
        target_address = patient_target
        logger.info("Ziel: using Patient address")


    # Institution selection
    clinic = prescription.get("block10_clinic", {})

    clinic_name = (clinic.get("clinic_name") or "").strip()
    clinic_street = (clinic.get("clinic_street") or "").strip()
    clinic_zip = (clinic.get("clinic_zip") or "").strip()
    clinic_city = (clinic.get("clinic_city") or "").strip()

    can_create = bool(clinic_name and clinic_street and clinic_zip and clinic_city)
    if can_create:
        institution_name = clinic_name
        default_institution_params = {
            "mandant": mandant_new_inst,
            "name": clinic_name,
            "street": clinic_street,
            "zip": clinic_zip,
            "city": clinic_city,
            "tel": "",
        }
        create_if_missing = mandant_new_inst > 0
        if not create_if_missing:
            logger.warning("WARNING: DISPOLIVE_MANDANT not set - skip institution creation.")
    else:
        institution_name = "KH Urban 43"
        default_institution_params = {}
        create_if_missing = False

    # Date format conversion
    prescription_date = parse_date(prescription.get("Datum", ""))
    start_date = parse_date(prescription.get("vom/am", ""))
    end_date = parse_date(prescription.get("bis voraussichtlich", ""))
    birth_date = parse_date(prescription.get("geb. am", ""))

    # Parameters from prescription
    transport_type = get_transport_type(prescription.get("block11_transport_type", {}))
    verordnungsartId = get_verordnungsart_by_name(transport_type) if transport_type else ""
    # Trip direction
    direction = get_direction(prescription)

    # Get or create institution

    inst = get_or_create_institution(
        institution_name=institution_name,
        get_institution_func=get_institution,
        create_institution_func=create_institution,
        default_params=default_institution_params,
        create_if_missing=create_if_missing,
    )
    # Normalize doctor/contact block with safe fallbacks to clinic/institution
    doc = prescription.get("block13_doctor_contact", {}) or {}
    doc_name = (doc.get("auftraggeberName") or "").strip()
    doc_info = (doc.get("auftraggeberInfo") or "").strip()
    doc_city = (doc.get("auftraggeberCity") or "").strip()
    doc_zip = (doc.get("auftraggeberZip") or "").strip()
    doc_tel = (doc.get("auftraggeberTelefon") or "").strip()

    fallback_name = (clinic_name or inst.get("name", "") or "").strip()
    fallback_city = (clinic_city or inst.get("city", "") or "").strip()
    fallback_zip = (clinic_zip or inst.get("zip", "") or "").strip()
    fallback_info = (clinic_street or inst.get("street", "") or "").strip()
    # Set date
    confirm_block = prescription.get("block15_patient_confirmation")
    confirm_date_raw = ""
    if isinstance(confirm_block, list) and confirm_block:
        confirm_date_raw = (confirm_block[0] or {}).get("date", "")
    elif isinstance(confirm_block, dict):
        confirm_date_raw = confirm_block.get("date", "")
    datum = parse_date(confirm_date_raw)
    date = datum if datum else datetime.now().strftime("%Y-%m-%d")


    # Add data to payload
    payload = {
        "auftraggeberCity": doc_city or fallback_city,
        "auftraggeberInfo": doc_info or fallback_info,
        # "auftraggeberName": prescription["block13_doctor_contact"]["auftraggeberName"],
        # "auftraggeberName": prescription["block10_clinict"]["clinic_name"],
        "auftraggeberName": doc_name or fallback_name,
        # "auftraggeberSurname":  prescription["block13_doctor_contact"]["auftraggeberName"],
        # "auftraggeberSurnamee": prescription["block10_clinict"]["clinic_name"],
        "auftraggeberSurname": doc_name or fallback_name,
        "auftraggeberId": inst.get("_id", ""),
        "auftraggeberTelefon": doc_tel,
        "auftraggeberZip": doc_zip or fallback_zip,
        "carNo": "",
        "carPlan": "",
        "category": "",
        "check": check,
        "costStatus": cost_status,
        "date": date,  # Р”Р°С‚Р° РїРѕРµР·РґРєРё ?
        "dauergenehmigung": dauergenehmigung,  # СЂР°Р·СЂРµС€РµРЅРёРµ РЅР° СЂРµРіСѓР»СЏСЂРЅС‹Рµ РїРѕРµР·РґРєРё
        "direction": direction,  # РїРѕРµР·РґРєРё РІ РѕР±Рµ СЃС‚РѕСЂРѕРЅС‹
        "driveQuestions": True,
        "empfangenVonId": "",
        "endTime": END_TIME,  # РІСЂРµРјСЏ РѕРєРѕРЅС‡Р°РЅРёСЏ РїРѕРµР·РґРєРё
        "gefahreneFirma": "",  # ? "РєРѕРјРїР°РЅРёСЏ_РєРѕС‚РѕСЂР°СЏ_РІРµР·Р»Р°"
        "genehmigungsEnde": "",  # "РѕРєРѕРЅС‡Р°РЅРёРµ_СЂР°Р·СЂРµС€РµРЅРёСЏ"
        "genehmigungsNr": "",
        "infection": infection,
        "infectionType": "",
        "manuelleAnfahrt": manuelle_anfahrt,  # РњРёРЅСѓС‚С‹ РІСЂРµРјСЏ РїРѕРґСЉРµР·РґР° Р°РІС‚Рѕ
        "materialfahrt": False,
        "note": "",
        "patientBirthday": birth_date,
        "patientCity": prescription["block2_patient"]["patiant_city"],
        "patientInfo": "",
        "patientLand": prescription["block2_patient"]["patiant_city"],
        "patientMobile": "",
        "patientName": prescription["block2_patient"]["patiant_name"],
        "patientStreet": prescription["block2_patient"]["patiant_street"],
        "patientSurname": prescription["block2_patient"]["patiant_surname"],
        "patientTelephone": "",
        "patientZip": prescription["block2_patient"]["patiant_zip"],
        "possibleReturnNotice": "true",
        "provider": doc_name or fallback_name,
        "sonderleistungen": [],
        "startCity": "",
        "startInfo": "",
        "startInstitution": "",
        "startStreet": "",
        "startTime": START_TIME,
        "startTimeBis": "",
        "startZip": "",
        "targetCity": target_address["targetCity"],
        "targetInfo": "",
        "targetInstitution": "",
        "targetStreet": target_address["targetStreet"],
        "targetZip": target_address["targetZip"],
        "terminfahrt": True,
        "transportart": "",
        "transportscheinVorhanden": transportschein_vorhanden,
        "verordnungAusstellungsDatum": prescription_date,
        "verordnungsartId": verordnungsartId,
        "versicherungsnummer": prescription.get("Versichertennr.", ""),
    }

    payload.update({
        # Start (origin institution)
        "startInstitution": inst.get("name", ""),
        "startStreet": inst.get("street", ""),
        "startZip": inst.get("zip", ""),
        "startCity": inst.get("city", ""),

        # Auftraggeber / Provider (from stamp/doctor)
        "auftraggeberName": doc_name or fallback_name,
        "auftraggeberSurname": doc_name or fallback_name,
        "auftraggeberTelefon": doc_tel,
        "auftraggeberZip": doc_zip or fallback_zip,
        "auftraggeberCity": doc_city or fallback_city,
        "auftraggeberInfo": doc_info or fallback_info,
        "provider": doc_name or fallback_name,
    })
    
    return payload


if __name__ == "__main__":

    json_file = "../files/new_parser.json"

    if os.path.exists(json_file):
        prescription = get_json(json_file)
        logging.info(f"Р¤Р°Р№Р» {json_file} СѓСЃРїРµС€РЅРѕ Р·Р°РіСЂСѓР¶РµРЅ")
        payload = build_payload(prescription)
        logging.info(f"Payload: {payload}")
        create_driver_report(payload)
    else:
        logging.info(f"вќЊ Р¤Р°Р№Р» {json_file} РЅРµ РЅР°Р№РґРµРЅ")


