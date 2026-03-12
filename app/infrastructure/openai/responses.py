from __future__ import annotations

import json
from pathlib import Path

from openai import OpenAI


client = OpenAI()

SCHEMA_PATH = Path("app/schemas/mile_analysis.schema.json")
MILE_PROMPT_PATH = Path("app/prompts/mile_prompt.txt")


def run_mile_agent(user_question: str, data_payload: dict) -> dict:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    prompt = MILE_PROMPT_PATH.read_text(encoding="utf-8")

    response = client.responses.create(
        model="gpt-5.4",
        input=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": f"Вопрос: {user_question}\n\nДанные:\n{json.dumps(data_payload, ensure_ascii=False)}",
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": schema["name"],
                "schema": schema["schema"],
                "strict": True,
            }
        },
    )

    return json.loads(response.output_text)

