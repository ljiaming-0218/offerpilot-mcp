from bs4 import BeautifulSoup


def parse_job_page(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = _extract_title(soup)
    text = _extract_text(soup)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    return {
        "title": title,
        "company_name": _extract_company_name(lines),
        "city": _extract_city(lines, title),
        "job_type": _extract_job_type(lines, title),
        "description": text,
    }


def _extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(" ", strip=True)
        if title:
            return title

    if soup.title:
        title = soup.title.get_text(" ", strip=True)
        if title:
            return title[:120]

    return "未识别岗位标题"


def _extract_text(soup: BeautifulSoup) -> str:
    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    merged = "\n".join(lines)

    return merged[:8000]


def _extract_company_name(lines: list[str]) -> str | None:
    for index, line in enumerate(lines):
        if line == "职位来源" and index + 1 < len(lines):
            company = lines[index + 1].strip()
            if company:
                return company[:120]

    company_suffixes = ("有限公司", "股份有限公司", "集团", "研究院", "科技公司")
    for line in lines:
        if any(suffix in line for suffix in company_suffixes):
            return line[:120]

    return None


def _extract_city(lines: list[str], title: str) -> str | None:
    city_candidates = {
        "北京", "上海", "广州", "深圳", "成都", "杭州", "武汉", "南京", "苏州",
        "天津", "重庆", "西安", "长沙", "合肥", "厦门", "青岛", "郑州", "宁波",
        "东莞", "佛山", "惠州",
    }

    for index, line in enumerate(lines):
        if line == title and index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            if _looks_like_city(next_line, city_candidates):
                return next_line[:80]

    for line in lines[:80]:
        if _looks_like_city(line, city_candidates):
            return line[:80]

    return None


def _extract_job_type(lines: list[str], title: str) -> str | None:
    text = "\n".join(lines[:120])
    if "校招" in title or "校招" in text or "校园招聘" in text:
        return "校招"
    if "实习" in title or "实习生" in text:
        return "实习"
    if "社招" in title or "社招" in text:
        return "社招"
    return None


def _looks_like_city(value: str, city_candidates: set[str]) -> bool:
    if not value or len(value) > 40:
        return False
    parts = value.replace("、", "/").split("/")
    return all(part in city_candidates for part in parts if part)
