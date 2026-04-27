# Starting Point (启点) UI Design Specification v2

> **For Stitch**: Apple-grade dark theme, mobile-first chat app. Every像素都有理由。

---

## 0. Design Philosophy

三句话定义这个产品的视觉灵魂:

1. **减法设计**: 如果删除30%的内容页面更好，就删。白(黑)空间不是浪费，是呼吸。
2. **暗色 + 金色**: 经验是暗夜里的金子。深色背景上的金色强调，像打开一个精致的盒子。
3. **一个焦点**: 每个屏幕只有一个视觉重心。用户不需要思考"我该看哪里"。

**参考产品**: Apple Watch App, Bear (dark mode), Arc Browser, Lottie Files

---

## 1. Color System

### Dark Palette (唯一主题)

```
--bg-primary:       #0A0A0B    接近纯黑，但不是纯黑。比纯黑温暖。
--bg-secondary:     #1C1C1E    Apple 暗灰，卡片/气泡背景
--bg-tertiary:      #2C2C2E    输入框背景，hover 状态
--bg-elevated:      #3A3A3C    弹出层、modal 背景

--text-primary:     #F5F5F7    Apple 白，主文字
--text-secondary:   #8E8E93    Apple 灰，辅助文字
--text-tertiary:    #636366    弱辅助文字，placeholder

--accent:           #C9A96E    低饱和金色，CTA、进度条、关键强调
--accent-subtle:    rgba(201, 169, 110, 0.15)  金色半透明，用于 hover/高亮背景

--success:          #30D158    Apple 绿，完成状态
--error:            #FF453A    Apple 红，错误状态

--divider:          rgba(255, 255, 255, 0.08)  几乎看不见的分隔线
--border:           rgba(255, 255, 255, 0.12)  卡片/输入框边框
```

### Color Usage Rules

- 金色 `#C9A96E` 只出现在: CTA 按钮、进度条填充、能力估值标签、关键图标。绝不用于大面积填充。
- 每个屏幕最多出现2次金色元素。
- 文字只有三种灰度: F5F5F7 / 8E8E93 / 636366。没有第四种。

---

## 2. Typography

### Font Stack

```css
--font-display: "SF Pro Display", "PingFang SC", -apple-system, sans-serif;
--font-body:     "SF Pro Text",   "PingFang SC", -apple-system, sans-serif;
--font-mono:     "SF Mono",       "Menlo",        monospace;
```

**不要**用 `system-ui`。不要用 `Inter`。不要用 `Roboto`。

### Type Scale

| Token | Size | Weight | Tracking | Usage |
|-------|------|--------|----------|-------|
| `--t-hero` | 28px | 600 (semibold) | -0.02em | 首页标题 |
| `--t-title` | 22px | 600 | -0.01em | 页面标题、卡片标题 |
| `--t-body` | 17px | 400 (regular) | 0 | AI消息、用户消息 |
| `--t-body-sm` | 15px | 400 | 0 | 辅助说明、选项文字 |
| `--t-caption` | 13px | 400 | 0.01em | 时间戳、进度标签 |
| `--t-micro` | 11px | 500 (medium) | 0.02em | badge、tag |
| `--t-button` | 17px | 500 | 0 | 按钮文字 |

行高统一 `1.5`。中文段落的段间距 `16px`。

---

## 3. Spacing & Layout

### Spacing Scale (4px base)

```
--sp-1: 4px    微间距
--sp-2: 8px    图标与文字间距
--sp-3: 12px   内边距（紧凑）
--sp-4: 16px   标准内边距
--sp-5: 20px   卡片内边距
--sp-6: 24px   section 间距
--sp-8: 32px   大块间距
--sp-10: 40px  页面边距
--sp-16: 64px  首页大面积留白
--sp-24: 96px  首页超大留白
```

### Layout Constants

- 页面安全边距: `20px` 左右
- 最大内容宽度: `480px` (居中)
- 圆角标准: `12px` (卡片), `20px` (按钮/输入框), `24px` (AI气泡)
- 底部安全区: `34px` (iPhone notch)

---

## 4. Pages

### 4.1 Landing Page (首页) — `/`

这是用户的第一印象。一个屏幕，一个故事。

```
┌─────────────────────────────────┐
│                                 │  ← status bar (系统)
│                                 │
│           96px 留白              │
│                                 │
│            ◇                    │  ← 金色细线指南针图标, 48x48
│                                 │  ← 40px 留白
│                                 │
│     你的经验                     │  ← 28px semibold, #F5F5F7
│     比你想象的更值钱              │  ← 28px semibold, #C9A96E (金色)
│                                 │  ← 16px 留白
│     8个问题，找到变现方向         │  ← 15px, #8E8E93
│                                 │
│           96px 留白              │
│                                 │
│  ┌───────────────────────────┐  │
│  │         开 始              │  │  ← 全宽CTA, #C9A96E 金色填充
│  │         50px高             │  │     #0A0A0B 黑色文字, 17px medium
│  └───────────────────────────┘  │     圆角 14px
│                                 │  ← 12px 留白
│     已有 2,847 人开始            │  ← 13px, #636366, 居中
│                                 │
│           40px 留白              │
│                                 │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │  ← 三步流程, 水平排列
│   ① 认识自己  ② 规划路径  ③ 开张 │  ← 13px, #8E8E93
│   ──→──→──                      │  ← 金色箭头连接
│                                 │
│           34px 底部安全区         │
└─────────────────────────────────┘
```

**设计决策:**
- 标题第二行用金色，不是整个标题用金色。金色只在"更值钱"这个词上，强化核心信息。
- CTA 按钮是金色填充 + 黑色文字。不是金色边框，是实心。这是整个页面唯一大面积使用金色的地方。
- 三步流程极简: 不用图标，不用卡片，纯文字 + 箭头。信息密度刚好。
- 没有背景图，没有装饰图案，没有动画。黑色本身就是舞台。

**动画 (唯一):**
- 进入时，指南针图标 `opacity: 0 → 1`, 600ms ease-out
- 标题 `translateY(12px) → 0`, 400ms, 延迟 200ms
- CTA 按钮 `translateY(8px) → 0`, 300ms, 延迟 500ms
- 其他元素 `opacity: 0 → 1`, 300ms, 延迟 600ms

### 4.2 Chat Interface — `/chat`

这是核心页面。80%的用户时间在这里。

```
┌─────────────────────────────────┐
│  ←  认识自己      3/8  ≡       │  ← 44px header
│▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░│  ← 2px 进度条, #C9A96E
├─────────────────────────────────┤
│                                 │
│  ┌───────────────────────────┐  │
│  │ 你在哪个行业干了多少年？   │  │  ← AI 气泡
│  │                           │  │  bg: #1C1C1E
│  └───────────────────────────┘  │  文字: #F5F5F7 17px
│                                 │  圆角: 24px 24px 24px 4px
│  ┌──────┐  ┌──────┐            │
│  │建材   │  │餐饮   │            │  ← 选项按钮
│  └──────┘  └──────┘            │  bg: transparent
│  ┌──────┐  ┌──────┐            │  border: 1px rgba(255,255,255,0.12)
│  │零售   │  │制造   │            │  文字: #F5F5F7 15px
│  └──────┘  └──────┘            │  选中: border #C9A96E, bg accent-subtle
│                                 │
│           建材  ✓               │  ← 用户气泡 (选中选项)
│                                 │  bg: #C9A96E, 文字: #0A0A0B
│                                 │  圆角: 20px 20px 4px 20px
│                                 │
│  ┌───────────────────────────┐  │
│  │ 过去10年，哪件事你做得     │  │  ← 下一个 AI 气泡
│  │ 比身边大多数同行都稳？     │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐  │  ← 信心鼓励卡
│  │ 你帮人省了3万块，这是真   │  │  bg: accent-subtle
│  │ 本事。很多业主愿意为此付费 │  │  左边框: 2px #C9A96E
│  └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘  │  文字: 15px #F5F5F7
│                                 │
├─────────────────────────────────┤
│  ┌─────────────────────┐  ●    │  ← 输入栏 56px
│  │ 说点什么...           │  ●    │  输入框: bg #2C2C2E, 圆角 20px
│  └─────────────────────┘       │  发送按钮: ● #636366 (空) / ● #C9A96E (有文字)
│                                 │
└─────────────────────────────────┘
```

**Header 设计:**
- 高度 44px。不是 48px。Apple 的标准是 44px。
- 左侧: 返回箭头 `←` + skill 名称 "认识自己"
- 右侧: 步骤计数 "3/8" + 菜单图标 `≡`
- 进度条 2px 高，金色填充，带 300ms ease 过渡

**AI 气泡:**
- 背景 `#1C1C1E` (比页面背景亮一级，形成层次)
- 不带头像，不带名字。不是"AI助手在说话"，是"系统在引导你"。
- 气泡间距 `12px`

**用户气泡:**
- 选项模式: 金色填充 `#C9A96E`，黑色文字。像一个选中标签。
- 自由文字模式: `#2C2C2E` 背景，`#F5F5F7` 文字。和 AI 气泡区分。

**信心鼓励卡:**
- 不是气泡。是气泡下方的内嵌卡片。
- 背景: `rgba(201, 169, 110, 0.08)` — 几乎不可见的金色底
- 左边框: `2px solid #C9A96E`
- 这是金色出现的地方之一。很克制。

### 4.3 Deliverable Card (能力清单/变现方案)

当 skill 完成时，在聊天中展示结果。

```
┌─────────────────────────────────┐
│                                 │
│  ┌───────────────────────────┐  │
│  │                           │  │  ← 结果卡片
│  │  你的能力清单              │  │  bg: #1C1C1E
│  │                           │  │  标题: 22px semibold #F5F5F7
│  │  ───────────────────────  │  │  分隔线: 1px rgba(255,255,255,0.08)
│  │                           │  │
│  │  装修报价单审核与砍价      │  │  能力名: 17px medium #F5F5F7
│  │  "帮人看报价单，告诉他     │  │  引用: 15px #8E8E93 italic
│  │   哪里被坑了"             │  │
│  │  ┌──────────────────┐     │  │  估值标签: pill, bg accent-subtle
│  │  │ 500 - 2,000 元/单 │     │  │  文字: 13px #C9A96E
│  │  └──────────────────┘     │  │
│  │                           │  │
│  │  ───────────────────────  │  │
│  │                           │  │
│  │  瓷砖选型与采购指导        │  │
│  │  "帮朋友去佛山工厂直购     │  │
│  │   便宜40%"                │  │
│  │  ┌──────────────────┐     │  │
│  │  │ 300 - 1,000 元/次 │     │  │
│  │  └──────────────────┘     │  │
│  │                           │  │
│  │  ┌─────────────────────┐  │  │  ← CTA
│  │  │    继续规划路径  →   │  │  │  金色填充, 黑色文字
│  │  └─────────────────────┘  │  │
│  │                           │  │
│  └───────────────────────────┘  │
│                                 │
└─────────────────────────────────┘
```

**设计决策:**
- 卡片没有阴影。在深色背景下，阴影看不见也不需要。用背景色差异(1C1C1E vs 0A0A0B)做层次。
- 估值标签是金色出现的第二个地方。
- 能力条目之间用细线分隔，不留大间距。信息紧凑但不拥挤。

### 4.4 Skill Navigator (侧边抽屉)

从 header 右侧 `≡` 滑入。

```
┌─────────────────────────────────┐
│  ████████████████████████████   │  ← 半透明遮罩 rgba(0,0,0,0.6)
│  ██████████████┌──────────────┐ │
│  ██████████████│              │ │
│  ██████████████│  认识自己  ✓ │ │  ← 已完成: #30D158 勾
│  ██████████████│              │ │
│  ██████████████│  规划路径  ● │ │  ← 进行中: #C9A96E 点
│  ██████████████│              │ │
│  ██████████████│  开张行动    │ │  ← 未解锁: #636366 文字
│  ██████████████│              │ │
│  ██████████████│  卡住了？    │ │  ← 未解锁
│  ██████████████│              │ │
│  ██████████████│              │ │
│  ██████████████│              │ │  bg: #1C1C1E
│  ██████████████│              │ │  宽度: 280px
│  ██████████████│              │ │  从右侧滑入
│  ██████████████└──────────────┘ │
│                                 │
└─────────────────────────────────┘
```

**设计决策:**
- 纯文字列表。没有图标，没有卡片，没有描述文字。
- 状态用颜色: 绿勾(完成)、金点(进行中)、暗灰(未解锁)。
- 每项 `56px` 高，左对齐 `20px` 缩进。

---

## 5. Component Specs

### 5.1 Buttons

| Type | Background | Text | Border | Radius | Height |
|------|-----------|------|--------|--------|--------|
| Primary (CTA) | `#C9A96E` | `#0A0A0B` 17px/500 | none | 14px | 50px |
| Secondary | transparent | `#F5F5F7` 17px/500 | 1px `rgba(255,255,255,0.2)` | 14px | 50px |
| Option (default) | transparent | `#F5F5F7` 15px/400 | 1px `rgba(255,255,255,0.12)` | 12px | 48px |
| Option (selected) | `accent-subtle` | `#C9A96E` 15px/500 | 1px `#C9A96E` | 12px | 48px |
| Option (disabled) | transparent | `#636366` 15px/400 | 1px `rgba(255,255,255,0.06)` | 12px | 48px |

### 5.2 Input

- Background: `#2C2C2E`
- Border: none
- Border-radius: `20px`
- Padding: `14px 20px`
- Placeholder color: `#636366`
- Text color: `#F5F5F7`
- Font-size: `17px` (防 iOS 缩放)
- Focus: 无边框变化，placeholder 文字消失
- 发送按钮: 圆形 `36px`，空心 `#636366` → 有文字时实心 `#C9A96E`

### 5.3 Toast / Snackbar

- Background: `#3A3A3C`
- Text: `#F5F5F7` 15px
- Border-radius: `14px`
- Position: bottom, `20px` from bottom edge, centered
- Width: `calc(100% - 40px)`
- Duration: 3s auto-dismiss
- Animation: `translateY(100%) → 0`, 300ms ease-out

### 5.4 Loading Indicator

三个圆点，间距 `8px`，依次闪烁。

- 圆点大小: `6px`
- 颜色: `#8E8E93`
- 动画: opacity 0.3 → 1 → 0.3，每点延迟 200ms
- 循环: 无限

### 5.5 Progress Bar

- 高度: `2px`
- 背景: `rgba(255, 255, 255, 0.08)`
- 填充: `#C9A96E`
- 过渡: `width` 300ms ease-in-out
- 位置: header 底部边缘

---

## 6. Animations

克制。每个动画都有存在的理由。

| Element | Animation | Duration | Easing | Why |
|---------|-----------|----------|--------|-----|
| AI bubble appear | `translateY(8px) → 0` + `opacity 0 → 1` | 250ms | ease-out | 表示"AI在思考后回答" |
| User message send | `translateY(-4px) → 0` + `opacity 0 → 1` | 150ms | ease-out | 确认发送反馈 |
| Option tap | `scale 1 → 0.97 → 1` | 100ms | ease-in-out | 触觉反馈 |
| Progress fill | `width` transition | 300ms | ease-in-out | 进度可视化 |
| Confidence boost | `opacity 0 → 1` + 金色左边框 `height 0 → 100%` | 400ms | ease-out | "点亮"信心 |
| Deliverable card | `opacity 0 → 1` + `scale 0.98 → 1` | 350ms | ease-out | "揭晓"成果 |
| Nav drawer | `translateX(100%) → 0` + overlay `opacity 0 → 1` | 280ms | ease-out | 导航 |

没有弹跳。没有旋转。没有缩放到 1.05。没有 confetti。

---

## 7. Interaction States

### Chat Flow States

| State | User Sees |
|-------|-----------|
| Waiting for input | 选项按钮 + 输入框同时可见 |
| User sent, AI thinking | Loading indicator (三点闪烁) + 输入框禁用 |
| AI responded | 新气泡从底部滑入，自动滚动到底部 |
| Confidence boost | 金色左边框卡片从气泡下方展开 |
| Skill complete | 结果卡片从底部滑入，带 CTA |
| Network error | Toast: "网络不太好，再试一次" + 重试按钮 |
| LLM timeout (>15s) | Toast: "思考时间有点长..." + 三点继续闪烁 |

### Empty States

| Screen | Empty State |
|--------|------------|
| Chat history | 不需要，首次进入直接开始第一个问题 |
| Result page | "还没有完成任何环节" + "开始第一步 →" CTA |
| Deliverable | 不存在空状态，skill 完成才显示 |

---

## 8. Responsive

| Viewport | Behavior |
|----------|----------|
| < 640px (mobile) | 全宽，固定输入栏，自然布局 |
| 640-1024px (tablet) | 居中 `480px` 容器，两侧深色背景 |
| > 1024px (desktop) | 居中 `480px` 容器，大留白 |

移动端和桌面端没有布局差异。只是容器宽度不同。这是聊天 app，不是 dashboard。

---

## 9. Routes

| Route | Content | Transition |
|-------|---------|------------|
| `/` | Landing page | 首次加载 |
| `/chat` | Chat interface | 从 landing 的 CTA push 进 |
| `/chat/{skill_id}` | 跳转到特定 skill | drawer 点击触发 |
| `/result` | 查看所有成果 | push |

页面切换: iOS 原生 push/pop 动画。`translateX` 滑动，`280ms`。

---

## 10. Dark Mode Only

这个产品只有深色模式。没有浅色模式切换。

理由:
1. 目标用户在焦虑中，深色更安静、更保护隐私。
2. 金色强调色在深色背景下效果是浅色的10倍。
3. 实现和维护成本减半。
4. 品牌辨识度: "那个深色的金色 app"。

---

## 11. Accessibility

- 最小触控区域: `44px × 44px` (Apple 标准)
- 文字对比度: 主文字 `#F5F5F7` on `#0A0A0B` = 18.5:1 (AAA)
- 辅助文字 `#8E8E93` on `#0A0A0B` = 5.2:1 (AA)
- 金色 `#C9A96E` on `#0A0A0B` = 7.8:1 (AAA)
- `lang="zh-CN"` on root
- 所有按钮有 `aria-label`
- 聊天区域 `role="log"`, `aria-live="polite"`
- 进度条 `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`

---

## 12. NOT in Scope

以下明确不做，附理由:

| Item | Reason |
|------|--------|
| Light mode | 品牌定位，深色是核心视觉 |
| Custom illustrations | MVP 不需要，纯文字和色彩足够 |
| Onboarding tutorial | 第一个问题就是 onboarding |
| Profile/settings | MVP 只有一个对话流 |
| Push notifications | 后续版本 |
| Voice input | 后续版本 |
| Animation parallax | 克制，不做装饰性动画 |

---

## 13. Stitch 实现检查清单

Stitch 需要实现的关键点:

- [ ] Color system: 全部 CSS variables，不要硬编码颜色值
- [ ] Typography: PingFang SC 字体，确保中文字体回退链正确
- [ ] Landing page: 指南针图标用 SVG 细线风格，金色描边
- [ ] Chat bubbles: AI 和 user 气泡的圆角方向不同
- [ ] 金色只用3处: CTA按钮、进度条、估值标签
- [ ] 没有 box-shadow。深色背景用背景色差异做层次
- [ ] 没有渐变背景。纯色。
- [ ] 所有动画时长 < 400ms
- [ ] 移动端 input font-size 必须 17px（防 iOS 自动缩放）
- [ ] 底部安全区 34px（iPhone）
