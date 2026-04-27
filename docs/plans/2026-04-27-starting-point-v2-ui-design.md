# Starting Point V2 UI 设计文档

> 目标：将 V1 的3页多页应用改造为统一单页应用，支持6阶段全流程引导，保持 dark+gold 设计语言。

## 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 页面架构 | 统一单页面 (app.html) | 阶段切换无需跳转，状态管理简单，回退操作容易 |
| JS 架构 | 模块拆分（app.js + store.js + phases/*.js） | 代码组织清晰，每个 phase 独立渲染器 |
| 进度展示 | 固定进度芯片 + 可展开3×2网格 | 移动端紧凑，点击可回退已完成阶段 |
| 内容卡片 | 原生 `<details>/<summary>` 折叠 | 移动端友好，无 JS 也能用，语义化 HTML |
| 历史管理 | 阶段完成后折叠为摘要，卸载 DOM | 控制滚动长度，移动端性能保障 |

## 文件结构

```
static/
  index.html                  ← Landing 页（重新设计6阶段旅程）
  app.html                    ← 统一聊天页面（新增）
  design-system.css           ← 保持现有 + 新增组件样式
  js/
    app.js                    ← 主控：初始化、API调用、共享DOM渲染
    store.js                  ← 状态管理：localStorage 持久化、phase 状态机
    phases/
      index.js                ← Phase 注册表 + 顺序定义
      assessment.js           ← 阶段0 渲染器
      self-discovery.js       ← 阶段1 渲染器
      product-packaging.js    ← 阶段2 渲染器
      customer-acquisition.js ← 阶段3 渲染器（30天内容卡片）
      first-deal.js           ← 阶段4 渲染器
      growth.js               ← 阶段5 渲染器
  # V1 保留兼容
  chat-self-discovery.html
  chat-plan-path.html
  chat-take-action.html
  result-self-discovery.html
```

## 模块职责

### store.js — 状态管理

管理所有客户端状态，每次有意义的变更写 localStorage：

```javascript
// 状态结构
{
  userId: string,          // localStorage 生成的 UUID
  currentPhase: number,    // 0-5
  currentStep: number,     // 当前阶段内的步骤索引
  phaseResults: {          // 每个阶段的产出
    "0": { summary: "...", data: {...} },
    "1": { summary: "...", data: {...} },
  },
  contentPlan: {           // 阶段3专用
    platform: "xiaohongshu",
    currentWeek: 1,
    weeks: [...],
  },
  isPaused: boolean,
  chatHistory: [],         // 所有消息记录
}
```

提供方法：`init()`, `save()`, `load()`, `advanceStep()`, `advancePhase()`, `goBack()`, `pause()`, `resume()`

### app.js — 主控

- 初始化页面，绑定事件
- 调用后端 API (`/api/chat`, `/api/back`, `/api/state`)
- 调用对应 phase 渲染器
- 共享 DOM 工具函数：`renderBubble()`, `renderOptions()`, `renderCard()`, `renderLoading()`, `scrollToBottom()`

### phases/*.js — 阶段渲染器

每个模块导出：

```javascript
export function renderOutput(container, data) { ... }
export function getSummary(data) { ... }  // 折叠摘要，1-2行
```

## 页面结构 (app.html)

```
┌─────────────────────────┐
│ ◀ 返回    启点    ▶ 菜单  │  ← 固定顶栏
│  [==●------] 2/6 包装产品 │  ← 进度芯片（点击展开）
├─────────────────────────┤
│                         │
│  ┌─ 阶段0 已完成 ──────┐ │  ← 折叠的已完成阶段
│  │ 策略标签: xxx        │ │     (<details> 摘要)
│  └─────────────────────┘ │
│                         │
│  🤖 你最舒服的服务方式？   │  ← 当前阶段聊天
│     ○ 一对一咨询         │
│     ○ 出报告             │
│     ○ 陪跑              │
│                         │
├─────────────────────────┤
│  [输入你的回答...]    发送 │  ← 固定底部输入
└─────────────────────────┘
```

## 进度芯片交互

- 默认紧凑显示："第 2/6 阶段 · 包装产品"
- 点击展开 3×2 网格，每个阶段一个圆形按钮：
  - 已完成阶段：✓ + 金色，可点击回退
  - 当前阶段：● + 金色高亮
  - 未到达阶段：○ + 灰色不可点
- 点击已完成阶段 → 弹出确认 "回到阶段X？当前进度会保留"
- 回退时保留后续阶段数据，直到用户确认覆盖

## 阶段折叠策略

- 阶段完成后，详细聊天记录折叠成 `<details>` 摘要
- 摘要只显示该阶段的关键产出（1-2行）
- DOM 中卸载详细消息节点
- 用户展开 → 重新从 store 渲染

## 阶段3：30天内容卡片

使用原生 `<details>/<summary>` 实现周折叠：

```
┌─ 第1周：试水期 (7条) ──── ▼ ─┐  ← <details open>
│                               │
│  ┌─ Day 1 · 经验分享 ──────┐ │  ← <details>
│  │ 标题：15年建材老兵告诉你  │ │
│  │ 标签：#装修 #建材 #避坑   │ │
│  │ [展开完整脚本 ▼]         │ │
│  └─────────────────────────┘ │
│  ...（Day 2-7 类似）          │
└───────────────────────────────┘
┌─ 第2周：找感觉期 (7条) ─── ▶ ─┐  ← <details closed>
└───────────────────────────────┘
┌─ 第3周：突破期 (8条) ──── ▶ ──┐
└───────────────────────────────┘
┌─ 第4周：收获期 (8条) ──── ▶ ──┐
└───────────────────────────────┘

💡 情绪支持："第一周不求浏览量，
   只求你完成了。发出去就是胜利。"
```

## 各阶段卡片颜色标识

| 阶段 | 卡片标题色 | 关键元素 |
|------|-----------|---------|
| 0 评估 | `#C9A96E` 金色 | 策略标签 + 内容节奏 + 期望管理话术 |
| 1 发现金矿 | `#4CAF50` 绿色 | 可定价资产列表 + 市场参考价 |
| 2 包装产品 | `#C9A96E` 金色 | 服务产品卡片（名称/定价/流程/交付物） |
| 3 找客户 | `#C9A96E` 金色 | 30天内容计划 + 情绪支持话术 |
| 4 首单 | `#4CAF50` 绿色 | 沟通话术 + 报价公式 + 交付清单 |
| 5 增长 | `#C9A96E` 金色 | 涨价建议 + 转介绍机制 + 复购设计 |

## API 对接

```javascript
// 现有 API
POST /api/chat              { user_id, message, selected_option }
POST /api/back/{user_id}/{step_id}
GET  /api/state/{user_id}

// V2 新增（后端实现计划 Task 8）
POST /api/pause/{user_id}
POST /api/resume/{user_id}
GET  /api/content-plan/{user_id}
POST /api/content-week/{user_id}/{week}
```

`user_id` 使用 localStorage 生成的 UUID，跨会话保持一致。

## Landing 页 (index.html)

重新设计为6阶段旅程预览：

```
启点
陪你赚到第一块钱

从"我什么都不会"到"赚到第一笔钱"

[开始你的旅程]

6个阶段：
0. 起跑评估 — 了解你的起点
1. 发现金矿 — 发现你能卖什么
2. 包装产品 — 把经验变成服务
3. 找到客户 — 30天内容计划
4. 完成首单 — 教你搞定第一单
5. 转起来 — 持续赚钱
```

点击 [开始你的旅程] → 跳转到 app.html，开始阶段0。

## 设计约束

- 保持 V1 的 dark+gold 设计语言（#0A0A0B + #C9A96E）
- 保持移动优先（max-width 480px，touch target ≥ 44px）
- 不引入前端框架，保持 vanilla JS
- V1 页面保留，不影响向后兼容
- 所有文案使用中文
- iOS safe area 适配
