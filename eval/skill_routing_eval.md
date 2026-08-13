# Skill Router 评估说明

自动用例位于 `skill_routing_eval_cases.json`。评估运行时关闭 LLM，仅验证确定性兜底路由，避免网络和模型随机性影响持续集成。

覆盖7个 Skill：`job-search`、`jd-crawl`、`jd-analysis`、`profile-match`、`mock-interview`、`answer-evaluator`、`study-plan`。

LLM 路由质量属于独立在线评估范围，需要固定模型、Prompt 版本、温度和数据集后再报告，不能用本离线结果代替。
