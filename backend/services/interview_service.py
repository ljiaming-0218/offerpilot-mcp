from backend.errors import AppError
from backend.repositories import interview_repository, job_repository, user_profile_repository
from backend.schemas.interview_schema import AnswerEvaluationRequest, MockInterviewRequest
from backend.services.interview_llm_service import generate_interview_questions_by_llm
from backend.services.interview_signal_service import build_interview_questions


def generate_mock_interview(payload: MockInterviewRequest) -> dict:
    profile = user_profile_repository.get_user_profile(payload.user_id)
    if profile is None:
        raise AppError(
            error="USER_PROFILE_NOT_FOUND",
            message="用户画像不存在，请先保存用户画像",
            status_code=404,
        )

    job = job_repository.get_job_by_id(payload.job_id)
    if job is None:
        raise AppError(
            error="JOB_NOT_FOUND",
            message="岗位不存在",
            status_code=404,
        )

    job_skills = _get_job_skill_names(payload.job_id)
    requirement = job.get("requirement_json") or {}
    questions = _generate_questions(
        profile=profile,
        job=job,
        job_skills=job_skills,
        requirement=requirement,
        difficulty=payload.difficulty,
    )

    session = interview_repository.create_interview_session(
        user_id=payload.user_id,
        job_id=payload.job_id,
        difficulty=payload.difficulty,
        questions=questions,
    )

    return {
        **session,
        "job_title": job["title"],
        "company_name": job["company_name"],
    }


def _generate_questions(
    profile: dict,
    job: dict,
    job_skills: list[str],
    requirement: dict,
    difficulty: str,
) -> list[dict]:
    try:
        return generate_interview_questions_by_llm(
            profile=profile,
            job=job,
            job_skills=job_skills,
            requirement=requirement,
            difficulty=difficulty,
        )
    except AppError:
        return build_interview_questions(
            profile=profile,
            job=job,
            job_skills=job_skills,
            requirement=requirement,
            difficulty=difficulty,
        )


def evaluate_answer(payload: AnswerEvaluationRequest) -> dict:
    session = interview_repository.get_interview_session(payload.session_id)
    if session is None:
        raise AppError(
            error="INTERVIEW_SESSION_NOT_FOUND",
            message="面试会话不存在，请先生成模拟面试题",
            status_code=404,
        )

    session_questions = [item.get("question", "") for item in session.get("questions", [])]
    if payload.question not in session_questions:
        raise AppError(
            error="QUESTION_NOT_IN_SESSION",
            message="该问题不属于当前面试会话",
            status_code=400,
        )

    evaluation = _score_answer(payload.question, payload.user_answer)
    return interview_repository.create_answer_evaluation(
        session_id=payload.session_id,
        question=payload.question,
        user_answer=payload.user_answer,
        score=evaluation["score"],
        dimension_scores=evaluation["dimension_scores"],
        strengths=evaluation["strengths"],
        weaknesses=evaluation["weaknesses"],
        improved_answer=evaluation["improved_answer"],
        follow_up_questions=evaluation["follow_up_questions"],
    )


def _get_job_skill_names(job_id: int) -> list[str]:
    for job in job_repository.list_jobs_with_skills():
        if job["job_id"] == job_id:
            return _unique([skill["skill_name"] for skill in job.get("skills", [])])
    return []


def _score_answer(question: str, answer: str) -> dict:
    answer_text = answer.lower()
    length = len(answer.strip())

    dimension_scores = {
        "accuracy": _score_by_keywords(
            answer_text,
            ["原因", "因为", "方案", "实现", "数据", "接口", "数据库", "验证", "日志", "trace"],
        ),
        "completeness": _score_completeness(length),
        "project_relevance": _score_by_keywords(
            answer_text,
            ["项目", "我负责", "我实现", "业务", "用户", "流程", "结果", "指标"],
        ),
        "clarity": _score_by_keywords(
            answer_text,
            ["首先", "然后", "最后", "第一", "第二", "第三", "输入", "输出"],
        ),
        "engineering_thinking": _score_by_keywords(
            answer_text,
            ["异常", "错误", "边界", "日志", "trace", "测试", "评估", "安全", "幂等", "重复"],
        ),
    }
    score = round(sum(dimension_scores.values()) / len(dimension_scores))
    strengths = _build_strengths(dimension_scores)
    weaknesses = _build_weaknesses(dimension_scores, length)

    return {
        "score": score,
        "dimension_scores": dimension_scores,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "improved_answer": _build_improved_answer(question, answer, weaknesses),
        "follow_up_questions": _build_follow_up_questions(question, dimension_scores),
    }


def _score_by_keywords(answer_text: str, keywords: list[str]) -> int:
    hits = sum(1 for keyword in keywords if keyword.lower() in answer_text)
    if hits >= 5:
        return 90
    if hits >= 3:
        return 75
    if hits >= 1:
        return 60
    return 40


def _score_completeness(length: int) -> int:
    if length >= 260:
        return 90
    if length >= 160:
        return 75
    if length >= 80:
        return 60
    return 40


def _build_strengths(dimension_scores: dict[str, int]) -> list[str]:
    labels = {
        "accuracy": "回答中出现了较明确的技术判断或实现依据",
        "completeness": "回答长度和信息量基本支撑一次面试表达",
        "project_relevance": "能够把回答和个人项目经历关联起来",
        "clarity": "表达有一定结构，便于面试官继续追问",
        "engineering_thinking": "体现了日志、测试、异常或安全等工程意识",
    }
    strengths = [labels[key] for key, value in dimension_scores.items() if value >= 75]
    return strengths or ["回答已经覆盖问题本身，但还需要补充更具体的项目证据"]


def _build_weaknesses(dimension_scores: dict[str, int], length: int) -> list[str]:
    labels = {
        "accuracy": "技术依据不够具体，容易被继续追问实现细节",
        "completeness": "回答信息量偏少，需要补充背景、方案、结果和复盘",
        "project_relevance": "和个人项目结合不够明显，建议加入自己负责的模块",
        "clarity": "表达结构还可以更清楚，建议按背景、方案、结果组织",
        "engineering_thinking": "工程化考虑不足，建议补充异常处理、日志、测试和验证方式",
    }
    weaknesses = [labels[key] for key, value in dimension_scores.items() if value < 75]
    if length < 80 and "回答信息量偏少，需要补充背景、方案、结果和复盘" not in weaknesses:
        weaknesses.append("回答信息量偏少，需要补充背景、方案、结果和复盘")
    return weaknesses or ["回答整体较完整，下一步可以准备更深入的技术追问"]


def _build_improved_answer(question: str, answer: str, weaknesses: list[str]) -> str:
    return (
        "可以按这个结构改进：先用一句话回答问题结论；再说明项目背景和自己负责的模块；"
        "然后展开核心实现，包括接口、数据流、数据库表、工具调用或模型调用；"
        "接着补充异常处理、日志 Trace、测试或评估方式；最后说明结果和后续优化。"
        f" 当前这题的重点是：{question}"
    )


def _build_follow_up_questions(question: str, dimension_scores: dict[str, int]) -> list[str]:
    follow_ups = [
        "如果这个方案线上失败，你会先看哪些日志或 Trace？",
        "这个实现里 MySQL 表结构和接口边界是怎么设计的？",
        "你怎么证明这个回答里提到的方案真的有效？",
    ]
    if dimension_scores.get("project_relevance", 0) < 75:
        follow_ups.insert(0, "这部分你在项目中具体负责了哪一块？")
    if dimension_scores.get("engineering_thinking", 0) < 75:
        follow_ups.insert(0, "如果出现重复请求或脏数据，你会怎么处理？")
    return _unique(follow_ups)[:3]


def _unique(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        item = value.strip()
        key = item.lower()
        if item and key not in seen:
            result.append(item)
            seen.add(key)
    return result
