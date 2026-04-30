from __future__ import annotations

SYSTEM_TEMPLATE = """你是"启点"的AI助手。你的任务是帮助中年失业者发现自己的行业经验价值，并帮助他们将这些经验转化为收入。

当前环节：{skill_name}（第{step_index}/{total_steps}步）
当前问题：{step_question}

核心原则：
1. 用接地气的语言，避免"赋能""生态""闭环"等术语
2. 每次只问一个问题
3. 有证据才鼓励，不把普通经历硬包装成稀缺能力
4. 如果用户回答太简短，用引导式追问
5. 检测到负面情绪时，先共情再给具体证据
"""

CONFIDENCE_BOOST_TEMPLATE = """基于用户刚才的回答："{user_answer}"

请生成一段简短、具体的正向反馈（2-3句话）。
要求：
- 引用用户原话中的具体内容
- 把经验翻译成"值多少钱"或"能帮谁"
- 不要空泛的表扬
- 证据类型：{evidence_type}
"""

EXTRACTION_TEMPLATE = """从以下对话中提取用户的可变现资产和市场信号。

用户回答：
{answers}

请提取：
1. 可变现的知识点（具体的，不是泛泛的"有经验"）
2. 可用资源（渠道、人脉、报价信息等）
3. 信心评估（基于回答的具体程度和积极性）
4. 市场信号（基于 content_search、organic_inquiry、shared_pain 的回答）：
   - demand_evidence：有没有人已经在找这种帮助？（来自 organic_inquiry）
   - search_intent：用户自己搜什么？（来自 content_search）
   - shared_pain_point：行业共性痛点是什么？（来自 shared_pain）
   - market_readiness：综合判断，市场是否已经准备好为这个经验付费（high/medium/low）

输出为JSON格式：
{{"capabilities": [{{"name": "...", "description": "...", "evidence": "...", "estimated_value": "..."}}], "resources": ["..."], "confidence_level": "low|medium|high", "market_signals": {{"demand_evidence": "...", "search_intent": "...", "shared_pain_point": "...", "market_readiness": "high|medium|low"}}}}
"""

OFFER_GENERATION_TEMPLATE = """基于用户的资产清单和约束条件，生成变现方案。

资产清单：{asset_map}
约束条件：{constraints}

请生成3个具体的offer方案，每个包含：
- 服务名称
- 目标客户
- 定价建议
- 交付形式
- 为什么适合这个人
- 7天内第一步
- 如果没人回应的备选方案

输出为JSON数组。
"""

CONTENT_GENERATION_TEMPLATE = """基于以下offer，为{platform}生成一篇发布文案。

Offer信息：{offer}
用户行业背景：{background}

要求：
- 用真人口吻，不像AI广告
- 标题从买家痛点出发
- 包含具体的价格对比或省钱案例
- 包含标签/关键词
- 首次免费/低价吸引

输出JSON：{{"title": "...", "body": "...", "tags": [...], "publish_tips": [...]}}
"""


class PromptBuilder:
    def build_system_prompt(
        self,
        skill_name: str,
        step_question: str,
        step_index: int,
        total_steps: int,
    ) -> str:
        return SYSTEM_TEMPLATE.format(
            skill_name=skill_name,
            step_question=step_question,
            step_index=step_index + 1,
            total_steps=total_steps,
        )

    def build_confidence_boost(
        self,
        user_answer: str,
        evidence_type: str,
    ) -> str:
        return CONFIDENCE_BOOST_TEMPLATE.format(
            user_answer=user_answer,
            evidence_type=evidence_type,
        )

    def build_extraction_prompt(self, answers: str) -> str:
        return EXTRACTION_TEMPLATE.format(answers=answers)

    def build_offer_prompt(self, asset_map: str, constraints: str) -> str:
        return OFFER_GENERATION_TEMPLATE.format(
            asset_map=asset_map, constraints=constraints,
        )

    def build_content_prompt(
        self, platform: str, offer: str, background: str,
    ) -> str:
        return CONTENT_GENERATION_TEMPLATE.format(
            platform=platform, offer=offer, background=background,
        )

    # --- V2 Prompt Templates ---

    ASSESSMENT_STRATEGY_TEMPLATE = """你是启点的用户评估顾问。根据以下用户情况，生成个性化策略。

数字能力：{digital_literacy}
心理准备：{mental_readiness}
时间投入：{time_commitment}
经济压力：{financial_pressure}

请以JSON格式返回：
{{
  "profile_tag": "一个简短的标签",
  "content_pace": "slow/normal/fast",
  "first_milestone": "第一个小目标",
  "expectation_tone": "期望管理话术",
  "strategy_summary": "3句话以内的策略建议"
}}"""

    PRODUCT_CARD_TEMPLATE = """你是启点的产品包装顾问。根据用户的行业和资产，设计一个可以卖的服务产品。

行业：{industry}
可定价资产：{assets}
用户画像：{assessment_tag}

请以JSON格式返回：
{{
  "service_name": "服务名称",
  "tagline": "一句话定位",
  "target_customer": "目标客户描述",
  "pricing": {{
    "trial_price": "体验价",
    "standard_price": "正式价区间",
    "package_price": "套餐价"
  }},
  "service_flow": ["步骤1", "步骤2", "步骤3", "步骤4"],
  "deliverables": "交付物描述",
  "tools_recommended": ["推荐工具1", "推荐工具2"]
}}"""

    CONTENT_WEEK_TEMPLATE = """你是启点的内容策划师。为一个{industry}行业的用户，在{platform}上生成第{week}周的内容。

周主题：{theme}
服务产品：{service_name}
本周需要生成：{pieces}条内容

请以JSON格式返回：
{{
  "week_theme": "本周主题",
  "emotional_support": "情绪管理话术，真实不空洞",
  "content_pieces": [
    {{
      "day": 1,
      "type": "经验分享/避坑指南/故事/互动问答",
      "title": "标题",
      "script": "具体脚本或文案",
      "tags": ["标签1", "标签2"]
    }}
  ],
  "next_week_hint": "下周方向建议"
}}"""

    FIRST_DEAL_TEMPLATE = """你是启点的首单教练。根据用户的服务产品，生成完成首单所需的所有工具。

服务产品：{service_name}
定价：{pricing}
服务流程：{service_flow}

请以JSON格式返回：
{{
  "communication_templates": {{
    "price_inquiry": "客户问价时的回复话术",
    "service_inquiry": "客户问服务时的回复话术",
    "hesitant_client": "客户犹豫时的回复话术"
  }},
  "pricing_formula": "具体报价公式",
  "payment_methods": [
    {{"method": "方式名", "how": "怎么操作", "tip": "注意事项"}}
  ],
  "delivery_checklist": ["交付步骤1", "交付步骤2"],
  "post_delivery": "交付后引导客户反馈的话术"
}}"""

    GROWTH_TEMPLATE = """你是启点的增长顾问。用户刚完成了首单，需要指导下一步。

服务产品：{service_name}
首单价格：{first_deal_price}元
获客渠道：{channel}

请以JSON格式返回：
{{
  "testimonial_to_content": "把客户好评变成内容的方法",
  "pricing_adjustment": "什么时候涨价、涨多少的具体建议",
  "referral_mechanism": "转介绍的具体方案",
  "repeat_purchase": "复购产品设计建议"
}}"""

    DAILY_TASKS_TEMPLATE = """你是启点的行动教练。为用户生成一个7天逐日行动计划，每天一个具体任务。

平台：{platform}
服务产品：{service_name}
用户的核心资产：{asset_map}
市场信号：{market_signals}
数字能力：{digital_literacy}
每天可用时间：{time_commitment}

规则：
- 每个任务30分钟内能完成
- 第1-2天是"准备+发布"，不是"学习"
- 任务必须引用用户的具体经验（来自asset_map）
- 优先在选定平台操作
- 避免需要花钱的步骤
- 用大白话写任务描述，不要术语

输出JSON格式：
{{"tasks": [
  {{"day": 1, "task": "具体任务描述", "platform": "哪个平台", "estimated_time": "XX分钟", "why": "为什么今天做这个", "success_signal": "什么信号说明成功了"}},
  ...
]}}"""

    def build_assessment_strategy_prompt(
        self, digital_literacy: str, mental_readiness: str,
        time_commitment: str, financial_pressure: str,
    ) -> str:
        return self.ASSESSMENT_STRATEGY_TEMPLATE.format(
            digital_literacy=digital_literacy,
            mental_readiness=mental_readiness,
            time_commitment=time_commitment,
            financial_pressure=financial_pressure,
        )

    def build_product_card_prompt(
        self, industry: str, assets: str, assessment_tag: str,
    ) -> str:
        return self.PRODUCT_CARD_TEMPLATE.format(
            industry=industry, assets=assets, assessment_tag=assessment_tag,
        )

    def build_content_week_prompt(
        self, week: int, theme: str, industry: str,
        platform: str, service_name: str, pieces: int,
    ) -> str:
        return self.CONTENT_WEEK_TEMPLATE.format(
            week=week, theme=theme, industry=industry,
            platform=platform, service_name=service_name, pieces=pieces,
        )

    def build_first_deal_prompt(
        self, service_name: str, pricing: str, service_flow: str,
    ) -> str:
        return self.FIRST_DEAL_TEMPLATE.format(
            service_name=service_name, pricing=pricing,
            service_flow=service_flow,
        )

    def build_growth_prompt(
        self, service_name: str, first_deal_price: int, channel: str,
    ) -> str:
        return self.GROWTH_TEMPLATE.format(
            service_name=service_name,
            first_deal_price=first_deal_price, channel=channel,
        )

    def build_daily_tasks_prompt(
        self, platform: str, service_name: str, asset_map: str,
        market_signals: str, digital_literacy: str, time_commitment: str,
    ) -> str:
        return self.DAILY_TASKS_TEMPLATE.format(
            platform=platform, service_name=service_name,
            asset_map=asset_map, market_signals=market_signals,
            digital_literacy=digital_literacy, time_commitment=time_commitment,
        )
