"""
微信通讯录遍历 + 转账 0.01 单删探测（uiautomator2）。

不会自动输入支付密码；若进入付款页则视为仍是好友并返回。
"""

from __future__ import annotations

import random
import time
from datetime import datetime
from pathlib import Path

import uiautomator2 as u2

import config
from device import assert_wechat_ui_readable
from log_util import log as print
from log_util import now_str
from io_util import (
    add_purged_friend_now,
    append_remove_result,
    append_result,
    load_deleted_names,
    write_deleted_list,
)


class WeChatDetector:
    def __init__(self, d: u2.Device):
        self.d = d

    def seen(self, timeout: float = 0, **kwargs) -> bool:
        """立即/短超时查找；缺省 timeout=0，避免空等把耗时刷到几十秒。"""
        return self.d(**kwargs).exists(timeout=timeout)

    def open_wechat(self) -> None:
        cur = self.d.app_current()
        if cur.get("package") != "com.tencent.mm":
            self.d.app_start("com.tencent.mm", stop=False)
            time.sleep(1.2)
        assert_wechat_ui_readable(self.d)

    def ensure_wechat(self) -> None:
        """若返回键把微信退出了，重新拉起。"""
        pkg = (self.d.app_current() or {}).get("package")
        if pkg == "com.tencent.mm":
            return
        print(f"[warn] 当前不在微信({pkg})，重新打开")
        self.d.app_start("com.tencent.mm", stop=False)
        time.sleep(1.2)

    def press_back(self, times: int = 1) -> None:
        for _ in range(times):
            self.d.press("back")
            time.sleep(config.BACK_WAIT)

    def dismiss_talkback_tips(self) -> None:
        for sel in (
            {"text": "关闭悬浮提示"},
            {"description": "关闭TalkBack悬浮提示"},
            {"textContains": "关闭悬浮"},
        ):
            if self.seen(**sel):
                try:
                    self.d(**sel).click()
                    time.sleep(config.UI_SHORT)
                except Exception:
                    pass

    def go_contacts(self) -> None:
        self.ensure_wechat()
        assert_wechat_ui_readable(self.d)
        self.dismiss_talkback_tips()

        if self.seen(timeout=config.EXISTS_NORMAL, text="新的朋友"):
            return

        tab = self.d(text="通讯录")
        if not tab.exists(timeout=config.EXISTS_NORMAL):
            tab = self.d(description="通讯录")
        if not tab.exists(timeout=0.2):
            self.press_back(1)
            self.ensure_wechat()
            tab = self.d(text="通讯录")
            if not tab.exists(timeout=config.EXISTS_NORMAL):
                tab = self.d(description="通讯录")
        if not tab.exists(timeout=0.2):
            raise RuntimeError(
                "找不到「通讯录」Tab。请确认微信主界面可见底部通讯录，"
                "并保持 TalkBack/选中朗读开启后运行 python debug_ui.py。"
            )
        tab.click()
        time.sleep(config.UI_PAGE)

    def _is_friend_name(self, name: str) -> bool:
        name = name.strip()
        if not name:
            return False
        if name in config.SKIP_NAMES:
            return False
        if name in config.SKIP_INDEX_CHARS:
            return False
        if len(name) == 1 and name.isascii():
            return False
        if name in {"微信", "发现", "我", "通讯录"}:
            return False
        if name.endswith("/s") or name in {"KB/s", "MB/s"}:
            return False
        if name.replace(".", "", 1).isdigit():
            return False
        return True

    def visible_friend_names(self) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        nodes = self.d(resourceId="com.tencent.mm:id/kbq")
        try:
            count = nodes.count if nodes.exists else 0
        except Exception:
            count = 0

        if count == 0:
            list_views = self.d(className="android.widget.ListView")
            if list_views.exists:
                nodes = list_views.child(className="android.widget.TextView")
            else:
                nodes = self.d(className="android.widget.TextView")
            try:
                count = nodes.count
            except Exception:
                count = 0

        _, screen_h = self.d.window_size()
        for i in range(count):
            try:
                text = (nodes[i].get_text() or "").strip()
            except Exception:
                continue
            if not self._is_friend_name(text) or text in seen:
                continue
            try:
                bounds = nodes[i].info.get("bounds") or {}
                top = bounds.get("top", 0)
                bottom = bounds.get("bottom", 0)
                if top > screen_h * 0.88 or top < screen_h * 0.12:
                    continue
                if bottom - top < 10:
                    continue
            except Exception:
                pass
            seen.add(text)
            names.append(text)
        return names

    def scroll_contacts(self, fast: bool = False) -> bool:
        before = self.visible_friend_names()
        self.d.swipe_ext("up", scale=0.75)
        time.sleep(config.UI_SHORT if fast else config.UI_STEP)
        after = self.visible_friend_names()
        return before != after

    def scroll_until_name(self, name: str, max_swipes: int = 60) -> bool:
        """从当前位置向下滑，直到看到指定好友（用于接续，避免每次从头点）。"""
        for _ in range(max_swipes):
            if name in self.visible_friend_names():
                return True
            if not self.scroll_contacts(fast=True):
                return name in self.visible_friend_names()
        return False

    def next_friend_after(self, last_name: str | None, visited: set[str]) -> str | None:
        """
        取下一位未检测好友。
        若返回后滚动位置还在，上一好友仍在屏上 → 直接点他下面的人，绝不先滑回顶部。
        """
        for _ in range(50):
            visible = self.visible_friend_names()
            if last_name and last_name in visible:
                for n in visible[visible.index(last_name) + 1 :]:
                    if n not in visited:
                        print(f"[step] 接续点击「{n}」（上一好友「{last_name}」仍在屏上）")
                        return n
            else:
                for n in visible:
                    if n not in visited:
                        print(f"[step] 接续点击「{n}」")
                        return n
            if not self.scroll_contacts(fast=True):
                return None
        return None

    def peek_following(self, name: str, visited: set[str]) -> list[str]:
        """打开某人之前，记下同屏后面的名字，返回后可优先点这些。"""
        visible = self.visible_friend_names()
        if name not in visible:
            return []
        return [n for n in visible[visible.index(name) + 1 :] if n not in visited]

    def _click_friend_name(self, name: str) -> bool:
        if not self.seen(text=name) and not self.seen(textContains=name):
            self.scroll_until_name(name)
        node = self.d(text=name)
        if not node.exists(timeout=config.EXISTS_NORMAL):
            node = self.d(textContains=name)
        if not node.exists(timeout=config.EXISTS_FAST):
            return False
        node.click()
        time.sleep(config.UI_STEP)
        return True

    def open_friend_from_contacts(self, name: str) -> bool:
        """点进好友并进入聊天（转账探测用）。"""
        if not self._click_friend_name(name):
            return False
        if self.d(text="发消息").exists(timeout=config.EXISTS_NORMAL):
            self.d(text="发消息").click()
            time.sleep(config.UI_STEP)
        return True

    def open_friend_profile(self, name: str) -> bool:
        """点进好友资料页，不点「发消息」（删除好友用）。"""
        if not self._click_friend_name(name):
            return False
        # 资料页常见按钮
        if self.seen(timeout=config.EXISTS_NORMAL, text="发消息") or self.seen(
            text="设置备注和标签"
        ) or self.seen(text="朋友权限"):
            return True
        # 有的会直接进聊天，再进一次资料：点右上角头像/标题
        if self.seen(className="android.widget.EditText"):
            # 聊天页点标题进资料
            if self.seen(description="聊天信息"):
                self.d(description="聊天信息").click()
                time.sleep(config.UI_STEP)
            elif self.seen(text=name):
                # 点顶部名字区域
                try:
                    self.d(text=name).click()
                    time.sleep(config.UI_STEP)
                except Exception:
                    pass
        on_profile = self.seen(text="发消息") or self.seen(text="删除联系人") or self.seen(
            text="删除"
        )
        if on_profile:
            # 资料页主体已出现，再等右上角「更多」渲染完
            time.sleep(config.UI_STEP)
        return on_profile

    def _profile_menu_opened(self) -> bool:
        return (
            self.seen(text="删除")
            or self.seen(text="删除联系人")
            or self.seen(text="设置备注和标签")
            or self.seen(text="把他推荐给朋友")
            or self.seen(text="把她推荐给朋友")
        )

    def _find_profile_more_button(self):
        """资料页右上角「⋯ / 更多」；不要误点聊天页「聊天信息」。"""
        w, h = self.d.window_size()
        candidates = [
            {"description": "更多"},
            {"descriptionContains": "更多"},
            {"description": "选项"},
            {"descriptionContains": "选项"},
        ]
        for sel in candidates:
            node = self.d(**sel)
            if not node.exists(timeout=0.15):
                continue
            try:
                bounds = node.info.get("bounds") or {}
                top = bounds.get("top", 0)
                left = bounds.get("left", 0)
                if top < h * 0.25 and left > w * 0.55:
                    return node, sel
            except Exception:
                continue
        return None, None

    def _wait_profile_more_button(self, timeout: float = 1.8):
        """轮询直到右上角「更多」节点出现（资料页常比按钮晚渲染）。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            node, sel = self._find_profile_more_button()
            if node is not None:
                return node, sel
            time.sleep(0.12)
        return None, None

    def _click_profile_more_menu(self) -> bool:
        """
        点击资料页右上角「⋯ / 更多」选项。
        不要点「聊天信息」（那是聊天页右上角）。
        """
        w, h = self.d.window_size()

        node, sel = self._wait_profile_more_button()
        if node is not None:
            for attempt in (1, 2):
                label = sel or "更多"
                print(f"[step] 点击右上角选项: {label}" + ("（重试）" if attempt > 1 else ""))
                node.click()
                time.sleep(config.UI_PAGE)
                if self._profile_menu_opened():
                    return True
                if attempt == 1:
                    time.sleep(config.UI_STEP)
                    node, sel = self._find_profile_more_button()
                    if node is None:
                        break

        # 坐标兜底：标题栏右侧（常见三个点位置）
        print("[step] 坐标点击资料页右上角选项")
        for x_ratio, y_ratio in ((0.93, 0.08), (0.90, 0.07), (0.95, 0.09)):
            self.d.click(int(w * x_ratio), int(h * y_ratio))
            time.sleep(config.UI_PAGE)
            if self._profile_menu_opened():
                return True
        return self._profile_menu_opened()

    def delete_friend_on_profile(self, name: str) -> tuple[str, str]:
        """
        正确流程：资料页 → 右上角选项 → 删除/删除联系人 → 确认。
        """
        print(f"[step] 准备删除好友「{name}」")
        if not self.seen(timeout=config.EXISTS_NORMAL, text="发消息") and not self.seen(
            text="设置备注和标签"
        ):
            print("[warn] 当前可能不在资料页，仍尝试点右上角选项")

        if not self._click_profile_more_menu():
            Path(config.SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)
            self.d.screenshot(str(Path(config.SCREENSHOT_DIR) / "no_profile_more.png"))
            return "失败", "打不开资料页右上角选项菜单"

        # 菜单里点删除
        delete_item = None
        if self.seen(timeout=config.EXISTS_NORMAL, text="删除联系人"):
            delete_item = self.d(text="删除联系人")
        elif self.seen(timeout=config.EXISTS_NORMAL, text="删除"):
            delete_item = self.d(text="删除")
        if delete_item is None:
            Path(config.SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)
            self.d.screenshot(str(Path(config.SCREENSHOT_DIR) / "no_delete_entry.png"))
            return "失败", "右上角菜单里没有「删除」"

        print("[step] 点击菜单「删除」")
        delete_item.click()
        time.sleep(config.UI_PAGE)

        # 确认弹窗
        confirmed = False
        for text in ("删除联系人", "删除", "确定"):
            btn = self.d(text=text)
            if not btn.exists(timeout=0.7):
                continue
            try:
                count = btn.count
                for i in range(count - 1, -1, -1):
                    info = btn[i].info
                    if info.get("clickable", True):
                        print(f"[step] 确认删除：点击「{text}」")
                        btn[i].click()
                        confirmed = True
                        break
                if confirmed:
                    break
            except Exception:
                print(f"[step] 确认删除：点击「{text}」")
                btn.click()
                confirmed = True
                break

        if not confirmed:
            Path(config.SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)
            self.d.screenshot(str(Path(config.SCREENSHOT_DIR) / "no_delete_confirm.png"))
            return "失败", "未找到删除确认按钮"

        time.sleep(config.UI_PAGE)
        self.dismiss_alert()
        if self.on_contacts_list() or not self.seen(text="发消息"):
            return "已删除", "确认删除成功"
        return "已删除或待确认", "已点确认，请核对通讯录"

    def page_blob(self) -> str:
        return self.d.dump_hierarchy()

    def classify(self, blob: str) -> tuple[str, str]:
        for kw in config.DELETED_KEYWORDS:
            if kw in blob:
                return "疑似单删/非好友", kw
        for kw in config.NORMAL_KEYWORDS:
            if kw in blob:
                return "正常", kw
        if "转账金额" in blob or ("转账" in blob and "元" in blob):
            return "正常或无法判定", "已进入转账页"
        return "正常或无法判定", ""

    def _safe_name(self, name: str) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:40]

    def _remove_old_screenshots(self, safe: str) -> None:
        """删除同一联系人的旧截图（不用 glob，避免特殊字符匹配失败）。"""
        out_dir = Path(config.SCREENSHOT_DIR)
        if not out_dir.exists():
            return
        prefix = f"{safe}_"
        for old in out_dir.iterdir():
            if not old.is_file() or old.suffix.lower() != ".png":
                continue
            if old.name.startswith(prefix):
                try:
                    old.unlink()
                    print(f"[step] 已删除旧截图: {old.name}")
                except OSError as e:
                    print(f"[warn] 删除旧截图失败 {old.name}: {e}")

    def screenshot(self, name: str, force: bool = False) -> None:
        if config.SCREENSHOT_ONLY_HIT and not force:
            return
        out_dir = Path(config.SCREENSHOT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = self._safe_name(name)

        # 同一联系人只保留最新一张
        self._remove_old_screenshots(safe)

        now = datetime.now()
        stamp = (
            f"{now.year}年{now.month}月{now.day}日"
            f"{now.hour}时{now.minute}分{now.second}秒"
        )
        path = out_dir / f"{safe}_{stamp}.png"
        self.d.screenshot(str(path))
        print(f"[step] 已截图: {path.name}")

    def _on_transfer_amount_page(self) -> bool:
        return self.seen(textContains="转账金额") or (
            self.seen(text="转账") and self.seen(className="android.widget.EditText")
        )

    def _on_payment_page(self) -> bool:
        return any(
            self.seen(textContains=kw)
            for kw in ("支付密码", "付款方式", "指纹支付", "面容支付")
        )

    def _ensure_in_chat(self) -> None:
        self.dismiss_talkback_tips()
        if self.seen(text="聊天信息") or self.seen(text="查找聊天记录"):
            print("[step] 离开聊天信息页")
            self.press_back(1)

        if self.seen(timeout=config.EXISTS_FAST, text="发消息"):
            print("[step] 点击 发消息 进入聊天")
            self.d(text="发消息").click()
            time.sleep(config.UI_STEP)

        if self.seen(text="聊天信息"):
            self.press_back(1)

    def _open_plus_panel(self) -> None:
        if self.seen(text="转账") or self.seen(text="相册"):
            return

        candidates = [
            {"description": "更多功能按钮"},
            {"descriptionContains": "更多功能"},
        ]
        w, h = self.d.window_size()
        clicked = False
        for sel in candidates:
            node = self.d(**sel)
            if not node.exists(timeout=0.25):
                continue
            try:
                bounds = node.info.get("bounds") or {}
                if bounds.get("top", 0) < h * 0.7:
                    continue
                node.click()
                clicked = True
                time.sleep(config.UI_STEP)
                break
            except Exception:
                continue

        if not clicked:
            print("[step] 坐标点击底部 +")
            for x_ratio, y_ratio in ((0.93, 0.90), (0.91, 0.88)):
                self.d.click(int(w * x_ratio), int(h * y_ratio))
                time.sleep(config.UI_STEP)
                if self.seen(text="转账") or self.seen(text="相册"):
                    break

    def _open_transfer_panel(self) -> bool:
        """打开转账金额页。返回是否已进入金额页（或已出现失败弹窗）。"""
        if self._on_transfer_amount_page():
            print("[step] 已在转账金额页")
            return True

        self._ensure_in_chat()
        print("[step] 打开聊天底部附件栏(+)")
        self._open_plus_panel()

        if self.seen(text="聊天信息"):
            self.press_back(1)
            self._open_plus_panel()

        print("[step] 点击 转账")
        transfer = self.d(text="转账")
        if not transfer.exists(timeout=config.EXISTS_NORMAL):
            transfer = self.d(description="转账")
        if not transfer.exists(timeout=0.25):
            w, h = self.d.window_size()
            self.d.swipe(int(w * 0.8), int(h * 0.75), int(w * 0.2), int(h * 0.75), 0.15)
            time.sleep(config.UI_SHORT)
            transfer = self.d(text="转账")
        if not transfer.exists(timeout=config.EXISTS_NORMAL):
            Path(config.SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)
            self.d.screenshot(str(Path(config.SCREENSHOT_DIR) / "no_transfer.png"))
            raise RuntimeError("找不到「转账」入口（已截图 screenshots/no_transfer.png）")
        transfer.click()
        time.sleep(config.UI_PAGE)

        if self.seen(text="我知道了"):
            print("[step] 点转账后出现失败提示")
            return False
        if self._on_transfer_amount_page():
            print("[step] 已进入转账金额页")
            return True
        print("[warn] 点击转账后未识别到金额页")
        return False

    def _fill_amount_and_submit(self) -> None:
        if self.seen(text="我知道了") or self._on_payment_page():
            return
        if not self._on_transfer_amount_page():
            return

        print(f"[step] 输入金额 {config.TRANSFER_AMOUNT}")
        if self.seen(timeout=config.EXISTS_NORMAL, className="android.widget.EditText"):
            edit = self.d(className="android.widget.EditText")
            edit.click()
            time.sleep(config.UI_SHORT)
            try:
                edit.clear_text()
            except Exception:
                pass
            edit.set_text(config.TRANSFER_AMOUNT)
            time.sleep(config.UI_SHORT)
        else:
            for ch in config.TRANSFER_AMOUNT:
                if self.seen(text=ch):
                    self.d(text=ch).click()
                    time.sleep(0.08)
                elif ch == ".":
                    for cand in (".", "·"):
                        if self.seen(text=cand):
                            self.d(text=cand).click()
                            time.sleep(0.08)
                            break

        print("[step] 确认转账（不会输入支付密码）")
        btn = self.d(text="转账")
        if btn.exists(timeout=config.EXISTS_NORMAL):
            try:
                count = btn.count
                clicked = False
                for i in range(count - 1, -1, -1):
                    info = btn[i].info
                    if info.get("clickable") or info.get("enabled"):
                        btn[i].click()
                        clicked = True
                        break
                if not clicked:
                    btn.click()
            except Exception:
                btn.click()
        time.sleep(config.AFTER_TRANSFER_WAIT)

    def dismiss_alert(self) -> bool:
        """只关「我知道了」类提示；用 timeout=0，避免空等。"""
        self.dismiss_talkback_tips()
        for text in config.DISMISS_BUTTONS:
            if self.seen(text=text):
                print(f"[step] 关闭弹窗：点击「{text}」")
                try:
                    self.d(text=text).click()
                except Exception:
                    try:
                        self.d(text=text).click(offset=(0.5, 0.5))
                    except Exception:
                        pass
                time.sleep(config.UI_SHORT)
                return True
        return False

    def cancel_payment_if_needed(self) -> None:
        if self._on_payment_page():
            print("[info] 已到付款页，判定为仍是好友，取消支付")
            self.press_back(1)
            time.sleep(config.UI_SHORT)
            if self.seen(text="取消"):
                self.d(text="取消").click()
                time.sleep(config.UI_SHORT)
            elif self.seen(text="退出"):
                self.d(text="退出").click()
                time.sleep(config.UI_SHORT)
            else:
                self.press_back(1)

    def finish_and_leave_transfer(self, name: str, status: str, detail: str) -> tuple[str, str]:
        if status.startswith("疑似"):
            # 无障碍树里文案往往比弹窗动画更早出现；等「我知道了」可见并再停一会再截
            self.d(text="我知道了").exists(timeout=config.EXISTS_NORMAL)
            time.sleep(config.SCREENSHOT_SETTLE)
            self.screenshot(name, force=True)
        for _ in range(3):
            if not self.dismiss_alert():
                break
        return status, detail

    def check_by_transfer(self, name: str) -> tuple[str, str]:
        # 尽量不用 dump_hierarchy（TalkBack+微信下可耗时十余秒，导致「耗时」虚高）
        if self.seen(timeout=config.EXISTS_FAST, text="添加到通讯录"):
            return self.finish_and_leave_transfer(name, "疑似单删/非好友", "添加到通讯录")

        entered_amount = self._open_transfer_panel()
        if self.seen(text="我知道了"):
            return self.finish_and_leave_transfer(name, "疑似单删/非好友", "转账失败弹窗")

        if entered_amount or self._on_transfer_amount_page():
            entered_amount = True
            self._fill_amount_and_submit()

        if self.seen(timeout=config.EXISTS_NORMAL, text="我知道了") or self.seen(
            textContains="你不是收款方好友"
        ):
            return self.finish_and_leave_transfer(name, "疑似单删/非好友", "你不是收款方好友")

        if self._on_payment_page():
            self.cancel_payment_if_needed()
            return "正常", "可转账"

        if entered_amount:
            # 已成功走过金额页且无失败弹窗 → 视为正常，不再 dump
            self.press_back(1)
            self.dismiss_alert()
            if self._on_payment_page():
                self.cancel_payment_if_needed()
            return "正常", "已完成转账探测"

        self.press_back(1)
        self.dismiss_alert()
        return "正常或无法判定", "未稳定进入转账页"

    def _in_chat_ui(self) -> bool:
        """是否在单聊/转账等非通讯录页（有输入框或转账页）。"""
        if self.seen(textContains="转账金额") or self.seen(text="我知道了"):
            return True
        if self.seen(text="发消息"):
            return True  # 资料页
        if self.seen(className="android.widget.EditText") and (
            self.seen(description="更多功能按钮")
            or self.seen(descriptionContains="更多功能")
            or self.seen(text="发送")
        ):
            return True
        return False

    def on_contacts_list(self) -> bool:
        """
        判断是否在通讯录好友列表。
        注意：滑到列表中部时看不到「新的朋友」，不能只靠它判断，
        否则会误点底部「通讯录」Tab，把滚动位置重置到顶部。
        """
        if self._in_chat_ui():
            return False
        # 好友行 resource-id（列表中部也能看到）
        try:
            if self.d(resourceId="com.tencent.mm:id/kbq").exists:
                return True
        except Exception:
            pass
        if self.seen(text="新的朋友"):
            return True
        return False

    def return_to_contacts(self) -> None:
        """
        用返回键回到通讯录，尽量保持原来的滚动位置。
        只有确认已经不在通讯录列表时，才允许点底部「通讯录」Tab（会重置到顶部）。
        """
        print("[step] 返回通讯录（保持列表位置）")
        for _ in range(8):
            self.ensure_wechat()
            self.dismiss_alert()

            if self.on_contacts_list():
                print("[step] 已回到通讯录（未重置滚动）")
                return

            if self.seen(text="取消"):
                self.d(text="取消").click()
                time.sleep(config.UI_SHORT)
                continue
            if self.seen(text="退出"):
                self.d(text="退出").click()
                time.sleep(config.UI_SHORT)
                continue

            # 优先返回，不要点 Tab
            self.d.press("back")
            time.sleep(config.BACK_WAIT)

        # 仍不在列表：可能停在「微信」消息 Tab
        if not self.on_contacts_list() and self.seen(text="通讯录"):
            print("[warn] 返回未能保持位置，只能点击通讯录 Tab（会回到顶部）")
            self.d(text="通讯录").click()
            time.sleep(config.UI_PAGE)
            if self.on_contacts_list() or self.seen(timeout=0.5, text="新的朋友"):
                return

        if not self.on_contacts_list():
            print("[warn] 强制重新进入通讯录")
            self.ensure_wechat()
            self.go_contacts()

    def scan(self, offset: int, count: int) -> list[dict]:
        if offset < 0 or count <= 0:
            raise ValueError("offset 必须 >=0，count 必须 >0")

        self.open_wechat()
        self.go_contacts()

        results: list[dict] = []
        visited: set[str] = set()
        last_name: str | None = None
        upcoming: list[str] = []
        global_index = 0
        checked = 0
        # 已在单删名单中的不再做转账探测
        known_deleted = set(load_deleted_names(config.DELETED_TXT))

        print(
            f"[info] 转账={config.TRANSFER_AMOUNT}；间隔 {config.MIN_DELAY}-{config.MAX_DELAY}s；"
            f"从偏移 {offset} 起测 {count} 人（接续上一好友，不从头点）；"
            f"名单已有 {len(known_deleted)} 人将跳过复检"
        )

        # 先按 offset 跳过，只滑动记名，不做转账
        while global_index < offset:
            name = self.next_friend_after(last_name, visited)
            if not name:
                print("[info] 跳过偏移时通讯录已到底")
                return results
            visited.add(name)
            print(f"[skip] #{global_index} {name}（未到偏移）")
            last_name = name
            global_index += 1

        while checked < count:
            # 优先用上一屏记下的「后面几个」；仍在屏上则直接点，免重头滑
            name = None
            while upcoming:
                cand = upcoming.pop(0)
                if cand in visited:
                    continue
                if cand in self.visible_friend_names() or self.seen(text=cand):
                    name = cand
                    print(f"[step] 同屏接续点击「{name}」")
                    break
                # 不在屏上：回到以 last_name 定位的逻辑
                upcoming.insert(0, cand)
                break

            if name is None:
                name = self.next_friend_after(last_name, visited)
            if not name:
                print("[info] 通讯录似乎已到底，结束。")
                break

            visited.add(name)
            upcoming = self.peek_following(name, visited)

            print(f"\n=== 检测 #{global_index} ({checked + 1}/{count}) {name} ===")
            if upcoming:
                print(f"[info] 已记下后续: {', '.join(upcoming[:5])}{'…' if len(upcoming) > 5 else ''}")

            t_detect = time.time()
            if name in known_deleted:
                status, detail = "疑似单删/非好友", "名单已有，跳过复检"
                print(f"[skip] {name} 已在单删名单，不再转账探测")
                need_return = False
            else:
                need_return = True
                try:
                    if not self.open_friend_from_contacts(name):
                        status, detail = "跳过", "点击失败"
                    else:
                        status, detail = self.check_by_transfer(name)
                except Exception as e:
                    status, detail = "错误", str(e)
                    print(f"[error] {e}")
            detect_s = time.time() - t_detect

            row = {
                "index": str(global_index),
                "name": name,
                "status": status,
                "detail": detail,
                "time": now_str(),
            }
            results.append(row)
            # 每结束一人立刻落盘
            append_result(config.RESULT_CSV, row)
            if status.startswith("疑似"):
                added = write_deleted_list(config.DELETED_TXT, [name])
                known_deleted.add(name)
                tag = "已写入名单" if added else "名单已有"
                print(f"[HIT] {name} => {status} | {detail} | {tag}")
            else:
                print(f"[result] {name} => {status} | {detail}")

            last_name = name
            t_back = time.time()
            if need_return and not self.on_contacts_list():
                self.return_to_contacts()
            back_s = time.time() - t_back
            print(f"[time] 检测 {detect_s:.1f}s | 返回 {back_s:.1f}s | 合计 {detect_s + back_s:.1f}s")

            global_index += 1
            checked += 1
            if checked < count:
                # 名单跳过的人不必长时间等待
                if name in known_deleted and detail == "名单已有，跳过复检":
                    time.sleep(config.UI_SHORT)
                else:
                    sleep_jitter()

        return results

    def purge(
        self, offset: int, count: int, targets: set[str], dry_run: bool = False
    ) -> tuple[list[dict], int]:
        """
        遍历通讯录（支持 offset/count；count=0 表示一直到列表结束）。
        若好友名在 targets（deleted.txt）中，则删除该好友。
        每处理完一人立刻写 remove_result / purge_summary。
        返回 (结果列表, 本批新计入累计的人数)。
        """
        if offset < 0 or count < 0:
            raise ValueError("offset 必须 >=0，count 必须 >=0（0 表示扫到通讯录结束）")
        if not targets:
            raise ValueError("名单为空：请先用 scan 生成 data/deleted.txt")

        self.open_wechat()
        self.go_contacts()

        results: list[dict] = []
        visited: set[str] = set()
        last_name: str | None = None
        upcoming: list[str] = []
        global_index = 0
        processed = 0  # 本批实际检查过的人数（含跳过不在名单的）
        newly_added = 0
        unlimited = count == 0

        print(
            f"[info] 清理模式：名单 {len(targets)} 人；"
            f"偏移 {offset}；数量 {'全部(至通讯录结束)' if unlimited else count}；"
            f"{'仅演练不删除' if dry_run else '将真实删除'}"
        )

        while global_index < offset:
            name = self.next_friend_after(last_name, visited)
            if not name:
                print("[info] 跳过偏移时通讯录已到底")
                return results
            visited.add(name)
            print(f"[skip] #{global_index} {name}（未到偏移）")
            last_name = name
            global_index += 1

        while unlimited or processed < count:
            name = None
            while upcoming:
                cand = upcoming.pop(0)
                if cand in visited:
                    continue
                if cand in self.visible_friend_names() or self.seen(text=cand):
                    name = cand
                    print(f"[step] 同屏接续「{name}」")
                    break
                upcoming.insert(0, cand)
                break

            if name is None:
                name = self.next_friend_after(last_name, visited)
            if not name:
                print("[info] 通讯录似乎已到底，结束。")
                break

            visited.add(name)
            upcoming = self.peek_following(name, visited)
            in_list = name in targets
            print(
                f"\n=== 清理 #{global_index} "
                f"({processed + 1}{'' if unlimited else f'/{count}'}) {name} ==="
            )
            print(f"[info] 是否在删除名单: {'是' if in_list else '否'}")

            t0 = time.time()
            if not in_list:
                status, detail = "跳过", "不在名单中"
            elif dry_run:
                status, detail = "演练命中", "dry-run 未真实删除"
            else:
                try:
                    if not self.open_friend_profile(name):
                        status, detail = "失败", "打开资料页失败"
                    else:
                        status, detail = self.delete_friend_on_profile(name)
                except Exception as e:
                    status, detail = "错误", str(e)
                    print(f"[error] {e}")

            cost = time.time() - t0
            row = {
                "index": str(global_index),
                "name": name,
                "status": status,
                "detail": detail,
                "time": now_str(),
            }
            results.append(row)
            # 每结束一人立刻落盘
            append_remove_result(config.REMOVE_CSV, row)
            if status.startswith("已删除") and not dry_run:
                if add_purged_friend_now(config.PURGE_SUMMARY_TXT, name):
                    newly_added += 1
                    print(f"[save] 已写入删除记录: {name}")
                else:
                    print(f"[save] 记录已有，跳过重复: {name}")
            print(f"[result] {name} => {status} | {detail} | {cost:.1f}s")

            last_name = name
            # 删除成功后通常已在通讯录；否则尝试返回（保持滚动）
            if not self.on_contacts_list():
                self.return_to_contacts()

            global_index += 1
            processed += 1
            if (unlimited or processed < count) and in_list and not dry_run:
                sleep_jitter()
            elif (unlimited or processed < count) and not in_list:
                # 不在名单：很快看下一位，短停即可
                time.sleep(config.UI_SHORT)

        return results, newly_added


def sleep_jitter() -> None:
    delay = random.uniform(config.MIN_DELAY, config.MAX_DELAY)
    print(f"[wait] {delay:.1f}s")
    time.sleep(delay)