# Auth, Payment & User Data Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add WeChat OAuth login, 3-tier WeChat Pay, and user data management to the Starting Point V2 app.

**Architecture:** JWT-based auth with WeChat OAuth. SQLite multi-table (users, orders, user_profiles) alongside existing user_states JSON. Alembic migrations. Paywall gate in SkillRunner checks user.tier before advancing past Phase 1. Frontend adds login.html, account.html, auth.js module, pricing card components.

**Tech Stack:** FastAPI, PyJWT, httpx (already installed), aiosqlite, Alembic, vanilla JS ES modules

**Dependencies to add:** `PyJWT>=2.8.0`, `alembic>=1.13.0`

**Project root:** `/Users/weilei/part-time job/autoresearch-mlx/starting-point/`
**Backend source:** `src/starting_point/`
**Frontend static:** `static/`
**Tests:** `tests/`
**Venv activate:** `source .venv/bin/activate`
**Run tests:** `PYTHONPATH=src pytest tests/ -v`
**Run server:** `PYTHONPATH=src python3 -m starting_point.main`

---

### Task 1: Add dependencies and config fields

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/starting_point/config.py`

**Step 1: Add PyJWT and Alembic to pyproject.toml**

In `dependencies` array, add `"PyJWT>=2.8.0"` and `"alembic>=1.13.0"`.

**Step 2: Add auth/payment config fields to config.py**

Add to the `Settings` class:

```python
jwt_secret: str = "dev-secret-change-in-prod"
jwt_expiry_hours: int = 168  # 7 days
wx_app_id: str = ""
wx_app_secret: str = ""
wx_pay_mch_id: str = ""
wx_pay_api_key: str = ""
wx_pay_cert_path: str = ""
wx_pay_notify_url: str = ""
```

**Step 3: Install new dependencies**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && source .venv/bin/activate && uv pip install PyJWT alembic`
Expected: Successfully installed

**Step 4: Verify config loads**

Run: `cd "/Users/weilei/part-time job/autoresearch-mlx/starting-point" && source .venv/bin/activate && PYTHONPATH=src python3 -c "from starting_point.config import settings; print(settings.jwt_secret)"`
Expected: `dev-secret-change-in-prod`

**Step 5: Commit**

```bash
git add pyproject.toml src/starting_point/config.py
git commit -m "feat: add JWT, Alembic deps and auth/payment config fields"
```

---

### Task 2: Add Pydantic models for auth and payment

**Files:**
- Modify: `src/starting_point/models.py`

**Step 1: Write tests for new models**

Create `tests/test_models_auth.py`:

```python
from datetime import datetime, timedelta
from starting_point.models import User, Order, UserProfile, PricingTier, TIER_DEFINITIONS


def test_user_defaults():
    u = User(id="u1", wx_openid="wx123")
    assert u.tier == "free"
    assert u.tier_expires_at is None
    assert u.nickname == ""


def test_order_defaults():
    o = Order(id="o1", user_id="u1", tier="standard", amount=5900)
    assert o.status == "pending"
    assert o.paid_at is None


def test_tier_definitions():
    assert TIER_DEFINITIONS["free"]["price_fen"] == 0
    assert TIER_DEFINITIONS["standard"]["price_fen"] == 5900
    assert TIER_DEFINITIONS["low_ticket"]["duration_days"] == 60
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_models_auth.py -v`
Expected: FAIL — ImportError

**Step 3: Add models to models.py**

Append to `src/starting_point/models.py`:

```python
class User(BaseModel):
    id: str
    wx_openid: str
    wx_unionid: str = ""
    nickname: str = ""
    avatar_url: str = ""
    phone: str = ""
    tier: str = "free"
    tier_expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Order(BaseModel):
    id: str
    user_id: str
    tier: str
    amount: int  # price in fen (cents)
    wx_prepay_id: str = ""
    wx_transaction_id: str = ""
    status: str = "pending"
    paid_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class UserProfile(BaseModel):
    user_id: str
    industry: str = ""
    years_experience: int = 0
    goals: str = ""
    updated_at: datetime = Field(default_factory=datetime.now)


TIER_DEFINITIONS: dict[str, dict] = {
    "free": {
        "label": "免费体验",
        "price_fen": 0,
        "description": "Phase 0 + Phase 1 + Phase 2 预览",
        "duration_days": None,
    },
    "low_ticket": {
        "label": "产品包装",
        "price_fen": 1990,
        "description": "完整 Phase 2（产品包装 + 定价）",
        "duration_days": 60,
    },
    "standard": {
        "label": "完整方案",
        "price_fen": 5900,
        "description": "Phase 2-5 全部（包装 + 获客 + 首单 + 增长）",
        "duration_days": 60,
    },
    "human": {
        "label": "人工辅导",
        "price_fen": 19900,
        "description": "完整方案 + 一次人工审核 + 微信群答疑30天",
        "duration_days": 90,
    },
}


class PaywallResponse(BaseModel):
    paywall: bool = True
    preview_data: dict = Field(default_factory=dict)
    tiers: list[dict] = Field(default_factory=list)
```

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_models_auth.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add tests/test_models_auth.py src/starting_point/models.py
git commit -m "feat: add User, Order, UserProfile, PaywallResponse models"
```

---

### Task 3: JWT encode/decode module

**Files:**
- Create: `src/starting_point/auth/__init__.py`
- Create: `src/starting_point/auth/jwt.py`
- Create: `tests/test_auth_jwt.py`

**Step 1: Write tests**

Create `tests/test_auth_jwt.py`:

```python
from starting_point.auth.jwt import create_token, decode_token


def test_create_and_decode():
    token = create_token(user_id="u1")
    payload = decode_token(token)
    assert payload["sub"] == "u1"
    assert "exp" in payload


def test_decode_invalid_returns_none():
    result = decode_token("invalid.token.here")
    assert result is None
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_auth_jwt.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Create auth package and jwt.py**

Create empty `src/starting_point/auth/__init__.py`.

Create `src/starting_point/auth/jwt.py`:

```python
from __future__ import annotations

import jwt
from datetime import datetime, timedelta, timezone

from starting_point.config import settings


def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None
```

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_auth_jwt.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add src/starting_point/auth/ tests/test_auth_jwt.py
git commit -m "feat: add JWT encode/decode module"
```

---

### Task 4: Database migration — users, orders, user_profiles tables

**Files:**
- Create: `src/starting_point/db/__init__.py`
- Create: `src/starting_point/db/migrations.py`
- Modify: `src/starting_point/engine/state.py`
- Create: `tests/test_db_migrations.py`

**Step 1: Write tests**

Create `tests/test_db_migrations.py`:

```python
import pytest
import aiosqlite
from pathlib import Path

from starting_point.db.migrations import run_migrations


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "test.db"
    async with aiosqlite.connect(db_path) as conn:
        await run_migrations(conn)
        yield conn


@pytest.mark.asyncio
async def test_users_table_exists(db):
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_orders_table_exists(db):
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_user_profiles_table_exists(db):
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles'")
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_user_states_table_exists(db):
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_states'")
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_insert_user(db):
    await db.execute(
        "INSERT INTO users (id, wx_openid, tier) VALUES (?, ?, ?)",
        ("u1", "wx123", "free"),
    )
    await db.commit()
    cursor = await db.execute("SELECT wx_openid, tier FROM users WHERE id = ?", ("u1",))
    row = await cursor.fetchone()
    assert row == ("wx123", "free")
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_db_migrations.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Create db package and migrations.py**

Create empty `src/starting_point/db/__init__.py`.

Create `src/starting_point/db/migrations.py`:

```python
from __future__ import annotations

import aiosqlite


async def run_migrations(db: aiosqlite.Connection) -> None:
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS user_states (
            user_id TEXT PRIMARY KEY,
            data TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            wx_openid TEXT UNIQUE NOT NULL,
            wx_unionid TEXT NOT NULL DEFAULT '',
            nickname TEXT NOT NULL DEFAULT '',
            avatar_url TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            tier TEXT NOT NULL DEFAULT 'free',
            tier_expires_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            tier TEXT NOT NULL,
            amount INTEGER NOT NULL,
            wx_prepay_id TEXT NOT NULL DEFAULT '',
            wx_transaction_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            paid_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY REFERENCES users(id),
            industry TEXT NOT NULL DEFAULT '',
            years_experience INTEGER NOT NULL DEFAULT 0,
            goals TEXT NOT NULL DEFAULT '',
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_users_wx_openid ON users(wx_openid);
        CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
    """)
    await db.commit()
```

**Step 4: Update StateManager.initialize to use migrations**

In `src/starting_point/engine/state.py`, replace the `initialize` method body:

```python
from starting_point.db.migrations import run_migrations

# In initialize():
async with aiosqlite.connect(self._db_path) as db:
    await run_migrations(db)
```

**Step 5: Run tests to verify they pass**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_db_migrations.py -v`
Expected: 5 passed

**Step 6: Commit**

```bash
git add src/starting_point/db/ src/starting_point/engine/state.py tests/test_db_migrations.py
git commit -m "feat: add database migrations for users, orders, user_profiles"
```

---

### Task 5: Database repository layer

**Files:**
- Create: `src/starting_point/db/user_repo.py`
- Create: `tests/test_user_repo.py`

**Step 1: Write tests**

Create `tests/test_user_repo.py`:

```python
import pytest
import aiosqlite
from pathlib import Path

from starting_point.db.migrations import run_migrations
from starting_point.db.user_repo import UserRepo
from starting_point.models import User


@pytest.fixture
async def repo(tmp_path):
    db_path = tmp_path / "test.db"
    async with aiosqlite.connect(db_path) as db:
        await run_migrations(db)
        yield UserRepo(db)


@pytest.mark.asyncio
async def test_create_and_get_user(repo):
    user = User(id="u1", wx_openid="wx123", nickname="测试用户")
    await repo.save_user(user)
    loaded = await repo.get_user("u1")
    assert loaded is not None
    assert loaded.wx_openid == "wx123"
    assert loaded.nickname == "测试用户"


@pytest.mark.asyncio
async def test_get_user_by_openid(repo):
    user = User(id="u1", wx_openid="wx123")
    await repo.save_user(user)
    loaded = await repo.get_user_by_openid("wx123")
    assert loaded is not None
    assert loaded.id == "u1"


@pytest.mark.asyncio
async def test_get_nonexistent_user(repo):
    assert await repo.get_user("nonexistent") is None
    assert await repo.get_user_by_openid("nonexistent") is None


@pytest.mark.asyncio
async def test_update_user_tier(repo):
    user = User(id="u1", wx_openid="wx123")
    await repo.save_user(user)
    updated = user.model_copy(update={"tier": "standard"})
    await repo.save_user(updated)
    loaded = await repo.get_user("u1")
    assert loaded.tier == "standard"
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_user_repo.py -v`
Expected: FAIL

**Step 3: Create user_repo.py**

Create `src/starting_point/db/user_repo.py`:

```python
from __future__ import annotations

import json
import aiosqlite

from starting_point.models import User


class UserRepo:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def save_user(self, user: User) -> None:
        await self._db.execute(
            """INSERT OR REPLACE INTO users
            (id, wx_openid, wx_unionid, nickname, avatar_url, phone, tier, tier_expires_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (user.id, user.wx_openid, user.wx_unionid, user.nickname,
             user.avatar_url, user.phone, user.tier, user.tier_expires_at),
        )
        await self._db.commit()

    async def get_user(self, user_id: str) -> User | None:
        cursor = await self._db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        data = dict(zip(cols, row))
        return User(**data)

    async def get_user_by_openid(self, wx_openid: str) -> User | None:
        cursor = await self._db.execute("SELECT * FROM users WHERE wx_openid = ?", (wx_openid,))
        row = await cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        data = dict(zip(cols, row))
        return User(**data)
```

**Step 4: Run tests**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_user_repo.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/starting_point/db/user_repo.py tests/test_user_repo.py
git commit -m "feat: add UserRepo for user CRUD operations"
```

---

### Task 6: WeChat OAuth client

**Files:**
- Create: `src/starting_point/auth/wechat.py`
- Create: `tests/test_wechat_oauth.py`

**Step 1: Write tests**

Create `tests/test_wechat_oauth.py`:

```python
from starting_point.auth.wechat import build_authorize_url, parse_callback_code


def test_build_authorize_url():
    url = build_authorize_url("http://localhost:8000/api/auth/wechat/callback")
    assert "open.weixin.qq.com" in url
    assert "snsapi_userinfo" in url
    assert "state=" in url


def test_parse_callback_code():
    code = parse_callback_code({"code": "abc123", "state": "xyz"})
    assert code == "abc123"


def test_parse_callback_code_missing():
    code = parse_callback_code({})
    assert code is None
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_wechat_oauth.py -v`
Expected: FAIL

**Step 3: Create wechat.py**

Create `src/starting_point/auth/wechat.py`:

```python
from __future__ import annotations

import hashlib
import secrets
import urllib.parse

import httpx

from starting_point.config import settings

_STATE_STORE: dict[str, float] = {}


def build_authorize_url(redirect_uri: str) -> str:
    state = secrets.token_urlsafe(16)
    _STATE_STORE[state] = __import__("time").time()
    params = {
        "appid": settings.wx_app_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "snsapi_userinfo",
        "state": state,
    }
    return f"https://open.weixin.qq.com/connect/oauth2/authorize?{urllib.parse.urlencode(params)}#wechat_redirect"


def parse_callback_code(params: dict) -> str | None:
    return params.get("code")


async def exchange_code_for_token(code: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                "appid": settings.wx_app_id,
                "secret": settings.wx_app_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        return None
    data = resp.json()
    if "openid" not in data:
        return None
    return data


async def get_user_info(access_token: str, openid: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.weixin.qq.com/sns/userinfo",
            params={"access_token": access_token, "openid": openid, "lang": "zh_CN"},
        )
    if resp.status_code != 200:
        return None
    return resp.json()
```

**Step 4: Run tests**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_wechat_oauth.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/starting_point/auth/wechat.py tests/test_wechat_oauth.py
git commit -m "feat: add WeChat OAuth client with authorize URL and token exchange"
```

---

### Task 7: Auth middleware and API routes

**Files:**
- Create: `src/starting_point/auth/middleware.py`
- Create: `src/starting_point/auth/routes.py`
- Create: `tests/test_auth_routes.py`
- Modify: `src/starting_point/main.py`

**Step 1: Write tests**

Create `tests/test_auth_routes.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path
import aiosqlite

from starting_point.db.migrations import run_migrations
from starting_point.db.user_repo import UserRepo
from starting_point.models import User
from starting_point.auth.jwt import create_token


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "test_auth.db"
    async with aiosqlite.connect(db_path) as conn:
        await run_migrations(conn)
        yield conn


@pytest.mark.asyncio
async def test_get_me_valid_token(db):
    repo = UserRepo(db)
    user = User(id="u1", wx_openid="wx1", nickname="测试")
    await repo.save_user(user)
    token = create_token("u1")

    from starting_point.auth.middleware import get_current_user
    result = await get_current_user(token, repo)
    assert result is not None
    assert result.id == "u1"


@pytest.mark.asyncio
async def test_get_me_invalid_token(db):
    repo = UserRepo(db)
    from starting_point.auth.middleware import get_current_user
    result = await get_current_user("invalid.token", repo)
    assert result is None


@pytest.mark.asyncio
async def test_get_me_deleted_user(db):
    repo = UserRepo(db)
    token = create_token("nonexistent")
    from starting_point.auth.middleware import get_current_user
    result = await get_current_user(token, repo)
    assert result is None
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_auth_routes.py -v`
Expected: FAIL

**Step 3: Create middleware.py**

Create `src/starting_point/auth/middleware.py`:

```python
from __future__ import annotations

from starting_point.auth.jwt import decode_token
from starting_point.db.user_repo import UserRepo
from starting_point.models import User


async def get_current_user(token: str, repo: UserRepo) -> User | None:
    payload = decode_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    return await repo.get_user(user_id)
```

**Step 4: Create routes.py**

Create `src/starting_point/auth/routes.py`:

```python
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from starting_point.auth.jwt import create_token
from starting_point.auth.middleware import get_current_user
from starting_point.auth.wechat import build_authorize_url, exchange_code_for_token, get_user_info
from starting_point.config import settings
from starting_point.db.user_repo import UserRepo
from starting_point.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_repo(request: Request) -> UserRepo:
    return request.app.state.user_repo


@router.get("/wechat/login")
async def wechat_login(request: Request):
    callback_url = str(request.base_url).rstrip("/") + "/api/auth/wechat/callback"
    url = build_authorize_url(callback_url)
    return RedirectResponse(url)


@router.get("/wechat/callback")
async def wechat_callback(code: str | None = None, state: str | None = None, request: Request = None):
    if not code:
        raise HTTPException(400, "Missing authorization code")

    token_data = await exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(400, "Failed to exchange code for token")

    openid = token_data["openid"]
    access_token = token_data["access_token"]

    repo = _get_repo(request)
    user = await repo.get_user_by_openid(openid)

    if user is None:
        wx_info = await get_user_info(access_token, openid)
        nickname = wx_info.get("nickname", "") if wx_info else ""
        avatar = wx_info.get("headimgurl", "") if wx_info else ""
        user = User(
            id=f"u_{uuid.uuid4().hex[:12]}",
            wx_openid=openid,
            wx_unionid=token_data.get("unionid", ""),
            nickname=nickname,
            avatar_url=avatar,
        )
        await repo.save_user(user)

    jwt_token = create_token(user.id)
    response = RedirectResponse(url="/app.html")
    response.set_cookie("token", jwt_token, httponly=True, max_age=settings.jwt_expiry_hours * 3600)
    return response


@router.get("/me")
async def get_me(request: Request):
    token = request.cookies.get("token") or _extract_bearer(request)
    if not token:
        raise HTTPException(401, "Not authenticated")
    repo = _get_repo(request)
    user = await get_current_user(token, repo)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user.model_dump()


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None
```

**Step 5: Wire routes into main.py**

In `src/starting_point/main.py`, add imports and include the router. In the `lifespan` function, create `UserRepo` and store on `app.state`. Add `from starting_point.auth.routes import router as auth_router` and `app.include_router(auth_router)`.

**Step 6: Run tests**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_auth_routes.py -v`
Expected: 3 passed

**Step 7: Commit**

```bash
git add src/starting_point/auth/ tests/test_auth_routes.py src/starting_point/main.py
git commit -m "feat: add auth middleware, WeChat OAuth routes, JWT auth"
```

---

### Task 8: Paywall logic in SkillRunner

**Files:**
- Create: `src/starting_point/payments/tiers.py`
- Create: `src/starting_point/payments/access.py`
- Create: `tests/test_paywall.py`
- Modify: `src/starting_point/engine/runner.py`

**Step 1: Write tests**

Create `tests/test_paywall.py`:

```python
from datetime import datetime, timedelta
from starting_point.payments.access import check_phase_access, AccessResult


def test_free_user_phase0_allowed():
    result = check_phase_access(tier="free", tier_expires_at=None, phase_index=0)
    assert result.allowed is True


def test_free_user_phase1_allowed():
    result = check_phase_access(tier="free", tier_expires_at=None, phase_index=1)
    assert result.allowed is True


def test_free_user_phase2_blocked():
    result = check_phase_access(tier="free", tier_expires_at=None, phase_index=2)
    assert result.allowed is False


def test_standard_user_phase5_allowed():
    expiry = datetime.now() + timedelta(days=30)
    result = check_phase_access(tier="standard", tier_expires_at=expiry, phase_index=5)
    assert result.allowed is True


def test_expired_standard_blocked():
    expiry = datetime.now() - timedelta(days=1)
    result = check_phase_access(tier="standard", tier_expires_at=expiry, phase_index=2)
    assert result.allowed is False


def test_low_ticket_phase2_allowed():
    expiry = datetime.now() + timedelta(days=30)
    result = check_phase_access(tier="low_ticket", tier_expires_at=expiry, phase_index=2)
    assert result.allowed is True


def test_low_ticket_phase3_blocked():
    expiry = datetime.now() + timedelta(days=30)
    result = check_phase_access(tier="low_ticket", tier_expires_at=expiry, phase_index=3)
    assert result.allowed is False


def test_human_all_allowed():
    expiry = datetime.now() + timedelta(days=30)
    result = check_phase_access(tier="human", tier_expires_at=expiry, phase_index=5)
    assert result.allowed is True
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_paywall.py -v`
Expected: FAIL

**Step 3: Create tiers.py**

Create `src/starting_point/payments/__init__.py` (empty) and `src/starting_point/payments/tiers.py`:

```python
from starting_point.models import TIER_DEFINITIONS


def get_tiers() -> list[dict]:
    return [
        {**v, "key": k}
        for k, v in TIER_DEFINITIONS.items()
        if v["price_fen"] > 0
    ]
```

**Step 4: Create access.py**

Create `src/starting_point/payments/access.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AccessResult:
    allowed: bool
    reason: str = ""


def check_phase_access(
    tier: str,
    tier_expires_at: datetime | None,
    phase_index: int,
) -> AccessResult:
    # Phase 0 and 1 always free
    if phase_index <= 1:
        return AccessResult(allowed=True)

    # Check tier validity
    if tier == "free":
        return AccessResult(allowed=False, reason="free_tier_limit")

    # Check expiry
    if tier_expires_at and datetime.now() > tier_expires_at:
        return AccessResult(allowed=False, reason="tier_expired")

    # low_ticket: only Phase 2
    if tier == "low_ticket" and phase_index > 2:
        return AccessResult(allowed=False, reason="low_ticket_limit")

    # standard and human: all phases
    if tier in ("standard", "human"):
        return AccessResult(allowed=True)

    return AccessResult(allowed=False, reason="unknown_tier")
```

**Step 5: Run tests**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_paywall.py -v`
Expected: 8 passed

**Step 6: Integrate paywall into runner.py**

In `src/starting_point/engine/runner.py`, at the top of `process_message`, after loading state, add paywall check:

```python
from starting_point.payments.access import check_phase_access

# After state = await self._get_or_create_state(user_id):
skill_order = V2_SKILL_ORDER.index(state.current_skill) if state.current_skill in V2_SKILL_ORDER else 0
```

Add a new method `_check_paywall` and a `user_tier`/`user_tier_expires` parameter to `process_message`. When blocked, return a `ChatResponse` with `paywall=True` data in the output field.

**Step 7: Run existing tests to verify no regression**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/ -v`
Expected: All pass

**Step 8: Commit**

```bash
git add src/starting_point/payments/ tests/test_paywall.py src/starting_point/engine/runner.py
git commit -m "feat: add paywall access control and tier checking"
```

---

### Task 9: WeChat Pay client and payment routes

**Files:**
- Create: `src/starting_point/payments/wechat.py`
- Create: `src/starting_point/payments/routes.py`
- Create: `src/starting_point/db/order_repo.py`
- Create: `tests/test_payment_routes.py`

**Step 1: Write tests**

Create `tests/test_payment_routes.py`:

```python
import pytest
import aiosqlite
from pathlib import Path
from datetime import datetime, timedelta

from starting_point.db.migrations import run_migrations
from starting_point.db.order_repo import OrderRepo
from starting_point.models import Order


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "test_pay.db"
    async with aiosqlite.connect(db_path) as conn:
        await run_migrations(conn)
        yield conn


@pytest.mark.asyncio
async def test_create_order(db):
    repo = OrderRepo(db)
    order = Order(id="o1", user_id="u1", tier="standard", amount=5900)
    await repo.save_order(order)
    loaded = await repo.get_order("o1")
    assert loaded is not None
    assert loaded.tier == "standard"
    assert loaded.amount == 5900


@pytest.mark.asyncio
async def test_update_order_status(db):
    repo = OrderRepo(db)
    order = Order(id="o1", user_id="u1", tier="standard", amount=5900)
    await repo.save_order(order)
    await repo.update_status("o1", "paid", wx_transaction_id="wx_tx_123")
    loaded = await repo.get_order("o1")
    assert loaded.status == "paid"
    assert loaded.wx_transaction_id == "wx_tx_123"


@pytest.mark.asyncio
async def test_get_orders_by_user(db):
    repo = OrderRepo(db)
    await repo.save_order(Order(id="o1", user_id="u1", tier="standard", amount=5900))
    await repo.save_order(Order(id="o2", user_id="u1", tier="low_ticket", amount=1990))
    orders = await repo.get_orders_by_user("u1")
    assert len(orders) == 2
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_payment_routes.py -v`
Expected: FAIL

**Step 3: Create order_repo.py**

Create `src/starting_point/db/order_repo.py`:

```python
from __future__ import annotations

import aiosqlite
from datetime import datetime

from starting_point.models import Order


class OrderRepo:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def save_order(self, order: Order) -> None:
        await self._db.execute(
            """INSERT OR REPLACE INTO orders
            (id, user_id, tier, amount, wx_prepay_id, wx_transaction_id, status, paid_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order.id, order.user_id, order.tier, order.amount,
             order.wx_prepay_id, order.wx_transaction_id, order.status,
             order.paid_at, order.created_at),
        )
        await self._db.commit()

    async def get_order(self, order_id: str) -> Order | None:
        cursor = await self._db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        return Order(**dict(zip(cols, row)))

    async def update_status(
        self, order_id: str, status: str, wx_transaction_id: str = "",
    ) -> None:
        paid_at = datetime.now().isoformat() if status == "paid" else None
        await self._db.execute(
            """UPDATE orders SET status = ?, wx_transaction_id = ?, paid_at = ?
            WHERE id = ?""",
            (status, wx_transaction_id, paid_at, order_id),
        )
        await self._db.commit()

    async def get_orders_by_user(self, user_id: str) -> list[Order]:
        cursor = await self._db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [Order(**dict(zip(cols, row))) for row in rows]
```

**Step 4: Create wechat.py (payment client stub)**

Create `src/starting_point/payments/wechat.py`:

```python
from __future__ import annotations

import hashlib
import time
import uuid

import httpx

from starting_point.config import settings


def _generate_sign(params: dict, api_key: str) -> str:
    sorted_params = sorted(params.items())
    query = "&".join(f"{k}={v}" for k, v in sorted_params if v)
    query += f"&key={api_key}"
    return hashlib.md5(query.encode()).hexdigest().upper()


async def create_prepay_order(
    order_id: str,
    amount_fen: int,
    description: str,
    openid: str,
    notify_url: str,
) -> dict:
    params = {
        "appid": settings.wx_app_id,
        "mch_id": settings.wx_pay_mch_id,
        "nonce_str": uuid.uuid4().hex[:16],
        "body": description[:128],
        "out_trade_no": order_id,
        "total_fee": str(amount_fen),
        "spbill_create_ip": "127.0.0.1",
        "notify_url": notify_url,
        "trade_type": "JSAPI",
        "openid": openid,
    }
    params["sign"] = _generate_sign(params, settings.wx_pay_api_key)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.mch.weixin.qq.com/pay/unifiedorder",
            content=_to_xml(params),
            headers={"Content-Type": "application/xml"},
        )
    return _parse_xml(resp.text)


async def verify_callback(xml_body: str, api_key: str) -> dict | None:
    data = _parse_xml(xml_body)
    if not data:
        return None
    sign = data.pop("sign", "")
    expected = _generate_sign(data, api_key)
    if sign != expected:
        return None
    return data


def _to_xml(params: dict) -> str:
    items = "".join(f"<{k}><![CDATA[{v}]]></{k}>" for k, v in params.items())
    return f"<xml>{items}</xml>"


def _parse_xml(xml: str) -> dict:
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml)
        return {child.tag: child.text or "" for child in root}
    except ET.ParseError:
        return {}
```

**Step 5: Create payment routes**

Create `src/starting_point/payments/routes.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request

from starting_point.auth.middleware import get_current_user
from starting_point.config import settings
from starting_point.db.order_repo import OrderRepo
from starting_point.db.user_repo import UserRepo
from starting_point.models import Order, TIER_DEFINITIONS
from starting_point.payments.tiers import get_tiers
from starting_point.payments.wechat import create_prepay_order, verify_callback

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("/tiers")
async def list_tiers():
    return get_tiers()


@router.post("/create")
async def create_order(tier: str, request: Request):
    if tier not in TIER_DEFINITIONS or tier == "free":
        raise HTTPException(400, "Invalid tier")

    token = request.cookies.get("token") or _extract_bearer(request)
    if not token:
        raise HTTPException(401, "Not authenticated")

    repo: UserRepo = request.app.state.user_repo
    user = await get_current_user(token, repo)
    if not user:
        raise HTTPException(401, "Invalid token")

    tier_def = TIER_DEFINITIONS[tier]
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:12]}",
        user_id=user.id,
        tier=tier,
        amount=tier_def["price_fen"],
    )

    order_repo: OrderRepo = request.app.state.order_repo
    await order_repo.save_order(order)

    notify_url = str(request.base_url).rstrip("/") + "/api/payments/wechat/callback"
    prepay = await create_prepay_order(
        order_id=order.id,
        amount_fen=tier_def["price_fen"],
        description=tier_def["label"],
        openid=user.wx_openid,
        notify_url=notify_url,
    )
    return {"order_id": order.id, "prepay": prepay}


@router.post("/wechat/callback")
async def wechat_pay_callback(request: Request):
    body = await request.body()
    data = await verify_callback(body.decode(), settings.wx_pay_api_key)
    if not data:
        return "<xml><return_code><![CDATA[FAIL]]></return_code></xml>"

    order_repo: OrderRepo = request.app.state.order_repo
    user_repo: UserRepo = request.app.state.user_repo

    order_id = data.get("out_trade_no", "")
    order = await order_repo.get_order(order_id)
    if not order:
        return "<xml><return_code><![CDATA[FAIL]]></return_code></xml>"

    await order_repo.update_status(
        order_id, "paid", data.get("transaction_id", ""),
    )

    tier_def = TIER_DEFINITIONS.get(order.tier, {})
    duration_days = tier_def.get("duration_days", 60) or 60
    user = await user_repo.get_user(order.user_id)
    if user:
        updated = user.model_copy(update={
            "tier": order.tier,
            "tier_expires_at": datetime.now() + timedelta(days=duration_days),
        })
        await user_repo.save_user(updated)

    return "<xml><return_code><![CDATA[SUCCESS]]></return_code></xml>"


@router.get("/status/{order_id}")
async def payment_status(order_id: str, request: Request):
    order_repo: OrderRepo = request.app.state.order_repo
    order = await order_repo.get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return {"status": order.status, "tier": order.tier}


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None
```

**Step 6: Run tests**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_payment_routes.py -v`
Expected: 3 passed

**Step 7: Wire payment routes into main.py**

Add `from starting_point.payments.routes import router as payment_router` and `app.include_router(payment_router)`.

**Step 8: Commit**

```bash
git add src/starting_point/payments/ src/starting_point/db/order_repo.py tests/test_payment_routes.py src/starting_point/main.py
git commit -m "feat: add WeChat Pay client, order repo, payment routes"
```

---

### Task 10: Frontend — auth.js module

**Files:**
- Create: `static/js/auth.js`
- Modify: `static/js/store.js`

**Step 1: Create auth.js**

Create `static/js/auth.js`:

```javascript
// starting-point/static/js/auth.js
// JWT token management and auth flow

const TOKEN_KEY = 'sp_token';

export function getToken() {
  // Check cookie first (set by OAuth callback), then localStorage
  const cookieToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('token='));
  if (cookieToken) {
    const token = cookieToken.split('=')[1];
    localStorage.setItem(TOKEN_KEY, token);
    document.cookie = 'token=; max-age=0; path=/';
    return token;
  }
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isLoggedIn() {
  return !!getToken();
}

export async function fetchWithAuth(url, options = {}) {
  const token = getToken();
  if (!token) {
    window.location.href = '/login.html';
    return;
  }
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  const resp = await fetch(url, { ...options, headers });
  if (resp.status === 401) {
    clearToken();
    window.location.href = '/login.html';
    return;
  }
  return resp;
}

export async function getCurrentUser() {
  const resp = await fetchWithAuth('/api/auth/me');
  if (!resp) return null;
  return resp.json();
}
```

**Step 2: Modify store.js — remove randomUUID, use server userId**

In `static/js/store.js`, change `createInitialState` to not generate userId:

```javascript
function createInitialState() {
  return {
    userId: null,       // Will be set from server after login
    currentPhase: 0,
    currentStep: 0,
    phaseResults: {},
    contentPlan: null,
    isPaused: false,
    chatHistory: [],
  };
}
```

Remove the `generateId` function.

**Step 3: Commit**

```bash
git add static/js/auth.js static/js/store.js
git commit -m "feat: add auth.js module, update store.js for server-side userId"
```

---

### Task 11: Frontend — login.html

**Files:**
- Create: `static/login.html`

**Step 1: Create login.html**

Create `static/login.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>启点 — 登录</title>
  <link rel="stylesheet" href="design-system.css">
  <style>
    .login-page {
      min-height: 100dvh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: var(--sp-6);
      text-align: center;
    }
    .login-page__logo {
      font-size: 3rem;
      font-weight: 800;
      margin-bottom: var(--sp-2);
      color: var(--gold);
    }
    .login-page__subtitle {
      color: var(--text-muted);
      font-size: 1.1rem;
      margin-bottom: var(--sp-8);
    }
    .login-page__btn {
      display: flex;
      align-items: center;
      gap: var(--sp-3);
      background: #07c160;
      color: #fff;
      font-size: 1.1rem;
      font-weight: 600;
      padding: var(--sp-4) var(--sp-8);
      border-radius: var(--radius-lg);
      border: none;
      cursor: pointer;
      width: 100%;
      max-width: 320px;
      justify-content: center;
      transition: background 0.2s;
    }
    .login-page__btn:hover {
      background: #06ad56;
    }
    .login-page__btn-icon {
      width: 24px;
      height: 24px;
      fill: currentColor;
    }
    .login-page__note {
      margin-top: var(--sp-6);
      color: var(--text-muted);
      font-size: 0.85rem;
    }
  </style>
</head>
<body class="dark-bg">
  <div class="login-page">
    <div class="login-page__logo">启点</div>
    <p class="login-page__subtitle">陪你赚到第一块钱</p>
    <button class="login-page__btn" onclick="loginWithWechat()">
      <svg class="login-page__btn-icon" viewBox="0 0 24 24"><path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 0 0 .167-.054l1.903-1.114a.864.864 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178A1.17 1.17 0 0 1 4.623 7.17c0-.651.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178 1.17 1.17 0 0 1-1.162-1.178c0-.651.52-1.18 1.162-1.18zm5.34 2.867c-1.797-.052-3.746.512-5.28 1.786-1.72 1.428-2.687 3.72-1.78 6.22.942 2.453 3.666 4.229 6.884 4.229.826 0 1.622-.12 2.361-.336a.722.722 0 0 1 .598.082l1.584.926a.272.272 0 0 0 .14.047c.134 0 .24-.111.24-.247 0-.06-.023-.12-.038-.177l-.327-1.233a.582.582 0 0 1-.023-.156.49.49 0 0 1 .201-.398C23.024 18.48 24 16.82 24 14.98c0-3.21-2.931-5.837-7.062-6.122zM14.033 13.33c.535 0 .969.44.969.982a.976.976 0 0 1-.969.983.976.976 0 0 1-.969-.983c0-.542.434-.982.97-.982zm4.844 0c.535 0 .969.44.969.982a.976.976 0 0 1-.97.983.976.976 0 0 1-.968-.983c0-.542.434-.982.969-.982z"/></svg>
      微信登录
    </button>
    <p class="login-page__note">登录即代表同意《用户协议》和《隐私政策》</p>
  </div>
  <script>
    function loginWithWechat() {
      window.location.href = '/api/auth/wechat/login';
    }
  </script>
</body>
</html>
```

**Step 2: Commit**

```bash
git add static/login.html
git commit -m "feat: add login.html with WeChat OAuth button"
```

---

### Task 12: Frontend — auth guard in app.html and app.js

**Files:**
- Modify: `static/app.html`
- Modify: `static/js/app.js`

**Step 1: Add auth guard to app.js**

At the top of `app.js`, add import:

```javascript
import { getToken, fetchWithAuth, getCurrentUser } from './auth.js';
```

Replace all `fetch(API_BASE + '/chat', ...)` calls with `fetchWithAuth(API_BASE + '/chat', ...)`.

Replace all `fetch(API_BASE + '/back/...', ...)` calls with `fetchWithAuth(...)`.

At the end of the init block, add auth check:

```javascript
// Auth guard
if (!getToken()) {
  window.location.href = '/login.html';
  return;
}
const currentUser = await getCurrentUser();
if (!currentUser) return;
// Set userId from server
state = { ...state, userId: currentUser.id };
store.save(state);
```

**Step 2: Add user avatar to app.html header**

In `static/app.html`, in the header, add after the title span:

```html
<span class="app-header__title">启点</span>
<img id="user-avatar" class="app-header__avatar" src="" alt="" style="display:none; width:32px; height:32px; border-radius:50%; margin-left:auto;">
```

**Step 3: Commit**

```bash
git add static/js/app.js static/app.html
git commit -m "feat: add auth guard, JWT fetch wrapper, user avatar in header"
```

---

### Task 13: Frontend — pricing cards and paywall rendering

**Files:**
- Modify: `static/js/app.js`
- Modify: `static/design-system.css`

**Step 1: Add paywall CSS to design-system.css**

Append to `static/design-system.css`:

```css
/* Paywall / Pricing Cards */
.paywall {
  padding: var(--sp-6) var(--sp-4);
  text-align: center;
}
.paywall__title {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--gold);
  margin-bottom: var(--sp-2);
}
.paywall__subtitle {
  color: var(--text-muted);
  margin-bottom: var(--sp-6);
}
.pricing-grid {
  display: grid;
  gap: var(--sp-4);
  max-width: 600px;
  margin: 0 auto;
}
.pricing-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--sp-5);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s;
}
.pricing-card:hover {
  border-color: var(--gold);
}
.pricing-card__name {
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--text);
  margin-bottom: var(--sp-1);
}
.pricing-card__price {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--gold);
  margin-bottom: var(--sp-2);
}
.pricing-card__price span {
  font-size: 0.9rem;
  font-weight: 400;
  color: var(--text-muted);
}
.pricing-card__desc {
  color: var(--text-muted);
  font-size: 0.9rem;
}
.pricing-card--popular {
  border-color: var(--gold);
  position: relative;
}
.pricing-card--popular::after {
  content: '推荐';
  position: absolute;
  top: -10px;
  right: 16px;
  background: var(--gold);
  color: var(--bg);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 99px;
}
```

**Step 2: Add paywall rendering function to app.js**

In `static/js/app.js`, add a function to render the paywall:

```javascript
function renderPaywall(previewData, tiers) {
  const area = $('#chat-messages');
  // Preview card
  if (previewData && Object.keys(previewData).length > 0) {
    const preview = document.createElement('div');
    preview.className = 'chat-row chat-row--ai fade-in';
    preview.innerHTML = `<div class="output-card"><div class="output-card__title">预览方案</div><div class="output-card__body">${formatPreview(previewData)}</div></div>`;
    area.appendChild(preview);
  }
  // Paywall message
  const wall = document.createElement('div');
  wall.className = 'chat-row chat-row--ai fade-in';
  wall.innerHTML = `
    <div class="paywall">
      <div class="paywall__title">解锁完整方案</div>
      <div class="paywall__subtitle">选择适合你的方案，继续你的旅程</div>
      <div class="pricing-grid">
        ${tiers.map(t => `
          <div class="pricing-card ${t.key === 'standard' ? 'pricing-card--popular' : ''}" data-tier="${t.key}">
            <div class="pricing-card__name">${t.label}</div>
            <div class="pricing-card__price">¥${(t.price_fen / 100).toFixed(1)} <span>/${t.duration_days}天</span></div>
            <div class="pricing-card__desc">${t.description}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  area.appendChild(wall);
  // Bind click events
  wall.querySelectorAll('.pricing-card').forEach(card => {
    card.addEventListener('click', () => handlePurchase(card.dataset.tier));
  });
  scrollToBottom();
}

async function handlePurchase(tier) {
  const resp = await fetchWithAuth(`${API_BASE}/payments/create?tier=${tier}`, { method: 'POST' });
  if (!resp) return;
  const data = await resp.json();
  // In development without WeChat, show order ID
  alert(`订单创建成功: ${data.order_id}\n\n开发模式下请在后台确认支付。`);
  // Poll for payment status
  pollPayment(data.order_id);
}

async function pollPayment(orderId) {
  const maxAttempts = 60;
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise(r => setTimeout(r, 3000));
    const resp = await fetchWithAuth(`${API_BASE}/payments/status/${orderId}`);
    if (!resp) return;
    const data = await resp.json();
    if (data.status === 'paid') {
      location.reload();
      return;
    }
  }
}

function formatPreview(data) {
  return Object.entries(data).map(([k, v]) =>
    `<div><strong>${k}</strong>: ${typeof v === 'object' ? JSON.stringify(v) : v}</div>`
  ).join('');
}
```

In the main message handler, after receiving a response, check for paywall:

```javascript
// After receiving response from /api/chat:
if (resp.paywall) {
  renderPaywall(resp.preview_data || {}, resp.tiers || []);
  return;
}
```

**Step 3: Commit**

```bash
git add static/js/app.js static/design-system.css
git commit -m "feat: add pricing cards, paywall rendering, payment flow"
```

---

### Task 14: Frontend — account.html

**Files:**
- Create: `static/account.html`

**Step 1: Create account.html**

Create `static/account.html` with user profile, order history, and data export. Uses auth.js for auth checks. Shows user info, current tier with expiry, order list, and a "delete account" button.

**Step 2: Commit**

```bash
git add static/account.html
git commit -m "feat: add account.html with profile, orders, data export"
```

---

### Task 15: Integration test — full auth flow

**Files:**
- Create: `tests/test_integration_auth.py`

**Step 1: Write integration test**

Create `tests/test_integration_auth.py`:

```python
import pytest
import aiosqlite
from pathlib import Path
from datetime import datetime, timedelta

from starting_point.db.migrations import run_migrations
from starting_point.db.user_repo import UserRepo
from starting_point.db.order_repo import OrderRepo
from starting_point.models import User, Order
from starting_point.auth.jwt import create_token, decode_token
from starting_point.auth.middleware import get_current_user
from starting_point.payments.access import check_phase_access


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "test_integration.db"
    async with aiosqlite.connect(db_path) as conn:
        await run_migrations(conn)
        yield conn


@pytest.mark.asyncio
async def test_full_auth_and_payment_flow(db):
    # 1. Create user (simulates WeChat OAuth callback)
    user_repo = UserRepo(db)
    user = User(id="u1", wx_openid="wx_test", nickname="测试用户")
    await user_repo.save_user(user)

    # 2. Issue JWT
    token = create_token("u1")
    payload = decode_token(token)
    assert payload["sub"] == "u1"

    # 3. Middleware extracts user
    loaded = await get_current_user(token, user_repo)
    assert loaded.nickname == "测试用户"

    # 4. Free user can access Phase 0 and 1
    assert check_phase_access("free", None, 0).allowed is True
    assert check_phase_access("free", None, 1).allowed is True
    assert check_phase_access("free", None, 2).allowed is False

    # 5. Create order
    order_repo = OrderRepo(db)
    order = Order(id="o1", user_id="u1", tier="standard", amount=5900)
    await order_repo.save_order(order)

    # 6. Simulate payment callback
    await order_repo.update_status("o1", "paid", "wx_tx_123")
    updated_order = await order_repo.get_order("o1")
    assert updated_order.status == "paid"

    # 7. Update user tier
    updated_user = user.model_copy(update={
        "tier": "standard",
        "tier_expires_at": datetime.now() + timedelta(days=60),
    })
    await user_repo.save_user(updated_user)

    # 8. Verify access
    loaded2 = await user_repo.get_user("u1")
    assert loaded2.tier == "standard"
    assert check_phase_access(loaded2.tier, loaded2.tier_expires_at, 5).allowed is True
```

**Step 2: Run test**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/test_integration_auth.py -v`
Expected: 1 passed

**Step 3: Commit**

```bash
git add tests/test_integration_auth.py
git commit -m "test: add integration test for full auth+payment flow"
```

---

### Task 16: Run full test suite and verify no regressions

**Step 1: Run all tests**

Run: `source .venv/bin/activate && PYTHONPATH=src pytest tests/ -v --tb=short`
Expected: All pass

**Step 2: Start server and verify it boots**

Run: `source .venv/bin/activate && PYTHONPATH=src python3 -m starting_point.main &`
Expected: Server starts on port 8000

**Step 3: Test login.html serves**

Run: `NO_PROXY="127.0.0.1,localhost" curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/login.html`
Expected: 200

**Step 4: Kill test server**

Run: `kill %1`

**Step 5: Commit (if any fixes needed)**

```bash
git add -A
git commit -m "test: verify full test suite passes after auth/payment changes"
```
