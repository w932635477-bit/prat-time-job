from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict | None:
    """Extract JSON from LLM response text -- handles ```json blocks and raw JSON."""
    json_block = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    if json_block:
        try:
            return json.loads(json_block.group(1))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
