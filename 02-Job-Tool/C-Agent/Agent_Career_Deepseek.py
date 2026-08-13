"""
Career Agent — 根据招聘信息为求职者筛选岗位，支持 DeepSeek 联网搜索公司舆论。

用法:
    cp .env.example .env   # 填入 DEEPSEEK_API_KEY
    python Agent_Career_Deepseek.py                        # 使用 career_input_template.json
    python Agent_Career_Deepseek.py career_input.json      # 从 JSON 文件读取用户数据
    python Agent_Career_Deepseek.py --massive              # 3次独立评分取平均 + 汇总警告
    python Agent_Career_Deepseek.py --massive data.json    # massive 模式 + 指定文件

依赖: pip install openai>=1.0 python-dotenv
文档: https://api-docs.deepseek.com/zh-cn/guides/responses_api
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

_DIR = Path(__file__).resolve().parent
load_dotenv(_DIR / ".env")

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-v4-flash"  # 备选: deepseek-v4-pro

RESPONSE_JSON_SCHEMA = """{
  "output": {
    "total_score": 85,
    "job_score": {
      "score": 40,
      "alert": "工作要求掌握k8s开发技能，与应聘者能力可能不符合"
    },
    "company_score": {
      "score": -15,
      "alert": "网络上的舆情较差，集中在以下几点：1、领导恶心，2、拖欠工资"
    }
  }
}"""

DEFAULT_INPUT_FILE = _DIR / "career_input_template.json"

SYSTEM_PROMPT = f"""# 角色设定

你是资深的职业生涯规划师，要根据用户输入的招聘信息，严格按照执行步骤为求职者筛选工作，一定要有输出内容。

# 硬性过滤器（红线：触发任意一条 → 所有评分直接归零）

- 学历要求博士生及以上
- 工作时间要求五年及以上
- 最高薪资低于8000
- 明确只有单休
- 工作信息中明确出现"要求加班或加班多",并且没有说明有加班费

# 评分规则

基础分：50 分。
依次检查加分项表和减分项表中的每一项，若命中，由你根据实际情况自主判断该命中的影响程度，并按以下档位计分：

| 影响程度 | 加分  | 减分  |
| ---- | --- | --- |
| 高    | +15 | -15 |
| 中    | +10 | -10 |
| 低    | +5  | -5  |

最终总分 = 50 + 加分合计 - 减分合计。

说明：
- job_score.score 为岗位相关加分项合计减去岗位相关减分项合计（不含基础分50）
- company_score.score 为公司相关加分项合计减去公司相关减分项合计（不含基础分50）
- total_score 为最终总分；若触发硬性过滤器则为 0

# 加分项表

| 序号 | 类别 | 检查项            |
| -- | -- | -------------- |
| 1  | 岗位 | 薪资达到或超出期望范围    |
| 2  | 岗位 | 福利完善（五险一金、补贴等） |
| 3  | 岗位 | 技能要求与求职者高度匹配   |
| 4  | 岗位 | 岗位有明确晋升或发展路径   |
| 5  | 岗位 | 通勤便利或可远程办公     |
| 6  | 公司 | 公司规模大或行业头部     |
| 7  | 公司 | 所属领域热门或前景好     |
| 8  | 公司 | 网上舆论评价良好       |
| 9  | 公司 | 工作描述中提及重视员工发展  |
| 10 | 公司 | 有加班费或明确不加班     |

# 减分项表

| 序号 | 类别 | 检查项            |
| -- | -- | -------------- |
| 1  | 岗位 | 薪资明显低于期望范围     |
| 2  | 岗位 | 福利缺失（无五险一金等）   |
| 3  | 岗位 | 技能要求与求职者明显不匹配  |
| 4  | 岗位 | 岗位职责模糊或过于宽泛    |
| 5  | 岗位 | 频繁加班且无加班费      |
| 6  | 公司 | 公司规模过小或初创风险高   |
| 7  | 公司 | 行业下行或前景堪忧      |
| 8  | 公司 | 网上差评较多（超过10条）  |
| 9  | 公司 | 网上有拖欠工资或劳动纠纷记录 |
| 10 | 公司 | 办公地点偏远或通勤不便    |

# 执行步骤

第一步：检查是否触发硬性过滤器。若触发任意一条，则所有分数归零，直接跳到最后一步输出。
第二步：若未触发硬性过滤器，必须先调用联网搜索工具，获取该公司网上舆论、员工评价、劳动纠纷等信息，再进入第三步。禁止在未搜索的情况下对公司舆论相关项（加分项8、减分项8/9等）进行评分。
第三步：对照加分项表和减分项表，逐一判断是否命中。对每个命中项，由你自主判断影响程度（高/中/低），并对应记分（±15/±10/±5）。
第四步：计算总分：总分 = 50 + 加分合计 - 减分合计。
第五步：按 JSON Schema 格式输出结果。

# 输出要求（必须严格遵守）

1. 最终回复必须是且仅是合法 JSON 对象字符串，不要输出 Markdown、代码块或任何 JSON 以外的文字
2. 字段名必须与下方 JSON Schema 完全一致
3. alert 字段用中文简要说明评分依据，无问题时可写"无明显问题"
4. 若触发硬性过滤器，total_score、job_score.score、company_score.score 均为 0，并在 alert 中说明触发的红线

# JSON Schema

{RESPONSE_JSON_SCHEMA}"""

WEB_SEARCH_TOOL = {"type": "web_search"}

SEARCH_NUDGE = (
    "你尚未完成第二步：必须先调用联网搜索工具搜索该公司网上舆论与员工评价信息，"
    "再对照加分/减分项评分并输出 JSON。请立即执行搜索。"
)

MASSIVE_ROUNDS = 3

_SUMMARY_SYSTEM_PROMPT = """你是一个评分汇总助手。下面是对同一份招聘信息进行的多次独立评分结果，每次评分包含岗位维度和公司维度的警告说明（alert）。

请将多次评分的警告说明进行汇总归纳：
1. 去除重复内容
2. 保留所有重要信息
3. 合并相似观点
4. 用中文输出统一的警告说明

输出格式必须是 JSON：
{"job_alert": "岗位维度统一警告说明", "company_alert": "公司维度统一警告说明"}"""


class TokenUsage:
    def __init__(self):
        self.prompt_tokens = 0
        self.search_tokens = 0
        self.completion_tokens = 0

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.search_tokens + self.completion_tokens


class CareerResponse:
    def __init__(self, answer, answer_raw, usage, search_info=None, reasoning=None):
        self.answer = answer
        self.answer_raw = answer_raw
        self.usage = usage
        self.search_info = search_info or []
        self.reasoning = reasoning or []


def _parse_user_json(raw):
    """解析用户输入的 JSON 数据。"""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"用户输入不是合法 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON 根节点必须是对象，实际为: {type(data).__name__}")
    return data


def _validate_user_data(data):
    """校验用户 JSON 结构。"""
    for key in ("recruit", "company", "worker"):
        if key not in data:
            raise ValueError(f"缺少必需字段: {key}")
        if not isinstance(data[key], dict):
            raise ValueError(f"字段 {key} 必须是对象")
    company_name = data["company"].get("company_name", "").strip()
    if not company_name:
        raise ValueError("company.company_name 不能为空（用于联网搜索舆论）")


def build_prompt_from_input(data):
    """将用户 JSON 拼装为发给大模型的提示词。"""
    _validate_user_data(data)
    recruit = data["recruit"]
    company = data["company"]
    worker = data["worker"]

    return "\n".join(
        [
            "请根据以下求职者与招聘信息进行岗位筛选评分。",
            "",
            "## 求职者信息",
            f"- 期望薪资：{worker.get('worker_salary', '')}",
            f"- 技能与经历：{worker.get('worker_skill', '')}",
            f"- 求职方向：{worker.get('worker_direction', '')}",
            "",
            "## 公司信息",
            f"- 公司名称：{company.get('company_name', '')}",
            f"- 公司概况：{company.get('company_base', '')}",
            f"- 公司详情：{company.get('company_detail', '')}",
            "",
            "## 招聘信息",
            f"- 薪资待遇：{recruit.get('recruit_salary', '')}",
            f"- 福利待遇：{recruit.get('recruit_welfare', '')}",
            f"- 技能/岗位要求：{recruit.get('recruit_requirment', '')}",
            f"- 岗位详情：{recruit.get('recruit_detail', '')}",
        ]
    )


def _repair_json(text):
    """尝试修复 LLM 输出中常见的 JSON 格式问题。

    目前处理：缺少闭合括号（} 和 ]）。
    通过统计字符串内（非引号内）的括号差值，在末尾补齐缺失的闭合符号。
    """
    # 统计引号外的括号配对情况
    in_string = False
    escape = False
    stack = []

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()

    # 根据未闭合的括号补齐
    closing_map = {"{": "}", "[": "]"}
    suffix = "".join(closing_map[c] for c in reversed(stack))
    if suffix:
        text = text + suffix
    return text


def _parse_answer_json(raw):
    """解析模型返回的 JSON 字符串，带自动修复能力。"""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        # 尝试修复常见的 JSON 格式问题（如缺少闭合括号）
        repaired = _repair_json(text)
        if repaired != text:
            try:
                data = json.loads(repaired)
            except json.JSONDecodeError as exc2:
                raise ValueError(
                    f"模型返回的不是合法 JSON（修复后仍失败）: {exc2}\n原始内容: {raw}"
                ) from exc2
        else:
            raise ValueError(
                f"模型返回的不是合法 JSON: {exc}\n原始内容: {raw}"
            ) from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON 根节点必须是对象，实际为: {type(data).__name__}")
    return data


def _hard_filter_skip_search(answer):
    """硬性过滤器触发时允许跳过搜索直接输出（total_score 为 0）。"""
    output = answer.get("output")
    if not isinstance(output, dict):
        return False
    return output.get("total_score") == 0


def _validate_answer_fields(answer):
    """检查解析后的 JSON 是否包含所有必需的评分字段。

    返回缺失的字段名列表，空列表表示完整。
    """
    missing = []
    output = answer.get("output")
    if not isinstance(output, dict):
        return ["output"]
    if "total_score" not in output:
        missing.append("total_score")
    job = output.get("job_score")
    if not isinstance(job, dict) or "score" not in job:
        missing.append("job_score.score")
    company = output.get("company_score")
    if not isinstance(company, dict) or "score" not in company:
        missing.append("company_score.score")
    return missing


def _format_search_record(record, index):
    """格式化单条联网搜索记录。

    DeepSeek web_search_call 的实际结构：
    - type = "search"    → queries: [str, ...]（搜索关键词列表）
    - type = "open_page" → url: str（打开的网页地址）
    - status: completed / failed / ...
    搜索结果正文由服务端内部喂给模型，API 不返回给客户端。
    """
    action_type = record.get("type", "unknown")
    lines = [f"--- 搜索 #{index + 1} ({action_type}) ---"]

    if action_type == "search":
        queries = record.get("queries", [])
        if queries:
            lines.append(f"搜索关键词: {', '.join(queries)}")
        else:
            lines.append("搜索关键词: (未获取到)")
    elif action_type == "open_page":
        url = record.get("url", "")
        lines.append(f"打开网页: {url}")
    else:
        lines.append(f"原始数据: {json.dumps(record, ensure_ascii=False)}")

    lines.append(f"状态: {record.get('status', 'unknown')}")
    return "\n".join(lines)


def _get_client():
    """创建 DeepSeek OpenAI 兼容客户端。"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误: 未找到 DEEPSEEK_API_KEY")
        print(f"  请复制 {_DIR / '.env.example'} 为 {_DIR / '.env'} 并填入密钥")
        sys.exit(1)
    return OpenAI(api_key=api_key, base_url=BASE_URL)


def _create_response(client, input_items):
    """调用 DeepSeek Responses API。"""
    return client.responses.create(
        model=MODEL,
        instructions=SYSTEM_PROMPT,
        input=input_items,
        tools=[WEB_SEARCH_TOOL],
        text={"format": {"type": "json_object"}},
        max_output_tokens=32768,
    )


def _accumulate_api_usage(usage, response):
    """累计 Responses API 返回的 token 用量。

    DeepSeek Responses API 的 usage 中：
    - input_tokens：输入 token（含联网搜索结果）
    - output_tokens：模型输出 token
    DeepSeek 没有 search_tokens 概念，搜索 token 已包含在 input_tokens 中。
    """
    if response.usage:
        usage.prompt_tokens += response.usage.input_tokens or 0
        usage.completion_tokens += response.usage.output_tokens or 0


def _extract_search_info(search_info, response):
    """从 Responses API 的输出中提取联网搜索记录。

    DeepSeek web_search_call 的实际结构：
    - action.type = "search"    → action.queries: [str, ...]
    - action.type = "open_page" → action.url: str
    - status: "completed" / "failed" / ...
    搜索结果正文由服务端内部喂给模型，API 不返回给客户端。
    """
    for item in (response.output or []):
        if not (hasattr(item, "type") and item.type == "web_search_call"):
            continue

        record = {"type": "unknown", "status": "unknown", "queries": [], "url": ""}

        dumped = {}
        if hasattr(item, "model_dump"):
            try:
                dumped = item.model_dump() or {}
            except Exception:
                pass

        # 提取 action 信息
        action = getattr(item, "action", None) or dumped.get("action") or {}
        if isinstance(action, dict):
            action_type = action.get("type", "unknown")
            record["type"] = action_type
            if action_type == "search":
                queries = action.get("queries") or []
                if not queries and action.get("query"):
                    queries = [action["query"]]
                record["queries"] = list(queries)
            elif action_type == "open_page":
                record["url"] = action.get("url", "")
        else:
            # action 可能是 Pydantic 模型对象
            action_type = getattr(action, "type", None) or "unknown"
            record["type"] = action_type
            if action_type == "search":
                queries = getattr(action, "queries", None) or []
                if not queries and getattr(action, "query", None):
                    queries = [action.query]
                record["queries"] = list(queries) if queries else []
            elif action_type == "open_page":
                record["url"] = getattr(action, "url", "")

        # 提取状态
        status = getattr(item, "status", None) or dumped.get("status", "")
        record["status"] = status or "unknown"

        search_info.append(record)


def _extract_reasoning(reasoning_list, response):
    """从 Responses API 的输出中提取模型推理过程。

    DeepSeek reasoning 输出项的结构可能是：
    - summary: [{type: "summary_text", text: "..."}, ...]
    - content: [{type: "reasoning_text", text: "..."}, ...]
    - 或直接 text 属性
    """
    for item in (response.output or []):
        if not (hasattr(item, "type") and item.type == "reasoning"):
            continue

        dumped = {}
        if hasattr(item, "model_dump"):
            try:
                dumped = item.model_dump() or {}
            except Exception:
                pass

        texts = []

        # 方式1: summary 字段（列表，每项含 text）
        summary = getattr(item, "summary", None) or dumped.get("summary")
        if summary and isinstance(summary, list):
            for entry in summary:
                if isinstance(entry, dict):
                    t = entry.get("text", "")
                else:
                    t = getattr(entry, "text", "")
                if t:
                    texts.append(t)

        # 方式2: content 字段（列表，每项含 text）
        if not texts:
            content = getattr(item, "content", None) or dumped.get("content")
            if content and isinstance(content, list):
                for entry in content:
                    if isinstance(entry, dict):
                        t = entry.get("text", "")
                    else:
                        t = getattr(entry, "text", "")
                    if t:
                        texts.append(t)

        # 方式3: 直接 text 属性
        if not texts:
            t = getattr(item, "text", None) or dumped.get("text", "")
            if t:
                texts.append(t)

        if texts:
            reasoning_list.append("\n".join(texts))


def ask(data):
    """单轮对话：根据用户 JSON 数据筛选岗位（DeepSeek Responses API，服务端自动联网搜索）。"""
    user_prompt = build_prompt_from_input(data)
    client = _get_client()

    usage = TokenUsage()
    search_info = []
    reasoning = []

    # 初始 input：只有 user 消息（system prompt 通过 instructions 参数传入）
    input_items = [{"role": "user", "content": user_prompt}]

    # 第一次调用：服务端自动决定是否联网搜索
    response = _create_response(client, input_items)
    _accumulate_api_usage(usage, response)
    _extract_search_info(search_info, response)
    _extract_reasoning(reasoning, response)

    search_called = len(search_info) > 0

    # 如果没有搜索且不是硬性过滤器触发，发送 nudge 再调一次，促使模型联网搜索
    if not search_called:
        answer_text = response.output_text or ""
        try:
            parsed = _parse_answer_json(answer_text)
            if not _hard_filter_skip_search(parsed):
                # 把上一轮的 output items 原样传回 + nudge 消息
                input_items = list(response.output) + [
                    {"role": "user", "content": SEARCH_NUDGE}
                ]
                response = _create_response(client, input_items)
                _accumulate_api_usage(usage, response)
                _extract_search_info(search_info, response)
                _extract_reasoning(reasoning, response)
        except ValueError:
            pass

    answer_raw = response.output_text or ""
    parsed = _parse_answer_json(answer_raw)

    # 字段完整性校验：如果必需字段缺失（通常是 JSON 被截断），重试一次
    missing = _validate_answer_fields(parsed)
    if missing:
        retry_input = list(response.output) + [
            {"role": "user", "content": (
                f"你上次的输出缺少以下字段: {', '.join(missing)}。"
                "请重新输出完整的评分 JSON，确保包含 output.total_score、"
                "output.job_score.score、output.company_score.score。"
            )}
        ]
        response = _create_response(client, retry_input)
        _accumulate_api_usage(usage, response)
        _extract_search_info(search_info, response)
        _extract_reasoning(reasoning, response)
        answer_raw = response.output_text or ""
        parsed = _parse_answer_json(answer_raw)

    return CareerResponse(
        answer=parsed,
        answer_raw=answer_raw,
        usage=usage,
        search_info=search_info,
        reasoning=reasoning,
    )


def _summarize_alerts(results, usage):
    """将多次评分的 alert 汇总为统一说明（额外消耗一次 API 调用）。"""
    client = _get_client()

    rounds_text = []
    for i, r in enumerate(results):
        output = r.answer.get("output", {})
        job_alert = output.get("job_score", {}).get("alert", "")
        company_alert = output.get("company_score", {}).get("alert", "")
        rounds_text.append(
            f"第{i + 1}次评分：\n岗位alert: {job_alert}\n公司alert: {company_alert}"
        )

    user_content = "\n\n".join(rounds_text)

    response = client.responses.create(
        model=MODEL,
        instructions=_SUMMARY_SYSTEM_PROMPT,
        input=[{"role": "user", "content": user_content}],
        text={"format": {"type": "json_object"}},
        max_output_tokens=8192,
    )
    _accumulate_api_usage(usage, response)

    raw = response.output_text or ""
    parsed = _parse_answer_json(raw)
    return parsed.get("job_alert", ""), parsed.get("company_alert", "")


def ask_massive(data, rounds=MASSIVE_ROUNDS):
    """多次评分取平均，alert 统一汇总（massive 模式）。

    流程：
    1. 独立调用 ask() N 次，每次都联网搜索 + 评分
    2. 三次分数取平均（四舍五入取整）
    3. 额外调一次 API 将三次的 alert 汇总为统一说明
    """
    results = []
    for i in range(rounds):
        print(f"  第 {i + 1}/{rounds} 次评分中...")
        r = ask(data)
        results.append(r)
        output = r.answer.get("output", {})
        print(
            f"    总分: {output.get('total_score', '?')}, "
            f"岗位: {output.get('job_score', {}).get('score', '?')}, "
            f"公司: {output.get('company_score', {}).get('score', '?')}"
        )

    # 计算平均分（只统计字段完整的轮次）
    total_scores = []
    job_scores = []
    company_scores = []
    valid_rounds = 0
    for r in results:
        output = r.answer.get("output", {})
        if not isinstance(output, dict):
            continue
        t = output.get("total_score")
        j = output.get("job_score", {}).get("score") if isinstance(output.get("job_score"), dict) else None
        c = output.get("company_score", {}).get("score") if isinstance(output.get("company_score"), dict) else None
        if t is not None and j is not None and c is not None:
            total_scores.append(t)
            job_scores.append(j)
            company_scores.append(c)
            valid_rounds += 1

    if valid_rounds == 0:
        raise ValueError("所有轮次的评分结果均不完整，无法计算平均分")

    avg_total = round(sum(total_scores) / valid_rounds)
    avg_job = round(sum(job_scores) / valid_rounds)
    avg_company = round(sum(company_scores) / valid_rounds)

    # 合并 token 用量
    merged_usage = TokenUsage()
    for r in results:
        merged_usage.prompt_tokens += r.usage.prompt_tokens
        merged_usage.completion_tokens += r.usage.completion_tokens

    # 汇总 alert
    print(f"  汇总警告说明中...")
    job_alert, company_alert = _summarize_alerts(results, merged_usage)

    # 合并 search_info 和 reasoning（标注轮次）
    merged_search = []
    merged_reasoning = []
    for i, r in enumerate(results):
        merged_search.extend(r.search_info)
        for text in r.reasoning:
            merged_reasoning.append(f"[第{i + 1}轮]\n{text}")

    # 构建合并的 answer
    merged_answer = {
        "output": {
            "total_score": avg_total,
            "job_score": {"score": avg_job, "alert": job_alert},
            "company_score": {"score": avg_company, "alert": company_alert},
        }
    }

    return CareerResponse(
        answer=merged_answer,
        answer_raw=json.dumps(merged_answer, ensure_ascii=False, indent=2),
        usage=merged_usage,
        search_info=merged_search,
        reasoning=merged_reasoning,
    )


def _read_user_data(input_file=None):
    """读取用户 JSON 数据（文件或默认模板）。"""
    if input_file:
        path = Path(input_file)
        if not path.is_file():
            print(f"错误: 文件不存在: {path}")
            sys.exit(1)
        raw = path.read_text(encoding="utf-8")
    elif DEFAULT_INPUT_FILE.is_file():
        raw = DEFAULT_INPUT_FILE.read_text(encoding="utf-8")
    else:
        print("请粘贴 JSON 数据，输入完成后单独一行输入 END：")
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line.strip().upper() == "END":
                break
            lines.append(line)
        raw = "\n".join(lines)
        if not raw.strip():
            print("输入不能为空。")
            sys.exit(1)

    try:
        data = _parse_user_json(raw)
        _validate_user_data(data)
    except ValueError as exc:
        print(f"错误: {exc}")
        sys.exit(1)
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Career Agent — DeepSeek Responses API 岗位筛选评分"
    )
    parser.add_argument(
        "input_file", nargs="?", default=None,
        help="输入 JSON 文件路径（默认使用 career_input_template.json）",
    )
    parser.add_argument(
        "--massive", action="store_true",
        help=f"多次评分取平均模式（{MASSIVE_ROUNDS} 次独立评分，取平均分 + 汇总警告）",
    )
    args = parser.parse_args()

    data = _read_user_data(args.input_file)

    if args.massive:
        print(f"\n massive 模式：{MASSIVE_ROUNDS} 次独立评分取平均，请稍候...\n")
        result = ask_massive(data)
    else:
        print("\n正在通过 DeepSeek 联网搜索公司舆论并评分，请稍候...\n")
        result = ask(data)

    output = result.answer.get("output", {})

    if args.massive:
        # massive 模式：精简输出，只显示平均分 + 汇总警告 + Token
        print("=" * 50)
        print(f"  平均总分: {output.get('total_score', '?')}")
        job = output.get("job_score", {})
        company = output.get("company_score", {})
        print(f"  岗位维度: {job.get('score', '?')}")
        print(f"  公司维度: {company.get('score', '?')}")
        print("=" * 50)
        if job.get("alert"):
            print(f"\n【岗位分析】\n{job['alert']}")
        if company.get("alert"):
            print(f"\n【公司分析】\n{company['alert']}")
        u = result.usage
        print(f"\nToken 消耗: {u.total_tokens}")
    else:
        # 普通模式：完整输出
        print(json.dumps(result.answer, ensure_ascii=False, indent=2))

        if "total_score" in output:
            print(f"\n岗位综合得分: {output['total_score']}")
            job = output.get("job_score", {})
            company = output.get("company_score", {})
            if job:
                print(f"岗位维度: {job.get('score')} — {job.get('alert', '')}")
            if company:
                print(f"公司维度: {company.get('score')} — {company.get('alert', '')}")

        print("\n--- 推理过程 ---")
        if result.reasoning:
            for i, text in enumerate(result.reasoning):
                print(f"\n[推理 {i + 1}]")
                print(text)
        else:
            print("（模型未输出推理过程）")

        print("\n--- 联网搜索信息 ---")
        if result.search_info:
            for i, record in enumerate(result.search_info):
                print(_format_search_record(record, i))
        else:
            print("（未执行搜索，可能触发了硬性过滤器）")

        u = result.usage
        print(
            f"\n--- Token 消耗 ---\n"
            f"prompt_tokens:     {u.prompt_tokens}\n"
            f"search_tokens:     {u.search_tokens}\n"
            f"completion_tokens: {u.completion_tokens}\n"
            f"total_tokens:      {u.total_tokens}"
        )


if __name__ == "__main__":
    main()
