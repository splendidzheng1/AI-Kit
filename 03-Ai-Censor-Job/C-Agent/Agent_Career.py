"""
Career Agent — 根据招聘信息为求职者筛选岗位，支持 Kimi 联网搜索公司舆论。

用法:
    cp .env.example .env   # 填入 MOONSHOT_API_KEY
    python Agent_Career.py                        # 使用 career_input_template.json
    python Agent_Career.py career_input.json      # 从 JSON 文件读取用户数据

依赖: pip install openai>=1.0 python-dotenv
文档: https://platform.kimi.com/docs/guide/use-web-search
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

_DIR = Path(__file__).resolve().parent
load_dotenv(_DIR / ".env")

BASE_URL = "https://api.moonshot.cn/v1"
MODEL = "kimi-k2.6"

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
第二步：若未触发硬性过滤器，必须先调用 $web_search 搜索工具，获取该公司网上舆论、员工评价、劳动纠纷等信息，再进入第三步。禁止在未搜索的情况下对公司舆论相关项（加分项8、减分项8/9等）进行评分。
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

WEB_SEARCH_TOOL = {
    "type": "builtin_function",
    "function": {"name": "$web_search"},
}

SEARCH_NUDGE = (
    "你尚未完成第二步：必须先调用 $web_search 搜索该公司网上舆论与员工评价信息，"
    "再对照加分/减分项评分并输出 JSON。请立即执行搜索。"
)


class TokenUsage:
    def __init__(self):
        self.prompt_tokens = 0
        self.search_tokens = 0
        self.completion_tokens = 0

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.search_tokens + self.completion_tokens


class CareerResponse:
    def __init__(self, answer, answer_raw, usage, search_info=None):
        self.answer = answer
        self.answer_raw = answer_raw
        self.usage = usage
        self.search_info = search_info or []


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


def _parse_answer_json(raw):
    """解析模型返回的 JSON 字符串。"""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"模型返回的不是合法 JSON: {exc}\n原始内容: {raw}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON 根节点必须是对象，实际为: {type(data).__name__}")
    return data


def _hard_filter_skip_search(answer):
    """硬性过滤器触发时允许跳过搜索直接输出（total_score 为 0）。"""
    output = answer.get("output")
    if not isinstance(output, dict):
        return False
    return output.get("total_score") == 0


def _get_client():
    api_key = os.environ.get("MOONSHOT_API_KEY")
    if not api_key:
        print("错误: 未找到 MOONSHOT_API_KEY")
        print(f"  请复制 {_DIR / '.env.example'} 为 {_DIR / '.env'} 并填入密钥")
        sys.exit(1)
    return OpenAI(api_key=api_key, base_url=BASE_URL)


def _search_impl(arguments):
    """Kimi 内置搜索：原样返回 arguments，由平台执行搜索。"""
    return arguments


def _chat(client, messages):
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=32768,
        response_format={"type": "json_object"},
        extra_body={"thinking": {"type": "disabled"}},
        tools=[WEB_SEARCH_TOOL],
    )


def _format_search_record(record, index):
    """格式化单条联网搜索记录，便于调试输出。"""
    lines = [f"--- 搜索 #{index + 1} ---"]
    args = record.get("arguments") or {}
    result = record.get("result") or {}

    for key in ("keyword", "query", "search_query"):
        if args.get(key):
            lines.append(f"关键词: {args[key]}")
            break

    search_result = (
        result.get("search_result")
        or args.get("search_result")
        or result.get("content")
        or args.get("content")
    )
    if search_result:
        if isinstance(search_result, str):
            lines.append(search_result)
        else:
            lines.append(json.dumps(search_result, ensure_ascii=False, indent=2))
    else:
        payload = result if result else args
        lines.append(json.dumps(payload, ensure_ascii=False, indent=2))

    return "\n".join(lines)


def _accumulate_api_usage(raw_prompt, usage, completion):
    """累计 API 返回的 prompt / completion tokens；返回更新后的 raw_prompt 累计值。"""
    if completion.usage:
        raw_prompt += completion.usage.prompt_tokens or 0
        usage.completion_tokens += completion.usage.completion_tokens or 0
    return raw_prompt


def ask(data):
    """单轮对话：根据用户 JSON 数据筛选岗位（内部可能多次调用 API 完成搜索）。"""
    user_prompt = build_prompt_from_input(data)
    client = _get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    usage = TokenUsage()
    raw_prompt = 0
    finish_reason = None
    choice = None
    search_called = False
    search_info = []

    while finish_reason is None or finish_reason == "tool_calls":
        completion = _chat(client, messages)
        choice = completion.choices[0]
        finish_reason = choice.finish_reason
        raw_prompt = _accumulate_api_usage(raw_prompt, usage, completion)

        if finish_reason == "tool_calls":
            msg = choice.message
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in (msg.tool_calls or [])
                    ],
                }
            )
            for tool_call in choice.message.tool_calls or []:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                if name == "$web_search":
                    search_called = True
                    result = _search_impl(args)
                    search_info.append(
                        {
                            "arguments": args,
                            "result": result,
                        }
                    )
                    usage.search_tokens += (
                        args.get("usage", {}).get("total_tokens") or 0
                    )
                else:
                    result = {"error": f"unknown tool: {name}"}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": name,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
            finish_reason = None
            continue

        if finish_reason == "stop" and not search_called:
            answer_raw = choice.message.content or ""
            try:
                parsed = _parse_answer_json(answer_raw)
                if _hard_filter_skip_search(parsed):
                    break
            except ValueError:
                pass
            messages.append({"role": "user", "content": SEARCH_NUDGE})
            finish_reason = None
            continue

        break

    usage.prompt_tokens = max(0, raw_prompt - usage.search_tokens)

    answer_raw = choice.message.content or ""
    return CareerResponse(
        answer=_parse_answer_json(answer_raw),
        answer_raw=answer_raw,
        usage=usage,
        search_info=search_info,
    )


def _read_user_data():
    """读取用户 JSON 数据（文件或默认模板）。"""
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
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
    data = _read_user_data()

    print("\n正在搜索公司舆论并评分，请稍候...\n")
    result = ask(data)
    print(json.dumps(result.answer, ensure_ascii=False, indent=2))

    output = result.answer.get("output", {})
    if "total_score" in output:
        print(f"\n岗位综合得分: {output['total_score']}")
        job = output.get("job_score", {})
        company = output.get("company_score", {})
        if job:
            print(f"岗位维度: {job.get('score')} — {job.get('alert', '')}")
        if company:
            print(f"公司维度: {company.get('score')} — {company.get('alert', '')}")

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
