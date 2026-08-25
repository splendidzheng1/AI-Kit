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

# ── Cleanup ──
mw.price_fetcher_thread.stop()
mw.deleteLater()

print("\n" + "=" * 60)
print(f"结果: {PASS} passed, {FAIL} failed")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
