import sys
import requests
import ctypes
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QLabel, QScrollArea, QFrame, QSystemTrayIcon, QMenu, QPushButton, QSizePolicy, QTextEdit,
                             QDialog, QSpinBox, QDoubleSpinBox, QAbstractSpinBox,
                             QStackedWidget, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QEvent, QSettings, QPointF
from PyQt6.QtGui import QIcon, QFont, QAction, QPixmap, QPainter, QColor, QKeySequence, QShortcut
from PIL import Image, ImageDraw
import io
import keyboard
import time
import webbrowser

# 全局快捷键配置
# 可以在这里方便地修改快捷键
GLOBAL_HOTKEY = 'shift+space'

# Mini mode default opacity (0.0 = fully transparent, 1.0 = fully opaque)
# The window is practically invisible at 0.0 but still receives mouse events
# (internally clamped to 0.01 minimum for Windows event compatibility).
# Adjust this value to change the default transparency of mini mode.
MINI_MODE_DEFAULT_OPACITY = 0.0

# ──────────────────────────────────────────────────────────────────── #
#  价格盯盘品种配置                                                      #
# ──────────────────────────────────────────────────────────────────── #
INSTRUMENTS = [
    {"code": "hf_GC",       "name": "COMEX黄金",  "category": "futures", "decimals": 2},
    {"code": "hf_CL",       "name": "WTI原油",    "category": "futures", "decimals": 2},
    {"code": "s_sh000001",  "name": "上证指数",    "category": "s_index", "decimals": 2},
    {"code": "s_sz399001",  "name": "深证成指",    "category": "s_index", "decimals": 2},
    {"code": "int_nikkei",  "name": "日经指数",    "category": "global",  "decimals": 2},
    {"code": "fx_susdcny",  "name": "美元人民币",  "category": "fx",      "decimals": 4},
    {"code": "fx_susdjpy",  "name": "美元日元",    "category": "fx",      "decimals": 4},
    {"code": "hf_CAD",      "name": "伦铜",        "category": "futures", "decimals": 2},
    {"code": "hf_AHD",      "name": "伦铝",        "category": "futures", "decimals": 2},
]
INST_BY_CODE = {inst["code"]: inst for inst in INSTRUMENTS}

class NewsFetcherThread(QThread):
    news_updated = pyqtSignal(list)

    def __init__(self, fetch_interval=600):
        super().__init__()
        self.seen_ids = set()
        self.api_base = "http://zhibo.sina.com.cn/api/zhibo/feed"
        self.running = True
        self.fetch_interval = fetch_interval  # Configurable polling interval in seconds

    def run(self):
        while self.running:
            try:
                news_list = self.fetch_24h_news()
                if news_list:
                    # 过滤已读
                    new_items = []
                    for news in news_list:
                        if news['id'] not in self.seen_ids:
                            self.seen_ids.add(news['id'])
                            new_items.append(news)
                    
                    if new_items:
                        # 按时间正序排列
                        new_items.sort(key=lambda x: x.get("time", ""))
                        self.news_updated.emit(new_items)
            except Exception as e:
                print(f"Fetch error: {e}")
            
            # Wait for the configurable interval before fetching again
            for _ in range(self.fetch_interval):
                if not self.running:
                    return
                self.msleep(1000)

    def fetch_24h_news(self, page=1, page_size=20):
        url = f"{self.api_base}?page={page}&page_size={page_size}&zhibo_id=152"
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            if (
                "result" in data
                and "data" in data["result"]
                and "feed" in data["result"]["data"]
                and "list" in data["result"]["data"]["feed"]
            ):
                return self.parse_news(data["result"]["data"]["feed"]["list"])
            return []
        except:
            return []

    def parse_news(self, raw_news_list):
        news_list = []
        for item in raw_news_list:
            try:
                multimedia = item.get("multimedia", {})
                if isinstance(multimedia, str):
                    try:
                        import json
                        multimedia = json.loads(multimedia)
                    except:
                        multimedia = {}
                
                images = multimedia.get("img_url", [])
                # Ensure images is a list
                if isinstance(images, str):
                    images = [images]
                
                news = {
                    "id": str(item.get("id", "")),
                    "title": item.get("rich_text", ""),
                    "time": item.get("create_time", ""),
                    "rich_text": item.get("rich_text", ""),
                    "images": images,
                    "source": "新浪7x24财经",
                }
                news_list.append(news)
            except:
                continue
        return news_list

    def stop(self):
        self.running = False
        self.wait()


# ════════════════════════════════════════════════════════════════════ #
#  价格盯盘组件                                                          #
# ════════════════════════════════════════════════════════════════════ #

class PriceFetcherThread(QThread):
    """后台线程：定时从新浪财经拉取 9 个品种实时价格（单次 HTTP 请求）。"""

    prices_updated = pyqtSignal(dict)

    def __init__(self, interval=5):
        super().__init__()
        self.interval = interval
        self.running = True
        self.headers = {"Referer": "https://finance.sina.com.cn/"}

    def run(self):
        while self.running:
            try:
                data = self._fetch_prices()
                if data:
                    self.prices_updated.emit(data)
            except Exception as e:
                print(f"Price fetch error: {e}")

            for _ in range(self.interval):
                if not self.running:
                    return
                self.msleep(1000)

    def _fetch_prices(self):
        codes = ",".join(inst["code"] for inst in INSTRUMENTS)
        url = f"http://hq.sinajs.cn/list={codes}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.encoding = "gbk"
            return self._parse_response(resp.text)
        except:
            return {}

    def _parse_response(self, text):
        result = {}
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or "var hq_str_" not in line:
                continue
            try:
                rest = line[len("var hq_str_"):]
                code, _, data_str = rest.partition("=")
                code = code.strip()
                data_str = data_str.strip().strip('";')
                if not data_str:
                    continue
                fields = data_str.split(",")
                parsed = self._parse_by_category(code, fields)
                if parsed:
                    result[code] = parsed
            except:
                continue
        return result

    def _parse_by_category(self, code, fields):
        inst = INST_BY_CODE.get(code)
        if not inst:
            return None
        cat = inst["category"]
        try:
            if cat == "futures":
                price = float(fields[0]) if fields[0] else None
                prev_close = float(fields[7]) if len(fields) > 7 and fields[7] else None
                name = fields[13] if len(fields) > 13 else inst["name"]
                change_pct = None
                if price and prev_close and prev_close > 0:
                    change_pct = (price - prev_close) / prev_close * 100
                return {"price": price, "change_pct": change_pct, "name": name, "timestamp": datetime.now()}

            elif cat in ("s_index", "global"):
                name = fields[0] if fields else inst["name"]
                price = float(fields[1]) if len(fields) > 1 and fields[1] else None
                change_pct = float(fields[3]) if len(fields) > 3 and fields[3] else None
                return {"price": price, "change_pct": change_pct, "name": name, "timestamp": datetime.now()}

            elif cat == "fx":
                price = float(fields[1]) if len(fields) > 1 and fields[1] else None
                name = fields[9] if len(fields) > 9 else inst["name"]
                return {"price": price, "change_pct": None, "name": name, "timestamp": datetime.now()}
        except (ValueError, IndexError):
            return None
        return None

    def stop(self):
        self.running = False
        self.wait()


class SparklineWidget(QWidget):
    """用 QPainter 画 polyline 折线图，涨红跌绿着色。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points = []
        self.setMinimumHeight(25)

    def set_points(self, points):
        self._points = list(points) if points else []
        self.update()

    def paintEvent(self, event):
        if len(self._points) < 2:
            return
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w = self.width()
            h = self.height()
            if w <= 0 or h <= 0:
                return
            pmin = min(self._points)
            pmax = max(self._points)
            prange = pmax - pmin if pmax > pmin else 1

            # 涨红跌绿（中国习惯）
            if self._points[-1] > self._points[0]:
                color = QColor(255, 68, 68)
            elif self._points[-1] < self._points[0]:
                color = QColor(0, 204, 102)
            else:
                color = QColor(136, 136, 136)

            pen = painter.pen()
            pen.setColor(color)
            pen.setWidthF(1.5)  # PyQt6 的 setWidth 只接受 int，传 float 会抛异常导致折线画不出来
            painter.setPen(pen)

            n = len(self._points)
            pts = []
            for i, p in enumerate(self._points):
                x = (i / (n - 1)) * w if n > 1 else 0
                y = h - ((p - pmin) / prange) * (h - 4) - 2
                pts.append(QPointF(x, y))
            for i in range(len(pts) - 1):
                painter.drawLine(pts[i], pts[i + 1])
            painter.end()
        except Exception as e:
            print(f"Sparkline paintEvent error: {e}")


class PriceCard(QFrame):
    """单个品种卡片，分四区：①名称 ④涨跌幅 ②价格 ③折线图。"""

    def __init__(self, inst, node_count=30, parent=None):
        super().__init__(parent)
        self.inst = inst
        self.node_count = node_count
        self.data_history = []  # [(timestamp, price, change_pct), ...] — 存全部历史

        self.setFixedSize(128, 95)
        # 卡片底色比外框 (#1e1e1e) 略亮，形成轻微浮起的层次感；
        # 涨跌文字与折线图统一使用红涨绿跌，保持色彩和谐
        self.setStyleSheet("""
            PriceCard {
                background-color: #242424;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
            PriceCard:hover {
                border: 1px solid #4a4a4a;
                background-color: #282828;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        # ① 名称(左) + ④ 涨跌幅(右)
        top_row = QHBoxLayout()
        self.lbl_name = QLabel(inst["name"])
        self.lbl_name.setStyleSheet("color: #ccc; font-size: 11px; font-weight: bold;")
        top_row.addWidget(self.lbl_name)
        top_row.addStretch()
        self.lbl_change = QLabel("--")
        self.lbl_change.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
        top_row.addWidget(self.lbl_change)
        layout.addLayout(top_row)

        # ② 价格（中央大字）
        self.lbl_price = QLabel("--")
        self.lbl_price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_price.setStyleSheet("color: #fff; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.lbl_price)

        # ③ 折线图
        self.spark = SparklineWidget()
        self.spark.setFixedHeight(28)
        layout.addWidget(self.spark)

    def update_price(self, data):
        price = data.get("price")
        change = data.get("change_pct")
        ts = data.get("timestamp", datetime.now())

        if price is not None:
            dec = self.inst.get("decimals", 2)
            self.lbl_price.setText(f"{price:.{dec}f}")

        # FX 无直接涨跌幅 → 从历史首点自算
        if change is None and price is not None and len(self.data_history) >= 1:
            first_price = self.data_history[0][1]
            if first_price and first_price > 0:
                change = (price - first_price) / first_price * 100

        if change is not None:
            if change > 0:
                color = "#ff4444"
                sign = "+"
            elif change < 0:
                color = "#00cc66"
                sign = ""
            else:
                color = "#888"
                sign = ""
            self.lbl_change.setText(f"{sign}{change:.2f}%")
            self.lbl_change.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")

        self.data_history.append((ts, price, change))
        recent = [p for _, p, _ in self.data_history[-self.node_count:] if p is not None]
        self.spark.set_points(recent)

    def set_node_count(self, n):
        self.node_count = n
        recent = [p for _, p, _ in self.data_history[-n:] if p is not None]
        self.spark.set_points(recent)


class AutoHeightTextEdit(QTextEdit):
    """QTextEdit that auto-grows to fit content and emits ctrl_clicked on Ctrl+Click."""

    ctrl_clicked = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setText(text)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: #e0e0e0;
                font-size: 13px;
                line-height: 1.4;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 6px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        # Set a reasonable max height for the text area itself
        self.setMaximumHeight(150)

    def sizeHint(self):
        # Calculate document height
        doc_height = self.document().size().height()
        # Add a little padding to avoid scrollbar flickering for near-matches
        return QSize(self.width(), int(doc_height + 10))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateGeometry()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = QApplication.keyboardModifiers()
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                self.ctrl_clicked.emit()
                return
        super().mousePressEvent(event)

class NewsCard(QFrame):
    def __init__(self, news_data, parent=None):
        super().__init__(parent)
        self.news_data = news_data
        self.init_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = QApplication.keyboardModifiers()
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                self.on_ctrl_click()
        super().mousePressEvent(event)

    def on_ctrl_click(self):
        images = self.news_data.get('images', [])
        if images:
            try:
                # Handle potential different formats (str or dict)
                url = images[0]
                if isinstance(url, dict):
                    url = url.get('url')
                
                if url and isinstance(url, str):
                    webbrowser.open(url)
            except Exception as e:
                print(f"Failed to open image: {e}")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Time
        time_label = QLabel(self.news_data['time'])
        time_label.setStyleSheet("color: #aaa; font-size: 12px; font-weight: bold;")
        layout.addWidget(time_label)

        # Content using AutoHeightTextEdit
        self.content_edit = AutoHeightTextEdit(self.news_data['rich_text'])
        self.content_edit.ctrl_clicked.connect(self.on_ctrl_click)
        layout.addWidget(self.content_edit)

        # Images (Only show first one for simplicity if exists)
        if self.news_data.get('images'):
            img_label = QLabel("[包含图片 - 请在浏览器查看详情]")
            img_label.setStyleSheet("color: #4da6ff; font-size: 12px; margin-top: 5px;")
            layout.addWidget(img_label)

        # Style for the card
        self.setStyleSheet("""
            NewsCard {
                background-color: #1e1e1e;
                border-radius: 8px;
                border: 1px solid #333;
            }
            NewsCard:hover {
                border: 1px solid #555;
                background-color: #252525;
            }
        """)

    def set_highlight(self, active):
        if active:
            self.setStyleSheet("""
                NewsCard {
                    background-color: #333333;
                    border-radius: 8px;
                    border: 2px solid #4da6ff;
                }
            """)
        else:
            self.setStyleSheet("""
                NewsCard {
                    background-color: #1e1e1e;
                    border-radius: 8px;
                    border: 1px solid #333;
                }
                NewsCard:hover {
                    border: 1px solid #555;
                    background-color: #252525;
                }
            """)

    def contains_text(self, text):
        if not text:
            return False
        text = text.lower()
        return (text in self.news_data.get('rich_text', '').lower() or 
                text in self.news_data.get('time', '').lower())

class HorizontalWheelScrollArea(QScrollArea):
    """把竖向滚轮增量映射到横向滚动条的滚动区域（用于盯盘卡片视图）。

    滚轮向上 → 向左翻看更早的卡片，滚轮向下 → 向右翻看后面的卡片；
    触控板的小步进增量同样适用（按像素平滑滚动）。
    """

    def wheelEvent(self, event):
        bar = self.horizontalScrollBar()
        delta = event.angleDelta().y()
        if delta == 0:
            delta = event.angleDelta().x()
        if bar is not None and delta != 0:
            bar.setValue(bar.value() - delta)
            event.accept()
        else:
            super().wheelEvent(event)


class MiniNewsWindow(QWidget):
    """Mini floating window that shows only the latest news item.

    Positioned at the bottom-right of the primary screen. Default opacity
    is controlled by ``MINI_MODE_DEFAULT_OPACITY``. On hover the window
    becomes fully opaque so the user can read the news.
    """

    # Signal emitted when the user wants to return to normal mode.
    return_to_normal_mode = pyqtSignal()

    def __init__(self, parent=None, default_opacity=MINI_MODE_DEFAULT_OPACITY):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Configurable default opacity (clamped to 0.01 minimum for event compatibility)
        self.default_opacity = default_opacity

        # Fixed size so the button bar position never shifts
        self.setFixedWidth(400)
        self.setFixedHeight(180)

        # For dragging the frameless window
        self.old_pos = None

        # Accept keyboard focus so ↑/↓ navigation works inside this window
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Auto-repeat timer for hold-to-scroll (buttons and arrow keys).
        # We use TWO timers so a quick click only flips ONE item, and a
        # long press waits for ``_initial_delay`` before the repeat kicks
        # in at ``_repeat_interval`` ms intervals. Without the initial
        # delay, even a brief tap (e.g. an accidental press) would
        # immediately start repeating, which felt too twitchy.
        self._initial_delay = QTimer(self)
        self._initial_delay.setSingleShot(True)
        self._initial_delay.setInterval(400)  # ms before repeat begins
        self._initial_delay.timeout.connect(self._begin_repeat)

        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(250)  # ms between repeats while held
        self._auto_timer.timeout.connect(self._on_auto_repeat)
        self._auto_action = None  # 'older' | 'newer'

        # The current news card displayed inside this mini window
        self.current_card = None

        # Navigation history: list of news dicts, newest first (index 0).
        # ``current_index`` points to the item currently shown.
        self.news_history = []
        self.current_index = 0

        # Price monitoring state
        self.price_cards = {}
        self.price_data = {}
        self.current_view = 0  # 0=news, 1=price
        self._news_size = (400, 180)
        # Price view uses the SAME size as news view — cards scroll horizontally

        settings = QSettings()
        self.price_interval = settings.value("price_interval", 5, type=int)
        self.price_node_count = settings.value("price_node_count", 30, type=int)
        saved_order_str = settings.value("price_card_order", "", type=str)
        if saved_order_str:
            self.price_card_order = saved_order_str.split(",")
        else:
            self.price_card_order = [i["code"] for i in INSTRUMENTS]

        # Build the UI
        self.setup_ui()

        # Apply initial opacity
        self.setWindowOpacity(max(self.default_opacity, 0.01))

    # ------------------------------------------------------------------ #
    #  UI setup                                                           #
    # ------------------------------------------------------------------ #

    def setup_ui(self):
        """Build the internal layout: a single NewsCard + return button."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(2)

        # ── Stacked widget: page 0 = news, page 1 = price cards ──
        self.stacked = QStackedWidget()

        # --- Page 0: News view ---
        self.news_page = QWidget()
        news_layout = QVBoxLayout(self.news_page)
        news_layout.setContentsMargins(0, 0, 0, 0)
        news_layout.setSpacing(0)

        self.card_container = QWidget()
        self.card_container.setStyleSheet("background-color: transparent;")
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(0)
        news_layout.addWidget(self.card_container, 1)
        self.stacked.addWidget(self.news_page)

        # --- Page 1: Price cards view (cards inside an outer frame) ---
        self.price_page = QWidget()
        price_layout = QVBoxLayout(self.price_page)
        price_layout.setContentsMargins(0, 0, 0, 0)
        price_layout.setSpacing(0)

        # 外框容器：与新闻视图的 NewsCard 保持同一套视觉框架，
        # 卡片视图嵌在这个外框内部，切换视图时整体轮廓保持一致
        self.price_frame = QFrame()
        self.price_frame.setObjectName("PriceFrame")
        self.price_frame.setStyleSheet("""
            QFrame#PriceFrame {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
            }
        """)
        frame_layout = QVBoxLayout(self.price_frame)
        frame_layout.setContentsMargins(6, 6, 6, 6)
        frame_layout.setSpacing(0)

        self.price_scroll = HorizontalWheelScrollArea()
        self.price_scroll.setWidgetResizable(True)
        self.price_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.price_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.price_scroll.setFrameStyle(QFrame.Shape.NoFrame)
        self.price_scroll.setStyleSheet("""
            QScrollArea { background-color: transparent; border: none; }
            QScrollBar:horizontal { border: none; background: #2d2d2d; height: 6px; margin: 0; border-radius: 3px; }
            QScrollBar::handle:horizontal { background: #555; min-width: 20px; border-radius: 3px; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
        """)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background-color: transparent;")
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(2, 4, 2, 4)
        self.cards_layout.setSpacing(6)

        for code in self.price_card_order:
            inst = INST_BY_CODE.get(code)
            if inst:
                card = PriceCard(inst, self.price_node_count)
                self.price_cards[code] = card
                self.cards_layout.addWidget(card)
        self.cards_layout.addStretch(1)

        self.price_scroll.setWidget(self.cards_container)
        frame_layout.addWidget(self.price_scroll)
        price_layout.addWidget(self.price_frame)
        self.stacked.addWidget(self.price_page)

        main_layout.addWidget(self.stacked, 1)

        # Small return-to-normal-mode button at the bottom-right
        btn_bar = QWidget()
        btn_bar.setStyleSheet("background-color: transparent;")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)
        btn_layout.addStretch()

        # Navigation buttons (up = older, down = newer)
        nav_btn_style = """
            QPushButton {
                background-color: #333;
                color: #ccc;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 12px;
                min-width: 24px;
            }
            QPushButton:hover {
                background-color: #444;
                color: #fff;
                border: 1px solid #4da6ff;
            }
            QPushButton:pressed {
                background-color: #222;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #555;
                border: 1px solid #333;
            }
        """

        self.btn_up = QPushButton("▲")
        self.btn_up.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_up.setToolTip("上一条（更早）· 键盘 ↑ / 长按连翻")
        self.btn_up.setStyleSheet(nav_btn_style)
        self.btn_up.pressed.connect(lambda: self._start_auto('older'))
        self.btn_up.released.connect(self._stop_auto)
        btn_layout.addWidget(self.btn_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_down.setToolTip("下一条（更新）· 键盘 ↓ / 长按连翻")
        self.btn_down.setStyleSheet(nav_btn_style)
        self.btn_down.pressed.connect(lambda: self._start_auto('newer'))
        self.btn_down.released.connect(self._stop_auto)
        btn_layout.addWidget(self.btn_down)

        # Jump straight back to the newest item
        self.btn_latest = QPushButton("最新")
        self.btn_latest.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_latest.setToolTip("一键回到最新一条")
        self.btn_latest.setStyleSheet(nav_btn_style)
        self.btn_latest.clicked.connect(self.show_latest)
        btn_layout.addWidget(self.btn_latest)

        # View toggle button
        self.btn_watch = QPushButton("实时盯盘")
        self.btn_watch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_watch.setStyleSheet(nav_btn_style)
        self.btn_watch.clicked.connect(self.toggle_view)
        btn_layout.addWidget(self.btn_watch)

        btn_return = QPushButton("返回正常模式")
        btn_return.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_return.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #ccc;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #444;
                color: #fff;
            }
            QPushButton:pressed {
                background-color: #222;
            }
        """)
        btn_return.clicked.connect(self.return_to_normal_mode.emit)
        btn_layout.addWidget(btn_return)
        main_layout.addWidget(btn_bar)

        # Semi-transparent dark background for the whole widget
        self.setStyleSheet("""
            MiniNewsWindow {
                background-color: rgba(0, 0, 0, 220);
                border: 1px solid #333;
                border-radius: 5px;
            }
        """)

    # ------------------------------------------------------------------ #
    #  Hover opacity handling                                             #
    # ------------------------------------------------------------------ #

    def enterEvent(self, event):
        """When the mouse enters, make the window fully opaque and grab keyboard focus."""
        self.setWindowOpacity(1.0)
        self.setFocus()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """When the mouse leaves, restore the configured default opacity."""
        self.setWindowOpacity(max(self.default_opacity, 0.01))
        super().leaveEvent(event)

    # ------------------------------------------------------------------ #
    #  Dragging support (same logic as MainWindow)                        #
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                self.old_pos = event.globalPosition().toPoint()
        except Exception as e:
            print(f"mousePressEvent error: {e}")

    def mouseMoveEvent(self, event):
        try:
            if self.old_pos:
                delta = event.globalPosition().toPoint() - self.old_pos
                self.move(self.pos() + delta)
                self.old_pos = event.globalPosition().toPoint()
        except Exception as e:
            print(f"mouseMoveEvent error: {e}")

    def mouseReleaseEvent(self, event):
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                self.old_pos = None
        except Exception as e:
            print(f"mouseReleaseEvent error: {e}")

    # ------------------------------------------------------------------ #
    #  Context menu for returning to normal mode                         #
    # ------------------------------------------------------------------ #

    def contextMenuEvent(self, event):
        """Right-click menu offering a return to normal mode."""
        menu = QMenu(self)
        action_return = QAction("返回正常模式", self)
        action_return.triggered.connect(self.return_to_normal_mode.emit)
        menu.addAction(action_return)
        menu.addSeparator()
        action_close = QAction("关闭", self)
        action_close.triggered.connect(self.hide)
        menu.addAction(action_close)
        menu.exec(event.globalPos())

    # ------------------------------------------------------------------ #
    #  News update & navigation                                           #
    # ------------------------------------------------------------------ #

    def update_news(self, news_data):
        """Receive a new news item, prepend it to history and display it.

        Args:
            news_data: A dict containing the keys ``id``, ``time``,
                        ``rich_text``, ``images``, ``source``, etc.
        """
        self.add_news_batch([news_data])

    def add_news_batch(self, news_list):
        """Receive multiple new items at once and merge them into history.

        ``news_list`` is expected to be in **ascending** time order
        (oldest first, newest last) — the same order the fetcher emits.
        Items are deduplicated against the existing history, then
        inserted at the front so the newest ends up at index 0.

        Args:
            news_list: A list of news dicts (ascending time order).
        """
        if not news_list:
            return

        # Filter out None entries (e.g. from update_news(None) calls)
        news_list = [n for n in news_list if n is not None]
        if not news_list:
            return

        existing_ids = {n.get('id') for n in self.news_history}
        to_add = [n for n in news_list if n.get('id') not in existing_ids]
        if not to_add:
            # All items already known — do NOT reset the display position.
            # This allows entering mini mode without losing the user's
            # current browsing position.
            return

        # Insert in ascending order (oldest first). Each insert(0, ...)
        # pushes previous items down, so the last (newest) ends up at
        # index 0 — which is exactly what we want.
        for news in to_add:
            self.news_history.insert(0, news)

        # Cap history to prevent unbounded growth (match main window limit)
        max_history = 1000
        if len(self.news_history) > max_history:
            self.news_history = self.news_history[:max_history]

        self.current_index = 0
        self._display_at_index()

    def set_news_history(self, news_list):
        """Initialize the history from an existing list of news dicts.

        Args:
            news_list: News dicts in newest-first order (same as the main
                       window's top-to-bottom card order).
        """
        self.news_history = list(news_list)
        self.current_index = 0
        if self.news_history:
            self._display_at_index()
        else:
            self._update_nav_buttons()

    def show_older(self):
        """Navigate to the previous (older) news item."""
        if self.current_index < len(self.news_history) - 1:
            self.current_index += 1
            self._display_at_index()

    def show_newer(self):
        """Navigate to the next (newer) news item."""
        if self.current_index > 0:
            self.current_index -= 1
            self._display_at_index()

    def show_latest(self):
        """Jump straight back to the newest news item (index 0)."""
        if self.news_history:
            self.current_index = 0
            self._display_at_index()

    # ------------------------------------------------------------------ #
    #  Hold-to-repeat navigation (buttons & arrow keys)                   #
    # ------------------------------------------------------------------ #

    def _start_auto(self, action):
        """Begin hold-to-scroll for ``action`` ('older' or 'newer').

        A single tap fires one navigation step immediately. If the
        button/key is still held when ``_initial_delay`` expires,
        ``_begin_repeat`` kicks off the periodic repeat loop.
        """
        if self._auto_action == action and (self._initial_delay.isActive() or self._auto_timer.isActive()):
            return
        self._auto_action = action
        self._auto_step()              # one step on press (handles single click)
        self._auto_timer.stop()        # ensure clean state
        self._initial_delay.start()    # arm the long-press timer

    def _stop_auto(self):
        """Stop the hold-to-scroll repeat loop."""
        self._initial_delay.stop()
        self._auto_timer.stop()
        self._auto_action = None

    def _begin_repeat(self):
        """Initial-delay elapsed; start the periodic repeat timer."""
        # Guard against the case where the action was switched (e.g.
        # opposite direction pressed) between press and timeout.
        if self._auto_action is not None and not self._auto_timer.isActive():
            self._auto_timer.start()

    def _on_auto_repeat(self):
        """Timer tick while a button/arrow key is held down."""
        self._auto_step()

    def _auto_step(self):
        """Perform one navigation step for the current auto action."""
        if self._auto_action == 'older':
            self.show_older()
        elif self._auto_action == 'newer':
            self.show_newer()

    # ------------------------------------------------------------------ #
    #  Keyboard navigation (↑ / ↓)                                        #
    # ------------------------------------------------------------------ #

    def keyPressEvent(self, event):
        # Only handle ↑/↓ navigation in news view (page 0)
        if self.current_view == 0:
            if event.key() == Qt.Key.Key_Up:
                self._start_auto('older')
                event.accept()
            elif event.key() == Qt.Key.Key_Down:
                self._start_auto('newer')
                event.accept()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.current_view == 0 and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self._stop_auto()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def _display_at_index(self):
        """Render the news card at ``self.current_index``."""
        if not (0 <= self.current_index < len(self.news_history)):
            return

        news_data = self.news_history[self.current_index]

        # Remove the old card if it exists
        if self.current_card is not None:
            self.card_layout.removeWidget(self.current_card)
            self.current_card.deleteLater()
            self.current_card = None

        # Create a fresh NewsCard and add it to the container
        self.current_card = NewsCard(news_data)
        self.card_layout.addWidget(self.current_card)

        # Window size is fixed, no need to adjust
        self._update_nav_buttons()

    def _update_nav_buttons(self):
        """Enable/disable the up/down/latest buttons based on the current index."""
        has_older = self.current_index < len(self.news_history) - 1
        has_newer = self.current_index > 0
        self.btn_up.setEnabled(has_older)
        self.btn_down.setEnabled(has_newer)
        self.btn_latest.setEnabled(has_newer)  # same condition as "has newer"

    # ------------------------------------------------------------------ #
    #  Price view: toggle, update, settings                                #
    # ------------------------------------------------------------------ #

    def toggle_view(self):
        """Switch between news view (page 0) and price card view (page 1).
        Window size stays the same — cards scroll horizontally."""
        try:
            if self.current_view == 0:
                self.current_view = 1
                self.stacked.setCurrentIndex(1)
                self.btn_watch.setText("快讯信息")
                self.btn_up.hide()
                self.btn_down.hide()
                self.btn_latest.hide()
            else:
                self.current_view = 0
                self.stacked.setCurrentIndex(0)
                self.btn_watch.setText("实时盯盘")
                self.btn_up.show()
                self.btn_down.show()
                self.btn_latest.show()
        except Exception as e:
            import traceback
            print(f"toggle_view error: {e}")
            traceback.print_exc()

    def update_prices(self, price_data):
        """Receive price data dict {code: {price, change_pct, name, timestamp}}."""
        try:
            for code, data in price_data.items():
                if code in self.price_cards:
                    self.price_cards[code].update_price(data)
        except Exception as e:
            import traceback
            print(f"update_prices error: {e}")
            traceback.print_exc()

    def apply_price_settings(self, interval, node_count, card_order):
        """Apply price monitoring settings (called from SettingsDialog)."""
        self.price_interval = interval
        self.price_node_count = node_count

        # Reorder cards if order changed
        if card_order != self.price_card_order:
            self.price_card_order = card_order
            # Remove all cards from layout (keep the stretch at end)
            for i in range(self.cards_layout.count() - 1, -1, -1):
                item = self.cards_layout.takeAt(i)
                w = item.widget()
                if w is not None:
                    w.setParent(None)
            # Re-add stretch first, then insert cards before it
            self.cards_layout.addStretch(1)
            for code in card_order:
                if code in self.price_cards:
                    self.cards_layout.insertWidget(self.cards_layout.count() - 1, self.price_cards[code])

        # Update node count on all cards
        for card in self.price_cards.values():
            card.set_node_count(node_count)

    # ------------------------------------------------------------------ #
    #  Positioning                                                        #
    # ------------------------------------------------------------------ #

    def position_bottom_right(self, margin=20):
        """Move the window to the bottom-right corner of the primary screen.

        Uses ``availableGeometry`` so the window does not overlap the taskbar.
        """
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        x = avail.right() - self.width() - margin
        y = avail.bottom() - self.height() - margin
        self.move(x, y)

    def showEvent(self, event):
        """Ensure correct position every time the window is shown."""
        self.position_bottom_right()
        super().showEvent(event)


class SettingsDialog(QDialog):
    """Modal settings dialog for configuring news fetcher parameters.

    Allows the user to configure:
        - max_cards: maximum number of news cards to keep in the list
        - mini_opacity: default opacity of the mini mode floating window
        - fetch_interval: polling interval (seconds) for the news fetcher thread

    Settings are persisted via QSettings and applied immediately on OK.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.main_window = parent

        # Load current values from QSettings (falling back to defaults)
        settings = QSettings()
        current_max_cards = settings.value("max_cards", 1000, type=int)
        current_opacity = settings.value("mini_opacity", 0.0, type=float)
        current_interval = settings.value("fetch_interval", 600, type=int)
        current_price_interval = settings.value("price_interval", 5, type=int)
        current_price_nodes = settings.value("price_node_count", 30, type=int)
        saved_order_str = settings.value("price_card_order", "", type=str)
        if saved_order_str:
            current_card_order = saved_order_str.split(",")
        else:
            current_card_order = [i["code"] for i in INSTRUMENTS]

        self._setup_ui(current_max_cards, current_opacity, current_interval,
                       current_price_interval, current_price_nodes, current_card_order)

    def _setup_ui(self, max_cards, opacity, interval, price_interval, price_nodes, card_order):
        """Build the dialog layout with dark theme styling.

        Each parameter row has: [Label] [SpinBox] [ - ] [ + ]
        The + / - buttons are placed outside the SpinBox and made large
        (36x32) so they are easy to click; the SpinBox has its built-in
        up/down arrows hidden via NoButtons.
        """
        # Dark theme stylesheet consistent with the main application.
        # Hide the QSpinBox built-in up/down arrows (we use our own +/- buttons).
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #333;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                min-height: 22px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #4da6ff;
            }
            /* Hide the built-in up/down arrow buttons */
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 0px;
                height: 0px;
                border: none;
            }
        """)

        self.setFixedSize(420, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # --- Helper to build one parameter row: [label] [spin] [-] [+] ---
        def make_param_row(label_text, spin_widget, step):
            """Create a horizontal row with label, spinbox and +/- buttons.

            Args:
                label_text: the parameter name to show on the left
                spin_widget: already-configured QSpinBox / QDoubleSpinBox
                step: how much + / - changes the value (int or float)
            """
            row = QHBoxLayout()
            row.setSpacing(8)

            lbl = QLabel(label_text)
            lbl.setMinimumWidth(150)

            # Hide the built-in up/down arrows; we have our own buttons
            spin_widget.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin_widget.setFixedSize(110, 32)
            spin_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Build the +/- button pair
            def make_btn(text):
                b = QPushButton(text)
                b.setFixedSize(36, 32)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet("""
                    QPushButton {
                        background-color: #3a3a3a;
                        color: #e0e0e0;
                        border: 1px solid #555;
                        border-radius: 4px;
                        font-size: 18px;
                        font-weight: bold;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #4a4a4a;
                        border: 1px solid #4da6ff;
                        color: #fff;
                    }
                    QPushButton:pressed {
                        background-color: #2a2a2a;
                    }
                    QPushButton:disabled {
                        background-color: #2a2a2a;
                        color: #666;
                        border: 1px solid #333;
                    }
                """)
                return b

            btn_minus = make_btn("−")  # U+2212 minus sign, more visible than hyphen
            btn_plus = make_btn("+")

            # Decrement / increment with range clamping via setValue
            def dec():
                spin_widget.setValue(spin_widget.value() - step)
            def inc():
                spin_widget.setValue(spin_widget.value() + step)

            btn_minus.clicked.connect(dec)
            btn_plus.clicked.connect(inc)

            row.addWidget(lbl)
            row.addWidget(spin_widget)
            row.addWidget(btn_minus)
            row.addWidget(btn_plus)
            return row

        # --- Row: max_cards (step 10) ---
        self.spin_max_cards = QSpinBox()
        self.spin_max_cards.setRange(10, 10000)
        self.spin_max_cards.setValue(max_cards)
        self.spin_max_cards.setSingleStep(10)  # arrow keys / wheel step
        layout.addLayout(make_param_row("新闻卡片最大数量", self.spin_max_cards, 10))

        # --- Row: mini_opacity (step 0.1) ---
        self.spin_opacity = QDoubleSpinBox()
        self.spin_opacity.setRange(0.0, 1.0)
        self.spin_opacity.setSingleStep(0.1)
        self.spin_opacity.setDecimals(1)
        self.spin_opacity.setValue(opacity)
        layout.addLayout(make_param_row("迷你模式默认透明度", self.spin_opacity, 0.1))

        # --- Row: fetch_interval (step 30 seconds) ---
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(10, 3600)
        self.spin_interval.setValue(interval)
        self.spin_interval.setSingleStep(30)
        self.spin_interval.setSuffix(" 秒")
        layout.addLayout(make_param_row("新闻抓取间隔", self.spin_interval, 30))

        # ── Section: Price monitoring ──
        lbl_price = QLabel("价格盯盘设置")
        lbl_price.setStyleSheet("color: #4da6ff; font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl_price)

        # price_interval row
        self.spin_price_interval = QSpinBox()
        self.spin_price_interval.setRange(2, 60)
        self.spin_price_interval.setValue(price_interval)
        self.spin_price_interval.setSingleStep(1)
        self.spin_price_interval.setSuffix(" 秒")
        layout.addLayout(make_param_row("价格请求间隔", self.spin_price_interval, 1))

        # price_node_count row
        self.spin_price_nodes = QSpinBox()
        self.spin_price_nodes.setRange(10, 120)
        self.spin_price_nodes.setValue(price_nodes)
        self.spin_price_nodes.setSingleStep(5)
        layout.addLayout(make_param_row("折线图节点数", self.spin_price_nodes, 5))

        # card_order QListWidget
        order_label = QLabel("卡片排列顺序")
        layout.addWidget(order_label)

        order_row = QHBoxLayout()
        self.list_order = QListWidget()
        self.list_order.setFixedHeight(120)
        self.list_order.setStyleSheet("""
            QListWidget {
                background-color: #333;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
                font-size: 13px;
            }
            QListWidget::item { padding: 2px 4px; }
            QListWidget::item:selected { background-color: #4da6ff; color: #fff; }
        """)
        for code in card_order:
            inst = INST_BY_CODE.get(code)
            if inst:
                item = QListWidgetItem(inst["name"])
                item.setData(Qt.ItemDataRole.UserRole, code)
                self.list_order.addItem(item)

        order_btns = QVBoxLayout()
        order_btns.setSpacing(4)
        self.btn_order_up = QPushButton("↑")
        self.btn_order_up.setFixedSize(36, 32)
        self.btn_order_up.setStyleSheet("""
            QPushButton { background-color: #3a3a3a; color: #e0e0e0; border: 1px solid #555; border-radius: 4px; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background-color: #4a4a4a; border: 1px solid #4da6ff; color: #fff; }
            QPushButton:pressed { background-color: #2a2a2a; }
        """)
        self.btn_order_up.clicked.connect(lambda: self._move_card_item(-1))
        self.btn_order_down = QPushButton("↓")
        self.btn_order_down.setFixedSize(36, 32)
        self.btn_order_down.setStyleSheet(self.btn_order_up.styleSheet())
        self.btn_order_down.clicked.connect(lambda: self._move_card_item(1))
        order_btns.addWidget(self.btn_order_up)
        order_btns.addWidget(self.btn_order_down)
        order_btns.addStretch()
        order_row.addWidget(self.list_order)
        order_row.addLayout(order_btns)
        layout.addLayout(order_row)

        layout.addStretch()

        # --- Buttons (OK / Cancel) ---
        btn_style = """
            QPushButton {
                background-color: #333;
                color: #ccc;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #444;
                color: #fff;
            }
            QPushButton:pressed {
                background-color: #222;
            }
        """

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_ok = QPushButton("确定")
        self.btn_ok.setFixedSize(80, 32)
        self.btn_ok.setStyleSheet(btn_style)
        self.btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ok.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFixedSize(80, 32)
        self.btn_cancel.setStyleSheet(btn_style)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(self.btn_ok)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

    def _move_card_item(self, direction):
        """Move the selected card order item up (-1) or down (+1)."""
        row = self.list_order.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if 0 <= new_row < self.list_order.count():
            item = self.list_order.takeItem(row)
            self.list_order.insertItem(new_row, item)
            self.list_order.setCurrentRow(new_row)

    def apply_settings(self):
        """Save settings to QSettings and apply them to the MainWindow immediately.

        This method is called only when the user clicks OK (Accepted).
        """
        settings = QSettings()

        new_max_cards = self.spin_max_cards.value()
        new_opacity = self.spin_opacity.value()
        new_interval = self.spin_interval.value()

        # Persist to QSettings for next launch
        settings.setValue("max_cards", new_max_cards)
        settings.setValue("mini_opacity", new_opacity)
        settings.setValue("fetch_interval", new_interval)

        # Apply to MainWindow immediately
        if self.main_window is not None:
            mw = self.main_window

            # --- max_cards: write back and trim excess cards if needed ---
            mw.max_cards = new_max_cards
            while mw.news_layout.count() > mw.max_cards:
                item = mw.news_layout.takeAt(mw.news_layout.count() - 1)
                if item is not None:
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()

            # --- mini_opacity: write back and update if mini mode is active ---
            mw.mini_opacity = new_opacity
            mw.mini_window.default_opacity = new_opacity
            if mw.mini_mode_active:
                mw.mini_window.setWindowOpacity(max(new_opacity, 0.01))

            # --- fetch_interval: write back to the fetcher thread ---
            mw.fetcher_interval = new_interval
            mw.fetcher_thread.fetch_interval = new_interval

            # --- price settings ---
            new_price_interval = self.spin_price_interval.value()
            new_price_nodes = self.spin_price_nodes.value()
            new_card_order = []
            for i in range(self.list_order.count()):
                item = self.list_order.item(i)
                new_card_order.append(item.data(Qt.ItemDataRole.UserRole))

            settings.setValue("price_interval", new_price_interval)
            settings.setValue("price_node_count", new_price_nodes)
            settings.setValue("price_card_order", ",".join(new_card_order))

            mw.price_fetcher_thread.interval = new_price_interval
            mw.mini_window.apply_price_settings(new_price_interval, new_price_nodes, new_card_order)


class MainWindow(QMainWindow):
    toggle_visibility_signal = pyqtSignal()

    # Maximum number of news cards to keep in the list.
    # Adjust this value to change the limit. Older cards (at the bottom)
    # are removed when the count exceeds this number.
    max_cards = 1000

    def __init__(self):
        super().__init__()
        # Frameless window, no title bar, no icon, always on top
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 600)
        
        # For dragging
        self.old_pos = None
        
        # Search state
        self.search_matches = []
        self.current_match_index = -1

        # Mini mode state
        self.mini_mode_active = False
        self.latest_news = None  # Keep track of the newest news item

        # Load persisted settings (override class-level defaults)
        settings = QSettings()
        self.max_cards = settings.value("max_cards", 1000, type=int)
        self.mini_opacity = settings.value("mini_opacity", 0.0, type=float)
        self.fetcher_interval = settings.value("fetch_interval", 600, type=int)
        self.price_interval = settings.value("price_interval", 5, type=int)

        # Setup UI
        self.setup_ui()
        
        # Shortcuts (Internal)
        self.setup_shortcuts()
        
        # Global Hotkey (System-wide)
        self.setup_global_hotkey()

        # Setup Tray
        self.setup_tray()

        # Create the mini news window (hidden by default)
        # Use the persisted opacity value instead of the module-level constant
        self.mini_window = MiniNewsWindow(default_opacity=self.mini_opacity)
        self.mini_window.return_to_normal_mode.connect(self.exit_mini_mode)

        # Start Fetcher with configurable interval
        self.fetcher_thread = NewsFetcherThread(fetch_interval=self.fetcher_interval)
        self.fetcher_thread.news_updated.connect(self.add_news)
        self.fetcher_thread.start()

        # Start Price Fetcher for real-time instrument monitoring
        self.price_fetcher_thread = PriceFetcherThread(interval=self.price_interval)
        self.price_fetcher_thread.prices_updated.connect(self.mini_window.update_prices)
        self.price_fetcher_thread.start()

    def setup_global_hotkey(self):
        # Connect the signal to the toggle slot
        self.toggle_visibility_signal.connect(self.toggle_window_visibility)
        self.last_toggle_time = 0
        # Whether the global hotkey is currently registered with the
        # ``keyboard`` library. We track this so focus events can
        # temporarily suspend the hotkey (e.g. while typing a search
        # query that contains a space) without losing the registration.
        self._global_hotkey_active = False

        # Register the hotkey using keyboard library
        # We use a lambda to emit the signal because keyboard runs in a separate thread
        try:
            keyboard.add_hotkey(GLOBAL_HOTKEY, self.toggle_visibility_signal.emit)
            self._global_hotkey_active = True
        except Exception as e:
            print(f"Failed to register global hotkey: {e}")

    def suspend_global_hotkey(self):
        """Temporarily remove the shift+space global hotkey.

        Used while the search input has focus, so the user can type
        spaces (and ``shift+space``) freely without the window
        toggling its visibility.
        """
        if not self._global_hotkey_active:
            return
        try:
            keyboard.remove_hotkey(GLOBAL_HOTKEY)
            self._global_hotkey_active = False
        except Exception as e:
            print(f"Failed to suspend global hotkey: {e}")

    def resume_global_hotkey(self):
        """Re-register the shift+space global hotkey after a suspend."""
        if self._global_hotkey_active:
            return
        try:
            keyboard.add_hotkey(GLOBAL_HOTKEY, self.toggle_visibility_signal.emit)
            self._global_hotkey_active = True
        except Exception as e:
            print(f"Failed to resume global hotkey: {e}")

    def eventFilter(self, obj, event):
        """Intercept focus events on the search input.

        QLineEdit does not expose ``focusIn`` / ``focusOut`` signals
        (only the protected ``focusInEvent`` / ``focusOutEvent`` hooks).
        We install this filter on the search box so we can suspend the
        global hotkey while the user is typing a query.
        """
        if obj is getattr(self, 'search_input', None):
            etype = event.type()
            if etype == QEvent.Type.FocusIn:
                self.suspend_global_hotkey()
            elif etype == QEvent.Type.FocusOut:
                self.resume_global_hotkey()
        return super().eventFilter(obj, event)

    def toggle_window_visibility(self):
        # Simple debounce to prevent double triggering
        current_time = time.time()
        if current_time - self.last_toggle_time < 0.3:
            return
        self.last_toggle_time = current_time

        # In mini mode, toggle the mini window instead of the main window
        if self.mini_mode_active:
            if self.mini_window.isVisible():
                self.mini_window.hide()
            else:
                self.mini_window.show()
        else:
            if self.isVisible():
                self.hide()
            else:
                self.show_window()

    def setup_shortcuts(self):
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self.toggle_search)

        # Toggle mini mode
        self.mini_mode_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        self.mini_mode_shortcut.activated.connect(self.toggle_mini_mode)

        # Open settings dialog
        self.settings_shortcut = QShortcut(QKeySequence("Ctrl+,"), self)
        self.settings_shortcut.activated.connect(self.open_settings)

    def toggle_search(self):
        if self.search_widget.isVisible():
            self.search_widget.hide()
            self.search_input.clear()
            self.perform_search("") # Clear search results
        else:
            self.search_widget.show()
            self.search_input.setFocus()
            self.search_input.selectAll()

    def setup_ui(self):
        # Central Widget
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Search Bar Area
        self.search_widget = QWidget()
        self.search_widget.setStyleSheet("background-color: transparent;")
        self.search_widget.hide() # Hidden by default
        search_layout = QHBoxLayout(self.search_widget)
        search_layout.setContentsMargins(10, 10, 45, 5) # Right margin for close button
        search_layout.setSpacing(5)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键字按回车搜索...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                color: #fff;
                border: 1px solid #555;
                border-radius: 15px;
                padding: 4px 12px;
                font-size: 13px;
                height: 20px;
            }
            QLineEdit:focus {
                border: 1px solid #4da6ff;
                background-color: #3a3a3a;
            }
        """)
        # Trigger search only on Enter
        self.search_input.returnPressed.connect(lambda: self.perform_search(self.search_input.text()))
        # Suspend the global shift+space hotkey while typing in the search
        # box, otherwise pressing space (or shift+space) inside a query
        # would toggle the window's visibility and interrupt input.
        # QLineEdit has no focusIn/focusOut signals, so we intercept the
        # underlying focus events via an event filter.
        self.search_input.installEventFilter(self)
        
        # Navigation Buttons
        btn_style = """
            QPushButton {
                background-color: #333;
                color: #ccc;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #444;
                color: #fff;
            }
            QPushButton:pressed {
                background-color: #222;
            }
        """
        
        # Search Trigger Button
        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedSize(28, 28)
        self.btn_search.setStyleSheet(btn_style)
        self.btn_search.setToolTip("搜索")
        self.btn_search.clicked.connect(lambda: self.perform_search(self.search_input.text()))
        
        self.btn_prev = QPushButton("▲")
        self.btn_prev.setFixedSize(28, 28)
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.clicked.connect(self.search_prev)
        
        self.btn_next = QPushButton("▼")
        self.btn_next.setFixedSize(28, 28)
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.clicked.connect(self.search_next)
        
        self.lbl_match_count = QLabel("")
        self.lbl_match_count.setStyleSheet("color: #888; font-size: 11px;")
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_search)
        search_layout.addWidget(self.lbl_match_count)
        search_layout.addWidget(self.btn_prev)
        search_layout.addWidget(self.btn_next)
        
        main_layout.addWidget(self.search_widget)

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # Hide scrollbar but keep functionality? Or style it very minimal.
        # Let's keep it minimal.
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #444;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Container for news cards
        self.news_container = QWidget()
        self.news_container.setStyleSheet("background-color: transparent;")
        self.news_layout = QVBoxLayout(self.news_container)
        self.news_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.news_layout.setSpacing(8) # Slightly tighter spacing
        self.news_layout.setContentsMargins(5, 5, 5, 5) # Small margin around content
        
        self.scroll_area.setWidget(self.news_container)
        main_layout.addWidget(self.scroll_area)

        # Apply style to the main window for background
        # We need a background for the frameless window, otherwise it might be fully transparent depending on OS
        # Using a slight semi-transparent white or solid white
        self.setStyleSheet("""
            #CentralWidget {
                background-color: rgba(0, 0, 0, 240); 
                border: 1px solid #333;
                border-radius: 5px;
            }
        """)

        # Close Button (Floating)
        self.close_btn = QPushButton("×", self)
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #aaa;
                font-size: 24px;
                border: none;
                font-weight: 300;
                line-height: 24px;
            }
            QPushButton:hover {
                color: #ff4444;
                background-color: rgba(255,255,255,0.1);
                border-radius: 15px;
            }
        """)

        # Mini Mode Button (Floating, positioned just left of the close button)
        self.mini_btn = QPushButton("📋", self)
        self.mini_btn.setFixedSize(30, 30)
        self.mini_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mini_btn.setToolTip("迷你模式")
        self.mini_btn.clicked.connect(self.enter_mini_mode)
        self.mini_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #aaa;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                color: #4da6ff;
                background-color: rgba(255,255,255,0.1);
                border-radius: 15px;
            }
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep close button at top-right corner
        if hasattr(self, 'close_btn'):
            self.close_btn.move(self.width() - 35, 5)
        # Keep mini mode button directly below the close button, so it
        # no longer overlaps the search input on the right side.
        if hasattr(self, 'mini_btn'):
            self.mini_btn.move(self.width() - 35, 40)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None

    def create_icon_image(self):
        # Generate a simple icon
        width = 64
        height = 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        dc.ellipse((4, 4, 60, 60), fill=(0, 122, 204))
        dc.text((20, 16), "News", fill="white")
        
        # Convert to QIcon
        byte_arr = io.BytesIO()
        image.save(byte_arr, format='PNG')
        qpixmap = QPixmap()
        qpixmap.loadFromData(byte_arr.getvalue())
        return QIcon(qpixmap)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.create_icon_image())

        # Menu
        self.tray_menu = QMenu()
        show_action = QAction("显示新闻", self)
        show_action.triggered.connect(self.show_window)
        # The text of this action is refreshed in refresh_tray_menu() right
        # before the menu opens, so it always shows the *opposite* of the
        # current mode (i.e. the action the user can take next).
        self.mini_action = QAction("迷你模式", self)
        self.mini_action.triggered.connect(self.toggle_mini_mode)
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.open_settings)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)

        self.tray_menu.addAction(show_action)
        self.tray_menu.addAction(self.mini_action)
        self.tray_menu.addAction(settings_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(quit_action)

        # Refresh menu item text right before the menu opens, so it always
        # matches the current mode.
        self.tray_menu.aboutToShow.connect(self.refresh_tray_menu)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        self.tray_icon.setToolTip("新浪财经7x24 (运行中)")

    def refresh_tray_menu(self):
        """Update the tray menu item text to reflect the current mode.

        In normal mode the menu shows ``迷你模式`` (clicking enters mini mode).
        In mini mode it shows ``正常模式`` (clicking returns to normal mode).
        """
        if self.mini_mode_active:
            self.mini_action.setText("正常模式")
        else:
            self.mini_action.setText("迷你模式")

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # In mini mode, toggle the mini window
            if self.mini_mode_active:
                if self.mini_window.isVisible():
                    self.mini_window.hide()
                else:
                    self.mini_window.show()
            else:
                if self.isVisible():
                    self.hide()
                else:
                    self.show_window()

    def show_window(self):
        # In mini mode, show the mini window instead of the main window
        if self.mini_mode_active:
            self.mini_window.show()
            return
        # Force window to top and active using Windows API if needed
        self.show()
        
        # Ensure window is not minimized
        if self.windowState() & Qt.WindowState.WindowMinimized:
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        else:
            self.setWindowState(Qt.WindowState.WindowActive)
            
        self.activateWindow()
        self.raise_()
        
        # Windows-specific focus stealing workaround
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                
                # Get foreground window thread ID
                foreground_hwnd = user32.GetForegroundWindow()
                foreground_thread_id = user32.GetWindowThreadProcessId(foreground_hwnd, None)
                
                # Get current app thread ID
                app_thread_id = user32.GetWindowThreadProcessId(hwnd, None)
                
                if foreground_thread_id != app_thread_id:
                    # Attach thread input
                    user32.AttachThreadInput(foreground_thread_id, app_thread_id, True)
                    
                    # Bring to top and set foreground
                    user32.BringWindowToTop(hwnd)
                    user32.SetForegroundWindow(hwnd)
                    
                    # Detach thread input
                    user32.AttachThreadInput(foreground_thread_id, app_thread_id, False)
            except Exception as e:
                print(f"Focus error: {e}")

    def quit_app(self):
        # Stop the mini window before quitting
        if hasattr(self, 'mini_window'):
            self.mini_window.hide()
        self.fetcher_thread.stop()
        if hasattr(self, 'price_fetcher_thread'):
            self.price_fetcher_thread.stop()
        QApplication.quit()

    # ------------------------------------------------------------------ #
    #  Mini mode                                                          #
    # ------------------------------------------------------------------ #

    def enter_mini_mode(self):
        """Hide the main window and show the mini floating window."""
        if self.mini_mode_active:
            return
        self.mini_mode_active = True
        self.hide()
        # The mini window's news_history is always kept in sync by
        # add_news(), so no manual sync is needed here.
        self.mini_window.show()

    def exit_mini_mode(self):
        """Hide the mini window and restore the main window."""
        if not self.mini_mode_active:
            return
        self.mini_mode_active = False
        self.mini_window.hide()
        self.show_window()

    def toggle_mini_mode(self):
        """Switch between normal and mini mode."""
        if self.mini_mode_active:
            self.exit_mini_mode()
        else:
            self.enter_mini_mode()

    def open_settings(self):
        """Open the settings dialog and apply changes if the user clicks OK."""
        dialog = SettingsDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.apply_settings()

    def closeEvent(self, event):
        # Override close event to minimize to tray instead of exiting
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            # Also hide the mini window on real close
            if hasattr(self, 'mini_window'):
                self.mini_window.hide()
            event.accept()

    def add_news(self, news_list):
        # Insert new news at the top
        for news in news_list:
            card = NewsCard(news)
            self.news_layout.insertWidget(0, card)

        # Track the latest news item.
        # The fetcher emits items sorted in ascending time order,
        # so the last element is the newest.
        if news_list:
            self.latest_news = news_list[-1]
            # Always forward ALL new items to the mini window so its
            # history stays in sync with the main window regardless of
            # which mode is currently active.
            self.mini_window.add_news_batch(news_list)
        
        # Limit the number of cards: remove oldest (bottom) when exceeding max_cards
        while self.news_layout.count() > self.max_cards:
            item = self.news_layout.takeAt(self.news_layout.count() - 1)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        # Re-run search if active and text matches current input
        # Note: Since we only search on Enter now, maybe we shouldn't auto-search new items unless user explicitly wants to?
        # But if the user *has* a search term active, new matching items should probably be highlighted.
        # Let's keep it but check if search input is visible.
        if self.search_widget.isVisible() and self.search_input.text():
            self.perform_search(self.search_input.text())

    def perform_search(self, text):
        # Reset highlights
        for i in range(self.news_layout.count()):
            item = self.news_layout.itemAt(i)
            if item.widget():
                item.widget().set_highlight(False)
        
        if not text:
            self.search_matches = []
            self.current_match_index = -1
            self.lbl_match_count.setText("")
            return

        # Find matches
        self.search_matches = []
        for i in range(self.news_layout.count()):
            item = self.news_layout.itemAt(i)
            widget = item.widget()
            if widget and isinstance(widget, NewsCard):
                if widget.contains_text(text):
                    self.search_matches.append(widget)

        # Update label
        count = len(self.search_matches)
        if count > 0:
            self.lbl_match_count.setText(f"1/{count}")
            self.current_match_index = 0
            self.highlight_current_match()
        else:
            self.lbl_match_count.setText("0/0")
            self.current_match_index = -1

    def highlight_current_match(self):
        if 0 <= self.current_match_index < len(self.search_matches):
            # Deactivate all matches first (optional, but cleaner)
            for widget in self.search_matches:
                widget.set_highlight(False)
            
            # Activate current
            widget = self.search_matches[self.current_match_index]
            widget.set_highlight(True)
            self.scroll_area.ensureWidgetVisible(widget)
            
            self.lbl_match_count.setText(f"{self.current_match_index + 1}/{len(self.search_matches)}")

    def search_next(self):
        if not self.search_matches:
            return
        
        self.current_match_index += 1
        if self.current_match_index >= len(self.search_matches):
            self.current_match_index = 0 # Loop back
            
        self.highlight_current_match()

    def search_prev(self):
        if not self.search_matches:
            return
            
        self.current_match_index -= 1
        if self.current_match_index < 0:
            self.current_match_index = len(self.search_matches) - 1 # Loop back
            
        self.highlight_current_match()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Important for tray app

    # Configure QSettings organization/application name for persistence
    app.setOrganizationName("AI-Kit")
    app.setApplicationName("XinlangNews")

    window = MainWindow()
    # window.show() # Don't show initially, start in tray
    
    # But maybe user wants to see it on start? Let's show it.
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
