"""设备连接与基础自检。"""

from __future__ import annotations

import subprocess

import uiautomator2 as u2

from log_util import log as print


def connect(serial: str | None = None) -> u2.Device:
    """连接手机。serial 为空时自动选第一台已授权设备。"""
    d = u2.connect(serial) if serial else u2.connect()
    info = d.info
    print(f"[ok] 已连接: {info.get('productName') or info.get('model')} | SDK={info.get('sdkInt')}")
    return d


def current_focus() -> str:
    try:
        out = subprocess.check_output(
            ["adb", "shell", "dumpsys", "window"],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""
    for line in out.splitlines():
        if "mCurrentFocus=Window" in line:
            return line.strip()
    return ""


def assert_wechat_ui_readable(d: u2.Device) -> None:
    """
    只要控件树可读就可以继续（主微信/分身都行）。
    分身微信在 vivo 上经常整棵树为空，需要先打通无障碍再跑。
    """
    focus = current_focus()
    xml = d.dump_hierarchy()
    has_tab = ("通讯录" in xml) or ("新的朋友" in xml)
    if has_tab:
        return

    tip = [
        "当前微信界面控件读不到（dump 几乎为空），脚本无法点「通讯录」/好友。",
        f"焦点窗口: {focus or '(未知)'}",
        "",
        "分身微信也可以跑，但必须先让系统把控件树暴露出来。请按顺序试：",
        "A. 设置 → 无障碍 → 打开「选中朗读 / Speak selection」或 TalkBack，再回到分身微信主界面",
        "B. 或安装 Hamibot，开启其无障碍服务并保持后台运行",
        "C. 然后执行: python debug_ui.py",
        "   看到 has 通讯录: True / STATUS: OK 后再 scan",
        "",
        "若 A/B 后仍然读不到，这台机的分身微信对 uiautomator 屏蔽了控件，",
        "需要改走「截图 OCR + 坐标点击」方案（可继续做，但要另写一套）。",
    ]
    if d.app_current().get("package") == "com.tencent.mm" or "com.tencent.mm" in focus:
        raise RuntimeError("\n".join(tip))


def smoke_test(d: u2.Device) -> None:
    """验证自动化通道是否可用：亮屏、读取当前包名。"""
    d.screen_on()
    print(f"[ok] 当前 App: {d.app_current()}")
    print(f"[ok] 屏幕尺寸: {d.window_size()}")
    focus = current_focus()
    if focus:
        print(f"[ok] 焦点窗口: {focus}")
    if "u999" in focus:
        print("[warn] 检测到分身微信(u999)。后续 scan 必须改用主微信，否则会失败。")
    print("自检通过。请用主微信停在主界面，再运行检测。")
