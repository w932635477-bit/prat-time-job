import re

# Short patterns that need context-aware matching to avoid false positives.
# Bare substring matching on "算了" would match "我算了一下大概能赚5000" etc.
NEGATIVE_PATTERNS_COMPILED: list[re.Pattern[str]] = [
    re.compile(r'(?:^|[，。！？、\s])' + re.escape(p) + r'(?:$|[，。！？、\s])')
    for p in [
        "我不行", "我做不到", "没什么用", "什么都不懂",
        "没什么经验", "不值钱", "比不上", "没人要",
        "没希望", "算了", "没意思", "老了", "过时了",
        "学不会", "不敢", "丢人", "不好意思", "白费", "浪费",
    ]
]
