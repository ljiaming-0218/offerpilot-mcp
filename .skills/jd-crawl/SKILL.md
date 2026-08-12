# jd-crawl

## 适用场景
用户提供公开岗位 URL，希望采集岗位 JD。

## 触发关键词
采集、抓取、爬取、岗位链接、URL、招聘页面

## 输入格式
公开可访问的岗位详情页 URL。

## 执行步骤
1. 检查 URL 是否为公开页面。
2. 调用 crawl_job_url 工具。
3. 保存 source_url 和岗位正文。
4. 如果用户同时要求分析岗位，则使用采集结果返回的 job_id 调用 extract_skills。
5. 返回采集状态、岗位信息和可选的岗位要求分析。

## 可调用工具
- crawl_job_url
- extract_skills

## 输出格式
返回采集状态、岗位 ID、岗位标题、公司、城市和 source_url。

## 质量检查
1. 不采集登录页、验证码页、隐私数据。
2. 保留 source_url。
3. 失败时返回错误原因。
4. extract_skills 只能使用本次采集返回的 job_id，不能由模型编造。

## 失败处理
如果网页无法访问或解析失败，返回 CRAWL_FAILED。
