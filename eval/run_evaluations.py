import argparse
import asyncio
import json
from pathlib import Path
from unittest.mock import patch

from sqlglot import exp, parse_one

from backend.agent import intent_router, skill_loader
from backend.crawler.parsers.generic_parser import parse_job_page
from backend.mcp_server import offerpilot_mcp
from backend.services import sql_guard_service, text2sql_service
from backend.tools import registry


EVAL_DIR = Path(__file__).resolve().parent
REPORT_JSON = EVAL_DIR / "latest_report.json"
REPORT_MD = EVAL_DIR / "latest_report.md"


def _load_json(name: str) -> list[dict]:
    return json.loads((EVAL_DIR / name).read_text(encoding="utf-8"))


def _metric(name: str, passed: int, total: int, failures: list[dict]) -> dict:
    return {
        "name": name,
        "passed": passed,
        "total": total,
        "rate": round(passed / total, 4) if total else 0,
        "failures": failures,
    }


def evaluate_skill_routing() -> dict:
    cases = _load_json("skill_routing_eval_cases.json")
    failures = []
    with patch("backend.agent.intent_router.llm_service.is_llm_available", return_value=False):
        for case in cases:
            actual = intent_router.route_task(case["task"])["skill_name"]
            if actual != case["expected_skill"]:
                failures.append({**case, "actual_skill": actual})
    return _metric("skill_routing", len(cases) - len(failures), len(cases), failures)


def evaluate_sql_guard() -> dict:
    cases = _load_json("safe_sql_cases.json") + _load_json("unsafe_sql_cases.json")
    failures = []
    for case in cases:
        result = sql_guard_service.check_sql_safety(case["sql"])
        if result["safe"] != case["expected_safe"]:
            failures.append({**case, "actual_safe": result["safe"], "actual_reason": result["reason"]})
            continue
        if result["safe"]:
            limit = parse_one(result["sql"], read="mysql").args.get("limit")
            if limit is None or int(limit.expression.name) > sql_guard_service.MAX_RESULT_ROWS:
                failures.append({**case, "actual_sql": result["sql"], "error": "result_limit_missing"})
    return _metric("sql_guard", len(cases) - len(failures), len(cases), failures)


def _sql_semantics(sql: str) -> set[str]:
    expression = parse_one(sql, read="mysql")
    tables = {table.name.lower() for table in expression.find_all(exp.Table)}
    semantics = set()
    if "city" in sql.lower() and "like" in sql.lower():
        semantics.add("city_filter")
    if "skill_name" in sql.lower() and "where" in sql.lower():
        semantics.add("skill_filter")
    if expression.args.get("group") is not None:
        if "company_name" in sql.lower():
            semantics.add("group_by_company")
        if "skill_name" in sql.lower():
            semantics.add("group_by_skill")
        if "job_type" in sql.lower():
            semantics.add("group_by_job_type")
    if "count(" in sql.lower():
        semantics.add("count_jobs")
    limit = expression.args.get("limit")
    if limit is not None:
        semantics.add(f"limit_{limit.expression.name}")
    if "jobs" in tables and "job_id" in sql.lower() and expression.args.get("group") is None:
        semantics.add("job_list")
    return semantics


def evaluate_text2sql_rules() -> dict:
    cases = _load_json("text2sql_eval_cases.json")
    failures = []
    for case in cases:
        try:
            raw_sql = text2sql_service._generate_sql_by_rules(case["question"])
            guard = sql_guard_service.check_sql_safety(raw_sql)
            tables = {table.name.lower() for table in parse_one(guard["sql"], read="mysql").find_all(exp.Table)}
            semantics = _sql_semantics(guard["sql"])
            missing_tables = sorted(set(case["expected_tables"]) - tables)
            missing_semantics = sorted(set(case["expected_semantics"]) - semantics)
            if not guard["safe"] or missing_tables or missing_semantics:
                failures.append({
                    "question": case["question"],
                    "missing_tables": missing_tables,
                    "missing_semantics": missing_semantics,
                    "sql": guard["sql"],
                })
        except Exception as exc:
            failures.append({"question": case["question"], "error": type(exc).__name__, "message": str(exc)})
    return _metric("text2sql_rules", len(cases) - len(failures), len(cases), failures)


def evaluate_crawler_parser() -> dict:
    cases = _load_json("crawler_eval_cases.json")
    failures = []
    for case in cases:
        actual = parse_job_page(case["html"])
        mismatches = {
            field: {"expected": expected, "actual": actual.get(field)}
            for field, expected in case["expected"].items()
            if actual.get(field) != expected
        }
        if mismatches:
            failures.append({"case_id": case["case_id"], "mismatches": mismatches})
    return _metric("crawler_parser", len(cases) - len(failures), len(cases), failures)


def evaluate_skill_assets() -> dict:
    skills = skill_loader.list_skills()
    failures = []
    for skill in skills:
        loaded = skill_loader.load_skill(skill["skill_name"])
        missing = [
            field
            for field in ("description", "trigger_keywords", "execution_steps", "allowed_tools", "quality_checks", "failure_handling")
            if not loaded.get(field)
        ]
        unknown_tools = sorted(set(loaded.get("allowed_tools", [])) - set(registry.TOOLS))
        if missing or unknown_tools:
            failures.append({"skill_name": skill["skill_name"], "missing": missing, "unknown_tools": unknown_tools})
    return _metric("skill_assets", len(skills) - len(failures), len(skills), failures)


def evaluate_mcp_capabilities() -> dict:
    tools = asyncio.run(offerpilot_mcp.list_tools())
    resources = asyncio.run(offerpilot_mcp.list_resources())
    tool_names = {tool.name for tool in tools}
    resource_uris = {str(resource.uri) for resource in resources}
    expected_tools = {"search_jobs", "get_job_detail", "get_job_requirements", "list_skills", "text2sql_query"}
    expected_resources = {"offerpilot://skills/catalog"}
    failures = []
    if missing := sorted(expected_tools - tool_names):
        failures.append({"missing_tools": missing})
    if missing := sorted(expected_resources - resource_uris):
        failures.append({"missing_resources": missing})
    total = len(expected_tools) + len(expected_resources)
    missing_count = sum(len(next(iter(item.values()))) for item in failures)
    return _metric("mcp_capabilities", total - missing_count, total, failures)


def run_all() -> dict:
    metrics = [
        evaluate_skill_routing(),
        evaluate_sql_guard(),
        evaluate_text2sql_rules(),
        evaluate_crawler_parser(),
        evaluate_skill_assets(),
        evaluate_mcp_capabilities(),
    ]
    passed = sum(metric["passed"] for metric in metrics)
    total = sum(metric["total"] for metric in metrics)
    return {
        "scope": "offline_deterministic",
        "passed": passed,
        "total": total,
        "rate": round(passed / total, 4) if total else 0,
        "metrics": metrics,
        "limitations": [
            "不连接生产数据库，不评价线上数据完整性",
            "不调用 LLM，不代表模型路由、抽取或生成质量",
            "爬虫仅验证通用解析器对固定 HTML fixture 的行为",
            "模拟面试与回答评价需要人工抽样复核",
        ],
    }


def write_report(report: dict) -> None:
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# OfferPilot 离线评估报告",
        "",
        f"确定性检查：{report['passed']}/{report['total']}，通过率 {report['rate'] * 100:.1f}% 。",
        "",
        "| 指标 | 通过 | 总数 | 通过率 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for metric in report["metrics"]:
        lines.append(f"| `{metric['name']}` | {metric['passed']} | {metric['total']} | {metric['rate'] * 100:.1f}% |")
    lines.extend(["", "## 失败明细", ""])
    failed_metrics = [metric for metric in report["metrics"] if metric["failures"]]
    if failed_metrics:
        for metric in failed_metrics:
            lines.append(f"### {metric['name']}")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(metric["failures"], ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
    else:
        lines.append("无。")
        lines.append("")
    lines.extend(["## 评估边界", ""] + [f"- {item}" for item in report["limitations"]])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OfferPilot deterministic offline evaluations")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    report = run_all()
    if args.write_report:
        write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
