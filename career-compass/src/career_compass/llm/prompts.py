from __future__ import annotations

SYSTEM_TEMPLATE = """你是"经验变现导航器"的AI助手。你的任务是帮助中年失业者发现自己的行业经验价值，并帮助他们将这些经验转化为收入。

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

EXTRACTION_TEMPLATE = """从以下对话中提取用户的可变现资产。

用户回答：
{answers}

请提取：
1. 可变现的知识点（具体的，不是泛泛的"有经验"）
2. 可用资源（渠道、人脉、报价信息等）
3. 信心评估（基于回答的具体程度和积极性）

输出为JSON格式：
{{"capabilities": [{{"name": "...", "description": "...", "evidence": "...", "estimated_value": "..."}}], "resources": ["..."], "confidence_level": "low|medium|high"}}
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
