import sys
import requests
import ctypes
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QLabel, QScrollArea, QFrame, QSystemTrayIcon, QMenu, QPushButton, QSizePolicy, QTextEdit,
                             QDialog, QSpinBox, QDoubleSpinBox, QAbstractSpinBox)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QEvent, QSettings
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

class AutoHeightTextEdit(QTextEdit):
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

        # Auto-repeat timer for hold-to-scroll (buttons and arrow keys)
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(100)  # ms between repeats while held
        self._auto_timer.timeout.connect(self._on_auto_repeat)
        self._auto_action = None  # 'older' | 'newer'

        # The current news card displayed inside this mini window
        self.current_card = None

        # Navigation history: list of news dicts, newest first (index 0).
        # ``current_index`` points to the item currently shown.
        self.news_history = []
        self.current_index = 0

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

        # Container that holds the NewsCard (re-created on every update).
        # Stretch=1 so it fills all space above the button bar, keeping the
        # button bar pinned to the bottom regardless of card content height.
        self.card_container = QWidget()
        self.card_container.setStyleSheet("background-color: transparent;")
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(0)
        main_layout.addWidget(self.card_container, 1)

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
        if news_data is None:
            return

        # Deduplicate: skip if this exact item is already at the front
        news_id = news_data.get('id')
        if self.news_history and self.news_history[0].get('id') == news_id:
            self.current_index = 0
            self._display_at_index()
            return

        self.news_history.insert(0, news_data)
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
        """Begin hold-to-scroll for ``action`` ('older' or 'newer')."""
        if self._auto_action == action and self._auto_timer.isActive():
            return
        self._auto_action = action
        self._auto_step()          # fire once immediately
        self._auto_timer.start()   # then keep repeating every 100ms

    def _stop_auto(self):
        """Stop the hold-to-scroll repeat loop."""
        self._auto_timer.stop()
        self._auto_action = None

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
        if event.key() == Qt.Key.Key_Up:
            self._start_auto('older')
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self._start_auto('newer')
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
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
        self.setFixedSize(380, 240)
        self.main_window = parent

        # Load current values from QSettings (falling back to defaults)
        settings = QSettings()
        current_max_cards = settings.value("max_cards", 1000, type=int)
        current_opacity = settings.value("mini_opacity", 0.0, type=float)
        current_interval = settings.value("fetch_interval", 600, type=int)

        self._setup_ui(current_max_cards, current_opacity, current_interval)

    def _setup_ui(self, max_cards, opacity, interval):
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

        self.setFixedSize(420, 240)

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

    def setup_global_hotkey(self):
        # Connect the signal to the toggle slot
        self.toggle_visibility_signal.connect(self.toggle_window_visibility)
        self.last_toggle_time = 0
        
        # Register the hotkey using keyboard library
        # We use a lambda to emit the signal because keyboard runs in a separate thread
        try:
            keyboard.add_hotkey(GLOBAL_HOTKEY, self.toggle_visibility_signal.emit)
        except Exception as e:
            print(f"Failed to register global hotkey: {e}")

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
        # Keep mini mode button just left of the close button
        if hasattr(self, 'mini_btn'):
            self.mini_btn.move(self.width() - 70, 5)

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
        # Collect existing news from the main window's cards (newest first,
        # since insertWidget(0, ...) puts the newest at the top).
        existing_news = []
        for i in range(self.news_layout.count()):
            item = self.news_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None and hasattr(widget, 'news_data'):
                    existing_news.append(widget.news_data)
        if existing_news:
            self.mini_window.set_news_history(existing_news)
        elif self.latest_news is not None:
            self.mini_window.update_news(self.latest_news)
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
            # If mini mode is active, update the mini window immediately
            if self.mini_mode_active:
                self.mini_window.update_news(self.latest_news)
        
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
