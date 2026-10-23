# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent — Minimalist & Cozy Internal Surfaces (`newtab` & `workspace`)
Features:
- Clean, spacious layout without cluttered side drawers or excessive cards
- Cute 3D-tactile site launcher badges (`make_3d_badge_pixmap`)
- Smooth Dual-Mode Omnibox (Search <-> Ask AI)
- Inline AI Result Stream directly inside `NewTabWidget` (Image 1) when the user asks a question from New Tab!
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QPlainTextEdit,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal

from theme import get_palette
from icons import make_3d_badge_pixmap, get_internal_title_icon_pixmap
from sidepanel import MessageCardWidget


class NewTabOmniboxEdit(QPlainTextEdit):
    """Multi-line Omnibox editor that toggles Search <-> Ask on Tab and submits on Enter."""
    tab_toggled = Signal()
    submitted = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab:
            event.accept()
            self.tab_toggled.emit()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            event.accept()
            self.submitted.emit()
            return
        super().keyPressEvent(event)


class NewTabWidget(QWidget):
    """
    Minimalist, cozy New Tab page (Image 1):
    - Displays 3D Bside badge, Dual-Mode Omnibox card, and 3D site tiles.
    - When the user submits an AI question here, renders the conversation/result directly inside this New Tab view
      (and if the right-hand sidepanel is open, syncs with the sidepanel as well).
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.mode = "ask"  # Default to AI question mode or toggle with Tab
        self.inline_streaming_card: Optional[MessageCardWidget] = None
        self._build_ui()
        self.refresh_content()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.stage_widget = QWidget()
        stage_outer = QVBoxLayout(self.stage_widget)
        stage_outer.setContentsMargins(40, 44, 40, 48)
        stage_outer.setSpacing(20)

        stage_outer.addStretch(1)

        # Center Container (Max width 700px for cozy, balanced proportions)
        center_wrap = QHBoxLayout()
        center_wrap.addStretch(1)

        self.center_box = QWidget()
        self.center_box.setMaximumWidth(700)
        self.center_box.setMinimumWidth(480)
        self.center_col = QVBoxLayout(self.center_box)
        self.center_col.setContentsMargins(0, 0, 0, 0)
        self.center_col.setSpacing(20)

        # 1. Internal Brand Title Header with Image 2 ('B' icon) right in front of the title
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_row.addStretch(1)
        self.logo_lbl = QLabel()
        self.logo_lbl.setFixedSize(42, 42)
        self.logo_lbl.setPixmap(get_internal_title_icon_pixmap(42))
        title_row.addWidget(self.logo_lbl)

        self.hero_title = QLabel("무엇을 찾거나 AI로 제어할까요?")
        self.hero_title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.hero_title.setStyleSheet("font-size: 24px; font-weight: 800; letter-spacing: -0.5px;")
        title_row.addWidget(self.hero_title)
        title_row.addStretch(1)
        self.center_col.addLayout(title_row)

        # 2. Clean Rounded White Omnibox Card
        self.omnibox_card = QFrame()
        self.omnibox_card.setObjectName("NewTabOmniboxCard")
        card_layout = QVBoxLayout(self.omnibox_card)
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setSpacing(10)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        self.btn_mode_search = QPushButton("🔍 웹 검색 / 주소 이동")
        self.btn_mode_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_search.clicked.connect(lambda: self.set_mode("search"))

        self.btn_mode_ask = QPushButton("✦ AI 에이전트 질문")
        self.btn_mode_ask.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_ask.clicked.connect(lambda: self.set_mode("ask"))

        mode_row.addWidget(self.btn_mode_search)
        mode_row.addWidget(self.btn_mode_ask)
        mode_row.addStretch()

        self.hint_lbl = QLabel("Tab 키로 전환")
        mode_row.addWidget(self.hint_lbl)
        card_layout.addLayout(mode_row)

        self.omnibox_edit = NewTabOmniboxEdit()
        self.omnibox_edit.setObjectName("NewTabOmniboxEdit")
        self.omnibox_edit.setFrameShape(QFrame.Shape.NoFrame)
        self.omnibox_edit.setFixedHeight(52)
        self.omnibox_edit.tab_toggled.connect(
            lambda: self.set_mode("search" if self.mode == "ask" else "ask")
        )
        self.omnibox_edit.submitted.connect(self._submit_omnibox)
        card_layout.addWidget(self.omnibox_edit)

        bottom_row = QHBoxLayout()
        self.inline_status_lbl = QLabel("")
        self.inline_status_lbl.setVisible(False)
        self.inline_status_lbl.setStyleSheet("font-size: 11.5px; color: #4F46E5; font-weight: 600;")
        bottom_row.addWidget(self.inline_status_lbl)

        bottom_row.addStretch(1)

        self.clear_inline_btn = QPushButton("결과 지우기")
        self.clear_inline_btn.setVisible(False)
        self.clear_inline_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_inline_btn.clicked.connect(self.clear_inline_results)
        bottom_row.addWidget(self.clear_inline_btn)

        self.submit_btn = QPushButton("AI 질문 ↵")
        self.submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_btn.clicked.connect(self._submit_omnibox)
        bottom_row.addWidget(self.submit_btn)
        card_layout.addLayout(bottom_row)

        self.center_col.addWidget(self.omnibox_card)

        # 3. Inline AI Result Area (Shown directly inside Image 1 when user asks from Image 1!)
        self.inline_results_frame = QFrame()
        self.inline_results_frame.setObjectName("NewTabInlineResults")
        self.inline_results_frame.setVisible(False)
        self.inline_results_layout = QVBoxLayout(self.inline_results_frame)
        self.inline_results_layout.setContentsMargins(0, 4, 0, 4)
        self.inline_results_layout.setSpacing(10)
        self.center_col.addWidget(self.inline_results_frame)

        # 4. Cute 3D-Tactile Quick Launch Tiles (6 practical shortcuts)
        self.bm_grid = QGridLayout()
        self.bm_grid.setSpacing(12)
        self.center_col.addLayout(self.bm_grid)

        center_wrap.addWidget(self.center_box, 1)
        center_wrap.addStretch(1)
        stage_outer.addLayout(center_wrap)

        stage_outer.addStretch(2)

        self.scroll.setWidget(self.stage_widget)
        root.addWidget(self.scroll, 1)

    def set_mode(self, mode: str):
        self.mode = mode
        p = get_palette(self.main_window.theme_mode)

        self.omnibox_card.setStyleSheet(
            f"""
            QFrame#NewTabOmniboxCard {{
                background-color: {p['card']};
                border: 1px solid {p['border']};
                border-radius: 20px;
            }}
            """
        )
        self.omnibox_edit.setStyleSheet(
            f"""
            QPlainTextEdit#NewTabOmniboxEdit {{
                background: transparent;
                color: {p['fg']};
                border: none;
                padding: 4px 2px;
                font-size: 14.5px;
            }}
            """
        )
        self.hint_lbl.setStyleSheet(f"color: {p['fg_subtle']}; font-size: 11.5px;")
        self.clear_inline_btn.setStyleSheet(
            f"background-color: {p['bg_elevated']}; color: {p['fg_muted']}; border: none; border-radius: 9px; padding: 6px 12px; font-size: 11.5px; font-weight: 600;"
        )

        if mode == "ask":
            self.btn_mode_ask.setStyleSheet(
                f"background-color: {p['accent']}; color: #fff; border: none; border-radius: 10px; padding: 6px 14px; font-weight: 700;"
            )
            self.btn_mode_search.setStyleSheet(
                f"background-color: {p['bg_elevated']}; color: {p['fg_muted']}; border: none; border-radius: 10px; padding: 6px 14px; font-weight: 600;"
            )
            self.omnibox_edit.setPlaceholderText("AI 에이전트에게 질문하거나 웹 자동조작을 지시하세요...")
            self.submit_btn.setText("AI 질문 ↵")
            self.submit_btn.setStyleSheet(
                f"background-color: {p['accent']}; color: #fff; border: none; border-radius: 10px; padding: 7px 18px; font-weight: 700;"
            )
        else:
            self.btn_mode_search.setStyleSheet(
                f"background-color: {p['primary']}; color: {p['primary_fg']}; border: none; border-radius: 10px; padding: 6px 14px; font-weight: 700;"
            )
            self.btn_mode_ask.setStyleSheet(
                f"background-color: {p['bg_elevated']}; color: {p['fg_muted']}; border: none; border-radius: 10px; padding: 6px 14px; font-weight: 600;"
            )
            self.omnibox_edit.setPlaceholderText("검색어 또는 웹사이트 주소(URL)를 입력하세요...")
            self.submit_btn.setText("이동 ↵")
            self.submit_btn.setStyleSheet(
                f"background-color: {p['primary']}; color: {p['primary_fg']}; border: none; border-radius: 10px; padding: 7px 18px; font-weight: 700;"
            )

    def _submit_omnibox(self):
        val = self.omnibox_edit.toPlainText().strip()
        if not val:
            return
        self.omnibox_edit.clear()
        if self.mode == "ask" or val.startswith("@"):
            # Pass source="newtab" so MainWindow knows it was submitted in Image 1!
            self.main_window.run_agent_prompt(val, source="newtab")
        else:
            self.main_window.navigate_current_tab(val)

    # --- Inline Result Rendering inside Image 1 (`NewTabWidget`) ---
    def start_inline_turn(self, user_msg: Dict[str, Any]):
        theme_mode = self.main_window.theme_mode
        self.inline_results_frame.setVisible(True)
        self.clear_inline_btn.setVisible(True)

        user_card = MessageCardWidget(user_msg, theme_mode=theme_mode)
        self.inline_results_layout.addWidget(user_card)

        self.inline_streaming_card = MessageCardWidget(
            {"role": "assistant", "content": "✦ 생각 중..."}, theme_mode=theme_mode
        )
        self.inline_results_layout.addWidget(self.inline_streaming_card)
        self._scroll_to_bottom()

    def update_inline_streaming(self, partial_text: str):
        if self.inline_streaming_card is not None:
            self.inline_streaming_card.update_streaming_text(partial_text)
            self._scroll_to_bottom()

    def finalize_inline_turn(self, final_msg: Dict[str, Any]):
        if self.inline_streaming_card is not None:
            self.inline_streaming_card.update_streaming_text(final_msg.get("content", ""))
            if final_msg.get("visual_html"):
                self.inline_streaming_card.add_visual_html(final_msg["visual_html"])
            if final_msg.get("draft_card"):
                self.inline_streaming_card.add_draft_card(final_msg["draft_card"])
            self.inline_streaming_card = None
            self._scroll_to_bottom()

    def set_inline_status(self, text: str, busy: bool = False):
        self.inline_status_lbl.setVisible(busy)
        self.inline_status_lbl.setText(text)
        self.submit_btn.setEnabled(not busy)

    def clear_inline_results(self):
        self.inline_streaming_card = None
        while self.inline_results_layout.count():
            item = self.inline_results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.inline_results_frame.setVisible(False)
        self.clear_inline_btn.setVisible(False)

    def _scroll_to_bottom(self):
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def refresh_content(self):
        p = get_palette(self.main_window.theme_mode)
        self.setStyleSheet(f"background-color: {p['bg']}; color: {p['fg']};")
        self.stage_widget.setStyleSheet(f"background-color: {p['bg']}; color: {p['fg']};")
        self.set_mode(self.mode)

        while self.bm_grid.count():
            item = self.bm_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        quick_sites = [
            ("Naver", "https://www.naver.com", "N", "#22C55E", "#15803D"),
            ("Google", "https://www.google.com", "G", "#3B82F6", "#1D4ED8"),
            ("YouTube", "https://www.youtube.com", "▶", "#EF4444", "#B91C1C"),
            ("GitHub", "https://github.com", "🐙", "#4B5563", "#1F2937"),
            ("Hacker News", "https://news.ycombinator.com", "Y", "#F97316", "#C2410C"),
            ("Wikipedia", "https://ko.wikipedia.org", "W", "#64748B", "#334155"),
        ]

        for idx, (title, url, glyph, c_top, c_bot) in enumerate(quick_sites):
            tile = QPushButton(f"  {title}")
            tile.setCursor(Qt.CursorShape.PointingHandCursor)
            tile.setToolTip(f"🌐 {title} 열기 ({url})")
            pix = make_3d_badge_pixmap(glyph, c_top, c_bot, size=32, radius=9)
            tile.setIcon(pix)
            tile.setIconSize(pix.size())
            tile.setFixedHeight(52)
            tile.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {p['card']};
                    color: {p['fg']};
                    border: 1px solid {p['border']};
                    border-radius: 14px;
                    padding: 8px 14px;
                    font-size: 13px;
                    font-weight: 700;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {p['card_hover']};
                    border: 1px solid {p['border_strong']};
                }}
                """
            )
            tile.clicked.connect(lambda checked=False, u=url: self.main_window.navigate_current_tab(u))
            self.bm_grid.addWidget(tile, idx // 3, idx % 3)


class WorkspaceWidget(QWidget):
    """Minimalist Workspace page."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self._build_ui()
        self.refresh_content()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.container = QWidget()
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(36, 28, 36, 36)
        self.main_layout.setSpacing(18)

        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        self.ws_icon_lbl = QLabel()
        self.ws_icon_lbl.setFixedSize(32, 32)
        self.ws_icon_lbl.setPixmap(get_internal_title_icon_pixmap(32))
        hdr.addWidget(self.ws_icon_lbl)

        self.title_lbl = QLabel("Bside 워크스페이스")
        self.title_lbl.setStyleSheet("font-size: 20px; font-weight: 800;")
        hdr.addWidget(self.title_lbl)
        hdr.addStretch()

        self.back_btn = QPushButton("← 홈으로")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(lambda: self.main_window.navigate_current_tab("bside://newtab"))
        hdr.addWidget(self.back_btn)

        self.settings_btn = QPushButton("⚙ 구독/API 설정")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.main_window.open_settings_dialog)
        hdr.addWidget(self.settings_btn)

        self.main_layout.addLayout(hdr)

        self.grid = QGridLayout()
        self.grid.setSpacing(14)
        self.main_layout.addLayout(self.grid)
        self.main_layout.addStretch(1)

        scroll.setWidget(self.container)
        root.addWidget(scroll)

    def refresh_content(self):
        p = get_palette(self.main_window.theme_mode)
        self.container.setStyleSheet(f"background-color: {p['bg']}; color: {p['fg']};")
        btn_style = (
            f"background-color: {p['card']}; color: {p['fg']}; border: 1px solid {p['border']}; border-radius: 10px; padding: 7px 14px; font-weight: 600;"
        )
        self.back_btn.setStyleSheet(btn_style)
        self.settings_btn.setStyleSheet(btn_style)

        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        storage = self.main_window.storage
        sections = [
            ("📁 프로젝트", [f"• {pr['name']}: {pr['description']}" for pr in storage.data.get("projects", [])]),
            ("⚡ 루틴", [f"• {rt['name']} ({rt['schedule']})" for rt in storage.data.get("routines", [])]),
            ("🧠 장기 기억", [f"• {m['content']}" for m in storage.data.get("memories", [])]),
            ("🛠️ 내장 스킬", [f"• {s['name']} ({s['tag']})" for s in storage.data.get("skills", [])]),
        ]

        for idx, (sec_title, items) in enumerate(sections):
            panel_id = f"WsPanel_{idx}"
            panel = QFrame()
            panel.setObjectName(panel_id)
            panel.setStyleSheet(
                f"QFrame#{panel_id} {{ background-color: {p['card']}; border: 1px solid {p['border']}; border-radius: 14px; }}"
            )
            pl = QVBoxLayout(panel)
            pl.setContentsMargins(16, 14, 16, 14)
            pl.setSpacing(6)

            h = QLabel(sec_title)
            h.setStyleSheet(f"color: {p['accent']}; font-size: 13.5px; font-weight: 800;")
            pl.addWidget(h)

            for text in items:
                lbl = QLabel(text)
                lbl.setWordWrap(True)
                lbl.setStyleSheet(f"color: {p['fg']}; font-size: 12.5px;")
                pl.addWidget(lbl)

            pl.addStretch(1)
            self.grid.addWidget(panel, idx // 2, idx % 2)
