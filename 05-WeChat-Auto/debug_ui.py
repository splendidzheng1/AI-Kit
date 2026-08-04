"""调试：当前微信控件是否可读（主微信/分身都看这个）。"""

from __future__ import annotations

import re
import subprocess

import uiautomator2 as u2

from log_util import log as print


def focus_line() -> str:
    out = subprocess.check_output(
        ["adb", "shell", "dumpsys", "window"],
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    for line in out.splitlines():
        if "mCurrentFocus=Window" in line:
            return line.strip()
    return ""


def analyze() -> None:
    d = u2.connect()
    cur = d.app_current()
    focus = focus_line()
    xml = d.dump_hierarchy()
    from pathlib import Path

    out = Path("screenshots")
    out.mkdir(parents=True, exist_ok=True)
    (out / "debug_hierarchy.xml").write_text(xml, encoding="utf-8")

    texts = [t for t in re.findall(r'package="com.tencent.mm"[^>]*text="([^"]*)"', xml) if t]
    print("focus:", focus)
    print("current:", cur)
    print("mm readable texts:", len(texts), texts[:30])
    print("has 通讯录:", "通讯录" in xml)
    print("has 新的朋友:", "新的朋友" in xml)
    print("dual-app(u999):", "u999" in focus)

    if "通讯录" in xml or "新的朋友" in xml:
        print("STATUS: OK - 控件可读，可以 scan（分身/主微信都行）")
    elif cur.get("package") == "com.tencent.mm" or "com.tencent.mm" in focus:
        print("STATUS: BAD - 微信在前台但控件不可读")
        print("下一步: 打开无障碍「选中朗读/TalkBack」或 Hamibot 后再测一次")
    else:
        print("STATUS: UNKNOWN - 请先打开微信并停在主界面")


if __name__ == "__main__":
    analyze()
