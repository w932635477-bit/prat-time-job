from __future__ import annotations

import json
import logging
import re

from starting_point.llm.client import LLMClient
from starting_point.db.repos import KitRepo
from starting_point.prompts.kit import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict | None:
    """Extract JSON from LLM response text."""
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


class KitGenerator:
    """Generates a full startup kit from knowledge points and product package."""

    def __init__(self, llm: LLMClient, kit_repo: KitRepo) -> None:
        self._llm = llm
        self._kit_repo = kit_repo

    async def generate(
        self,
        user_id: str,
        knowledge_points: list[dict],
        product_package: dict,
    ) -> dict:
        kit_id = await self._kit_repo.create(
            user_id=user_id,
            knowledge_points=knowledge_points,
        )

        try:
            context = (
                f"知识点:\n{json.dumps(knowledge_points, ensure_ascii=False, indent=2)}\n\n"
                f"产品方案:\n{json.dumps(product_package, ensure_ascii=False, indent=2)}"
            )
            response_text = await self._llm.chat(
                messages=[{"role": "user", "content": context}],
                system=SYSTEM_PROMPT,
                temperature=0.8,
                max_tokens=8192,
            )

            parsed = _extract_json(response_text)
            if parsed is None:
                raise ValueError("Kit generation returned non-JSON response")

            await self._kit_repo.update_kit(
                kit_id=kit_id,
                product_package=product_package,
                content_direction=parsed.get("content_direction", ""),
                platform_recommendations=parsed.get("platform_recommendations", []),
                startup_materials=parsed.get("startup_materials", {}),
            )
            await self._kit_repo.update_status(kit_id=kit_id, status="completed")

        except Exception as e:
            logger.error("Kit generation failed for user %s: %s", user_id, e)
            await self._kit_repo.update_status(kit_id=kit_id, status="failed")
            raise

        return await self._kit_repo.load_by_user(user_id)
