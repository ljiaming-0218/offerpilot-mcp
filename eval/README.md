# OfferPilot Eval

本目录区分自动确定性评估和人工业务评估。

运行离线评估：

```bat
conda.bat run -n offerpilot python -m eval.run_evaluations --write-report
```

输出：

- `latest_report.json`：机器可读结果。
- `latest_report.md`：项目展示与复盘结果。

自动评估覆盖规则路由、SQL Guard、Text2SQL 规则兜底、通用 HTML 解析器、Skill 文件完整性和 MCP Tool/Resource 注册。它不连接生产数据库、不调用 LLM，也不代表线上数据质量或生成质量。

`sample_jobs.json` 和 `crawler_eval_cases.json` 都是明确标记的测试 fixture，不会写入生产数据库。模拟面试、回答评价和真实 Agent Trace 使用对应 Markdown 表格人工复核。
