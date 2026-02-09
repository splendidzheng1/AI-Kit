import sys
import requests
import ctypes
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QLabel, QScrollArea, QFrame, QSystemTrayIcon, QMenu, QPushButton, QSizePolicy, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QIcon, QFont, QAction, QPixmap, QPainter, QColor, QKeySequence, QShortcut
from PIL import Image, ImageDraw
import io
import keyboard
import time
import webbrowser

# 全局快捷键配置
# 可以在这里方便地修改快捷键
GLOBAL_HOTKEY = 'shift+space'

class NewsFetcherThread(QThread):
    news_updated = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.seen_ids = set()
        self.api_base = "http://zhibo.sina.com.cn/api/zhibo/feed"
        self.running = True

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
            
            # 每600秒(10分钟)检查一次
            for _ in range(600):
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

class MainWindow(QMainWindow):
    toggle_visibility_signal = pyqtSignal()

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

        # Setup UI
        self.setup_ui()
        
        # Shortcuts (Internal)
        self.setup_shortcuts()
        
        # Global Hotkey (System-wide)
        self.setup_global_hotkey()

        # Setup Tray
        self.setup_tray()

        # Start Fetcher
        self.fetcher_thread = NewsFetcherThread()
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

        if self.isVisible():
            self.hide()
        else:
            self.show_window()

    def setup_shortcuts(self):
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self.toggle_search)

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep button at top right
        if hasattr(self, 'close_btn'):
            self.close_btn.move(self.width() - 35, 5)

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
        tray_menu = QMenu()
        show_action = QAction("显示新闻", self)
        show_action.triggered.connect(self.show_window)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        self.tray_icon.setToolTip("新浪财经7x24 (运行中)")

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_window()

    def show_window(self):
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
        self.fetcher_thread.stop()
        QApplication.quit()

    def closeEvent(self, event):
        # Override close event to minimize to tray instead of exiting
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    def add_news(self, news_list):
        # Insert new news at the top
        for news in news_list:
            card = NewsCard(news)
            self.news_layout.insertWidget(0, card)
        
        # Don't limit the number of items anymore
        # while self.news_layout.count() > 50: ...

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
    
    window = MainWindow()
    # window.show() # Don't show initially, start in tray
    
    # But maybe user wants to see it on start? Let's show it.
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
