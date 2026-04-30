# 启点（Starting Point）项目文档

> 生成日期：2026-04-30
> 版本：v2.0（含自适应任务计划 + BuilderPulse 增强 + Codex 审查修复）

---

## 一、项目定位

**一句话**：帮助中年失业者把自己的行业经验变成能卖的服务，从"发现值什么钱"到"赚到第一笔钱"。

**目标用户**：40-55岁、有10年以上行业经验、但不会用互联网变现的人。

**核心思路**：用 AI 对话引导，把用户脑子里的经验"挖出来"，包装成可以卖的产品，再给一个逐日行动计划帮他们赚到第一笔钱。

**技术栈**：
- 后端：Python 3.14 / FastAPI / Pydantic v2 / SQLite / aiosqlite
- 前端：Vanilla JS（ES modules） / 无框架
- AI：DeepSeek LLM API
- 认证：微信 OAuth + JWT
- 支付：微信支付（开发模式支持后台确认）
- 测试：pytest / 108 个测试全部通过

---

## 二、系统架构

```
用户（微信浏览器）
    ↓ 微信 OAuth 登录
    ↓ JWT Token
前端（index.html + JS modules）
    ↓ /api/chat（ChatRequest → ChatResponse）
后端（FastAPI）
    ├─ SkillRunner（步骤引擎）
    │   ├─ SkillRegistry（技能注册表）
    │   └─ StateManager（SQLite 状态持久化）
    ├─ 6 个 Skill（阶段处理器）
    │   ├─ AssessmentSkill（评估）
    │   ├─ SelfDiscoverySkill（发现金矿）
    │   ├─ ProductPackagingSkill（包装产品）
    │   ├─ CustomerAcquisitionSkill（找到客户）★ 已重构
    │   ├─ FirstDealSkill（完成首单）
    │   └─ GrowthSkill（转起来）
    ├─ DeepSeekClient（LLM 调用）
    ├─ PromptBuilder（模板系统）
    ├─ ConfidenceEngine（情绪检测）
    ├─ PaywallService（付费墙）
    └─ WechatPayClient（微信支付）
```

**关键文件清单**：

| 文件 | 作用 |
|------|------|
| `src/starting_point/models.py` | 所有数据模型（UserState, TaskDay, TaskPlan, MarketSignals 等） |
| `src/starting_point/engine/runner.py` | SkillRunner 步骤引擎，处理消息流转和阶段切换 |
| `src/starting_point/engine/skill_base.py` | BaseSkill 抽象基类 |
| `src/starting_point/engine/registry.py` | 技能注册表 |
| `src/starting_point/engine/state.py` | SQLite 状态持久化 |
| `src/starting_point/skills/self_discovery.py` | 阶段 1：发现金矿（11步） |
| `src/starting_point/skills/customer_acquisition.py` | 阶段 3：找到客户（4步 + 打卡循环）★ 已重构 |
| `src/starting_point/llm/prompts.py` | 所有 LLM Prompt 模板 |
| `src/starting_point/llm/client.py` | DeepSeek API 客户端 |
| `src/starting_point/confidence/engine.py` | 情绪检测和正向反馈引擎 |
| `static/js/app.js` | 前端主控制器（对话、选项、打卡渲染） |
| `static/js/phases/index.js` | 阶段定义和渲染器加载 |
| `static/js/phases/self-discovery.js` | 阶段 1 输出渲染（资产卡 + 市场雷达） |
| `static/js/phases/customer-acquisition.js` | 阶段 3 输出渲染（任务卡 + 打卡卡 + 救援卡） |
| `static/design-system.css` | 全局样式（900+ 行） |

---

## 三、六阶段功能详解

### 阶段 0：起跑评估（Assessment）
**4 步问答 → 生成用户画像**

| 步骤 | 问题 | 作用 |
|------|------|------|
| 数字能力 | 你平时用哪些App？ | 判断内容形式（文字/视频/图文） |
| 心理准备 | 你现在最想解决什么？ | 定基调：赚钱 vs 试试看 |
| 时间投入 | 每天能花多少时间？ | 影响阶段 3 的计划天数（14-30天） |
| 经济压力 | 你的紧迫程度？ | 决定话术强度和目标设定 |

**输出**：
- 用户画像标签（如"新媒体新手-慢节奏"）
- 首个小目标
- 期望管理话术
- 内容节奏建议（slow/normal/fast）

**效果**：后续所有阶段的计划天数、任务难度、话术风格都基于这个画像调整。

---

### 阶段 1：发现金矿（Self Discovery）
**11 步引导 → 可定价资产清单 + 市场雷达**

#### 步骤列表

| # | 步骤 ID | 问题 | 类型 |
|---|---------|------|------|
| 0 | industry | 你在哪个行业干了多少年？（6选项 + 自由输入）★ 新增"其他" | 行业定位 |
| 1 | proud_moment | 过去10年哪件事你做得比身边大多数同行都稳？ | 能力挖掘 |
| 2 | save_money_story | 讲一个你帮别人省钱或避坑的真实例子 | 证据收集 |
| 3 | insider_knowledge | 行内人知道但外行不知道的信息？ | 差异化资产 |
| 4 | people_ask_me | 客户或同事最常因为什么来找你？ | 需求验证 |
| 5 | price_judgment | 你能判断什么"贵了、坑了、不值"？ | 定价能力 |
| 6 | unique_resources | 报价、渠道、工厂、名单等资源？ | 资源盘点 |
| 7 | first_100 | 明天只靠经验赚第一笔100元，卖什么？ | 变现方向 |
| 8 | content_search | 你在抖音/小红书搜过什么？★ BuilderPulse 新增 | 市场验证 |
| 9 | organic_inquiry | 最近有人主动找你帮忙吗？★ BuilderPulse 新增 | 需求验证 |
| 10 | shared_pain | 你行业里什么最坑？★ BuilderPulse 新增 | 痛点验证 |

#### AI 处理流程

```
用户 11 个回答
    ↓
PromptBuilder.build_extraction_prompt()
    ↓ DeepSeek LLM
资产提取结果
    ├─ capabilities: [{name, description, evidence, estimated_value}]
    ├─ resources: ["渠道", "报价信息"...]
    ├─ confidence_level: high/medium/low
    └─ market_signals: {demand_evidence, search_intent, shared_pain_point, market_readiness}
    ↓
PromptBuilder.build_market_radar_prompt()
    ↓ DeepSeek LLM（第二次调用）
行业雷达
    ├─ existing_sellers: ["闲鱼上有人卖装修咨询"...]
    ├─ price_range: "50-300元"
    ├─ hot_topics: ["装修避坑", "建材选购"]
    ├─ unique_edge: "20年实战经验"
    ├─ demand_level: high/medium/low
    └─ summary: "建材咨询市场需求旺盛"
```

#### 输出渲染

前端展示两个板块：

**可定价资产卡**：
- 每个资产显示：名称 + 市场价格 + 证据

**行业雷达面板**：
- 市场需求级别（高/中/低，带颜色标签）
- 市场定价区间
- 你的独特优势（高亮）
- 谁在卖类似服务
- 热门话题（标签云）

#### 情绪引擎

- 检测负面情绪（"我不行"、"没什么特别的"）→ 先共情再给具体证据
- 回答具体详细时 → 给正向反馈（引用用户原话）
- 回答简短时 → 引导式追问

---

### 阶段 2：包装产品（Product Packaging）
**4 步 → 生成可售卖的服务产品卡**

| 步骤 | 内容 |
|------|------|
| 服务定位 | 基于资产自动生成服务名称和定位 |
| 定价策略 | 体验价 + 正式价 + 套餐价 |
| 服务流程 | 3-4步交付流程设计 |
| 工具推荐 | 需要用的工具和平台 |

**输出（产品卡 JSON）**：
```json
{
  "service_name": "装修避坑咨询",
  "tagline": "20年建材人，帮你省30%装修费",
  "target_customer": "准备装修的业主",
  "pricing": {
    "trial_price": "9.9元/次",
    "standard_price": "99-299元",
    "package_price": "499元/全屋"
  },
  "service_flow": ["了解需求", "出避坑清单", "陪同选购", "验收把关"],
  "deliverables": "避坑清单 + 选购建议 + 3次线上咨询",
  "tools_recommended": ["微信", "小红书", "腾讯文档"]
}
```

---

### 阶段 3：找到客户（Customer Acquisition）
**4 步 → 自适应 14-30 天逐日打卡计划 + AI 救援** ★ 本轮重构

#### 步骤流程

```
步骤 0: platform_choice     → 选平台（抖音/小红书/朋友圈/帮我选）
步骤 1: content_readiness   → 评估经验（从未发过/发过没人看/有看过没咨询）
步骤 2: confirm_plan        → 展示计划，用户确认
步骤 3: daily_checkin       → 每日打卡循环（完成/卡住了）★ 循环步骤
```

#### 自适应天数计算

```python
def _calculate_suggested_days(digital_literacy, time_commitment):
    base = 14
    if digital_literacy == "beginner":  base = 21
    if digital_literacy == "advanced":  base = 14
    if "1h" in time_commitment:         base += 7  # 时间少多给几天
    return min(base, 30)  # 上限 30 天
```

| 用户画像 | 每天时间 | 计划天数 |
|----------|----------|----------|
| 新手 | 30分钟-1小时 | 28 天 |
| 新手 | 3小时以上 | 21 天 |
| 中等 | 1-3小时 | 14 天 |
| 熟练 | 3-5小时 | 14 天 |

#### 每日打卡交互

```
┌─────────────────────────────────────┐
│ ████████░░░░░░  第 5/14 天          │  ← 进度条
├─────────────────────────────────────┤
│ 在小红书发一篇"瓷砖选购避坑指南"     │  ← 今天任务
│ 📍 小红书  ⏱ 30分钟                  │  ← 平台和时间
│ 为什么：让内容替你说话，被搜索到      │  ← 原因
│ 成功信号：有人收藏或评论              │  ← 成功标准
├─────────────────────────────────────┤
│  [ ✅ 完成了 ]    [ 🆘 卡住了 ]       │  ← 两个按钮
└─────────────────────────────────────┘
```

#### "卡住了" AI 救援流程

```
用户点击"卡住了"
    ↓
前端展示文本框："说说卡在哪里？"
    ↓
用户输入："不知道怎么拍照，手机拍出来效果很差"
    ↓
后端 process_answer("daily_checkin", "卡住了：不知道怎么拍照...")
    ↓ 标记任务为 stuck，保存原因
    ↓
SkillRunner._handle_stuck_rescue()
    ↓ PromptBuilder.build_stuck_rescue_prompt()
    ↓ DeepSeek LLM
    ↓ 返回救援建议
前端展示救援卡：
┌─────────────────────────────────────┐
│ 🔧 帮你分析一下                      │
├─────────────────────────────────────┤
│ 坚持到了第5天，很不容易！             │  ← 鼓励
│ 分析：拍照技巧需要一点小技巧          │  ← 诊断
│ 1. 找个窗户边，用自然光拍             │  ← 步骤1
│ 2. 拍3张选最好的一张                  │  ← 步骤2
│ 3. 不用美颜，真实反而更可信           │  ← 步骤3
│ 替代方案：先发纯文字笔记也可以        │  ← 替代
└─────────────────────────────────────┘
```

#### 无 LLM 后备

当 DeepSeek API 不可用时，自动生成 3 天基础计划：
1. 在平台注册账号，完善个人资料
2. 发第一篇内容，分享行业经验
3. 回复至少3个同行业内容的评论

---

### 阶段 4：完成首单（First Deal）
**2 步 → 生成成交所需全部工具**

**输出（首单工具包）**：
```json
{
  "communication_templates": {
    "price_inquiry": "客户问价时的回复话术",
    "service_inquiry": "客户问服务时的回复话术",
    "hesitant_client": "客户犹豫时的回复话术"
  },
  "pricing_formula": "具体报价公式",
  "payment_methods": [
    {"method": "微信转账", "how": "直接转", "tip": "先发服务说明再收款"}
  ],
  "delivery_checklist": ["确认需求", "提供服务", "收集反馈"],
  "post_delivery": "交付后引导客户反馈的话术"
}
```

---

### 阶段 5：转起来（Growth）
**2 步 → 从首单到持续增长**

**输出（增长策略）**：
```json
{
  "testimonial_to_content": "把客户好评变成内容的方法",
  "pricing_adjustment": "什么时候涨价、涨多少",
  "referral_mechanism": "转介绍的具体方案",
  "repeat_purchase": "复购产品设计建议"
}
```

---

## 四、支付体系

### 层级定义

| 层级 | 价格 | 包含内容 | 有效期 |
|------|------|----------|--------|
| 免费体验 | 0 元 | Phase 0 + Phase 1 + Phase 2 预览 | 无限期 |
| 产品包装 | 19.9 元 | 完整 Phase 2（包装 + 定价） | 60 天 |
| 完整方案 | 59 元 | Phase 2-5 全部 | 60 天 |
| 人工辅导 | 199 元 | 完整方案 + 人工审核 + 微信群答疑 | 90 天 |

### 付费墙机制

- 每个阶段边界检查用户 tier 权限
- 权限不足时返回付费墙，展示预览数据 + 定价选项
- 微信支付集成（预支付 → 轮询确认）
- 开发模式支持后台手动确认支付

---

## 五、用户系统

### 认证流程

```
微信浏览器 → 微信 OAuth 授权
    ↓
/code?code=xxx → WechatOAuthClient.exchange_code()
    ↓ 获取 openid + access_token
    ↓ 获取用户信息（昵称、头像）
    ↓ 创建/更新 User 记录
    ↓ 生成 JWT Token
    ↓ 设置 HttpOnly Cookie
前端后续请求自动携带 Cookie
```

### 用户模型

```python
class User:
    id: str               # UUID
    wx_openid: str        # 微信 openid
    wx_unionid: str       # 微信 unionid
    nickname: str         # 昵称
    avatar_url: str       # 头像
    phone: str            # 手机号
    tier: str             # 会员等级（free/low_ticket/standard/human）
    tier_expires_at: datetime  # 到期时间
```

### 数据 API

- `GET /api/state/{user_id}` — 获取当前进度状态（需认证）
- `POST /api/chat` — 对话消息（需认证）
- `POST /api/back/{user_id}/{step_id}` — 回退到指定步骤
- `GET /api/user-data/{user_id}` — 获取用户数据
- `DELETE /api/user-data/{user_id}` — 删除用户数据

---

## 六、前端交互设计

### 整体布局

```
┌──────────────────────────────────────┐
│  [第 3/6 阶段 · 找到客户]  [👤]      │  ← 顶部导航
│  ████████████████░░░░░░░░░ 65%       │  ← 进度条
├──────────────────────────────────────┤
│                                      │
│  🤖 你想先在哪个平台开始发内容？      │  ← AI 气泡
│                                      │
│  [抖音（短视频）]                     │
│  [小红书（图文笔记）]                 │  ← 选项按钮
│  [朋友圈（私域）]                     │
│  [我都不熟，帮我选]                   │
│                                      │
│  💬 用户选择了"小红书"               │  ← 用户气泡
│                                      │
│  🤖 我帮你制定了14天行动计划...       │  ← AI 气泡
│  ┌────────────────────────────┐      │
│  │  打卡卡（进度+任务+按钮）  │      │  ← 阶段输出卡
│  └────────────────────────────┘      │
│                                      │
├──────────────────────────────────────┤
│  [💬 输入消息...]           [发送]    │  ← 输入栏
└──────────────────────────────────────┘
```

### 阶段网格

点击顶部阶段名称，展开网格：
- ✅ 已完成阶段（绿色对勾，可点击回退）
- ● 当前阶段（橙色高亮）
- ○ 未开始阶段（灰色）

### 「其他」输入交互

```
用户点击"其他（手动输入）"选项
    ↓
选项按钮变灰，下方展开输入框
    ↓
[请输入你的行业...        ] [确认]
    ↓
用户输入行业名称，点确认
    ↓
以 free_text 形式提交给后端
```

---

## 七、本轮会话完成的工作

### 7.1 BuilderPulse 增强（3个功能）

| 功能 | Commit | 说明 |
|------|--------|------|
| 市场验证问题 | `1e78dcc` | 阶段 1 增加 3 个验证步骤（content_search, organic_inquiry, shared_pain） |
| 7天任务卡 | `b87ab0c` | 阶段 3 从内容计划改为逐日任务卡 |
| 行业机会雷达 | `201b23a` | 阶段 1 输出增加行业雷达（竞品/定价/话题/优势） |

### 7.2 代码审查修复

| Commit | 修复内容 |
|--------|----------|
| `b105eb4` | 验证 market_readiness 枚举值、修复变量遮蔽、前端白名单校验、mock 修正、日志补全 |

### 7.3 产品问题修复（2个）

| 问题 | 设计文档 | 实现 |
|------|----------|------|
| 行业选择受限 | `2026-04-30-adaptive-task-plan-design.md` | 增加"其他（手动输入）"选项 + 前端输入框 |
| 7天计划太短 | 同上 | 改造为 14-30 天自适应打卡计划 + AI 救援 |

### 7.4 自适应任务计划实现（8个 commit）

| Commit | 内容 |
|--------|------|
| `2a81395` | 行业选项加"其他" |
| `c8391ee` | 前端"其他"输入处理器 |
| `7ac83cd` | TaskDay / TaskPlan 数据模型 |
| `88aa096` | 救援 Prompt + 自适应天数模板 |
| `2bd08a6` | CustomerAcquisitionSkill 改造（4步 + 打卡循环） |
| `27c95a2` | SkillRunner 处理打卡循环 |
| `074c479` | 打卡 UI（前端） |
| `c315afd` | CSS 样式 |
| `e7a788b` | 集成测试 |

### 7.5 Codex 审查修复

| Commit | 修复内容 |
|--------|----------|
| `5b26232` | 5个问题：StepResult import 缺失、打卡卡首次渲染、救援建议不可见、无LLM后备计划、空plan保护 |

---

## 八、测试覆盖

### 测试统计

- **108 个测试，全部通过**
- 覆盖率：模型 / 技能 / Prompt / Runner / 状态管理 / 认证 / 支付 / 集成

### 测试文件清单

| 文件 | 测试数 | 内容 |
|------|--------|------|
| `tests/test_skills/test_self_discovery.py` | 12 | 行业选项、步骤数、情绪检测、资产提取、市场雷达 |
| `tests/test_skills/test_other_skills.py` | 21 | 任务计划、打卡、救援、天数计算、Prompt 模板 |
| `tests/test_engine/test_runner.py` | 8 | 消息处理、阶段切换、回退 |
| `tests/test_engine/test_registry.py` | 3 | 技能注册和查找 |
| `tests/test_engine/test_state.py` | 3 | 状态持久化 |
| `tests/test_models.py` | 9 | 数据模型验证 |
| `tests/test_integration.py` | 3 | API 集成 |
| `tests/test_integration_auth.py` | 3 | 认证+支付流程 |
| `tests/test_paywall.py` | 8 | 付费墙权限检查 |
| `tests/test_db_migrations.py` | 5 | 数据库迁移 |
| `tests/test_models_auth.py` | 3 | 认证模型 |
| `tests/test_user_repo.py` | 4 | 用户仓库 |
| `tests/test_wechat_oauth.py` | 3 | 微信 OAuth |
| `tests/test_payment_routes.py` | 4 | 支付路由 |

---

## 九、部署信息

- **域名**：firesing.cn
- **服务器**：腾讯云轻量应用服务器
- **备案号**：粤ICP备2024213848号-1
- **运行命令**：`python -m uvicorn starting_point.main:app --reload --port 8000`
- **开发环境**：需要 `--noproxy localhost` 绕过本地代理

---

## 十、已知限制和后续方向

### 已知限制

1. **Runner 集成测试缺失**：`SkillRunner.process_message()` 的 daily_checkin 循环和 stuck-rescue 分支没有端到端测试
2. **行业"其他"选项无端到端测试**：只测了选项存在，没测自由文本提交全流程
3. **阶段完成时 generate_output 重新生成**：会导致计划与用户实际执行的不一致（MEDIUM 级别）

### 后续方向

- 补充 Runner 端到端测试
- 阶段完成输出改为从持久化的 task_plan 派生
- 打卡数据持久化到服务器（目前仅 localStorage）
- 微信支付生产环境对接
- 内容计划周表功能完善
