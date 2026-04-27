# Starting Point V2 — Auth, Payment & User Data Design

**Date**: 2026-04-27
**Status**: Approved

## Context

启点 V2 has a working 6-phase coaching flow with anonymous users (crypto.randomUUID). Needs production auth, payment, and user data management.

Target users: Chinese unemployed workers aged 35-55. Low tech literacy, price-sensitive, WeChat-dependent.

## 1. Authentication — WeChat OAuth

### Flow
1. User clicks "微信登录" on login.html
2. Redirect to WeChat OAuth authorize endpoint (snsapi_userinfo scope)
3. WeChat callback with code → backend exchanges for access_token + openid
4. Backend creates/finds user, issues JWT (HS256, 7-day expiry)
5. Frontend stores JWT in localStorage, sends `Authorization: Bearer <token>` on requests

### users table
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,            -- internal UUID
    wx_openid TEXT UNIQUE NOT NULL, -- WeChat openid
    wx_unionid TEXT,                -- WeChat unionid (optional)
    nickname TEXT,                  -- WeChat nickname
    avatar_url TEXT,                -- WeChat avatar
    phone TEXT,                     -- phone number (from WeChat or manual)
    tier TEXT NOT NULL DEFAULT 'free',  -- free / low_ticket / standard / human
    tier_expires_at DATETIME,       -- paid tier expiry
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### API endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/auth/wechat/login` | Redirect to WeChat OAuth |
| GET | `/api/auth/wechat/callback` | WeChat callback, issue JWT |
| GET | `/api/auth/me` | Current user info |
| POST | `/api/auth/logout` | Clear token (client-side) |

### Frontend
- `login.html` — single page with WeChat login button, dark+gold theme
- `app.html` loads → check JWT → redirect to login.html if missing
- JWT stored in localStorage, Authorization header on all /api/ requests

### Middleware
- `get_current_user` FastAPI dependency: decode JWT, load user from DB
- Applied to all `/api/` routes except `/api/auth/*`

## 2. Payment — WeChat Pay (3-tier)

### Pricing tiers
| Tier | Price | Content | Duration |
|------|-------|---------|----------|
| Free | ¥0 | Phase 0 + Phase 1 full + Phase 2 one preview | Unlimited |
| Low-ticket | ¥19.9 | Phase 2 complete (product packaging + pricing) | 60 days |
| Standard | ¥59 | Phase 2-5 all (packaging, acquisition, first deal, growth) | 60 days |
| Human | ¥199 | Standard + one human review + WeChat group Q&A 30 days | 90 days |

### Paywall logic
- SkillRunner checks `user.tier` and `user.tier_expires_at` before processing
- Free users: complete Phase 0 + Phase 1, see one Phase 2 preview offer
- At paywall, backend returns `{paywall: true, preview_data: {...}, tiers: [...]}`
- Frontend renders pricing cards when paywall response received

### Payment flow
1. User selects tier on pricing card
2. Frontend calls `POST /api/payments/create` with tier
3. Backend creates order, calls WeChat Pay unified order API
4. Returns prepay parameters to frontend
5. Frontend invokes WeChat JSAPI payment (or displays QR for native pay)
6. WeChat notifies `POST /api/payments/wechat/callback`
7. Backend verifies signature, updates order status + user tier
8. Frontend polls `GET /api/payments/status/{order_id}` until confirmed

### orders table
```sql
CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    tier TEXT NOT NULL,                 -- low_ticket / standard / human
    amount INTEGER NOT NULL,            -- in cents (fen)
    wx_prepay_id TEXT,
    wx_transaction_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending', -- pending / paid / refunded / expired
    paid_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### API endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/payments/create` | Create order, return WeChat pay params |
| POST | `/api/payments/wechat/callback` | WeChat payment notification |
| GET | `/api/payments/status/{order_id}` | Check payment status |
| GET | `/api/payments/tiers` | List pricing tiers |

### Config
```
WX_APP_ID=xxx           -- WeChat app ID
WX_APP_SECRET=xxx       -- WeChat app secret
WX_PAY_MCH_ID=xxx       -- WeChat merchant ID
WX_PAY_API_KEY=xxx      -- Merchant API key
WX_PAY_CERT_PATH=xxx    -- Merchant certificate path
JWT_SECRET=xxx           -- JWT signing key
```

## 3. User Data Management

### Database: SQLite + Alembic migrations

Keep `user_states` as JSON storage for conversation state (complex, frequently changing).
Add relational tables for auth and billing.

### New table: user_profiles
```sql
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    industry TEXT,
    years_experience INTEGER,
    goals TEXT,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Migration strategy
- Use Alembic for schema migrations
- Initial migration: create users, orders, user_profiles
- Keep user_states table as-is (JSON blob)
- Future: add indexes on users.wx_openid, orders.user_id, orders.status

### API endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/user/profile` | Get user profile |
| PUT | `/api/user/profile` | Update profile |
| GET | `/api/user/progress` | All phase progress overview |
| GET | `/api/user/export` | Export all user data as JSON |
| DELETE | `/api/user/account` | Delete account and all data |

### Frontend pages
- `login.html` — WeChat login (new)
- `app.html` — main chat (modified: add auth check, user avatar, paywall cards)
- `account.html` — user profile, order history, data export (new)

### Data flow
```
login.html → WeChat OAuth → callback → JWT issued → redirect to app.html
app.html → every API call carries JWT → middleware extracts user
SkillRunner → checks user.tier → paywall or process
Payment complete → update user.tier + tier_expires_at → content unlocks
```

## 4. File changes summary

### Backend (new)
- `src/starting_point/auth/wechat.py` — WeChat OAuth client
- `src/starting_point/auth/jwt.py` — JWT encode/decode
- `src/starting_point/auth/middleware.py` — get_current_user dependency
- `src/starting_point/payments/wechat.py` — WeChat Pay client
- `src/starting_point/payments/tiers.py` — pricing tier definitions
- `src/starting_point/alembic/` — migration directory

### Backend (modified)
- `src/starting_point/main.py` — add auth/payment routes, JWT middleware
- `src/starting_point/config.py` — add WeChat/JWT config
- `src/starting_point/engine/runner.py` — add tier check, paywall response
- `src/starting_point/models.py` — add Order, UserProfile models

### Frontend (new)
- `static/login.html` — WeChat login page
- `static/account.html` — user profile and orders
- `static/js/auth.js` — JWT management, login flow

### Frontend (modified)
- `static/app.html` — add auth guard, user avatar, paywall cards
- `static/js/app.js` — add JWT to fetch calls, paywall rendering
- `static/js/store.js` — use server-side userId instead of randomUUID
- `static/design-system.css` — add paywall/pricing card styles
