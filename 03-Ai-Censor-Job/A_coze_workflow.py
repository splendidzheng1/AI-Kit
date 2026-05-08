import ast
import json
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


coze_api_token = ""
coze_api_base = COZE_CN_BASE_URL

coze = Coze(auth=TokenAuth(token=coze_api_token), base_url=coze_api_base)

workflow_id = "7525739855999352832"
dict_request_info = {}
workflow = coze.workflows.runs.create(
    workflow_id=workflow_id, parameters={"input": dict_request_info}
)

dict_censor_data = recursive_json_loads(workflow.data)
