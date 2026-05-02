# Changelog

## [4.0.0] - 2026-05-02

### Added

- **Stage 0: Discovery conversation** — AI identifies 3+ monetizable knowledge points from user's industry experience through a 10-15 minute chat. LLM-internal state machine with hard cap at 10 messages.
- **Stage 1: Product packaging** — AI packages a selected knowledge point into a structured product (pricing, target buyer, positioning).
- **Startup Kit generation** — Generates bio, posts, and video scripts for 2+ platforms from the packaged product.
- **Conversation engine** — Routes between stages, auto-triggers kit generation on Stage 1 completion.
- **LLM client** — Persistent httpx.AsyncClient, JSON extraction with Pydantic validation, 3-retry on malformed output.
- **Database layer** — 4-table SQLite schema (users, messages, conversation_states, startup_kits) with async repos.
- **H5 frontend** — Single-page WeChat-optimized app with 3 views (landing, chat, kit display), mobile-first CSS, copy-to-clipboard.
- **Prompt system** — Modular prompts for each stage (stage_zero, stage_one, kit) with Chinese language templates.
- **29 tests** — Full test suite covering models, database, repos, LLM client, stage handlers, engine, and kit generator.

### Changed

- Full rewrite from v2.0 step-based engine to v4.0 conversation-based engine.
- Config simplified: removed payment fields, added DeepSeek thinking toggle.
- Frontend rewritten from multi-page phase system to single-page chat interface.

### Removed

- Payment integration (deferred post-MVP).
- Reference account search (deferred — see TODOS.md).
- Fixed-step progress engine from v2.0.
