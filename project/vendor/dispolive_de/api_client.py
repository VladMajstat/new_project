import requests
import json
from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv
import logging
from .config import setup_logging

load_dotenv()

setup_logging()

logger = logging.getLogger(__name__)

# Конфигурация
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
BASE_URL = "https://abc-drive.dispolive.de/"

# Заголовки для всех запросов
HEADERS = {"Authorization": f"Bearer {BEARER_TOKEN}", "Accept": "application/json"}


def create_driver_report(payload) -> None:
    endpoint = "custom/open-api/fahrberichte/add"
    endpoint_url = BASE_URL + endpoint
    try:
        response = requests.post(
            endpoint_url, json=payload, headers=HEADERS, timeout=10
        )
        response_code = response.status_code
        response_text = response.json()

        if response_code == 200:
            logging.info(f"Successfully created ride: {response_text}")
            return response_text
        else:
            error_message = (
                f"API Error: Status Code {response_code}. Response: {response_text}"
            )
            logging.error(error_message)
            return None

    except requests.exceptions.RequestException as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logging.error(error_message)
        return None


def get_institution(name: str) -> str:
    """Получает все данные учреждения по названию"""

    endpoint = f"custom/open-api/institutionen/findByName/{name}"
    endpoint_url = BASE_URL + endpoint
    logging.info(f"endpoint_url: {endpoint_url}")

    try:
        response = requests.get(endpoint_url, headers=HEADERS, timeout=10)
        response_code = response.status_code
        response_text = response.json()

        if response_code == 200:
            logging.info(f"Successfully fetched Institution data: {response_text}")
            institution_data = response_text
            return institution_data
        else:
            error_message = (
                f"API Error: Status Code {response_code}. Response: {response_text}"
            )
            logging.error(error_message)

    except requests.exceptions.RequestException as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logging.info(error_message)
        return None


def create_institution(params: dict) -> dict:
    """Создает новое учреждение через API

    Args:
        params: Словарь с обязательными полями:
            - mandant (int): Mandant ID
            - name (str): Название учреждения
            - street (str): Улица
            - zip (str): Почтовый индекс
            - city (str): Город
            Опциональные поля:
            - tel (str): Телефон
            - mobile (str): Мобильный телефон

    Returns:
        dict: Созданное учреждение с _id или None при ошибке
    """

    endpoint = "custom/open-api/institutionen/add"
    endpoint_url = BASE_URL + endpoint

    # Используем переданные параметры как payload
    payload = params

    try:
        response = requests.post(
            endpoint_url, json=payload, headers=HEADERS, timeout=10
        )
        response_code = response.status_code
        response_text = response.json()

        if response_code == 200 or response_code == 201:
            logging.info(f"Successfully created Institution: {response_text}")
            return response_text  # Возвращаем весь объект
        else:
            error_message = (
                f"API Error: Status Code {response_code}. Response: {response_text}"
            )
            logging.error(error_message)
            return None

    except requests.exceptions.RequestException as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logging.error(error_message)
        return None


def get_verordnungs_daten() -> List[Dict[str, Any]]:
    """Получает данные о видах назначений (Verordnungsarten)"""

    endpoint = "custom/open-api/verordnungsarten/findByname"
    endpoint_url = BASE_URL + endpoint

    try:
        response = requests.get(endpoint_url, headers=HEADERS, timeout=10)
        response_code = response.status_code
        response_text = response.json()

        if response_code == 200:
            logging.info(f"Successfully fetched Verordnungsdaten: {response_text}")
            return response_text if isinstance(response_text, list) else [response_text]
        else:
            error_message = (
                f"API Error: Status Code {response_code}. Response: {response_text}"
            )
            logging.error(error_message)
            return []

    except requests.exceptions.RequestException as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logging.error(error_message)
        return []


def get_verordnungsart_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Найти тип назначения по имени

    Args:
        name (str): Название типа (например, "KTW", "BTW")

    Returns:
        Dict: {"_id": "...", "name": "..."} или None
    """
    endpoint = f"custom/open-api/verordnungsarten/findByName/{name}"
    endpoint_url = BASE_URL + endpoint

    try:
        response = requests.get(endpoint_url, headers=HEADERS, timeout=10)

        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict) and "_id" in data and "name" in data:
            logging.info(f'✅ Найден тип: {data["name"]} (ID: {data["_id"]})')
            return data
        else:
            logging.error(f'⚠️ Тип "{name}" не найден')
            return None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logging.info(f'❌ Тип "{name}" не существует')
        else:
            logging.error(f"❌ HTTP ошибка {e.response.status_code}: {e.response.text}")
        return None

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Ошибка запроса: {str(e)}")
        return None


def get_kostentraeger_by_ik(ik_nummer: str) -> Optional[Dict[str, Any]]:
    """Получает данные о страховой компании (Kostenträger) по IK-номеру

    Args:
        ik_nummer: IK-номер страховой компании (например, "10958001")

    Returns:
        Словарь с данными страховой или None если не найдена
        Данные включают: _id, name, IK-номер, контракты и тарифы
    Пример результата:
    {
        "_id": "108433248",
        "name": "SBK HV West",
        "city": "München",
        "ikKtNr": "108433248",
        "street": "Heimeranstraße 31",
        "zip": "80339",
        "vertrag": ["301510b6-d9d9-47f2-95d1-32f40313d7a9", ...]
    }
    """

    endpoint = f"custom/open-api/kostentraeger/findByIk/{ik_nummer}"
    endpoint_url = BASE_URL + endpoint
    logging.info(f"Searching for Kostentraeger with IK: {ik_nummer}")
    logging.info(f"endpoint_url: {endpoint_url}")

    try:
        response = requests.get(endpoint_url, headers=HEADERS, timeout=10)
        response_code = response.status_code
        response_text = response.json()

        logging.info(f"response_text: {response_text}")

        if response_code == 200:
            logging.info(f"Successfully fetched Kostentraeger data: {response_text}")
            # API может вернуть список или один объект
            if isinstance(response_text, list):
                kostentraeger = response_text[0] if response_text else None
            else:
                kostentraeger = response_text

            if kostentraeger:
                logging.info(f"Kostentraeger ID: {kostentraeger.get('_id')}")
                logging.info(f"Kostentraeger Name: {kostentraeger.get('name')}")

            return kostentraeger
        else:
            error_message = (
                f"API Error: Status Code {response_code}. Response: {response_text}"
            )
            logging.error(error_message)
            return None

    except requests.exceptions.RequestException as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logging.error(error_message)
        return None
