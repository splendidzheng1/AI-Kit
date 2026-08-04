"""结果写入（按人即时增量更新）。"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


def ensure_parent(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def append_result(result_path: str, row: dict[str, str]) -> None:
    """每检测完一人立刻追加一行。"""
    p = ensure_parent(result_path)
    write_header = not p.exists()
    with p.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["index", "name", "status", "detail", "time"]
        )
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def load_deleted_names(path: str | Path) -> list[str]:
    """读取已有名单（跳过标题/人数行），保持原有顺序。"""
    p = Path(path)
    if not p.exists():
        return []
    names: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("疑似单删") or (s.startswith("共 ") and s.endswith(" 人")):
            continue
        if s not in names:
            names.append(s)
    return names


def write_deleted_list(path: str, names: list[str]) -> list[str]:
    """
    增量更新 deleted.txt：已有名字保留，未出现过的才追加。
    可在每人检测完后立刻调用（传入单元素列表即可）。
    返回本次实际新增的名字列表。
    """
    p = ensure_parent(path)
    existing = load_deleted_names(p)
    existing_set = set(existing)
    added = [n for n in names if n and n not in existing_set]
    if not added and p.exists():
        return []
    merged = existing + added
    lines = ["疑似单删/非好友名单", f"共 {len(merged)} 人", ""] + merged
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return added


def append_remove_result(result_path: str, row: dict[str, str]) -> None:
    """每清理完一人立刻追加一行。"""
    p = ensure_parent(result_path)
    write_header = not p.exists()
    with p.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["index", "name", "status", "detail", "time"]
        )
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def _load_purged_names(path: Path) -> set[str]:
    """从逐条记录里解析已删除过的名字。"""
    if not path.exists():
        return set()
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if "已删除：" not in s:
            continue
        name = s.rsplit("已删除：", 1)[-1].strip()
        if name:
            names.add(name)
    return names


def add_purged_friend_now(path: str, name: str) -> bool:
    """
    每成功删除一人立刻追加一条记录。
    返回 True 表示本次为新增。
    """
    if not name:
        return False
    p = ensure_parent(path)
    if name in _load_purged_names(p):
        return False
    now = datetime.now()
    stamp = (
        f"{now.year}年{now.month}月{now.day}日"
        f"{now.hour}时{now.minute}分{now.second}秒"
    )
    with p.open("a", encoding="utf-8") as f:
        f.write(f"{stamp} 已删除：{name}\n")
    return True
