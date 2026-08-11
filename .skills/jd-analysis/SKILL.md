# jd-analysis

## 适用场景
用户希望分析岗位 JD、抽取技能、判断岗位方向。

## 触发关键词
分析岗位、JD 分析、提取技能、技能标签、岗位要求

## 输入格式
岗位 ID 或岗位 JD 文本。

## 执行步骤
1. 读取岗位详情。
2. 调用 extract_skills 工具。
3. 将技能写入 skills 和 job_skills。
4. 返回技能列表、岗位方向、难度和摘要。

## 可调用工具
- extract_skills
- list_skills

## 输出格式
返回岗位 ID、技能列表、岗位方向、难度和摘要。

## 质量检查
1. 不抽取 JD 中没有依据的技能。
2. 同一技能不重复创建。
3. 技能重要性限定为 high / medium / low。

## 失败处理
如果未识别到技能，返回 NO_SKILLS_EXTRACTED。