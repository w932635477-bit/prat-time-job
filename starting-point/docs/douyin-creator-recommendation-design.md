# 抖音创作者推荐功能 - Phase 1 技术设计

## 一句话总结

在用户和启点聊天时，根据用户的行业背景，从精选账号库中检索匹配的抖音创作者，注入到DeepSeek的system prompt中，让AI自然地在对话中推荐这些创作者并解释他们如何赚钱。

## 设计理念

这不是一个独立功能模块，而是**对话增强**。对用户来说，启点推荐的抖音创作者和普通聊天没有区别。不需要新页面、不需要新API、不需要爬虫。

技术实现 = **数据库查表 + prompt注入**，零新增外部依赖。

## 现有架构适配点

```
现有流程:
  用户发消息 → 路由到当前Skill → 构建system prompt → 调用DeepSeek → 返回

新增步骤:
  用户发消息 → 路由到当前Skill → [查creator_examples表] → 构建system prompt(含创作者) → 调用DeepSeek → 返回
                                     ↑ 唯一新增点
```

## 数据库设计

### 新增表: creator_examples

```sql
CREATE TABLE IF NOT EXISTS creator_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,              -- 抖音号名称，如"老饭骨"
    douyin_id TEXT NOT NULL DEFAULT '',      -- 抖音号ID（如果有）
    category TEXT NOT NULL,                  -- 主行业分类，如"餐饮"、"建材"、"家政"
    sub_category TEXT NOT NULL DEFAULT '',   -- 子分类，如"卤味"、"瓷砖"、"月嫂"
    follower_tier TEXT NOT NULL DEFAULT '',  -- 粉丝量级: "1万+" "10万+" "50万+" "100万+"
    monetization_methods TEXT NOT NULL DEFAULT '[]',  -- 变现方式JSON数组
    origin_story TEXT NOT NULL DEFAULT '',   -- 一句话起家故事
    user_profile_tags TEXT NOT NULL DEFAULT '[]',     -- 适合的用户画像标签JSON数组
    content_style TEXT NOT NULL DEFAULT '',  -- 内容风格简述
    is_active INTEGER NOT NULL DEFAULT 1,    -- 是否启用
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_creators_category ON creator_examples(category);
CREATE INDEX IF NOT EXISTS idx_creators_tags ON creator_examples(user_profile_tags);
```

### monetization_methods 示例值

```json
["直播带货", "橱窗带货", "知识付费", "广告", "咨询", "线下引流"]
```

### user_profile_tags 示例值

```json
["餐饮从业者", "中年转型", "小本创业", "有实体店经验", "县城"]
```

## Pydantic 模型

在 `models.py` 中新增:

```python
class CreatorExample(BaseModel):
    id: int
    account_name: str
    douyin_id: str = ""
    category: str
    sub_category: str = ""
    follower_tier: str = ""
    monetization_methods: list[str] = Field(default_factory=list)
    origin_story: str = ""
    user_profile_tags: list[str] = Field(default_factory=list)
    content_style: str = ""
    is_active: bool = True


class CreatorRecommendation(BaseModel):
    """注入到prompt中的创作者推荐上下文"""
    creators: list[CreatorExample]
    match_reason: str  # 为什么推荐这些创作者
```

## 数据访问层

新增 `src/starting_point/db/creator_repo.py`:

```python
from __future__ import annotations

import json
import logging

import aiosqlite

from starting_point.models import CreatorExample

logger = logging.getLogger(__name__)


class CreatorRepo:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def find_by_category(self, category: str, limit: int = 3) -> list[CreatorExample]:
        """按行业分类查找创作者"""
        cursor = await self._conn.execute(
            """SELECT * FROM creator_examples
               WHERE category = ? AND is_active = 1
               ORDER BY RANDOM() LIMIT ?""",
            (category, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    async def find_by_tags(self, tags: list[str], limit: int = 3) -> list[CreatorExample]:
        """按用户画像标签模糊匹配"""
        conditions = []
        params: list[str | int] = []
        for tag in tags:
            conditions.append("user_profile_tags LIKE ?")
            params.append(f"%{tag}%")

        if not conditions:
            return []

        where = " OR ".join(conditions)
        params.append(limit)

        cursor = await self._conn.execute(
            f"""SELECT * FROM creator_examples
                WHERE ({where}) AND is_active = 1
                ORDER BY RANDOM() LIMIT ?""",
            params,
        )
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    async def search(self, keyword: str, limit: int = 3) -> list[CreatorExample]:
        """按关键词搜索（行业名或子分类）"""
        cursor = await self._conn.execute(
            """SELECT * FROM creator_examples
               WHERE (category LIKE ? OR sub_category LIKE ? OR user_profile_tags LIKE ?)
                     AND is_active = 1
               ORDER BY RANDOM() LIMIT ?""",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    def _row_to_model(self, row: aiosqlite.Row) -> CreatorExample:
        return CreatorExample(
            id=row["id"],
            account_name=row["account_name"],
            douyin_id=row["douyin_id"],
            category=row["category"],
            sub_category=row["sub_category"],
            follower_tier=row["follower_tier"],
            monetization_methods=json.loads(row["monetization_methods"]),
            origin_story=row["origin_story"],
            user_profile_tags=json.loads(row["user_profile_tags"]),
            content_style=row["content_style"],
            is_active=bool(row["is_active"]),
        )
```

## Prompt 注入

在 `prompts.py` 的 `PromptBuilder` 中新增:

```python
CREATOR_CONTEXT_TEMPLATE = """
【同行参考】
以下是和用户情况类似的抖音创作者，请在对话中自然地提到他们，帮助用户建立信心。不要生硬地列出清单，而是像朋友聊天一样提到"有个跟你差不多的人，你可以看看他是怎么做的"。

推荐创作者：
{creator_profiles}

推荐要求：
1. 用大白话解释这个创作者是怎么赚钱的
2. 强调他和用户的相似之处
3. 如果用户问"我能做吗"，给一个具体的、门槛很低的第一步
4. 不要一次推荐太多，一次提1-2个就好
"""
```

`PromptBuilder` 新增方法:

```python
def build_creator_context(self, creators: list[CreatorExample]) -> str:
    if not creators:
        return ""
    profiles = []
    for c in creators:
        methods = "、".join(c.monetization_methods)
        tags = "、".join(c.user_profile_tags)
        profiles.append(
            f"- {c.account_name}（{c.follower_tier}）：{c.category}行业，"
            f"变现方式：{methods}。{c.origin_story}。适合人群：{tags}"
        )
    return self.CREATOR_CONTEXT_TEMPLATE.format(
        creator_profiles="\n".join(profiles),
    )
```

## 对话流程集成

修改 `SYSTEM_TEMPLATE`，在构建system prompt时合并创作者上下文:

```python
# 在调用LLM的地方（engine/runner.py 或各skill中），构建system prompt时：
def build_system_prompt_with_creators(
    skill_name: str,
    step_question: str,
    step_index: int,
    total_steps: int,
    creator_context: str = "",
) -> str:
    base = SYSTEM_TEMPLATE.format(
        skill_name=skill_name,
        step_question=step_question,
        step_index=step_index + 1,
        total_steps=total_steps,
    )
    if creator_context:
        return base + "\n" + creator_context
    return base
```

### 触发时机

在 `engine/runner.py` 处理用户消息时，根据用户已知的行业信息查询创作者:

```python
async def _get_creator_context(self, user_state: UserState) -> str:
    """根据用户行业/背景检索匹配的创作者，返回prompt上下文"""
    # 优先从用户画像中获取行业
    industry = ""
    tags: list[str] = []

    if user_state.assessment:
        # 从评估结果中提取标签
        tags.append(user_state.assessment.profile_tag)

    # 从phase_results中提取行业信息
    phase1 = user_state.phase_results.get("1")
    if phase1:
        asset_map = phase1.data.get("asset_map", {})
        caps = asset_map.get("capabilities", [])
        if caps:
            industry = caps[0].get("name", "")

    if not industry and not tags:
        return ""

    # 查询匹配的创作者
    creators: list[CreatorExample] = []
    if industry:
        creators = await self._creator_repo.search(industry, limit=2)
    if not creators and tags:
        creators = await self._creator_repo.find_by_tags(tags, limit=2)

    if not creators:
        return ""

    return self._prompt_builder.build_creator_context(creators)
```

### 防止重复推荐

在 `UserState` 中追踪已推荐的创作者:

```python
class UserState(BaseModel):
    # ... 现有字段 ...
    recommended_creators: list[int] = Field(default_factory=list)  # 已推荐的creator ID
```

查询时排除已推荐:

```python
# creator_repo.py 新增方法
async def find_unrecommended(
    self, category: str, exclude_ids: list[int], limit: int = 2,
) -> list[CreatorExample]:
    exclude = ",".join(str(i) for i in exclude_ids) if exclude_ids else "0"
    cursor = await self._conn.execute(
        f"""SELECT * FROM creator_examples
            WHERE category = ? AND is_active = 1 AND id NOT IN ({exclude})
            ORDER BY RANDOM() LIMIT ?""",
        (category, limit),
    )
    # ...
```

## 种子数据计划

第一批数据需要手动收集100-200个账号，按行业分类:

### 行业覆盖（第一批）

| 行业 | 目标数量 | 示例方向 |
|------|----------|----------|
| 餐饮/小吃 | 15-20 | 卤味、早餐、烧烤、面馆 |
| 建材/装修 | 15-20 | 瓷砖、水电、油漆、全屋定制 |
| 家政/育婴 | 10-15 | 月嫂、保洁、收纳整理 |
| 农业/农产品 | 10-15 | 水果、茶叶、土特产 |
| 服装/纺织 | 10-15 | 摆摊、直播带货、尾货 |
| 美业/养生 | 10-15 | 美甲、推拿、艾灸 |
| 汽修/驾培 | 5-10 | 汽车维修、二手车、驾校 |
| 教育/培训 | 5-10 | 成人教育、技能培训 |
| 其他行业 | 10-15 | 依据用户反馈补充 |

### 数据收集方式

1. 在抖音上按行业关键词搜索
2. 筛选粉丝1万-100万的创作者（太大不接地气，太小没说服力）
3. 手动填写: 账号名、行业、变现方式、起家故事
4. 录入SQL脚本，首次部署时执行

### 种子数据SQL示例

```sql
INSERT INTO creator_examples (account_name, category, sub_category, follower_tier, monetization_methods, origin_story, user_profile_tags, content_style)
VALUES
('老饭骨', '餐饮', '家常菜', '100万+',
 '["直播带货", "橱窗带货"]',
 '退休厨师长把饭店手艺搬上抖音，靠卖厨具和调料月入十几万',
 '["餐饮从业者", "中年转型", "有手艺"]',
 '专业但接地气，不做作'),
('某某卤味', '餐饮', '卤味', '10万+',
 '["直播带货", "线下引流", "知识付费"]',
 '从路边摊开始，拍制作过程吸引同城客户，现在开了3家店还教别人做卤味',
 '["小本创业", "餐饮从业者", "县城"]',
 '实拍制作过程，接地气');
-- ... 更多数据
```

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `db/migrations.py` | 修改 | 新增 creator_examples 建表语句 |
| `db/creator_repo.py` | 新增 | 创作者数据查询 |
| `models.py` | 修改 | 新增 CreatorExample、CreatorRecommendation 模型 |
| `llm/prompts.py` | 修改 | 新增 CREATOR_CONTEXT_TEMPLATE + build_creator_context |
| `engine/runner.py` | 修改 | 构建 prompt 时注入创作者上下文 |
| `main.py` | 修改 | 初始化 CreatorRepo 并挂载到 app.state |
| `seed_creators.py` | 新增 | 种子数据脚本 |

## 不做的事

- 不做爬虫。创作者数据手动收集。
- 不做独立页面。推荐在对话中自然发生。
- 不做实时搜索。用静态精选库。
- 不做创作者详情页。DeepSeek直接在对话中解释。
- 不做用户对推荐的反馈追踪（Phase 2考虑）。

## 上线验证

1. 部署后用测试账号输入"我是做餐饮的"，确认启点会提到相关创作者
2. 换行业再试（建材、家政等），确认推荐和行业匹配
3. 同一用户多次对话，确认不会重复推荐同一个创作者
4. 行业库里没有的行业（如"核工程师"），确认启点不会强行推荐不相关的创作者
