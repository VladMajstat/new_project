"""
required* fields "custom/open-api/fahrberichte/add"
date *         Datum der Fahrt
endTime *      Zielzeit der Fahrt
provider *     Name zur Identifikation des Quellsystems. ACHTUNG: soll der Webhook ausgelöst werden muss der Webhook im Feld Name den gleichen Wert erhalten
startCity *    Abholort Stadt
startStreet *  Abholort Straße
startTime *    Abholzeit des Patienten
startZip *     Abholort PLZ
targetCity *   Zielort Stadt
targetStreet * Zielort Straße
targetZip *    Zielort PLZ
"""

import json
import os
from typing import Dict, Any
from datetime import datetime
import logging
from config import setup_logging
from api_client import (
    get_institution,
    create_driver_report,
    get_kostentraeger_by_ik,
    get_verordnungsart_by_name,
)

setup_logging()

logger = logging.getLogger(__name__)

# const and required* fields
date = "2030-12-01"  # *
start_time = "07:30"  # *
end_time = "09:30"   # *

cost_status = 10
check = "0"  # 0 = не проверено, 1 = готово к счету, 2 = счет выставлен, 3 = архивировано
infection = 0  # ?
manuelle_anfahrt = 5
dauergenehmigung = "0"  # 0 = Nein, 1 = Ja  # Есть ли у пациента долгосрочное разрешение от страховой на регулярные поездки (например, на 6 месяцев)
transportschein_vorhanden = "Ja"


def get_json(json_file_path: str) -> Dict[str, Any]:
    try:
        # Пробуем сначала UTF-8, потом Windows-1252
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except UnicodeDecodeError:
            with open(json_file_path, "r", encoding="windows-1252") as f:
                return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON: {e}")
        return {}


def parse_patient_data(full_name_address: str) -> Dict[str, Any]:
    # Адрес и полное имя
    lines = full_name_address.split("\n")

    # Первая строка - имя и фамилия
    name_parts = lines[0].strip().split()
    patient_surname = name_parts[0] if len(name_parts) > 0 else ""
    patient_name = name_parts[1] if len(name_parts) > 1 else ""

    # Вторая строка - улица и номер дома
    patient_street = lines[1].strip() if len(lines) > 1 else ""

    # Третья строка - почтовый код, город и страна
    city_line = lines[2].strip() if len(lines) > 2 else ""
    city_parts = city_line.split()

    # Формат: "D 13507 Berlin" или "13507 Berlin"
    patient_country = ""
    patient_zip = ""
    patient_city = ""

    if len(city_parts) >= 3:
        patient_country = city_parts[0]  # D
        patient_zip = city_parts[1]  # 13507
        patient_city = city_parts[2]  # Berlin
    elif len(city_parts) >= 2:
        patient_zip = city_parts[0]
        patient_city = city_parts[1]
    return {
        "name": patient_name,
        "surname": patient_surname,
        "street": patient_street,
        "zip": patient_zip,
        "city": patient_city,
        "country": "DE" if patient_country == "D" else patient_country,
    }


def parse_facility_address(facility_str: str) -> Dict[str, str]:
    """
    Парсит адрес учреждения лечения из строки вида:
    'CVK Hama/Onko Augustenburger Platz 1, 13353 BERLIN'
    """
    # Разделяем по запятой
    if "," in facility_str:
        facility_name_part, city_zip_part = facility_str.rsplit(",", 1)
    else:
        facility_name_part = facility_str
        city_zip_part = ""
    # Парсим название и адрес учреждения
    facility_parts = facility_name_part.strip().split()

    facility_name = facility_parts[0] if len(facility_parts) > 0 else ""  # CVK
    facility_info = (
        " ".join(facility_parts[1:]) if len(facility_parts) > 1 else ""
    )  # Hama/Onko Augustenburger Platz 1

    # Ищем улицу в info (всё кроме последнего слова, если оно выглядит как название)
    facility_parts_info = facility_info.split()
    facility_street = ""

    # Пытаемся найти номер дома (обычно цифры в конце)
    for i, part in enumerate(facility_parts_info):
        if any(c.isdigit() for c in part):
            facility_street = " ".join(facility_parts_info[i:])
            break

    if not facility_street and facility_parts_info:
        facility_street = " ".join(facility_parts_info)
    # Парсим город и почтовый код
    city_zip_parts = city_zip_part.strip().split()

    facility_zip = ""
    facility_city = ""

    if len(city_zip_parts) >= 2:
        facility_zip = city_zip_parts[0]
        facility_city = city_zip_parts[1]
    elif len(city_zip_parts) == 1:
        facility_city = city_zip_parts[0]
    return {
        "name": facility_name_part,
        "zip": facility_zip,
        "info": facility_info,
        "street": facility_street,
        "city": facility_city,
    }


def parse_doctor_stamp(stamp_str: str) -> Dict[str, str]:
    """
    Парсит штамп врача из строки вида:
    'Charite Universitatsmedizin Berlin Ц Stempel присутствует'

    Извлекает город врача (auftraggeber)
    """
    if not stamp_str:
        return {"street": ""}

    # Удаляем лишние части со специальными символами и словами
    # Убираем текст после "Ц" или "-"
    clean_str = stamp_str.strip()
    # Разбиваем на слова
    street = clean_str.split(',')[1]
    

    # Ищем город - обычно это последнее слово перед разделителем
    # Типичные немецкие города: Berlin, München, Hamburg, etc.
    # Они обычно начинаются с заглавной буквы
    # city = ""

    # # Берём последнее слово как город
    # if words:
    #     city = words[-1] if words[-1][0].isupper() else ""

    return {"street": street}


def parse_date(date_str: str, format_in: str = "%d.%m.%y") -> str:
    """
    Преобразует дату из формата DD.MM.YY в YYYY-MM-DD
    """
    if not date_str or date_str.strip() == "":
        return ""

    try:
        dt = datetime.strptime(date_str.strip(), format_in)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        logging.info(f"Warning: Could not parse date '{date_str}'")
        return ""


def get_transport_type(prescription: Dict[str, Any]) -> str:
    """Определяет тип транспорта из данных рецепта"""
    if prescription.get("KTW, da medizinisch-fachliche Betreuung"):
        return "KTW"
    elif prescription.get("Taxi/Mietwagen"):
        return "Taxi"
    elif prescription.get("RTW"):
        return "RTW"
    elif prescription.get("NAW/NEF"):
        return "NAW/NEF"
    else:
        return ""


def get_direction(prescription: Dict[str, Any]) -> str:
    """Определяет направление поездки"""
    outbound = prescription.get("Hinfahrt", False)
    return_trip = prescription.get("Ruckfahrt", False)

    if outbound and return_trip:
        # Создаются две поездки
        return "Hinfahrt"
    elif outbound:
        return "Hinfahrt"
    elif return_trip:
        return "Rückfahrt"
    else:
        return "Hinfahrt"


def build_payload(prescription: Dict[str, Any]) -> Dict[str, Any]:
    """
    Заполняет payload данными из рецепта

    """
    # Адрес и полное имя
    patient_data = parse_patient_data(
        prescription.get("Name, Vorname des Versicherten", "")
    )

    # название_лечебного_учреждения_местоположение
    facility_data = parse_facility_address(
        prescription.get("Behandlungsstatte (Name, Ort)", "")
    )

    # Парсим штамп врача для получения города
    doctor_data = parse_doctor_stamp(
        prescription.get("Vertragsarztstempel / Unterschrift des Arztes", "")
    )

    # перевод формата даты
    prescription_date = parse_date(prescription.get("Datum", ""))
    start_date = parse_date(prescription.get("vom/am", ""))
    end_date = parse_date(prescription.get("bis voraussichtlich", ""))
    birth_date = parse_date(prescription.get("geb. am", ""))

    # Параметры из рецепта
    transport_type = get_transport_type(prescription)
    verordnungsartId = get_verordnungsart_by_name(transport_type) or ""
    # направление поездки
    direction = get_direction(prescription)

    # Получаем ID учреждения и полные данные через API
    facility_name = prescription.get("Behandlungsstatte (Name, Ort)", "")
    institution_data = get_institution(facility_name)

    # Если get_institution возвращает только ID, используем его
    # Если возвращает полный объект с адресом, извлекаем данные
    if isinstance(institution_data, dict):
        auftraggeber_id = institution_data.get("_id", "")
        # Переопределяем facility_data данными из API, если они есть
        if institution_data.get("city") or institution_data.get("zip"):
            facility_data["city"] = institution_data.get("city", facility_data.get("city", ""))
            facility_data["zip"] = institution_data.get("zip", facility_data.get("zip", ""))
            facility_data["street"] = institution_data.get("street", facility_data.get("street", ""))
    else:
        auftraggeber_id = institution_data if institution_data else ""

    # Проверяем id rjvgfybb
    logging.info("Поиск страховой компании ===")
    kostentraeger = get_kostentraeger_by_ik("10958001")
    if kostentraeger:
        logging.info(f"✓ Найдена страховая: {kostentraeger.get('name')}")
        logging.info(f"✓ ID страховой: {kostentraeger.get('_id')}")
        kostentraeger = kostentraeger["_id"]
    else:
        kostentraeger = prescription.get("Kostentragerkennung", "")

    provider = prescription.get("Krankenkasse bzw. Kostentrager")

 
    payload = {
        "auftraggeberCity": prescription.get("auftraggeberCity", ""),
        "auftraggeberInfo": doctor_data.get("street", ""),
        "auftraggeberName": facility_data.get("name", ""),
        "auftraggeberSurname": facility_data.get("name", ""),
        "auftraggeberId": auftraggeber_id,
        "auftraggeberTelefon": prescription.get("auftraggeberTelefon",""),
        "auftraggeberZip": prescription.get("auftraggeberZip", ""),
        "carNo": "",
        "carPlan": "",
        "category": "",
        "check": check,
        "costStatus": cost_status,
        "date": date,  # Дата поездки ?
        "dauergenehmigung": dauergenehmigung,  # разрешение на регулярные поездки
        "direction": direction,  # поездки в обе стороны
        "driveQuestions": True,
        "empfangenVonId": "",
        "endTime": end_time,  # время окончания поездки
        "gefahreneFirma": "",  # ? "компания_которая_везла"
        "genehmigungsEnde": "",  # "окончание_разрешения"
        "genehmigungsNr": "",
        "infection": infection,
        "infectionType": "",
        "manuelleAnfahrt": manuelle_anfahrt,  # Минуты время подъезда авто
        "materialfahrt": False,
        "note": "",
        "patientBirthday": birth_date,
        "patientCity": patient_data.get("city", ""),
        "patientInfo": "",
        "patientLand": patient_data.get("city", ""),
        "patientMobile": "",
        "patientName": patient_data.get("name", ""),
        "patientStreet": patient_data.get("street", ""),
        "patientSurname": patient_data.get("surname", ""),
        "patientTelephone": "",
        "patientZip": patient_data.get("zip", ""),
        "possibleReturnNotice": "true",
        "provider": provider,
        "sonderleistungen": [],
        "startCity": patient_data.get("city", ""),  # город клиента?
        "startInfo": "",  # ?
        "startInstitution": "",  # ?
        "startStreet": patient_data.get(
            "street",
            "",
        ),
        "startTime": start_time,  # ?
        "startTimeBis": "",
        "startZip": patient_data.get("zip", ""),
        "targetCity": facility_data.get("city", ""),
        "targetInfo": "",
        "targetInstitution": "",
        "targetStreet": facility_data.get("street", ""),
        "targetZip": facility_data.get("zip", ""),
        "terminfahrt": True,
        "transportart": "",
        "transportscheinVorhanden": transportschein_vorhanden,
        "verordnungAusstellungsDatum": prescription_date,
        "verordnungsartId": verordnungsartId,
        "versicherungsnummer": prescription.get("Versichertennr.", ""),
        "arztNummer": prescription.get("Arzt-Nr.", ""),
        "betriebsstaettenNummer": prescription.get("Betriebsstatten-Nr.", ""),
        "kkId": kostentraeger,  # id страховой
    }

    return payload


if __name__ == "__main__":

    json_file = "../files/7.json"

    if os.path.exists(json_file):
        prescription = get_json(json_file)
        logging.info(f"Файл {json_file} успешно загружен")
        payload = build_payload(prescription)
        create_driver_report(payload)
    else:
        logging.info(f"❌ Файл {json_file} не найден")
