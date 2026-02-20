import json
import logging
from datetime import datetime
from typing import Callable, Dict, Any, Optional

logger = logging.getLogger(__name__)


def get_json(json_file_path: str) -> Dict[str, Any]:
    try:
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except UnicodeDecodeError:
            with open(json_file_path, "r", encoding="windows-1252") as f:
                return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON: {e}")
        return {}


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


def get_or_create_institution(
    institution_name: str,
    get_institution_func,
    create_institution_func,
    default_params: Dict[str, Any],
    create_if_missing: bool = False,
) -> Dict[str, Any]:
    """
    Получает существующее учреждение или создает новое.
    """

    institution_name = (institution_name or "").strip()
    if not institution_name:
        logger.warning("⚠️ institution_name пустой — возвращаем {}")
        return {}

    try:
        institution_data = get_institution_func(institution_name)
        if institution_data and isinstance(institution_data, list) and len(institution_data) > 0:
            logger.info(f"✅ Учреждение найдено: {institution_data[0].get('name')}")
            return institution_data[0]
    except Exception as e:
        logger.error(f"❌ Ошибка при поиске учреждения '{institution_name}': {e}")
        return {}

    logger.warning(f"⚠️ Учреждение '{institution_name}' не найдено.")

    if not create_if_missing:
        logger.info("🛡️ create_if_missing=False — не создаем, возвращаем {}")
        return {}

    try:
        logger.warning("➕ Создаем новое учреждение...")
        created_inst = create_institution_func(default_params)
        if not created_inst:
            logger.error(f"❌ Не удалось создать учреждение. default_params={default_params}")
            return {}

        if isinstance(created_inst, dict) and "data" in created_inst and isinstance(created_inst["data"], dict):
            inst = created_inst["data"]
            logger.info(f"✅ Учреждение создано: {inst.get('name')}")
            return inst

        if isinstance(created_inst, dict):
            logger.info(f"✅ Учреждение создано: {created_inst.get('name')}")
            return created_inst

        return {}
    except Exception as e:
        logger.error(f"❌ Ошибка при создании учреждения: {e}. default_params={default_params}")
        return {}

