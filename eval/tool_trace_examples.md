# Agent Trace 人工验收表

每类 Skill 至少执行一次真实任务，并检查 Trace 是否包含完整链路。

| Skill | intent | skill | plan | tool_call | tool_result | final | call_id | 结果 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| job-search | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| jd-crawl | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| jd-analysis | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| profile-match | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| mock-interview | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| answer-evaluator | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| study-plan | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |

失败判定：缺少工具输入、工具输出、调用编号或最终结果中的任意一项，均不能称为完整可观测链路。
