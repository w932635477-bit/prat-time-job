from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict | None:
    """Extract JSON from LLM response text -- handles ```json blocks and raw JSON.

    Handles truncated output by attempting to auto-close brackets.
    """
    json_block = re.search(r"```json\s*\n(.*?)\n?```", text, re.DOTALL)
    raw = json_block.group(1) if json_block else text

    # First try: parse as-is
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Second try: auto-close truncated brackets
    repaired = _repair_json(raw)
    if repaired is not None:
        return repaired

    # Third try: find any valid JSON object in the text
    brace_start = raw.find("{")
    if brace_start >= 0:
        try:
            return json.loads(raw[brace_start:])
        except json.JSONDecodeError:
            pass

    return None


def _repair_json(raw: str) -> dict | None:
    """Try to repair truncated JSON by closing open brackets/braces."""
    # Count unclosed brackets
    open_stack: list[str] = []
    in_string = False
    escape_next = False

    for ch in raw:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            open_stack.append(ch)
        elif ch == "}" and open_stack and open_stack[-1] == "{":
            open_stack.pop()
        elif ch == "]" and open_stack and open_stack[-1] == "[":
            open_stack.pop()

    if not open_stack:
        return None  # Nothing to repair

    # Build closing sequence
    closing = []
    for opener in reversed(open_stack):
        closing.append("}" if opener == "{" else "]")

    # Find where to append closings — trim trailing incomplete content
    trimmed = raw.rstrip()
    # If last char is a comma or colon, remove it
    while trimmed and trimmed[-1] in ",:":
        trimmed = trimmed[:-1].rstrip()

    # If we're inside an unclosed string, close it first
    # Check if the number of unescaped quotes is odd
    quote_count = 0
    i = 0
    while i < len(trimmed):
        if trimmed[i] == "\\":
            i += 2
            continue
        if trimmed[i] == '"':
            quote_count += 1
        i += 1

    if quote_count % 2 == 1:
        trimmed += '"'

    candidate = trimmed + "".join(closing)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None
