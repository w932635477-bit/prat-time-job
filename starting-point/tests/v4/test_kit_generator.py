from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_generate_kit_creates_entry(db):
    from starting_point.stages.kit_generator import KitGenerator
    from starting_point.db.repos import KitRepo

    kit_repo = KitRepo(db)
    llm = AsyncMock()

    kit_json = {
        "content_direction": "价格对比类视频内容",
        "platform_recommendations": [
            {"platform": "xianyu", "priority": 1, "reason": "直接触达买家", "content_format": "服务帖"},
            {"platform": "douyin", "priority": 2, "reason": "短视频展示专业度", "content_format": "短视频"},
        ],
        "startup_materials": {
            "xianyu": {
                "account_name_suggestions": ["建材老兵"],
                "bio_short": "10年建材经验",
                "bio_full": "帮你省30%",
                "first_post": {"title": "帮你审材料清单", "body": "...", "price": 99},
                "reply_templates": [],
            }
        },
    }
    llm.chat.return_value = f"```json\n{json.dumps(kit_json)}\n```"

    generator = KitGenerator(llm, kit_repo)
    result = await generator.generate(
        user_id="u1",
        knowledge_points=[{"id": "kp_1"}],
        product_package={"product_name": "test"},
    )
    assert result["generation_status"] == "completed"
