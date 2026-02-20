# Dispolive (new_project)

Це Django‑проєкт для обробки медичних направлень на транспорт (нім. "Verordnung einer Krankenbeförderung"). Проєкт приймає PDF або фото, конвертує у зображення, витягує структурований JSON через OpenAI, дає можливість перевірити дані, формує payload для Dispolive та надсилає його через API.

## Ключові можливості

- Завантаження PDF та фото (мобільна камера підтримується).
- Розбір форми через OpenAI у структурований JSON.
- Ручний review перед відправкою в Dispolive.
- Логування запитів до Dispolive.
- Feature flags для модулів (accounts, people, blog, sitemaps, admin_panel, documents).

## Структура проєкту

- `project/` – Django проєкт (settings, urls, wsgi/asgi, vendor).
- `project/apps/` – основні Django apps:
  - `documents` – завантаження PDF/фото, OpenAI парсинг, review, Dispolive API.
  - `accounts` – allauth логін/реєстрація.
  - `people` – HR/кандидати (опційно).
  - `blogs` – блог (опційно).
  - `sitemaps` – sitemap (опційно).
  - `admin_panel` – адмін панель (опційно).
  - `core` – breadcrumbs + контекст фіч.
- `templates/` – HTML шаблони.
- `static/` – статичні файли.
- `requirements.txt` – залежності.

## Основний потік Documents

1) Upload PDF/Photo → `DocumentUpload`.
2) Конвертація у base64 (PDF через PyMuPDF, фото через PIL).
3) OpenAI парсить форму у JSON за схемою `new_parser.json`.
4) Review користувачем.
5) Формування payload + відправка в Dispolive API.

Ключові URL:
- `/documents/upload/` – PDF upload.
- `/documents/photo/` – фото upload.
- `/documents/review/<id>/` – перевірка/редагування.
- `/documents/logs/dispolive/` – лог Dispolive.

## Змінні середовища

У `project/project/settings/local_conf.py` читаються змінні:

```
DEBUG=1
SECRET_KEY=your-secret
DB_NAME=...
DB_USER=...
DB_PASSOWRD=...
DB_HOST=...
DB_PORT=...
OPENAI_API_KEY=...
BEARER_TOKEN=...        # токен Dispolive API
```

Примітка: `DB_PASSOWRD` саме так у коді.

## Швидкий локальний запуск

1) Створити venv і встановити залежності:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2) Міграції бази:

```bash
python project/manage.py migrate
```

3) Запуск сервера:

```bash
python project/manage.py runserver
```

За замовчуванням стартова сторінка — `/`.

## Docker запуск (dev)

У репозиторії є `docker-compose.dev.yml` для підняття PostgreSQL.

```bash
docker compose -f docker-compose.dev.yml up -d
```

Далі в `.env` або змінних середовища вкажи параметри БД з compose‑файлу:

```
DB_HOST=localhost
DB_PORT=5437
DB_NAME=crawler_db
DB_USER=userdb
DB_PASSOWRD=123456
```

Після цього виконай міграції і запускай сервер стандартно.

## Важливі залежності

- `openai` – парсинг форми.
- `PyMuPDF` (`fitz`) – рендер PDF у PNG.
- `Pillow` – робота з фото.
- `django-allauth` – логін/реєстрація.

## Примітки

- `ALLOWED_HOSTS = ['*']` та `CSRF_TRUSTED_ORIGINS = []` — для продакшену потрібно налаштувати.
- Логи Dispolive зберігаються у `project/logs/dispolive.log`.
- У репозиторії є багато backup‑папок (`documents.backup_*`) — для чистоти проєкту краще їх винести.
