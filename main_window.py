# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent — Main Browser Window
Minimalist, cozy & tactile 3D UI:
- Crisp, well-proportioned vector icons (`make_nav_icon` & `make_3d_badge_pixmap`)
- Uncluttered navigation bar (Back, Forward, Reload, Home, Omnibox, Sidebar Toggle)
- Full `target="_blank"` / `window.open()` support (`createWindow`)
- Real-time AI streaming + Direct Remote Page Control (`_execute_bsidewright_action`)
"""

import json
import urllib.parse
from typing import Dict, Any, List, Optional

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QFrame,
    QSplitter,
    QStackedWidget,
    QLabel,
    QApplication,
    QMessageBox,
    QToolTip,
)
from PySide6.QtCore import Qt, QUrl, Signal, QSize, QEvent, QObject
from PySide6.QtGui import QShortcut, QKeySequence, QCursor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings, QWebEngineProfile

from theme import APP_NAME, APP_VERSION, get_app_stylesheet, get_palette
from storage import StorageManager
from internal_pages import NewTabWidget, WorkspaceWidget
from sidepanel import BsideAgentSidepanel
from icons import make_nav_icon, make_3d_badge_pixmap, get_internal_title_icon_pixmap
from agent_engine import (
    BSIDEWRIGHT_SNAPSHOT_JS,
    build_bsidewright_action_js,
    build_vault_login_autofill_js,
    build_vault_card_autofill_js,
    AgentWorker,
)
from dialogs import TabSearchDialog, BsideVaultDialog, SettingsWorkspaceDialog
from extensions import ChromeExtensionManagerDialog, ExtensionActionPopup
from updater import AutoUpdater


class InstantTooltipFilter(QObject):
    """
    Application-wide event filter that displays a speech-bubble tooltip (`QToolTip`)
    immediately whenever the mouse hovers over any widget with a non-empty `toolTip()`.
    """
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter and isinstance(watched, QWidget):
            tip = watched.toolTip()
            if tip:
                QToolTip.showText(
                    watched.mapToGlobal(watched.rect().bottomLeft()),
                    tip,
                    watched,
                )
        elif event.type() == QEvent.Type.Leave and isinstance(watched, QWidget):
            if watched.toolTip():
                QToolTip.hideText()
        return super().eventFilter(watched, event)


class OmniboxLineEdit(QLineEdit):
    """Address & Ask bar that toggles Search <-> Ask mode when pressing Tab."""
    tab_pressed = Signal()

    def event(self, event):
        if event.type() == event.Type.KeyPress and event.key() == Qt.Key.Key_Tab:
            self.tab_pressed.emit()
            return True
        return super().event(event)


class BsideWebEnginePage(QWebEnginePage):
    """
    Intercepts custom `bside://` URLs and supports all `target="_blank"` / `window.open()`
    links on portals like Naver, Google, GitHub, etc. via `createWindow()`.
    Uses the persistent `main_window.web_profile` so Chrome Extensions and cookies/sessions work!
    """
    bside_action_triggered = Signal(str, dict)
    internal_url_requested = Signal(str)

    def __init__(self, main_window, parent=None):
        if main_window is not None and hasattr(main_window, "web_profile"):
            super().__init__(main_window.web_profile, parent)
        else:
            super().__init__(parent)
        self.main_window = main_window
        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled, True)

    def createWindow(self, _type):
        if self.main_window is not None:
            new_tab = self.main_window.add_new_tab("about:blank")
            new_tab.stack.setCurrentWidget(new_tab.webview)
            new_tab.webview.setFocus()
            return new_tab.page_obj
        return super().createWindow(_type)

    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame: bool) -> bool:
        scheme = url.scheme().lower()
        if scheme == "bside":
            host = url.host().lower()
            path = url.path().strip("/")
            if host == "action":
                query = urllib.parse.parse_qs(url.query())
                raw_data = query.get("data", ["{}"])[0]
                try:
                    payload = json.loads(urllib.parse.unquote(raw_data))
                except Exception:
                    payload = {}
                self.bside_action_triggered.emit(path, payload)
                return False
            elif host in ("newtab", "workspace"):
                self.internal_url_requested.emit(f"bside://{host}")
                return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class BrowserTab(QWidget):
    """Encapsulates a single Chromium tab with native internal pages + real web browsing."""

    def __init__(self, main_window, initial_url: str = "bside://newtab"):
        super().__init__()
        self.main_window = main_window
        self.logical_url = initial_url
        self.logical_title = "Bside — 새 탭"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget(self)
        layout.addWidget(self.stack)

        self.newtab_widget = NewTabWidget(self.main_window)
        self.stack.addWidget(self.newtab_widget)

        self.workspace_widget = WorkspaceWidget(self.main_window)
        self.stack.addWidget(self.workspace_widget)

        self.webview = QWebEngineView(self)
        self.webview.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.page_obj = BsideWebEnginePage(self.main_window, self.webview)
        self.webview.setPage(self.page_obj)

        self.page_obj.bside_action_triggered.connect(self.main_window.handle_internal_action)
        self.page_obj.internal_url_requested.connect(self.navigate)

        self.webview.urlChanged.connect(self._on_url_changed)
        self.webview.titleChanged.connect(self._on_title_changed)
        self.webview.loadFinished.connect(self._on_load_finished)

        self.stack.addWidget(self.webview)
        self.navigate(initial_url)

    def navigate(self, target: str):
        target = (target or "").strip()
        if not target:
            return
        if target in ("bside://newtab", "about:newtab", "chrome://newtab"):
            self.logical_url = "bside://newtab"
            self.logical_title = "Bside — 새 탭"
            self.newtab_widget.refresh_content()
            self.stack.setCurrentWidget(self.newtab_widget)
            self.main_window.on_tab_updated(self)
            return

        if target in ("bside://workspace", "bside://main"):
            self.logical_url = "bside://workspace"
            self.logical_title = "Bside — 워크스페이스"
            self.workspace_widget.refresh_content()
            self.stack.setCurrentWidget(self.workspace_widget)
            self.main_window.on_tab_updated(self)
            return

        if target == "about:blank":
            self.logical_url = "about:blank"
            self.logical_title = "로딩 중..."
            self.stack.setCurrentWidget(self.webview)
            return

        if "://" not in target:
            if "." in target and " " not in target:
                target = "https://" + target
            else:
                search_prefix = self.main_window.storage.get_setting(
                    "search_engine", "https://www.google.com/search?q="
                )
                target = search_prefix + urllib.parse.quote(target)

        self.logical_url = target
        self.stack.setCurrentWidget(self.webview)
        self.webview.setUrl(QUrl(target))
        self.webview.setFocus()

    def _on_url_changed(self, qurl: QUrl):
        u = qurl.toString()
        if u and not u.startswith("data:") and not u.startswith("bside://") and u != "about:blank":
            self.logical_url = u
            if self.stack.currentWidget() != self.webview:
                self.stack.setCurrentWidget(self.webview)
        self.main_window.on_tab_updated(self)

    def _on_title_changed(self, title: str):
        if self.logical_url == "bside://newtab":
            self.logical_title = "Bside — 새 탭"
        elif self.logical_url == "bside://workspace":
            self.logical_title = "Bside — 워크스페이스"
        else:
            self.logical_title = title or self.logical_url
            if self.logical_url.startswith("http"):
                self.main_window.storage.add_history(self.logical_title, self.logical_url)
        self.main_window.on_tab_updated(self)

    def _on_load_finished(self, ok: bool):
        self.main_window.on_tab_updated(self)
        if ok and self.logical_url.startswith("http"):
            if self.main_window.storage.get_setting("vault_auto_fill", True):
                match_entry = self.main_window.storage.find_vault_entry_for_url(self.logical_url)
                if match_entry:
                    js = build_vault_login_autofill_js(
                        username=match_entry.get("username", ""),
                        password=match_entry.get("password", ""),
                        auto_submit=False,
                        silent_if_no_form=True,
                    )
                    self.webview.page().runJavaScript(js)


class MainWindow(QMainWindow):
    def __init__(self, initial_url: str = "bside://newtab"):
        super().__init__()
        self.storage = StorageManager()
        # Default to warm ivory light theme matching the reference screenshots unless explicitly changed
        if "theme_migrated_v2" not in self.storage.data.get("settings", {}):
            self.storage.set_setting("theme", "light")
            self.storage.set_setting("theme_migrated_v2", True)
        self.theme_mode = self.storage.get_setting("theme", "light")
        self.omnibox_mode = "search"  # "search" | "ask"
        self.tabs: List[BrowserTab] = []
        self.active_worker: Optional[AgentWorker] = None

        # Use a named persistent QWebEngineProfile stored on the local C: drive (APPDATA)
        # so Chromium LevelDB/SQLite never stalls on virtualized Google Drive (`z:\`) mounts,
        # and Chrome extensions load instantaneously without "Can't load in off-the-record mode".
        self.web_profile = QWebEngineProfile("BsidePersistentProfile", self)
        self.web_profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        self.ext_mgr = self.web_profile.extensionManager()

        # Install instant hover speech-bubble tooltip filter across the entire app
        self._tooltip_filter = InstantTooltipFilter(self)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self._tooltip_filter)

        self.setWindowTitle(f"{APP_NAME} Browser & AI Agent v{APP_VERSION}")
        self.resize(1420, 880)

        self._build_ui()
        self._register_shortcuts()
        self.apply_theme()
        self._load_saved_extensions()

        self.add_new_tab(initial_url)

        # Automatic background update checker (auto-downloads, silently installs & relaunches on newer release)
        from PySide6.QtCore import QTimer
        self.auto_updater = AutoUpdater(self)
        QTimer.singleShot(2200, lambda: self.auto_updater.check(silent=True))

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("RootContainer")
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Clean Minimalist Tab Strip Bar
        self.top_chrome = QWidget()
        self.top_chrome.setObjectName("TopChrome")
        self.top_chrome.setFixedHeight(44)
        chrome_layout = QHBoxLayout(self.top_chrome)
        chrome_layout.setContentsMargins(10, 5, 10, 5)
        chrome_layout.setSpacing(6)

        self.tab_bar_container = QWidget()
        self.tab_bar_layout = QHBoxLayout(self.tab_bar_container)
        self.tab_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_bar_layout.setSpacing(6)
        chrome_layout.addWidget(self.tab_bar_container, 1)

        self.new_tab_btn = QPushButton()
        self.new_tab_btn.setFixedSize(32, 32)
        self.new_tab_btn.setIconSize(QSize(18, 18))
        self.new_tab_btn.setProperty("class", "NavIconBtn")
        self.new_tab_btn.setToolTip("새 탭 열기 (Ctrl+T)")
        self.new_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab("bside://newtab"))
        chrome_layout.addWidget(self.new_tab_btn)

        root_layout.addWidget(self.top_chrome)

        # 2. Navigation & Dual-Mode Omnibox Toolbar (Matches Image 2 & Image 3 proportions!)
        self.nav_toolbar = QWidget()
        self.nav_toolbar.setObjectName("NavToolbar")
        self.nav_toolbar.setFixedHeight(50)
        nav_layout = QHBoxLayout(self.nav_toolbar)
        nav_layout.setContentsMargins(12, 6, 12, 6)
        nav_layout.setSpacing(6)

        # Large, crisp, tactile navigation icon buttons (36x36 button, 22x22 vector icon)
        self.back_btn = QPushButton()
        self.back_btn.setFixedSize(36, 36)
        self.back_btn.setIconSize(QSize(22, 22))
        self.back_btn.setProperty("class", "NavIconBtn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setToolTip("뒤로 가기 (Alt+Left)")
        self.back_btn.clicked.connect(self._go_back)
        nav_layout.addWidget(self.back_btn)

        self.fwd_btn = QPushButton()
        self.fwd_btn.setFixedSize(36, 36)
        self.fwd_btn.setIconSize(QSize(22, 22))
        self.fwd_btn.setProperty("class", "NavIconBtn")
        self.fwd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fwd_btn.setToolTip("앞으로 가기 (Alt+Right)")
        self.fwd_btn.clicked.connect(self._go_forward)
        nav_layout.addWidget(self.fwd_btn)

        self.reload_btn = QPushButton()
        self.reload_btn.setFixedSize(36, 36)
        self.reload_btn.setIconSize(QSize(22, 22))
        self.reload_btn.setProperty("class", "NavIconBtn")
        self.reload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reload_btn.setToolTip("새로고침 (Ctrl+R)")
        self.reload_btn.clicked.connect(self._reload_page)
        nav_layout.addWidget(self.reload_btn)

        self.home_btn = QPushButton()
        self.home_btn.setFixedSize(36, 36)
        self.home_btn.setIconSize(QSize(22, 22))
        self.home_btn.setProperty("class", "NavIconBtn")
        self.home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.home_btn.setToolTip("홈 (bside://newtab)")
        self.home_btn.clicked.connect(lambda: self.navigate_current_tab("bside://newtab"))
        nav_layout.addWidget(self.home_btn)

        # Dual-Mode Omnibox Container
        self.omnibox_frame = QFrame()
        self.omnibox_frame.setObjectName("OmniboxContainer")
        self.omnibox_frame.setProperty("mode", "search")
        self.omnibox_frame.setFixedHeight(38)
        omni_layout = QHBoxLayout(self.omnibox_frame)
        omni_layout.setContentsMargins(10, 2, 8, 2)
        omni_layout.setSpacing(8)

        self.omnibox_badge = QPushButton("🔍 검색")
        self.omnibox_badge.setObjectName("OmniboxModeBadge")
        self.omnibox_badge.setProperty("mode", "search")
        self.omnibox_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.omnibox_badge.setToolTip("클릭하거나 Tab 키를 눌러 검색 ↔ AI 질문 모드 전환")
        self.omnibox_badge.clicked.connect(self.toggle_omnibox_mode)
        omni_layout.addWidget(self.omnibox_badge)

        self.omnibox_input = OmniboxLineEdit()
        self.omnibox_input.setObjectName("OmniboxInput")
        self.omnibox_input.setPlaceholderText("웹 주소(URL) 또는 검색어 입력 (Tab 키로 AI 질문 전환)...")
        self.omnibox_input.tab_pressed.connect(self.toggle_omnibox_mode)
        self.omnibox_input.returnPressed.connect(self._on_omnibox_submit)
        omni_layout.addWidget(self.omnibox_input, 1)

        self.bookmark_star_btn = QPushButton()
        self.bookmark_star_btn.setFixedSize(28, 28)
        self.bookmark_star_btn.setIconSize(QSize(18, 18))
        self.bookmark_star_btn.setProperty("class", "NavIconBtn")
        self.bookmark_star_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bookmark_star_btn.setToolTip("북마크 추가/해제 (Ctrl+D)")
        self.bookmark_star_btn.clicked.connect(self.toggle_current_bookmark)
        omni_layout.addWidget(self.bookmark_star_btn)

        nav_layout.addWidget(self.omnibox_frame, 1)

        # Right-hand Toolbar Icons matching uploaded reference image: Key (Vault) -> Puzzle (Chrome Extensions) -> Sidebar Toggle
        self.vault_nav_btn = QPushButton()
        self.vault_nav_btn.setFixedSize(36, 36)
        self.vault_nav_btn.setIconSize(QSize(22, 22))
        self.vault_nav_btn.setProperty("class", "NavIconBtn")
        self.vault_nav_btn.setToolTip("🔑 Bside Vault — 비밀번호 & 결제카드 자동입력 (Ctrl+Shift+Y)")
        self.vault_nav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vault_nav_btn.clicked.connect(self.open_vault_dialog)
        nav_layout.addWidget(self.vault_nav_btn)

        self.extensions_btn = QPushButton()
        self.extensions_btn.setFixedSize(36, 36)
        self.extensions_btn.setIconSize(QSize(22, 22))
        self.extensions_btn.setProperty("class", "NavIconBtn")
        self.extensions_btn.setToolTip("🧩 크롬 확장 프로그램 설치 및 관리")
        self.extensions_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.extensions_btn.clicked.connect(self.open_extensions_dialog)
        nav_layout.addWidget(self.extensions_btn)

        self.sidebar_toggle_btn = QPushButton()
        self.sidebar_toggle_btn.setFixedSize(36, 36)
        self.sidebar_toggle_btn.setIconSize(QSize(22, 22))
        self.sidebar_toggle_btn.setProperty("class", "NavIconBtn")
        self.sidebar_toggle_btn.setProperty("active", "true")
        self.sidebar_toggle_btn.setToolTip("◨ AI 사이드바 열기 / 닫기 (Alt+Shift+B)")
        self.sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle_btn.clicked.connect(self.toggle_sidebar)
        nav_layout.addWidget(self.sidebar_toggle_btn)

        root_layout.addWidget(self.nav_toolbar)

        # 3. Main Horizontal Splitter: Left Browser Viewport + Right Minimal AI Sidepanel
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tab_stack = QStackedWidget()
        self.splitter.addWidget(self.tab_stack)

        self.sidepanel = BsideAgentSidepanel(self.storage, self)
        self.sidepanel.prompt_submitted.connect(self.run_agent_prompt)
        self.sidepanel.quick_action_triggered.connect(lambda pr: self.run_agent_prompt(pr))
        self.sidepanel.remote_action_triggered.connect(self._execute_bsidewright_action)
        self.sidepanel.open_settings_requested.connect(self.open_settings_dialog)
        self.sidepanel.open_vault_requested.connect(self.open_vault_dialog)
        self.splitter.addWidget(self.sidepanel)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([1010, 410])

        root_layout.addWidget(self.splitter, 1)

    def _register_shortcuts(self):
        QShortcut(QKeySequence("Alt+Shift+B"), self, activated=self.toggle_sidebar)
        QShortcut(QKeySequence("Ctrl+Shift+A"), self, activated=self.open_tab_search)
        QShortcut(QKeySequence("Ctrl+Shift+Y"), self, activated=self.open_vault_dialog)
        QShortcut(QKeySequence("Ctrl+T"), self, activated=lambda: self.add_new_tab("bside://newtab"))
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self.close_current_tab)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self._focus_omnibox)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self._reload_page)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self.toggle_current_bookmark)

    def apply_theme(self):
        self.theme_mode = self.storage.get_setting("theme", "light")
        p = get_palette(self.theme_mode)
        QApplication.instance().setStyleSheet(get_app_stylesheet(self.theme_mode))

        # Apply crisp vector icons matching current theme
        self.new_tab_btn.setIcon(make_nav_icon("plus", p["fg"], p["accent"], 20))
        self.back_btn.setIcon(make_nav_icon("back", p["fg"], p["accent"], 22))
        self.fwd_btn.setIcon(make_nav_icon("forward", p["fg"], p["accent"], 22))
        self.reload_btn.setIcon(make_nav_icon("reload", p["fg"], p["accent"], 22))
        self.home_btn.setIcon(make_nav_icon("home", p["fg"], p["accent"], 22))
        self.vault_nav_btn.setIcon(make_nav_icon("vault", p["fg"], p["accent"], 22))
        self.extensions_btn.setIcon(make_nav_icon("extension", p["fg"], p["accent"], 22))
        self.sidebar_toggle_btn.setIcon(make_nav_icon("sidebar", p["fg"], p["accent"], 22))
        self.refresh_extension_pins()

        self.sidepanel.refresh_theme()
        cur = self.current_tab()
        if cur:
            self.on_tab_updated(cur)
            if cur.logical_url in ("bside://newtab", "bside://workspace"):
                cur.navigate(cur.logical_url)
        self._rebuild_tab_strip()

    # --- Tab Management ---
    def add_new_tab(self, url: str = "bside://newtab") -> BrowserTab:
        tab = BrowserTab(self, initial_url=url)
        self.tabs.append(tab)
        self.tab_stack.addWidget(tab)
        self.switch_to_tab(len(self.tabs) - 1)
        return tab

    def current_tab(self) -> Optional[BrowserTab]:
        w = self.tab_stack.currentWidget()
        return w if isinstance(w, BrowserTab) else None

    def switch_to_tab(self, index: int):
        if 0 <= index < len(self.tabs):
            self.tab_stack.setCurrentIndex(index)
            self.on_tab_updated(self.tabs[index])
            self._rebuild_tab_strip()

    def close_tab(self, index: int):
        if len(self.tabs) <= 1:
            self.tabs[0].navigate("bside://newtab")
            return
        if 0 <= index < len(self.tabs):
            tab = self.tabs.pop(index)
            self.tab_stack.removeWidget(tab)
            tab.deleteLater()
            new_idx = min(index, len(self.tabs) - 1)
            self.switch_to_tab(new_idx)

    def close_current_tab(self):
        idx = self.tab_stack.currentIndex()
        self.close_tab(idx)

    def navigate_current_tab(self, url: str):
        cur = self.current_tab()
        if cur:
            cur.navigate(url)

    def on_tab_updated(self, tab: BrowserTab):
        if tab == self.current_tab():
            if self.omnibox_mode == "search":
                self.omnibox_input.setText(tab.logical_url)
            self.sidepanel.update_active_page_context(tab.logical_title, tab.logical_url)
            p = get_palette(self.theme_mode)
            is_bm = self.storage.is_bookmarked(tab.logical_url)
            self.bookmark_star_btn.setIcon(
                make_nav_icon("star_on" if is_bm else "star_off", p["fg_muted"], p["accent"], 18)
            )
        self._rebuild_tab_strip()

    def _rebuild_tab_strip(self):
        while self.tab_bar_layout.count():
            item = self.tab_bar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        p = get_palette(self.theme_mode)
        active_idx = self.tab_stack.currentIndex()

        for i, tab in enumerate(self.tabs):
            is_active = i == active_idx
            pill = QFrame()
            pill.setObjectName("BrowserTabPill")
            pill.setProperty("active", "true" if is_active else "false")
            pill.setFixedHeight(34)
            pill.setMaximumWidth(230)
            pill_layout = QHBoxLayout(pill)
            pill_layout.setContentsMargins(10, 2, 6, 2)
            pill_layout.setSpacing(6)

            # Mini 3D badge inside tab
            low_u = tab.logical_url.lower()
            if "naver.com" in low_u:
                badge_pix = make_3d_badge_pixmap("N", "#22C55E", "#15803D", size=18, radius=5)
            elif "google.com" in low_u:
                badge_pix = make_3d_badge_pixmap("G", "#3B82F6", "#1D4ED8", size=18, radius=5)
            elif low_u.startswith("bside://"):
                badge_pix = get_internal_title_icon_pixmap(18)
            else:
                badge_pix = make_3d_badge_pixmap("🌐", "#38BDF8", "#0284C7", size=18, radius=5)

            icon_lbl = QLabel()
            icon_lbl.setFixedSize(18, 18)
            icon_lbl.setPixmap(badge_pix)
            pill_layout.addWidget(icon_lbl)

            title_text = tab.logical_title or "새 탭"
            short_title = title_text[:20] + ("…" if len(title_text) > 20 else "")
            tab_btn = QPushButton(short_title)
            tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            tab_btn.setToolTip(f"📑 {title_text}\n({tab.logical_url})")
            tab_btn.setStyleSheet(
                f"background: transparent; border: none; color: {p['fg'] if is_active else p['fg_muted']}; font-weight: {'700' if is_active else '500'}; font-size: 12.5px; text-align: left;"
            )
            tab_btn.clicked.connect(lambda checked=False, idx=i: self.switch_to_tab(idx))
            pill_layout.addWidget(tab_btn, 1)

            close_btn = QPushButton("×")
            close_btn.setFixedSize(20, 20)
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setToolTip("탭 닫기 (Ctrl+W)")
            close_btn.setStyleSheet(
                f"background: transparent; border: none; color: {p['fg_muted']}; font-size: 14px; font-weight: 700; border-radius: 5px;"
            )
            close_btn.clicked.connect(lambda checked=False, idx=i: self.close_tab(idx))
            pill_layout.addWidget(close_btn)

            self.tab_bar_layout.addWidget(pill)

        self.tab_bar_layout.addStretch(1)

    # --- Navigation & Omnibox ---
    def _go_back(self):
        cur = self.current_tab()
        if cur:
            cur.webview.back()

    def _go_forward(self):
        cur = self.current_tab()
        if cur:
            cur.webview.forward()

    def _reload_page(self):
        cur = self.current_tab()
        if cur:
            if cur.logical_url in ("bside://newtab", "bside://workspace"):
                cur.navigate(cur.logical_url)
            else:
                cur.webview.reload()

    def _focus_omnibox(self):
        self.omnibox_input.setFocus()
        self.omnibox_input.selectAll()

    def toggle_omnibox_mode(self):
        if self.omnibox_mode == "search":
            self.omnibox_mode = "ask"
            self.omnibox_frame.setProperty("mode", "ask")
            self.omnibox_badge.setProperty("mode", "ask")
            self.omnibox_badge.setText("✦ AI 질문")
            self.omnibox_input.clear()
            self.omnibox_input.setPlaceholderText("현재 페이지 분석·작성 또는 원격 제어를 지시하세요...")
        else:
            self.omnibox_mode = "search"
            self.omnibox_frame.setProperty("mode", "search")
            self.omnibox_badge.setProperty("mode", "search")
            self.omnibox_badge.setText("🔍 검색")
            cur = self.current_tab()
            self.omnibox_input.setText(cur.logical_url if cur else "")
            self.omnibox_input.setPlaceholderText("웹 주소(URL) 또는 검색어 입력 (Tab 키로 AI 질문 전환)...")
        self.omnibox_frame.style().unpolish(self.omnibox_frame)
        self.omnibox_frame.style().polish(self.omnibox_frame)
        self.omnibox_badge.style().unpolish(self.omnibox_badge)
        self.omnibox_badge.style().polish(self.omnibox_badge)
        self.omnibox_input.setFocus()

    def _on_omnibox_submit(self):
        val = self.omnibox_input.text().strip()
        if not val:
            return
        if self.omnibox_mode == "ask" or val.startswith("@"):
            if not self.sidepanel.isVisible():
                self.toggle_sidebar()
            self.run_agent_prompt(val)
            self.toggle_omnibox_mode()
        else:
            self.navigate_current_tab(val)

    def refresh_bookmarks_bar(self):
        pass

    def toggle_current_bookmark(self):
        cur = self.current_tab()
        if not cur:
            return
        url = cur.logical_url
        if self.storage.is_bookmarked(url):
            self.storage.remove_bookmark(url)
        else:
            self.storage.add_bookmark(cur.logical_title, url)
        self.on_tab_updated(cur)

    # --- Internal Page Bridge (`bside://action/...`) ---
    def handle_internal_action(self, action: str, payload: Dict[str, Any]):
        if action == "navigate":
            url = payload.get("url", "bside://newtab")
            self.navigate_current_tab(url)
        elif action == "ask_agent":
            prompt = payload.get("prompt", "")
            if prompt:
                self.run_agent_prompt(prompt, source="newtab")
        elif action == "toggle_sidebar":
            self.toggle_sidebar()
        elif action == "new_session":
            self.storage.create_session("새 대화")
            self.sidepanel.reload_active_session()
            if not self.sidepanel.isVisible():
                self.toggle_sidebar()
        elif action == "select_session":
            sess_id = payload.get("session_id")
            if sess_id:
                self.storage.data["active_session_id"] = sess_id
                self.storage.save()
                self.sidepanel.reload_active_session()
                if not self.sidepanel.isVisible():
                    self.toggle_sidebar()

    # --- Sidebar & Dialogs ---
    def toggle_sidebar(self):
        vis = not self.sidepanel.isVisible()
        self.sidepanel.setVisible(vis)
        self.storage.set_setting("sidebar_open", vis)
        self.sidebar_toggle_btn.setProperty("active", "true" if vis else "false")
        self.sidebar_toggle_btn.style().unpolish(self.sidebar_toggle_btn)
        self.sidebar_toggle_btn.style().polish(self.sidebar_toggle_btn)

    def open_tab_search(self):
        tabs_info = [
            {"index": i, "title": t.logical_title, "url": t.logical_url}
            for i, t in enumerate(self.tabs)
        ]
        dlg = TabSearchDialog(tabs_info, theme_mode=self.theme_mode, parent=self)
        dlg.tab_selected.connect(self.switch_to_tab)
        dlg.exec()

    def open_vault_dialog(self):
        cur = self.current_tab()
        cur_url = cur.logical_url if cur else ""
        dlg = BsideVaultDialog(self.storage, current_url=cur_url, parent=self)
        dlg.autofill_login_requested.connect(self._autofill_vault_login)
        dlg.autofill_card_requested.connect(self._autofill_vault_card)
        dlg.exec()

    def _autofill_vault_login(self, entry: Dict[str, Any], auto_submit: bool = False):
        cur = self.current_tab()
        if not cur:
            return
        site_url = (entry.get("site") or "").strip()
        if cur.logical_url.startswith("bside://") and site_url:
            cur.navigate(site_url)
        js = build_vault_login_autofill_js(
            username=entry.get("username", ""),
            password=entry.get("password", ""),
            auto_submit=auto_submit,
            silent_if_no_form=False,
        )
        cur.webview.page().runJavaScript(js)

    def _autofill_vault_card(self, card: Dict[str, Any]):
        cur = self.current_tab()
        if not cur:
            return
        js = build_vault_card_autofill_js(card)
        cur.webview.page().runJavaScript(js)

    def open_extensions_dialog(self):
        dlg = ChromeExtensionManagerDialog(self, parent=self)
        dlg.open_url_requested.connect(self.add_new_tab)
        dlg.extensions_changed.connect(self.refresh_extension_pins)
        dlg.exec()
        self.refresh_extension_pins()

    def _load_saved_extensions(self):
        import os
        from PySide6.QtCore import QTimer
        def _on_startup_ext_loaded(info):
            if not info.error():
                ext_path = os.path.normpath(info.path()) if info.path() else ""
                def _enable_later():
                    try:
                        for e in self.ext_mgr.extensions():
                            if os.path.normpath(e.path()) == ext_path and not e.isEnabled():
                                self.ext_mgr.setExtensionEnabled(e, True)
                    except Exception:
                        pass
                    self.refresh_extension_pins()
                QTimer.singleShot(50, _enable_later)

        self.ext_mgr.loadFinished.connect(_on_startup_ext_loaded)
        for path in self.storage.get_setting("installed_extension_paths", []):
            if path and os.path.isdir(path):
                self.ext_mgr.loadExtension(path)
        self.refresh_extension_pins()

    def refresh_extension_pins(self):
        # Do not clutter the toolbar with purple C / G letter badges;
        # all extensions are cleanly accessed via the puzzle icon button (`self.extensions_btn`).
        pass

    def _trigger_extension_action(self, ext, btn: QPushButton):
        popup_url = ext.actionPopupUrl()
        if popup_url and not popup_url.isEmpty():
            pop = ExtensionActionPopup(ext.name(), popup_url, self.web_profile, self)
            global_pos = btn.mapToGlobal(btn.rect().bottomLeft())
            pop.move(global_pos.x() - 300, global_pos.y() + 6)
            pop.exec()
        else:
            self.open_extensions_dialog()

    def open_settings_dialog(self):
        dlg = SettingsWorkspaceDialog(self.storage, parent=self)
        dlg.settings_updated.connect(self.apply_theme)
        dlg.exec()

    # --- AI Agent Execution, Fast Streaming & Remote Page Control ---
    def run_agent_prompt(
        self,
        prompt: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        source: str = "sidepanel",
    ):
        """
        Routes AI results based on where the user submitted the prompt and whether Image 2 (Sidepanel) is open:
        - If Image 2 (Sidepanel) is OPEN -> streams & displays the result in Image 2 (Sidepanel).
        - If Image 2 (Sidepanel) is CLOSED and the user typed in Image 1 (`NewTabWidget`) ->
          keeps Sidepanel closed and streams & displays the result directly inside Image 1 (`NewTabWidget`)!
        """
        if not prompt.strip():
            return

        cur = self.current_tab()
        on_newtab = bool(cur and cur.logical_url == "bside://newtab")
        sidepanel_open = self.sidepanel.isVisible()

        if source == "sidepanel" and not sidepanel_open:
            self.toggle_sidebar()
            sidepanel_open = True

        # Determine target display surface(s)
        self._route_to_sidepanel = sidepanel_open or not on_newtab
        self._route_to_newtab = (source == "newtab" and on_newtab and not sidepanel_open)
        self._target_newtab_widget = cur.newtab_widget if (cur and on_newtab) else None

        if self._route_to_sidepanel and not sidepanel_open:
            self.toggle_sidebar()

        sess = self.storage.get_active_session()
        full_prompt = prompt
        if attachments:
            att_notes = "\n".join([f"[첨부파일: {a['name']}]\n{a.get('excerpt', '')[:800]}" for a in attachments])
            full_prompt = f"{prompt}\n\n{att_notes}"

        page_ctx_title = cur.logical_title if cur else "새 탭"

        user_msg = self.storage.add_message(
            sess["id"], role="user", content=prompt, attachments=attachments or []
        )
        user_msg["page_context"] = page_ctx_title

        # Always keep sidepanel session history in sync, and stream to active target
        self.sidepanel.append_message_card(user_msg)
        self.sidepanel.start_streaming_assistant_card()
        self.sidepanel.set_agent_status("✦ AI 응답 생성 및 페이지 제어 중...", busy=True)

        if self._route_to_newtab and self._target_newtab_widget is not None:
            self._target_newtab_widget.start_inline_turn(user_msg)
            self._target_newtab_widget.set_inline_status("✦ AI 응답 생성 중...", busy=True)

        if not cur or cur.logical_url.startswith("bside://"):
            self._start_agent_worker(
                full_prompt,
                {
                    "title": cur.logical_title if cur else "새 탭",
                    "url": cur.logical_url if cur else "bside://newtab",
                    "bodyText": "",
                },
            )
            return

        def on_dom_snapshot(snapshot):
            if not isinstance(snapshot, dict):
                snapshot = {"title": cur.logical_title, "url": cur.logical_url, "bodyText": ""}
            snapshot["title"] = cur.logical_title
            snapshot["url"] = cur.logical_url
            self._start_agent_worker(full_prompt, snapshot)

        cur.webview.page().runJavaScript(BSIDEWRIGHT_SNAPSHOT_JS, on_dom_snapshot)

    def _start_agent_worker(self, prompt: str, snapshot: Dict[str, Any]):
        open_tabs = [{"title": t.logical_title, "url": t.logical_url} for t in self.tabs]
        sess = self.storage.get_active_session()

        self.active_worker = AgentWorker(
            prompt=prompt,
            page_snapshot=snapshot,
            open_tabs=open_tabs,
            history=self.storage.get_history(20),
            memories=self.storage.data.get("memories", []),
            settings=self.storage.data.get("settings", {}),
            conversation_messages=sess.get("messages", []),
        )
        self.active_worker.step_emitted.connect(self._on_worker_step)
        self.active_worker.chunk_emitted.connect(self._on_worker_chunk)
        self.active_worker.action_requested.connect(self._execute_bsidewright_action)
        self.active_worker.quota_alert.connect(self._show_quota_alert)
        self.active_worker.finished_reply.connect(self._on_agent_finished)
        self.active_worker.start()

    def _on_worker_step(self, st: Dict[str, Any]):
        status_txt = f"✦ {st.get('summary')}"
        self.sidepanel.set_agent_status(status_txt, busy=True)
        if getattr(self, "_route_to_newtab", False) and getattr(self, "_target_newtab_widget", None):
            self._target_newtab_widget.set_inline_status(status_txt, busy=True)

    def _on_worker_chunk(self, partial_text: str):
        self.sidepanel.update_streaming_assistant_card(partial_text)
        if getattr(self, "_route_to_newtab", False) and getattr(self, "_target_newtab_widget", None):
            self._target_newtab_widget.update_inline_streaming(partial_text)

    def _show_quota_alert(self, title: str, message: str):
        QMessageBox.warning(self, title, message)

    def _execute_bsidewright_action(self, act: Dict[str, Any]):
        act_type = act.get("action")
        cur = self.current_tab()
        if not cur:
            return
        if act_type == "navigate":
            cur.navigate(act.get("url", "bside://newtab"))
        elif act_type == "new_tab":
            self.add_new_tab(act.get("url", "bside://newtab"))
        elif act_type in ("click", "fill", "write", "scroll", "highlight"):
            js_code = build_bsidewright_action_js(act)
            cur.webview.page().runJavaScript(js_code)
        elif act_type == "vault_login":
            entry = self.storage.find_vault_entry_for_url(cur.logical_url)
            if not entry and self.storage.data.get("vault"):
                entry = self.storage.data["vault"][0]
            if entry:
                self._autofill_vault_login(entry, auto_submit=bool(act.get("submit", True)))
        elif act_type == "vault_card":
            cards = self.storage.get_card_entries()
            if cards:
                self._autofill_vault_card(cards[0])

    def _on_agent_finished(self, result: Dict[str, Any]):
        sess = self.storage.get_active_session()
        assistant_msg = self.storage.add_message(
            sess["id"],
            role="assistant",
            content=result.get("content", ""),
            steps=result.get("steps", []),
            visual_html=result.get("visual_html", ""),
            draft_card=result.get("draft_card"),
        )
        self.sidepanel.finalize_streaming_assistant_card(assistant_msg)
        self.sidepanel.set_agent_status("", busy=False)
        self.sidepanel.session_combo.setItemText(
            self.sidepanel.session_combo.currentIndex(), sess.get("title", "대화")
        )
        if getattr(self, "_route_to_newtab", False) and getattr(self, "_target_newtab_widget", None):
            self._target_newtab_widget.finalize_inline_turn(assistant_msg)
            self._target_newtab_widget.set_inline_status("", busy=False)
