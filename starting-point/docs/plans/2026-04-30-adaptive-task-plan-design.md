# 自由行业输入 + 自适应任务计划 设计文档

> 日期: 2026-04-30
> 状态: 已通过

## 背景

用户反馈两个产品问题：

1. **行业选择受限**：SelfDiscovery 第 0 步只有 5 个预设行业选项，不在列表中的用户无法继续。
2. **7 天计划太短**：当前 CustomerAcquisitionSkill 生成 7 天任务后立即结束阶段。用户实际需要 14-30 天引导，每天打卡汇报，卡住时需要 AI 救援。

## 设计 Section 1：行业自由输入

### 问题

`self_discovery.py` 的 `industry` 步骤只有 5 个选项（建材/餐饮/零售/制造/物流），不覆盖所有行业。

### 方案

在 steps[0] 的 options 中增加第 6 个选项 `"其他（手动输入）"`（value="other"）。前端检测到用户选 "other" 时，展示文本输入框让用户填写自定义行业。

### 改动

1. **`self_discovery.py`**：steps[0].options 增加 `StepOption(label="其他（手动输入）", value="other")`。`allow_free_text` 已经是 `True`，无需改动。
2. **`app.js`**：`renderOptions()` 中，当用户点击 value="other" 的选项时，显示输入框 + 确认按钮，用户输入后以 `free_text` 提交。其余选项行为不变。
3. **数据处理**：`process_answer` 已有 `free_text or answer` 逻辑，无需改动。

### 影响范围

2 个文件，约 20 行改动。新增测试覆盖"选其他 + 输入自定义行业"场景。

## 设计 Section 2：自适应任务计划（改造阶段 3）

### 问题

CustomerAcquisitionSkill 是 3 步 Q&A，生成 7 天任务后结束。用户需要更长时间、每日打卡、卡住救援。

### 架构

方案 A：直接改造 CustomerAcquisitionSkill，不新增独立模块。

### 2.1 数据模型

**新增 `TaskDay`**：

```python
class TaskDay(BaseModel):
    day: int
    task: str
    platform: str
    estimated_time: str = "30分钟"
    why: str = ""
    success_signal: str = ""
    status: str = "pending"          # pending | done | stuck | skipped
    stuck_reason: str | None = None
    rescue_advice: str | None = None
    completed_at: datetime | None = None
```

**改造 `TaskPlan`**（替换现有 `DailyTaskPlan`）：

```python
class TaskPlan(BaseModel):
    total_days: int = 14
    current_day: int = 1
    days: list[TaskDay] = Field(default_factory=list)
    platform: str = ""
    status: str = "active"  # active | completed | abandoned
```

**扩展 `UserState`**：增加 `task_plan: TaskPlan | None = None`。

### 2.2 步骤流程

```
步骤 0: platform_choice     → 选平台
步骤 1: content_readiness   → 了解经验
步骤 2: confirm_plan        → 展示计划，用户确认
--- 打卡循环 ---
步骤 3: daily_checkin       → 展示当天任务，用户选"完成"或"卡住了"
```

步骤 0-2 保留为计划生成阶段。步骤 3 是循环步骤，每天打卡一次。

### 2.3 LLM Prompt

- **改造 `DAILY_TASKS_TEMPLATE`**：接受 `suggested_days` 参数（14-30），Prompt 指示 LLM 根据用户数字素养和时间投入决定实际天数。
- **新增 `STUCK_RESCUE_TEMPLATE`**：用户卡住时，将任务内容 + 卡住原因 + 已完成天数发送给 LLM，生成针对性建议。

### 2.4 前端

**`customer-acquisition.js`** 改造为打卡界面：

- 步骤 0-2：保持问答形式
- 步骤 3（daily_checkin）：
  - 展示当天任务卡片：标题、说明、预计时间、成功信号
  - 两个按钮：「完成了」和「卡住了」
  - 点「卡住了」→ 展开文本框让用户描述问题 → 调用 API 获取 AI 建议 → 展示建议
  - 点「完成了」→ 标记完成，显示进度
  - 全部完成则触发阶段完成
- 进度条：`current_day / total_days`

### 2.5 API

复用现有 `/api/chat` 端点。打卡交互复用 ChatRequest：

```json
{
  "user_id": "xxx",
  "message": "完成了" 或 "卡住了：不知道怎么拍视频",
  "selected_option": "done" 或 "stuck"
}
```

后端 `process_answer` 根据 step_id="daily_checkin" 解析状态，更新 TaskDay，如果 stuck 则调用 LLM 救援。

### 2.6 影响范围

| 文件 | 改动量 |
|------|--------|
| `models.py` | 新增 TaskDay、改造 TaskPlan，~30 行 |
| `skills/customer_acquisition.py` | 改造步骤定义 + process_answer + generate_output，~150 行 |
| `llm/prompts.py` | 改造 DAILY_TASKS_TEMPLATE + 新增 STUCK_RESCUE_TEMPLATE，~80 行 |
| `static/js/phases/customer-acquisition.js` | 重写为打卡界面，~200 行 |
| `static/js/app.js` | 处理 daily_checkin 步骤的特殊渲染，~30 行 |
| 测试文件 | 新增 ~100 行测试 |

**总计**：约 600 行，6 个文件。
