import ast
import json
import os
import sys
from typing import Any

from cozepy import (
    COZE_CN_BASE_URL,
    ChatStatus,
    Coze,
    Message,
    MessageContentType,
    TokenAuth,
)


def recursive_json_loads(data: Any, max_depth: int = 10) -> Any:
    """
    一键式递归JSON解析函数

    Args:
        data: 要解析的数据，可以是字符串、字典、列表等
        max_depth: 最大递归深度，防止无限递归

    Returns:
        完全解析后的Python对象
    """
    depth = 0

    def _parse(obj, current_depth):
        nonlocal depth
        depth = current_depth

        if depth > max_depth:
            return obj

        # 如果是字符串，尝试解析
        if isinstance(obj, str):
            obj = obj.strip()

            # 快速判断是否是JSON格式
            if len(obj) >= 2 and (
                (obj.startswith("{") and obj.endswith("}"))
                or (obj.startswith("[") and obj.endswith("]"))
            ):
                # 尝试标准JSON解析
                try:
                    parsed = json.loads(obj)
                    return _parse(parsed, current_depth + 1)
                except json.JSONDecodeError:
                    # 尝试Python字面量
                    try:
                        parsed = ast.literal_eval(obj)
                        return _parse(parsed, current_depth + 1)
                    except (ValueError, SyntaxError):
                        return obj
            return obj

        # 如果是字典，递归处理值
        elif isinstance(obj, dict):
            return {k: _parse(v, current_depth + 1) for k, v in obj.items()}

        # 如果是列表，递归处理元素
        elif isinstance(obj, list):
            return [_parse(item, current_depth + 1) for item in obj]

        # 其他类型直接返回
        return obj

    return _parse(data, 0)


def run_coze_workflow(request_info: dict | None = None) -> dict:
    """
    运行 Coze 内容审核工作流。

    Args:
        request_info: 传入工作流的参数字典，默认为空。

    Returns:
        解析后的审核结果字典。

    Raises:
        ValueError: COZE_API_TOKEN 环境变量未设置。
        RuntimeError: Coze API 调用失败。
    """
    # 从环境变量读取 Coze API Token，避免硬编码敏感信息
    coze_api_token = os.environ.get("COZE_API_TOKEN", "")
    if not coze_api_token:
        raise ValueError(
            "COZE_API_TOKEN 环境变量未设置。请在运行前执行：\n"
            "  export COZE_API_TOKEN='your_token_here'  (macOS/Linux)\n"
            "  set COZE_API_TOKEN=your_token_here       (Windows CMD)\n"
            "  $env:COZE_API_TOKEN='your_token_here'    (PowerShell)"
        )

    coze = Coze(
        auth=TokenAuth(token=coze_api_token),
        base_url=COZE_CN_BASE_URL,
    )

    workflow_id = "7525739855999352832"
    payload = request_info if request_info is not None else {}

    try:
        workflow = coze.workflows.runs.create(
            workflow_id=workflow_id, parameters={"input": payload}
        )
    except Exception as exc:
        raise RuntimeError(f"Coze 工作流调用失败: {exc}") from exc

    return recursive_json_loads(workflow.data)


def main() -> int:
    """CLI 入口。"""
    try:
        result = run_coze_workflow()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ValueError as exc:
        print(f"[配置错误] {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"[运行时错误] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
