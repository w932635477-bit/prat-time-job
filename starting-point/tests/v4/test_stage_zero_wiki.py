"""Tests for Stage 0 wiki knowledge base injection."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from starting_point.stages.stage_zero import StageZeroHandler


def _detect(messages: list[dict]) -> str:
    return StageZeroHandler._detect_industry(messages)


class TestIndustryDetection:
    def test_direct_industry_name(self):
        assert _detect([{"role": "user", "content": "我在建材行业干了15年"}]) == "建材"

    def test_hints_keyword_mapping(self):
        assert _detect([{"role": "user", "content": "我卖瓷砖和卫浴"}]) == "建材"

    def test_hints_keyword_catering(self):
        assert _detect([{"role": "user", "content": "我在后厨干了10年"}]) == "餐饮"

    def test_hints_keyword_housekeeping(self):
        assert _detect([{"role": "user", "content": "我做了5年月嫂"}]) == "家政"

    def test_no_match_returns_empty(self):
        assert _detect([{"role": "user", "content": "你好"}]) == ""

    def test_no_match_unknown_industry(self):
        assert _detect([{"role": "user", "content": "我做机械加工20年"}]) == ""

    def test_multi_message_picks_up_industry(self):
        msgs = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你做什么行业？"},
            {"role": "user", "content": "我卖涂料的"},
        ]
        assert _detect(msgs) == "建材"

    def test_direct_name_takes_priority_over_hints(self):
        # "餐饮" is a direct name, "饭店" maps to "餐饮"
        assert _detect([{"role": "user", "content": "我做餐饮"}]) == "餐饮"

    def test_content_creation_keyword(self):
        assert _detect([{"role": "user", "content": "我拍短视频"}]) == "内容变现实战案例"


class TestWikiContextInjection:
    @pytest.mark.asyncio
    async def test_wiki_injected_when_industry_detected(self, db):
        from starting_point.db.repos import MessageRepo, StateRepo

        msg_repo = MessageRepo(db)
        state_repo = StateRepo(db)
        llm = AsyncMock()

        captured_system = None

        async def capture_chat(messages, system, **kwargs):
            nonlocal captured_system
            captured_system = system
            return "你对瓷砖很了解吧？"

        llm.chat = capture_chat

        handler = StageZeroHandler(llm, msg_repo, state_repo)
        await handler.handle(user_id="u1", message="我卖瓷砖和卫浴的")

        assert captured_system is not None
        assert "行业知识库" in captured_system
        assert "建材" in captured_system
        assert "行业知识使用规则" in captured_system
        assert "同行案例" in captured_system

    @pytest.mark.asyncio
    async def test_no_wiki_when_no_industry(self, db):
        from starting_point.db.repos import MessageRepo, StateRepo

        msg_repo = MessageRepo(db)
        state_repo = StateRepo(db)
        llm = AsyncMock()

        captured_system = None

        async def capture_chat(messages, system, **kwargs):
            nonlocal captured_system
            captured_system = system
            return "你做什么行业的？"

        llm.chat = capture_chat

        handler = StageZeroHandler(llm, msg_repo, state_repo)
        await handler.handle(user_id="u2", message="你好")

        assert captured_system is not None
        assert "行业知识库" not in captured_system

    @pytest.mark.asyncio
    async def test_wiki_persists_across_turns(self, db):
        """After industry is detected, wiki stays injected in subsequent turns."""
        from starting_point.db.repos import MessageRepo, StateRepo

        msg_repo = MessageRepo(db)
        state_repo = StateRepo(db)
        llm = AsyncMock()

        systems = []

        async def capture_chat(messages, system, **kwargs):
            systems.append(system)
            return "继续聊聊"

        llm.chat = capture_chat

        handler = StageZeroHandler(llm, msg_repo, state_repo)
        # Turn 1: no industry
        await handler.handle(user_id="u3", message="你好")
        # Turn 2: mentions industry
        await handler.handle(user_id="u3", message="我做早餐店的")
        # Turn 3: continues conversation
        await handler.handle(user_id="u3", message="10年了")

        assert "行业知识库" not in systems[0]
        assert "行业知识库" in systems[1]
        assert "行业知识库" in systems[2]
