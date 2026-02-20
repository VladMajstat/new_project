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
        "Do not invent. Unknown => \"\" for strings, false for booleans."
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
