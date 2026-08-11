def route_task(task: str) -> dict:
    normalized_task = task.strip().lower()

    if _contains_any(normalized_task, ["采集", "抓取", "爬取", "岗位链接", "url", "招聘页面"]):
        return {
            "task": task,
            "skill_name": "jd-crawl",
            "reason": "用户提供或提到了岗位链接采集意图",
        }

    if _contains_any(
        normalized_task,
        ["分析", "分析岗位", "jd分析", "jd 分析", "提取技能", "技能标签", "岗位要求", "需要哪些技能", "哪些技能"],
    ):
        return {
            "task": task,
            "skill_name": "jd-analysis",
            "reason": "用户表达了岗位分析或技能抽取意图",
        }

    if _contains_any(normalized_task, ["查询", "哪些岗位", "筛选", "统计", "热门技能", "成都", "rag", "agent"]):
        return {
            "task": task,
            "skill_name": "job-search",
            "reason": "用户表达了岗位查询、筛选或统计意图",
        }

    return {
        "task": task,
        "skill_name": "job-search",
        "reason": "未命中特定意图，默认进入岗位查询流程",
    }


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)
