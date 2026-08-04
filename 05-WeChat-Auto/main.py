"""
微信单删好友检测 / 按名单删除 - 入口

常用命令：
  python main.py smoke
  python main.py scan --offset 0 --count 20
  python main.py purge --offset 0 --count 20
  python main.py purge --offset 0 --count 0
  python main.py purge --offset 0 --count 5 --dry-run
  python main.py clear --yes
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import config
from detector import WeChatDetector
from device import connect, smoke_test
from io_util import load_deleted_names
from log_util import log as print


def format_duration(seconds: float) -> str:
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}小时{m}分{s}秒（{seconds:.1f}s）"
    if m > 0:
        return f"{m}分{s}秒（{seconds:.1f}s）"
    return f"{s}秒（{seconds:.1f}s）"


def record_paths() -> list[Path]:
    return [
        Path(config.RESULT_CSV),
        Path(config.DELETED_TXT),
        Path(config.REMOVE_CSV),
        Path(config.PURGE_SUMMARY_TXT),
    ]


def cmd_smoke(serial: str | None) -> None:
    d = connect(serial)
    smoke_test(d)


def cmd_clear(yes: bool) -> None:
    """清空所有运行记录文件与截图（不连手机）。"""
    paths = record_paths()
    shot_dir = Path(config.SCREENSHOT_DIR)
    print("将清空以下记录：")
    for p in paths:
        print(f"  - {p}")
    print(f"  - {shot_dir}/ 下全部截图")
    if not yes:
        print("未执行。若确认清空，请加上 --yes：")
        print("  python main.py clear --yes")
        return

    removed_files = 0
    for p in paths:
        if p.exists():
            p.unlink()
            removed_files += 1
            print(f"[ok] 已删除 {p}")
        else:
            print(f"[skip] 不存在 {p}")

    shot_dir.mkdir(parents=True, exist_ok=True)
    shot_count = 0
    for f in shot_dir.iterdir():
        if f.is_file():
            f.unlink()
            shot_count += 1
    print(f"[ok] 已清空截图 {shot_count} 张")
    print(f"完成：删除记录文件 {removed_files} 个，截图 {shot_count} 张")


def cmd_scan(offset: int, count: int, serial: str | None) -> None:
    t0 = time.time()
    d = connect(serial)
    det = WeChatDetector(d)
    print(
        f"转账探测 {config.TRANSFER_AMOUNT} 元（不会自动输支付密码）。"
        "请保持微信主界面/TalkBack 可读。Ctrl+C 可中止。"
        "（每检测完一人立刻写入 result.csv / deleted.txt）"
    )
    results = det.scan(offset=offset, count=count)

    deleted = [r["name"] for r in results if r["status"].startswith("疑似")]
    elapsed = time.time() - t0
    print("\n========== 本批疑似单删 ==========")
    if not deleted:
        print("（本批未发现）")
    else:
        for i, name in enumerate(deleted, 1):
            print(f"{i}. {name}")
    print("==================================")
    print(f"本批检测 {len(results)} 人，疑似 {len(deleted)} 人（已按人即时写入）")
    print(f"名单文件: {config.DELETED_TXT}")
    print(f"明细 CSV: {config.RESULT_CSV}")
    print(f"运行总时间: {format_duration(elapsed)}")


def cmd_purge(offset: int, count: int, serial: str | None, dry_run: bool) -> None:
    t0 = time.time()
    targets = set(load_deleted_names(config.DELETED_TXT))
    if not targets:
        print(f"名单为空：请先 scan 生成 {config.DELETED_TXT}")
        return

    d = connect(serial)
    det = WeChatDetector(d)
    print(
        f"按名单删除好友。名单共 {len(targets)} 人。"
        f"{'【演练模式：不会真删】' if dry_run else '【将真实删除，请谨慎】'}"
        " Ctrl+C 可中止。"
        "（每处理完一人立刻写入 remove_result.csv / purge_summary.txt）"
    )
    results, newly_added = det.purge(
        offset=offset, count=count, targets=targets, dry_run=dry_run
    )

    removed_names = [r["name"] for r in results if r["status"].startswith("已删除")]
    batch_names = (
        removed_names
        if not dry_run
        else [r["name"] for r in results if r["status"] == "演练命中"]
    )
    hit = [r for r in results if r["name"] in targets]
    elapsed = time.time() - t0
    duration_text = format_duration(elapsed)

    print("\n========== 本批清理结果 ==========")
    if not hit:
        print("（本批未命中名单中的好友）")
    else:
        for i, r in enumerate(hit, 1):
            print(f"{i}. {r['name']}  => {r['status']} | {r['detail']}")
    print("==================================")
    print(
        f"本批遍历 {len(results)} 人，命中名单 {len(hit)} 人，"
        f"{'演练命中' if dry_run else '已删除'} {len(batch_names)} 人"
        + (f"，新计入累计 {newly_added} 人" if not dry_run else "")
    )
    print(f"名单来源: {config.DELETED_TXT}")
    print(f"清理明细: {config.REMOVE_CSV}（按人即时写入）")
    print(f"删除记录: {config.PURGE_SUMMARY_TXT}（仅逐条）")
    print(f"运行总时间: {duration_text}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="微信单删检测 / 按名单删除 (uiautomator2)")
    p.add_argument("--serial", default=None, help="adb 设备序列号")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("smoke", help="连接自检")

    scan = sub.add_parser("scan", help="转账探测：找出疑似单删并写入名单")
    scan.add_argument("--offset", type=int, required=True, help="跳过前 N 个好友（从 0 开始）")
    scan.add_argument("--count", type=int, required=True, help="本批检测人数")

    purge = sub.add_parser("purge", help="按 deleted.txt 名单删除通讯录好友")
    purge.add_argument("--offset", type=int, required=True, help="跳过前 N 个好友（从 0 开始）")
    purge.add_argument(
        "--count",
        type=int,
        required=True,
        help="本批处理人数；0 表示从偏移起一直扫到通讯录结束",
    )
    purge.add_argument(
        "--dry-run",
        action="store_true",
        help="只报告命中名单的人，不执行真实删除",
    )

    clear = sub.add_parser("clear", help="清空所有记录文件与截图")
    clear.add_argument(
        "--yes",
        action="store_true",
        help="确认执行清空（不加此参数只预览、不删除）",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "smoke":
        cmd_smoke(args.serial)
    elif args.cmd == "scan":
        cmd_scan(args.offset, args.count, args.serial)
    elif args.cmd == "purge":
        cmd_purge(args.offset, args.count, args.serial, args.dry_run)
    elif args.cmd == "clear":
        cmd_clear(args.yes)
    else:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
