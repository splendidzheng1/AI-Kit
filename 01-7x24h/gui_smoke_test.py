#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GUI 冒烟测试：验证价格盯盘功能在 xinlang_news_fetcher.py 中的集成。"""

import sys
import os
from datetime import datetime
from unittest.mock import patch

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Import the main module
import xinlang_news_fetcher as mod

app = QApplication.instance() or QApplication(sys.argv)

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} — {detail}")

print("=" * 60)
print("GUI 冒烟测试 — 价格盯盘集成")
print("=" * 60)

# ── Test 1: MainWindow / MiniNewsWindow 初始化 ──
print("\n[1/7] 组件初始化")
try:
    mw = mod.MainWindow()
    check("MainWindow created", mw is not None)
    check("MiniNewsWindow exists", hasattr(mw, 'mini_window'))
    check("PriceFetcherThread exists", hasattr(mw, 'price_fetcher_thread'))
    check("StackedWidget has 2 pages", mw.mini_window.stacked.count() == 2,
          f"got {mw.mini_window.stacked.count()}")
    check("9 PriceCards created", len(mw.mini_window.price_cards) == 9,
          f"got {len(mw.mini_window.price_cards)}")
    check("current_view == 0 (news)", mw.mini_window.current_view == 0)
except Exception as e:
    check("MainWindow init", False, str(e))
    import traceback; traceback.print_exc()

# ── Test 2: 视图切换 ──
print("\n[2/7] 视图切换 (news ↔ price)")
try:
    mw.mini_window.toggle_view()
    check("toggle → price view (view==1)", mw.mini_window.current_view == 1)
    check("stacked currentIndex == 1", mw.mini_window.stacked.currentIndex() == 1)
    mw.mini_window.toggle_view()
    check("toggle → news view (view==0)", mw.mini_window.current_view == 0)
    check("stacked currentIndex == 0", mw.mini_window.stacked.currentIndex() == 0)
except Exception as e:
    check("view toggle", False, str(e))

# ── Test 3: 价格更新 ──
print("\n[3/7] 价格更新")
try:
    test_data = {
        "hf_GC": {"price": 2650.30, "change_pct": 0.85, "timestamp": datetime.now()},
        "hf_CL": {"price": 78.45, "change_pct": -1.20, "timestamp": datetime.now()},
        "s_sh000001": {"price": 3100.55, "change_pct": 0.30, "timestamp": datetime.now()},
        "s_sz399001": {"price": 10250.00, "change_pct": -0.50, "timestamp": datetime.now()},
        "int_nikkei": {"price": 38000.00, "change_pct": 1.10, "timestamp": datetime.now()},
        "fx_susdcny": {"price": 7.1850, "change_pct": None, "timestamp": datetime.now()},
        "fx_susdjpy": {"price": 148.50, "change_pct": None, "timestamp": datetime.now()},
        "hf_CAD": {"price": 9200.00, "change_pct": -0.30, "timestamp": datetime.now()},
        "hf_AHD": {"price": 2300.00, "change_pct": 0.60, "timestamp": datetime.now()},
    }
    mw.mini_window.update_prices(test_data)
    for code, data in test_data.items():
        card = mw.mini_window.price_cards.get(code)
        check(f"Card {code} price updated", card is not None and card.lbl_price.text() != "--",
              f"text='{card.lbl_price.text() if card else 'N/A'}'")
        check(f"Card {code} data_history has 1 entry",
              card is not None and len(card.data_history) == 1)
except Exception as e:
    check("price update", False, str(e))

# ── Test 4: Sparkline 渲染 ──
print("\n[4/7] Sparkline 渲染")
try:
    # Send more updates to build history
    for i in range(5):
        data = {}
        for code in test_data:
            base = test_data[code]["price"]
            data[code] = {
                "price": base + i * 0.5,
                "change_pct": test_data[code]["change_pct"],
                "timestamp": datetime.now(),
            }
        mw.mini_window.update_prices(data)
    card = mw.mini_window.price_cards.get("hf_GC")
    check("Card hf_GC has 6 history points", len(card.data_history) == 6,
          f"got {len(card.data_history)}")
    check("Sparkline points <= node_count", len(card.spark._points) <= card.node_count,
          f"spark={len(card.spark._points)}, node_count={card.node_count}")
    check("Sparkline has 6 points", len(card.spark._points) == 6,
          f"got {len(card.spark._points)}")
except Exception as e:
    check("sparkline render", False, str(e))

# ── Test 5: 节点数变更 ──
print("\n[5/7] 节点数变更")
try:
    card = mw.mini_window.price_cards.get("hf_GC")
    old_count = len(card.spark._points)
    mw.mini_window.apply_price_settings(interval=5, node_count=3,
                                         card_order=mw.mini_window.price_card_order)
    card = mw.mini_window.price_cards.get("hf_GC")
    check("node_count set to 3", card.node_count == 3, f"got {card.node_count}")
    check("sparkline shows 3 points", len(card.spark._points) == 3,
          f"got {len(card.spark._points)}")
except Exception as e:
    check("node count change", False, str(e))

# ── Test 6: 卡片顺序变更 ──
print("\n[6/7] 卡片顺序变更")
try:
    new_order = ["hf_CL", "hf_GC", "hf_CAD", "hf_AHD", "s_sh000001",
                 "s_sz399001", "int_nikkei", "fx_susdcny", "fx_susdjpy"]
    mw.mini_window.apply_price_settings(interval=5, node_count=30,
                                         card_order=new_order)
    # Verify order by checking layout item positions
    layout = mw.mini_window.cards_layout
    actual_codes = []
    for i in range(layout.count() - 1):  # -1 for stretch
        item = layout.itemAt(i)
        if item and item.widget():
            for code, card in mw.mini_window.price_cards.items():
                if card == item.widget():
                    actual_codes.append(code)
                    break
    check("card order matches new_order", actual_codes == new_order,
          f"got {actual_codes}")
except Exception as e:
    check("card reorder", False, str(e))

# ── Test 7: SettingsDialog ──
print("\n[7/7] SettingsDialog")
try:
    dlg = mod.SettingsDialog(mw)
    check("SettingsDialog created", dlg is not None)
    check("price_interval spin exists", hasattr(dlg, 'spin_price_interval'))
    check("price_node spin exists", hasattr(dlg, 'spin_price_nodes'))
    check("card order list exists", hasattr(dlg, 'list_order'))
    check("card order list has 9 items", dlg.list_order.count() == 9,
          f"got {dlg.list_order.count()}")
    # Test move up
    dlg.list_order.setCurrentRow(1)
    dlg._move_card_item(-1)
    check("move up works", dlg.list_order.currentRow() == 0,
          f"row={dlg.list_order.currentRow()}")
except Exception as e:
    check("settings dialog", False, str(e))

# ── Test 8: 清空新闻（右键菜单 / 双模式）──
print("\n[Test 8] 清空新闻（右键菜单 / 正常模式 + 迷你模式）")
try:
    fake_news = [
        {"id": f"n{i}", "time": "2026-10-22 10:00", "rich_text": f"测试快讯 {i}",
         "images": [], "source": "test"}
        for i in range(3)
    ]
    mw.add_news(fake_news)
    check("主窗口新增 3 张卡片", mw.news_layout.count() == 3,
          f"got {mw.news_layout.count()}")
    check("迷你窗历史同步 3 条", len(mw.mini_window.news_history) == 3,
          f"got {len(mw.mini_window.news_history)}")

    card0 = mw.news_layout.itemAt(0).widget()
    check("卡片持有右键回调",
          getattr(card0, "context_menu_callback", None) is not None)
    check("卡片内文本框持有右键回调",
          card0.content_edit.context_menu_callback is not None)

    check("主窗口有悬浮清空按钮", hasattr(mw, "clear_news_btn"))
    check("主窗口有 clear_all_news", hasattr(mw, "clear_all_news"))
    check("主窗口有新闻右键菜单", hasattr(mw, "_news_context_menu"))
    check("迷你窗有清空按钮 btn_clear", hasattr(mw.mini_window, "btn_clear"))
    check("迷你窗有新闻右键菜单", hasattr(mw.mini_window, "_news_context_menu"))
    check("迷你窗有 clear_news_history",
          hasattr(mw.mini_window, "clear_news_history"))

    ok = mw.clear_all_news(confirm=False)
    check("clear_all_news 返回 True", ok is True, f"got {ok}")
    check("主窗口卡片已清空（仅剩空态提示）", mw.news_layout.count() == 1,
          f"got {mw.news_layout.count()}")
    check("迷你窗历史已清空", len(mw.mini_window.news_history) == 0,
          f"got {len(mw.mini_window.news_history)}")
    check("迷你窗显示空态占位", mw.mini_window.empty_label is not None)
    check("迷你窗导航按钮已禁用", not mw.mini_window.btn_up.isEnabled())
    check("搜索状态已重置",
          mw.search_matches == [] and mw.current_match_index == -1)
    check("latest_news 已重置", mw.latest_news is None)

    mw.add_news([{"id": "after", "time": "2026-10-22 11:00",
                  "rich_text": "清空后的新快讯", "images": [], "source": "test"}])
    check("清空后新快讯可正常插入", mw.news_layout.count() == 1,
          f"got {mw.news_layout.count()}")
    check("清空后迷你窗占位已换回卡片",
          mw.mini_window.empty_label is None
          and mw.mini_window.current_card is not None)
except Exception as e:
    check("clear news", False, str(e))
    import traceback; traceback.print_exc()

# ── Test 9: 立即抓取一次（双模式 + 右键菜单）──
print("\n[Test 9] 立即抓取一次（双模式 + 右键菜单）")
try:
    check("fetcher 有 request_fetch_now",
          hasattr(mw.fetcher_thread, 'request_fetch_now'))
    check("fetcher 有 fetch_finished 信号",
          hasattr(mw.fetcher_thread, 'fetch_finished'))
    check("fetcher 用 Condition 等待间隔（可被打断且不丢唤醒）",
          hasattr(mw.fetcher_thread, '_cond'))
    check("主窗口有 fetch_news_now", hasattr(mw, 'fetch_news_now'))
    check("主窗口有悬浮抓取按钮", hasattr(mw, 'refresh_news_btn'))
    check("迷你窗有抓取按钮 btn_fetch", hasattr(mw.mini_window, 'btn_fetch'))
    check("迷你窗有 fetch_now_requested",
          hasattr(mw.mini_window, 'fetch_now_requested'))

    check("request_fetch_now 返回 bool",
          isinstance(mw.fetcher_thread.request_fetch_now(), bool))

    default_tip = mw.refresh_news_btn.toolTip()
    mw._pending_manual_fetch = True
    mw._set_fetch_buttons_enabled(False)
    check("抓取中按钮置灰", not mw.refresh_news_btn.isEnabled())
    mw._on_fetch_finished(3)
    check("抓取完成后 pending 复位", mw._pending_manual_fetch is False)
    check("抓取完成后按钮恢复可用", mw.refresh_news_btn.isEnabled())
    check("不弹提示（tooltip 保持原样）",
          mw.refresh_news_btn.toolTip() == default_tip,
          f"tip={mw.refresh_news_btn.toolTip()}")

    import inspect
    _params = list(inspect.signature(mw._set_fetch_buttons_enabled).parameters)
    check("抓取反馈不再携带提示文案", _params == ['enabled'], f"params={_params}")

    bar = mw.mini_window.btn_fetch.parentWidget().layout()
    total = 0
    bar_texts = []
    for i in range(bar.count()):
        it = bar.itemAt(i)
        if it and it.widget():
            total += it.widget().sizeHint().width()
            bar_texts.append(it.widget().text())
    total += max(0, bar.count() - 1) * bar.spacing()
    check("迷你窗按钮栏不溢出 400px", total <= mw.mini_window.width() - 10,
          f"需要 {total}px / 可用 {mw.mini_window.width() - 10}px")
    check("按钮栏顺序与文案符合需求",
          bar_texts == ['▲', '▼', '最新', '刷新', '清空', '实盘', '正常模式'],
          f"got {bar_texts}")

    import time as _t
    _t0 = _t.time()
    mw.fetcher_thread.stop()
    check("fetcher_thread.stop() 不会等满 600s 间隔",
          _t.time() - _t0 < 12, f"耗时 {_t.time() - _t0:.1f}s")
except Exception as e:
    check("fetch now", False, str(e))
    import traceback; traceback.print_exc()

# ── Test 10: 清空后立即抓取仍能显示（已读去重缓存回归）──
print("\n[Test 10] 清空后立即抓取可重新显示快讯（回归）")
try:
    ft = mw.fetcher_thread
    sample = [
        {"id": "reg-1", "time": "2026-10-22 11:00", "rich_text": "回归测试快讯 A",
         "images": [], "source": "test"},
        {"id": "reg-2", "time": "2026-10-22 11:01", "rich_text": "回归测试快讯 B",
         "images": [], "source": "test"},
    ]
    first = ft._filter_new(sample)
    check("首次过滤全部为新", len(first) == 2, f"got {len(first)}")
    check("再次过滤为空（去重生效）", len(ft._filter_new(sample)) == 0)

    mw.clear_all_news(confirm=False)
    check("清空后 seen_ids 被重置", len(ft.seen_ids) == 0,
          f"got {len(ft.seen_ids)}")
    again = ft._filter_new(sample)
    check("清空后同样的快讯重新被视为新内容", len(again) == 2, f"got {len(again)}")
    check("清空后抓取冷却被清零", ft._last_fetch_start == 0.0,
          f"got {ft._last_fetch_start}")

    mw.add_news(sorted(again, key=lambda x: x.get("time", "")))
    check("清空后重新抓取能显示到列表", mw.news_layout.count() == 2,
          f"got {mw.news_layout.count()}")
    check("迷你窗同步恢复", len(mw.mini_window.news_history) == 2,
          f"got {len(mw.mini_window.news_history)}")
except Exception as e:
    check("clear then fetch regression", False, str(e))
    import traceback; traceback.print_exc()

# ── Test 11: 真实点击与右键菜单事件模拟（QTest）──
print("\n[Test 11] 真实点击 / 右键菜单 / 键盘事件模拟（QTest）")
try:
    from PyQt6.QtTest import QTest
    from PyQt6.QtGui import QContextMenuEvent
    from PyQt6.QtCore import QPoint
    from contextlib import ExitStack
    from unittest.mock import patch

    ft = mw.fetcher_thread
    # Test 9 已 stop 抓取线程；这里只恢复标志位，不真正启动线程，
    # 以免后台真实抓取把新闻插进来干扰断言
    ft.running = True
    ft.reset_seen()

    demo = [{"id": "click-1", "time": "2026-10-22 11:30",
             "rich_text": "点击测试快讯", "images": [], "source": "test"}]
    mw.clear_all_news(confirm=False)
    mw.add_news(demo)
    check("准备：列表有 1 张卡片", mw.news_layout.count() == 1,
          f"got {mw.news_layout.count()}")

    # 1) 真实鼠标点击主窗口悬浮 ⟳ 按钮
    mw._pending_manual_fetch = False
    ft.reset_seen()
    QTest.mouseClick(mw.refresh_news_btn, Qt.MouseButton.LeftButton)
    check("点击主窗口 ⟳ 真的触发了抓取请求",
          mw._pending_manual_fetch is True, "pending 未置位")
    check("点击后按钮被置灰", not mw.refresh_news_btn.isEnabled())
    mw._pending_manual_fetch = False
    mw._set_fetch_buttons_enabled(True)

    # 2) 真实鼠标点击迷你窗 ⟳ 按钮（经信号回到主窗口）
    mw._pending_manual_fetch = False
    ft.reset_seen()
    QTest.mouseClick(mw.mini_window.btn_fetch, Qt.MouseButton.LeftButton)
    check("点击迷你窗 ⟳ 经信号触发主窗口抓取",
          mw._pending_manual_fetch is True, "pending 未置位")
    mw._pending_manual_fetch = False
    mw._set_fetch_buttons_enabled(True)

    # 3) 卡片右键 → 真的弹出菜单 → 菜单项齐备 → 真的点"清空"生效
    captured = {}

    def fake_exec(self, *args, **kwargs):
        captured['menu'] = self
        captured['texts'] = [a.text() for a in self.actions() if a.text()]
        return None  # 不真正进入模态循环

    with ExitStack() as stack:
        stack.enter_context(patch.object(mod.QMenu, 'exec', fake_exec))
        stack.enter_context(patch.object(
            mod.QMessageBox, 'question',
            return_value=mod.QMessageBox.StandardButton.Yes))

        card = mw.news_layout.itemAt(0).widget()
        QApplication.sendEvent(card, QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, QPoint(5, 5),
            card.mapToGlobal(QPoint(5, 5))))
        check("卡片右键真的弹出了菜单", 'menu' in captured)
        texts = captured.get('texts', [])
        check("菜单里含「立即抓取一次」", any('立即抓取' in t for t in texts), f"{texts}")
        check("菜单里含「清空全部新闻」", any('清空' in t for t in texts), f"{texts}")

        act_clear = next((a for a in captured['menu'].actions()
                          if '清空' in a.text()), None)
        act_clear.trigger()
        check("点菜单「清空全部新闻」后列表真被清空",
              mw.news_layout.count() == 1, f"got {mw.news_layout.count()}")
        check("点菜单清空后迷你窗同步为空",
              len(mw.mini_window.news_history) == 0)

        # 4) 卡片内文本编辑框上右键，也要转发到窗口菜单
        mw.add_news(demo)
        card2 = mw.news_layout.itemAt(0).widget()
        captured.clear()
        QApplication.sendEvent(card2.content_edit, QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, QPoint(3, 3), QPoint(200, 200)))
        check("文本编辑框上右键同样转发到窗口菜单",
              any('清空' in t for t in captured.get('texts', [])),
              f"{captured.get('texts')}")

        # 5) 迷你窗右键菜单
        captured.clear()
        QApplication.sendEvent(mw.mini_window, QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, QPoint(5, 5), QPoint(300, 300)))
        mini_texts = captured.get('texts', [])
        check("迷你窗右键含「立即抓取一次」",
              any('立即抓取' in t for t in mini_texts), f"{mini_texts}")
        check("迷你窗右键含「清空新闻」",
              any('清空' in t for t in mini_texts), f"{mini_texts}")

        # 6) 真实点击迷你窗底部「清空」按钮
        mw.add_news(demo)
        check("准备：迷你窗有 1 条", len(mw.mini_window.news_history) == 1)
        QTest.mouseClick(mw.mini_window.btn_clear, Qt.MouseButton.LeftButton)
        check("点击迷你窗「清空」按钮后两侧都清空",
              len(mw.mini_window.news_history) == 0 and mw.news_layout.count() == 1,
              f"mini={len(mw.mini_window.news_history)}, main={mw.news_layout.count()}")

    # 7) 键盘 ↑/↓ 真实按键导航
    mw.add_news([
        {"id": "kb-1", "time": "2026-10-22 11:40", "rich_text": "键盘测试 A",
         "images": [], "source": "test"},
        {"id": "kb-2", "time": "2026-10-22 11:41", "rich_text": "键盘测试 B",
         "images": [], "source": "test"},
    ])
    mw.mini_window.current_view = 0
    mw.mini_window.current_index = 0
    mw.mini_window._display_at_index()
    QTest.keyClick(mw.mini_window, Qt.Key.Key_Up)
    check("迷你窗按 ↑ 真的翻到更早一条", mw.mini_window.current_index == 1,
          f"got {mw.mini_window.current_index}")
    QTest.keyClick(mw.mini_window, Qt.Key.Key_Down)
    check("迷你窗按 ↓ 真的翻回更新一条", mw.mini_window.current_index == 0,
          f"got {mw.mini_window.current_index}")

    ft.running = False
    ft._fetch_requested = False
except Exception as e:
    check("real click simulation", False, str(e))
    import traceback; traceback.print_exc()

# ── Test 12: 菜单项的真实鼠标点击（不用 action.trigger() 走捷径）──
print("\n[Test 12] 菜单项真实鼠标点击（popup + QTest.mouseClick）")
try:
    from PyQt6.QtTest import QTest
    from PyQt6.QtGui import QContextMenuEvent
    from PyQt6.QtCore import QPoint
    from contextlib import ExitStack
    from unittest.mock import patch

    mw.clear_all_news(confirm=False)
    mw.add_news([{"id": "menu-1", "time": "2026-10-22 11:50",
                  "rich_text": "菜单真实点击测试", "images": [], "source": "test"}])
    check("准备：1 张卡片", mw.news_layout.count() == 1,
          f"got {mw.news_layout.count()}")

    shown = {}

    def popup_instead_of_exec(self, *args, **kwargs):
        # 真正把菜单 popup 出来（popup 立即返回），只跳过 exec 的模态循环
        pos = args[0] if args else QPoint(200, 200)
        self.popup(pos)
        shown['menu'] = self
        return None

    with ExitStack() as stack:
        stack.enter_context(patch.object(mod.QMenu, 'exec', popup_instead_of_exec))
        stack.enter_context(patch.object(
            mod.QMessageBox, 'question',
            return_value=mod.QMessageBox.StandardButton.Yes))

        card = mw.news_layout.itemAt(0).widget()
        QApplication.sendEvent(card, QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, QPoint(5, 5),
            card.mapToGlobal(QPoint(5, 5))))
        QTest.qWait(60)

        menu = shown.get('menu')
        check("菜单真的显示到了屏幕上", menu is not None and menu.isVisible(),
              f"visible={menu.isVisible() if menu else None}")
        act = next((a for a in menu.actions() if '清空' in a.text()), None)
        check("找到「清空全部新闻」菜单项", act is not None)
        rect = menu.actionGeometry(act)
        check("菜单项有真实可点击区域",
              rect.isValid() and not rect.isEmpty(), f"rect={rect}")

        # 真实鼠标点击菜单项所在矩形（不是 trigger 捷径）
        QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=rect.center())
        QTest.qWait(60)
        check("真实点击菜单项后主列表被清空", mw.news_layout.count() == 1,
              f"got {mw.news_layout.count()}")
        check("真实点击后迷你窗同步为空",
              len(mw.mini_window.news_history) == 0,
              f"got {len(mw.mini_window.news_history)}")
        check("点击后菜单自动收起", not menu.isVisible())
except Exception as e:
    check("real menu click", False, str(e))
    import traceback; traceback.print_exc()

# ── Test 13: 清空确认框真实弹窗 + 真实点击「是」──
print("\n[Test 13] 清空确认框真实弹窗并点击「是」")
try:
    from PyQt6.QtTest import QTest
    from PyQt6.QtCore import QTimer

    mw.clear_all_news(confirm=False)
    mw.add_news([{"id": "dlg-1", "time": "2026-10-22 11:55",
                  "rich_text": "确认框测试", "images": [], "source": "test"}])
    check("准备：1 张卡片", mw.news_layout.count() == 1,
          f"got {mw.news_layout.count()}")

    state = {'clicked': False, 'attempts': 0}

    def click_yes():
        """在模态事件循环里找到确认框，真实点击它的「是」按钮。"""
        state['attempts'] += 1
        for w in QApplication.topLevelWidgets():
            if isinstance(w, mod.QMessageBox) and w.isVisible():
                yes = w.button(mod.QMessageBox.StandardButton.Yes)
                if yes is not None:
                    QTest.mouseClick(yes, Qt.MouseButton.LeftButton)
                    state['clicked'] = True
                    return
        if state['attempts'] < 60:
            QTimer.singleShot(100, click_yes)

    def force_close():
        """保险：万一没点中，强制关掉对话框，避免测试永久挂死。"""
        for w in QApplication.topLevelWidgets():
            if isinstance(w, mod.QMessageBox) and w.isVisible():
                w.reject()

    QTimer.singleShot(150, click_yes)
    QTimer.singleShot(6000, force_close)
    ok = mw.clear_all_news(confirm=True)  # 这里会真的弹出模态确认框

    check("确认框被真实点击了「是」", state['clicked'] is True,
          f"attempts={state['attempts']}")
    check("点「是」后真的执行了清空",
          ok is True and mw.news_layout.count() == 1,
          f"ok={ok}, count={mw.news_layout.count()}")
except Exception as e:
    check("real dialog click", False, str(e))
    import traceback; traceback.print_exc()

# ── Cleanup ──
mw.price_fetcher_thread.stop()
mw.deleteLater()

print("\n" + "=" * 60)
print(f"结果: {PASS} passed, {FAIL} failed")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
