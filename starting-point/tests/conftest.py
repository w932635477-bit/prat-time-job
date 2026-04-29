import os

import pytest

os.environ.setdefault("SP_JWT_SECRET", "test-secret-that-is-at-least-32-bytes-long-for-hs256")


@pytest.fixture
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()
