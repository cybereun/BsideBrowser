# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent — Minimalist & Practical AI Sidepanel (Matches Uploaded Screenshots 1, 2, 3)
Features:
- Clean, uncluttered header (Session dropdown + cute 3D icon buttons for New Chat & Settings)
- Scrollable live-streaming chat view
- Attached Active Page Context Card INSIDE the rounded white composer card (3D glossy icon badge + Page Title + Domain + 1-click AI Remote Control tray)
- Bottom bar below composer matching Uploaded Images 1, 2, 3:
  * Hand Permission Dropdown (`🖐️ ⌄`)
  * Context/History Dropdown (`🗂️ ⌄`)
  * Searchable Model Popover (`🔍 Search models`, Model list for Claude / Codex / Antigravity / API with `✓` checkmark, and `Settings ↗` at bottom)
  * Effort & Fast Mode Popover (`Low`, `Medium`, `High`, `Extra High`, `Max`, rainbow `Ultrabrowse`, `Options` + `Fast mode` toggle switch)
"""

import os
import urllib.parse
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QScrollArea,
    QFrame,
    QPlainTextEdit,
    QFileDialog,
    QApplication,
    QSizePolicy,
    QDialog,
    QLineEdit,
    QMenu,
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint
from PySide6.QtWebEngineWidgets import QWebEngineView

from theme import get_palette
from storage import StorageManager
from icons import (
    make_3d_badge_pixmap,
    make_nav_icon,
    make_provider_icon_pixmap,
    make_provider_icon,
    make_status_chip_icon,
    get_internal_title_icon_pixmap,
)


# Complete Model Catalog for Claude, Codex, Antigravity Subscriptions + Direct APIs
# Supports searching and checkmark selection exactly as shown in Image 1
ALL_SUBSCRIPTION_AND_API_MODELS = [
    # --- Codex (ChatGPT/OpenAI Subscription) Models (Image 1) ---
    {"id": "codex:GPT-6.1 Sol", "name": "GPT-6.1 Sol", "group": "Codex 구독"},
    {"id": "codex:GPT-6 Astra", "name": "GPT-6 Astra", "group": "Codex 구독"},
    {"id": "codex:GPT-6 Sol", "name": "GPT-6 Sol", "group": "Codex 구독"},
    {"id": "codex:GPT-6 Luna", "name": "GPT-6 Luna", "group": "Codex 구독"},
    {"id": "codex:GPT-5.6 Sol", "name": "GPT-5.6 Sol", "group": "Codex 구독"},
    {"id": "codex:GPT-5.6 Terra", "name": "GPT-5.6 Terra", "group": "Codex 구독"},
    {"id": "codex:GPT-5.6 Luna", "name": "GPT-5.6 Luna", "group": "Codex 구독"},
    # --- Claude (Claude Code Subscription) Models ---
    {"id": "claude:Claude 4.5 Opus", "name": "Claude 4.5 Opus", "group": "Claude 구독"},
    {"id": "claude:Claude 4.5 Sonnet", "name": "Claude 4.5 Sonnet", "group": "Claude 구독"},
    {"id": "claude:Claude 4.5 Haiku", "name": "Claude 4.5 Haiku", "group": "Claude 구독"},
    # --- Antigravity (agy.exe Subscription) Models ---
    {"id": "antigravity:Gemini 3.8 Pro", "name": "Gemini 3.8 Pro (Antigravity)", "group": "Antigravity 구독"},
    {"id": "antigravity:Gemini 3.8 Flash", "name": "Gemini 3.8 Flash (Antigravity)", "group": "Antigravity 구독"},
    {"id": "antigravity:Antigravity Luna", "name": "Antigravity Luna", "group": "Antigravity 구독"},
    # --- Direct API & Local Models ---
    {"id": "claude-api", "name": "Claude API (Direct)", "group": "API / 로컬"},
    {"id": "openai-api", "name": "OpenAI API (Direct)", "group": "API / 로컬"},
    {"id": "gemini-api", "name": "Gemini API (Direct)", "group": "API / 로컬"},
    {"id": "custom-local", "name": "Ollama Local LLM", "group": "API / 로컬"},
    {"id": "bside-autonomous-v1", "name": "Bside 내장 엔진 (오프라인)", "group": "API / 로컬"},
]

EFFORT_LEVELS = [
    "Low",
    "Medium",
    "High",
    "Extra High",
    "Max",
    "Ultrabrowse",
]


class ModelSearchPopover(QDialog):
    """
    Replicates Image 1's floating model selector card:
    - Top search box: `🔍 Search models`
    - Scrollable list of models (Codex GPT-6.1 Sol / Luna, Claude Opus / Sonnet / Haiku, Antigravity Gemini 3.8, etc.) with `✓` checkmark on active model
    - Bottom divider + `Settings ↗` row
    """
    model_selected = Signal(str, str)  # (model_id, display_name)
    settings_clicked = Signal()

    def __init__(self, current_model_id: str, current_model_name: str, theme_mode: str = "light", parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.current_model_id = current_model_id
        self.current_model_name = current_model_name
        self.theme_mode = theme_mode
        self.setFixedWidth(270)
        self._build_ui()
        self._populate("")

    def _build_ui(self):
        p = get_palette(self.theme_mode)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("ModelPopoverCard")
        self.card.setStyleSheet(
            f"""
            QFrame#ModelPopoverCard {{
                background-color: {p['popover']};
                border: 1px solid {p['border_strong']};
                border-radius: 16px;
            }}
            """
        )
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        # Search input row (`🔍 Search models`)
        search_row = QHBoxLayout()
        search_row.setContentsMargins(6, 2, 6, 4)
        search_row.setSpacing(6)
        s_icon = QLabel("🔍")
        s_icon.setStyleSheet(f"color: {p['fg_subtle']}; font-size: 12px;")
        search_row.addWidget(s_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search models")
        self.search_input.setStyleSheet(
            f"background: transparent; border: none; color: {p['fg']}; font-size: 13px; padding: 2px;"
        )
        self.search_input.textChanged.connect(self._populate)
        search_row.addWidget(self.search_input, 1)
        layout.addLayout(search_row)

        # Scrollable model list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setFixedHeight(280)
        self.scroll.setStyleSheet("background: transparent;")

        self.list_widget = QWidget()
        self.list_widget.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(2)
        self.scroll.setWidget(self.list_widget)
        layout.addWidget(self.scroll)

        # Divider line
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {p['border']}; border: none;")
        layout.addWidget(div)

        # Bottom `Settings ↗` button
        settings_btn = QPushButton("Settings                                      ↗")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {p['fg']};
                border: none;
                border-radius: 8px;
                padding: 7px 8px;
                font-size: 13px;
                font-weight: 500;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {p['card_hover']};
            }}
            """
        )
        settings_btn.clicked.connect(self._on_settings)
        layout.addWidget(settings_btn)

        outer.addWidget(self.card)

    def _populate(self, query: str):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        p = get_palette(self.theme_mode)
        q = query.strip().lower()
        current_group = None

        for item in ALL_SUBSCRIPTION_AND_API_MODELS:
            m_id = item["id"]
            m_name = item["name"]
            grp = item["group"]
            if q and q not in m_name.lower() and q not in grp.lower():
                continue

            if grp != current_group:
                current_group = grp
                g_lbl = QLabel(grp)
                g_lbl.setStyleSheet(
                    f"color: {p['fg_subtle']}; font-size: 10.5px; font-weight: 700; padding: 6px 8px 2px 8px;"
                )
                self.list_layout.addWidget(g_lbl)

            is_sel = (m_id == self.current_model_id) or (m_name == self.current_model_name)
            row_btn = QPushButton()
            row_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            row_btn.setFixedHeight(34)
            row_layout = QHBoxLayout(row_btn)
            row_layout.setContentsMargins(8, 0, 8, 0)
            row_layout.setSpacing(8)

            icon_lbl = QLabel()
            icon_lbl.setFixedSize(20, 20)
            icon_lbl.setPixmap(make_provider_icon_pixmap(m_id, size=20))
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            row_layout.addWidget(icon_lbl)

            name_lbl = QLabel(m_name)
            name_lbl.setStyleSheet(
                f"color: {p['fg']}; font-size: 13px; font-weight: {'600' if is_sel else '400'}; background: transparent;"
            )
            row_layout.addWidget(name_lbl)
            row_layout.addStretch(1)

            if is_sel:
                chk_lbl = QLabel("✓")
                chk_lbl.setStyleSheet(f"color: {p['fg']}; font-size: 13px; font-weight: 700; background: transparent;")
                row_layout.addWidget(chk_lbl)

            row_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {p['card_hover'] if is_sel else 'transparent'};
                    border: none;
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    background-color: {p['card_hover']};
                }}
                """
            )
            row_btn.setToolTip(f"🤖 {m_name} ({grp}) 모델 선택")
            row_btn.clicked.connect(lambda checked=False, mid=m_id, mnm=m_name: self._select(mid, mnm))
            self.list_layout.addWidget(row_btn)

        self.list_layout.addStretch(1)

    def _select(self, model_id: str, model_name: str):
        self.model_selected.emit(model_id, model_name)
        self.accept()

    def _on_settings(self):
        self.settings_clicked.emit()
        self.accept()


class EffortPopover(QDialog):
    """
    Replicates Image 2's Effort & Options Popover:
    - Low
    - Medium
    - High
    - Extra High  ✓
    - Max
    - Ultrabrowse (Rainbow gradient text!)
    - Divider + `Options` header
    - `Fast mode` toggle switch
    """
    effort_selected = Signal(str)
    fast_mode_toggled = Signal(bool)

    def __init__(self, current_effort: str, fast_mode: bool, theme_mode: str = "light", parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.current_effort = current_effort
        self.fast_mode = fast_mode
        self.theme_mode = theme_mode
        self.setFixedWidth(195)
        self._build_ui()

    def _build_ui(self):
        p = get_palette(self.theme_mode)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("EffortPopoverCard")
        self.card.setStyleSheet(
            f"""
            QFrame#EffortPopoverCard {{
                background-color: {p['popover']};
                border: 1px solid {p['border_strong']};
                border-radius: 16px;
            }}
            """
        )
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(2)

        for eff in EFFORT_LEVELS:
            is_sel = eff == self.current_effort
            row_btn = QPushButton()
            row_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            row_btn.setFixedHeight(32)
            rl = QHBoxLayout(row_btn)
            rl.setContentsMargins(8, 0, 8, 0)

            lbl = QLabel()
            if eff == "Ultrabrowse":
                lbl.setTextFormat(Qt.TextFormat.RichText)
                lbl.setText(
                    '<span style="font-size:13px; font-weight:600;">'
                    '<span style="color:#F87171;">U</span>'
                    '<span style="color:#FB923C;">l</span>'
                    '<span style="color:#FACC15;">t</span>'
                    '<span style="color:#4ADE80;">r</span>'
                    '<span style="color:#38BDF8;">a</span>'
                    '<span style="color:#818CF8;">b</span>'
                    '<span style="color:#C084FC;">r</span>'
                    '<span style="color:#F472B6;">o</span>'
                    '<span style="color:#FB7185;">w</span>'
                    '<span style="color:#FBBF24;">s</span>'
                    '<span style="color:#FB923C;">e</span>'
                    "</span>"
                )
            else:
                lbl.setText(eff)
                lbl.setStyleSheet(
                    f"color: {p['fg']}; font-size: 13px; font-weight: {'600' if is_sel else '400'}; background: transparent;"
                )
            rl.addWidget(lbl)
            rl.addStretch(1)

            if is_sel:
                chk = QLabel("✓")
                chk.setStyleSheet(f"color: {p['fg']}; font-size: 13px; font-weight: 700; background: transparent;")
                rl.addWidget(chk)

            row_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {p['card_hover'] if is_sel else 'transparent'};
                    border: none;
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    background-color: {p['card_hover']};
                }}
                """
            )
            row_btn.clicked.connect(lambda checked=False, val=eff: self._choose_effort(val))
            layout.addWidget(row_btn)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {p['border']}; border: none; margin-top: 4px; margin-bottom: 4px;")
        layout.addWidget(div)

        opt_lbl = QLabel("Options")
        opt_lbl.setStyleSheet(f"color: {p['fg_subtle']}; font-size: 11.5px; font-weight: 600; padding: 2px 8px;")
        layout.addWidget(opt_lbl)

        # Fast mode toggle switch row (Image 2)
        fast_row = QHBoxLayout()
        fast_row.setContentsMargins(8, 4, 8, 2)
        f_lbl = QLabel("Fast mode")
        f_lbl.setStyleSheet(f"color: {p['fg']}; font-size: 13px; font-weight: 500;")
        fast_row.addWidget(f_lbl)
        fast_row.addStretch(1)

        self.fast_switch = QPushButton()
        self.fast_switch.setCheckable(True)
        self.fast_switch.setChecked(self.fast_mode)
        self.fast_switch.setFixedSize(40, 22)
        self.fast_switch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fast_switch.toggled.connect(self._on_fast_toggled)
        self._update_switch_style()
        fast_row.addWidget(self.fast_switch)

        layout.addLayout(fast_row)
        outer.addWidget(self.card)

    def _update_switch_style(self):
        on = self.fast_switch.isChecked()
        if on:
            self.fast_switch.setText("  ●")
            self.fast_switch.setStyleSheet(
                "background-color: #10B981; color: #FFFFFF; border: none; border-radius: 11px; font-size: 13px; font-weight: 900;"
            )
        else:
            self.fast_switch.setText("●  ")
            self.fast_switch.setStyleSheet(
                "background-color: #D4D4D8; color: #FFFFFF; border: none; border-radius: 11px; font-size: 13px; font-weight: 900;"
            )

    def _choose_effort(self, val: str):
        self.effort_selected.emit(val)
        self.accept()

    def _on_fast_toggled(self, checked: bool):
        self._update_switch_style()
        self.fast_mode_toggled.emit(checked)


class DraftPreviewCard(QFrame):
    """Minimalist draft card inside chat."""

    def __init__(self, draft: Dict[str, Any], theme_mode: str = "light", parent=None):
        super().__init__(parent)
        p = get_palette(theme_mode)
        self.draft = draft
        self.setObjectName("DraftCardBox")
        self.setStyleSheet(
            f"""
            QFrame#DraftCardBox {{
                background-color: {p['bg']};
                border: 1px solid {p['border']};
                border-radius: 12px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        badge = QLabel(f"✉️ {draft.get('channel', '초안 카드')}")
        badge.setStyleSheet(f"color: {p['accent']}; font-weight: 700; font-size: 11.5px;")
        top.addWidget(badge)
        top.addStretch()

        copy_btn = QPushButton("복사")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(
            f"background: {p['primary']}; color: {p['primary_fg']}; border: none; border-radius: 7px; padding: 3px 10px; font-size: 11px; font-weight: 600;"
        )
        copy_btn.clicked.connect(self._copy_draft)
        top.addWidget(copy_btn)
        layout.addLayout(top)

        subj = QLabel(draft.get("subject", ""))
        subj.setStyleSheet(f"color: {p['fg']}; font-weight: 700; font-size: 12px;")
        subj.setWordWrap(True)
        layout.addWidget(subj)

        body = QLabel(draft.get("body", ""))
        body.setStyleSheet(f"color: {p['fg_muted']}; font-size: 12px;")
        body.setWordWrap(True)
        layout.addWidget(body)

    def _copy_draft(self):
        text = f"{self.draft.get('subject', '')}\n\n{self.draft.get('body', '')}"
        QApplication.clipboard().setText(text)


class MessageCardWidget(QFrame):
    """Clean, cozy message bubble supporting real-time streaming updates."""

    def __init__(self, msg: Dict[str, Any], theme_mode: str = "light", parent=None):
        super().__init__(parent)
        p = get_palette(theme_mode)
        role = msg.get("role", "assistant")
        is_user = role == "user"

        bg_color = p["bg_elevated"] if is_user else p["card"]
        border_color = p["border"]

        self.setObjectName("MsgBubble")
        self.setStyleSheet(
            f"""
            QFrame#MsgBubble {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
            """
        )

        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(14, 11, 14, 11)
        self.card_layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        role_lbl = QLabel("나" if is_user else "✦ Bside AI")
        role_lbl.setStyleSheet(
            f"color: {p['fg_muted'] if is_user else p['accent']}; font-weight: 700; font-size: 11.5px;"
        )
        header_row.addWidget(role_lbl)

        page_ctx = msg.get("page_context")
        if is_user and page_ctx:
            ctx_pill = QLabel(f"🌐 {page_ctx[:24]}")
            ctx_pill.setStyleSheet(
                f"background: {p['card']}; color: {p['fg_muted']}; font-size: 10.5px; padding: 2px 7px; border-radius: 6px;"
            )
            header_row.addWidget(ctx_pill)

        header_row.addStretch()
        self.card_layout.addLayout(header_row)

        self.content_lbl = QLabel()
        self.content_lbl.setTextFormat(Qt.TextFormat.MarkdownText)
        self.content_lbl.setText(msg.get("content", ""))
        self.content_lbl.setWordWrap(True)
        self.content_lbl.setOpenExternalLinks(True)
        self.content_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.content_lbl.setStyleSheet(
            f"color: {p['fg']}; font-size: 13px; line-height: 1.5;"
        )
        self.card_layout.addWidget(self.content_lbl)

        self.theme_mode = theme_mode
        visual_html = msg.get("visual_html") or ""
        if visual_html:
            self.add_visual_html(visual_html)

        draft_card = msg.get("draft_card")
        if draft_card and isinstance(draft_card, dict):
            self.add_draft_card(draft_card)

    def update_streaming_text(self, text: str):
        self.content_lbl.setText(text)

    def add_visual_html(self, visual_html: str):
        web = QWebEngineView()
        web.setFixedHeight(195)
        web.setHtml(
            f"<!DOCTYPE html><html><body style='margin:0;padding:0;background:transparent;overflow:hidden;'>{visual_html}</body></html>"
        )
        self.card_layout.addWidget(web)

    def add_draft_card(self, draft_card: Dict[str, Any]):
        self.card_layout.addWidget(DraftPreviewCard(draft_card, theme_mode=self.theme_mode))


class ComposerTextEdit(QPlainTextEdit):
    """Multi-line composer that submits on Enter (without Shift)."""
    submitted = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            event.accept()
            self.submitted.emit()
            return
        super().keyPressEvent(event)


class BsideAgentSidepanel(QWidget):
    """
    Minimalist, practical Right-hand AI Sidebar modeled directly on Uploaded Images 1, 2, 3:
    - Top header: Session dropdown + New Chat icon button + Settings icon button
    - Center: Clean chat stream
    - Bottom Composer Card:
      1. Embedded Active Page Pill Card (`[3D Icon] Page Title / domain.com` + `[🕹️ 원격조정]`)
      2. Collapsible 1-click AI Remote Control Bar
      3. Borderless text input (`Ask AI a task, @ for context`)
      4. Circular `+` button on left, circular dark `🎤 / ↑` button on right
    - Footer row below Composer Card (Exact match to Images 1, 2, 3):
      * Hand Permission button (`🖐️ ⌄`)
      * Context/History button (`🗂️ ⌄`)
      * Model Selector Pill (`❂ GPT-6 Luna` / `Claude 4.5 Sonnet` / `Gemini 3.8 Pro`) -> opens `ModelSearchPopover` (Image 1)
      * Effort Selector Pill (`Extra High ⌄` / `Low` / `Medium` / `High` / `Max` / `Ultrabrowse`) -> opens `EffortPopover` (Image 2)
    """

    prompt_submitted = Signal(str, list)          # (prompt_text, attachments)
    quick_action_triggered = Signal(str)          # prompt_text
    remote_action_triggered = Signal(dict)        # direct Bsidewright action dict
    open_settings_requested = Signal()
    open_vault_requested = Signal()

    def __init__(self, storage: StorageManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.attachments: List[Dict[str, Any]] = []
        self.active_page_title = "Bside — 새 탭"
        self.active_page_url = "bside://newtab"
        self.streaming_card: Optional[MessageCardWidget] = None
        self.remote_btns: List[QPushButton] = []

        self.setMinimumWidth(355)
        self.setMaximumWidth(560)

        self._build_ui()
        self.refresh_theme()
        self.reload_active_session()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(8)

        # 1. Minimalist Top Header
        self.header_frame = QFrame()
        self.header_frame.setObjectName("SidepanelHeader")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(4, 2, 4, 4)
        header_layout.setSpacing(6)

        self.header_icon_lbl = QLabel()
        self.header_icon_lbl.setFixedSize(26, 26)
        self.header_icon_lbl.setPixmap(get_internal_title_icon_pixmap(26))
        self.header_icon_lbl.setToolTip("Bside AI 에이전트")
        header_layout.addWidget(self.header_icon_lbl)

        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(140)
        self.session_combo.setToolTip("💬 대화 목록 선택 및 전환")
        self.session_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.session_combo.currentIndexChanged.connect(self._on_session_combo_changed)
        header_layout.addWidget(self.session_combo, 1)

        self.new_chat_btn = QPushButton()
        self.new_chat_btn.setFixedSize(34, 34)
        self.new_chat_btn.setIconSize(QSize(20, 20))
        self.new_chat_btn.setToolTip("✏️ 새 대화 시작")
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_btn.setProperty("class", "NavIconBtn")
        self.new_chat_btn.clicked.connect(self._create_new_session)
        header_layout.addWidget(self.new_chat_btn)

        self.settings_btn = QPushButton()
        self.settings_btn.setFixedSize(34, 34)
        self.settings_btn.setIconSize(QSize(20, 20))
        self.settings_btn.setToolTip("⚙️ 구독 연결 (Claude / Codex / Antigravity) 및 브라우저 설정")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setProperty("class", "NavIconBtn")
        self.settings_btn.clicked.connect(self.open_settings_requested.emit)
        header_layout.addWidget(self.settings_btn)

        root.addWidget(self.header_frame)

        # 2. Scrollable Messages Stream
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(4, 6, 4, 6)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch(1)

        self.scroll_area.setWidget(self.messages_container)
        root.addWidget(self.scroll_area, 1)

        # Subtle Live Status Line
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.status_label.setContentsMargins(8, 0, 8, 0)
        root.addWidget(self.status_label)

        # 3. Rounded White Composer Card (Matches Image 3!)
        self.composer_card = QFrame()
        self.composer_card.setObjectName("SidepanelComposerCard")
        comp_layout = QVBoxLayout(self.composer_card)
        comp_layout.setContentsMargins(12, 12, 12, 10)
        comp_layout.setSpacing(8)

        # 3-A. Attached Current Page Pill inside Composer (Matches Image 3!)
        self.page_chip_card = QFrame()
        self.page_chip_card.setObjectName("AttachedPageChip")
        chip_layout = QHBoxLayout(self.page_chip_card)
        chip_layout.setContentsMargins(8, 7, 10, 7)
        chip_layout.setSpacing(10)

        self.page_icon_lbl = QLabel()
        self.page_icon_lbl.setFixedSize(36, 36)
        self.page_icon_lbl.setPixmap(
            make_3d_badge_pixmap("🌐", top_color="#38BDF8", bottom_color="#0284C7", size=36, radius=10)
        )
        chip_layout.addWidget(self.page_icon_lbl)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(1)
        self.page_title_lbl = QLabel("Bside — 새 탭")
        self.page_title_lbl.setStyleSheet("font-size: 12.5px; font-weight: 700;")
        self.page_domain_lbl = QLabel("bside://newtab")
        self.page_domain_lbl.setStyleSheet("font-size: 11px;")
        title_col.addWidget(self.page_title_lbl)
        title_col.addWidget(self.page_domain_lbl)
        chip_layout.addLayout(title_col, 1)

        self.remote_toggle_btn = QPushButton("🕹️ 원격조정")
        self.remote_toggle_btn.setCheckable(True)
        self.remote_toggle_btn.setChecked(False)
        self.remote_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remote_toggle_btn.setToolTip("이 웹페이지를 AI로 분석·작성·원격 제어하는 도구 모음 열기")
        self.remote_toggle_btn.toggled.connect(self._toggle_remote_bar)
        chip_layout.addWidget(self.remote_toggle_btn)

        comp_layout.addWidget(self.page_chip_card)

        # 3-B. Practical 1-Click Page Analysis & Remote Control Bar (Collapsible so composer stays super clean like Image 3)
        self.remote_bar = QWidget()
        self.remote_bar.setVisible(False)
        remote_layout = QHBoxLayout(self.remote_bar)
        remote_layout.setContentsMargins(0, 0, 0, 0)
        remote_layout.setSpacing(5)

        remote_actions = [
            ("📝 페이지 요약", lambda: self.quick_action_triggered.emit("현재 페이지의 핵심 내용을 3줄로 요약해줘.")),
            ("✍️ 입력란 작성", self._prompt_remote_write),
            ("🎯 요소 표시", lambda: self.remote_action_triggered.emit({"action": "highlight", "target": "all"})),
            ("⏬ 스크롤", lambda: self.remote_action_triggered.emit({"action": "scroll", "value": "down"})),
        ]
        self.remote_btns.clear()
        for label, handler in remote_actions:
            b = QPushButton(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda checked=False, fn=handler: fn())
            self.remote_btns.append(b)
            remote_layout.addWidget(b)

        comp_layout.addWidget(self.remote_bar)

        self.attachment_label = QLabel("")
        self.attachment_label.setVisible(False)
        comp_layout.addWidget(self.attachment_label)

        # 3-C. Clean Borderless Text Input (Matches Image 3: "Ask AI a task, @ for context")
        self.composer_input = ComposerTextEdit()
        self.composer_input.setObjectName("SidepanelComposerEdit")
        self.composer_input.setFrameShape(QFrame.Shape.NoFrame)
        self.composer_input.setPlaceholderText("Ask AI a task, @ for context (이 페이지 분석·작성·원격 제어)")
        self.composer_input.setFixedHeight(48)
        self.composer_input.submitted.connect(self._submit)
        comp_layout.addWidget(self.composer_input)

        # 3-D. Bottom Row inside Composer Card: Circular `+` on left, Circular Dark button on right (Image 3)
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 2, 0, 0)
        action_row.setSpacing(8)

        self.attach_btn = QPushButton()
        self.attach_btn.setFixedSize(34, 34)
        self.attach_btn.setIconSize(QSize(18, 18))
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.setToolTip("파일 첨부 (+)")
        self.attach_btn.clicked.connect(self._attach_file)
        action_row.addWidget(self.attach_btn)

        action_row.addStretch(1)

        self.send_btn = QPushButton()
        self.send_btn.setFixedSize(36, 36)
        self.send_btn.setIconSize(QSize(18, 18))
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setToolTip("전송 (Enter)")
        self.send_btn.clicked.connect(self._submit)
        action_row.addWidget(self.send_btn)

        comp_layout.addLayout(action_row)
        root.addWidget(self.composer_card)

        # 4. Bottom Control Bar below Composer Card (Exact match to Uploaded Images 1, 2, 3!)
        #    [🖐️ ⌄]   [🗂️ ⌄]          [❂ GPT-6 Luna]  [Extra High ⌄]
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(4, 2, 4, 0)
        footer_row.setSpacing(6)

        self.current_perm_key = self.storage.get_setting("remote_permission_mode", "perm_safe")
        self.current_ctx_key = self.storage.get_setting("active_ctx_mode", "ctx_summary")

        self.perm_btn = QPushButton(" ⌄")
        self.perm_btn.setIconSize(QSize(22, 22))
        self.perm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.perm_btn.clicked.connect(self._open_permission_menu)
        footer_row.addWidget(self.perm_btn)

        self.ctx_btn = QPushButton(" ⌄")
        self.ctx_btn.setIconSize(QSize(22, 22))
        self.ctx_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ctx_btn.clicked.connect(self._open_context_menu)
        footer_row.addWidget(self.ctx_btn)

        self._sync_perm_and_ctx_buttons()

        footer_row.addStretch(1)

        # Initialize saved Model & Effort
        saved_model_id = self.storage.get_setting("default_model", "codex:GPT-6 Luna")
        saved_model_name = self.storage.get_setting("selected_sub_model_name", "GPT-6 Luna")
        # Map legacy IDs cleanly
        if saved_model_id == "claude-sub":
            saved_model_id, saved_model_name = "claude:Claude 4.5 Sonnet", "Claude 4.5 Sonnet"
        elif saved_model_id == "codex-sub":
            saved_model_id, saved_model_name = "codex:GPT-6 Luna", "GPT-6 Luna"
        elif saved_model_id == "antigravity-sub":
            saved_model_id, saved_model_name = "antigravity:Gemini 3.8 Pro", "Gemini 3.8 Pro (Antigravity)"

        self.current_model_id = saved_model_id
        self.current_model_name = saved_model_name
        self.current_effort = self.storage.get_setting("reasoning_effort", "Extra High")
        self.fast_mode = bool(self.storage.get_setting("fast_mode", True))

        # Model Selector Button (`❂ GPT-6 Luna`)
        self.model_selector_btn = QPushButton(f" {self._short_model_label(self.current_model_name)}")
        self.model_selector_btn.setIconSize(QSize(16, 16))
        self.model_selector_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.model_selector_btn.setToolTip("클릭하여 AI 모델 검색 및 변경 (Claude / Codex / Antigravity / API)")
        self.model_selector_btn.clicked.connect(self._open_model_popover)
        footer_row.addWidget(self.model_selector_btn)

        # Effort Selector Button (`Extra High ⌄`)
        self.effort_selector_btn = QPushButton(f"{self.current_effort} ⌄")
        self.effort_selector_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.effort_selector_btn.setToolTip("클릭하여 추론 노력(Effort) 단계 및 Fast mode 설정")
        self.effort_selector_btn.clicked.connect(self._open_effort_popover)
        footer_row.addWidget(self.effort_selector_btn)

        root.addLayout(footer_row)

    def _short_model_label(self, name: str) -> str:
        clean = name.replace(" (Antigravity)", "").replace(" (Direct)", "")
        return clean[:16] + ("…" if len(clean) > 16 else "")

    def _open_model_popover(self):
        theme_mode = self.storage.get_setting("theme", "light")
        pop = ModelSearchPopover(self.current_model_id, self.current_model_name, theme_mode=theme_mode, parent=self)
        pop.model_selected.connect(self._on_model_selected)
        pop.settings_clicked.connect(self.open_settings_requested.emit)

        btn_pos = self.model_selector_btn.mapToGlobal(self.model_selector_btn.rect().topLeft())
        pop_x = max(20, btn_pos.x() - 40)
        pop_y = max(20, btn_pos.y() - 365)
        pop.move(QPoint(pop_x, pop_y))
        pop.exec()

    def _on_model_selected(self, model_id: str, model_name: str):
        self.current_model_id = model_id
        self.current_model_name = model_name
        self.storage.set_setting("default_model", model_id)
        self.storage.set_setting("selected_sub_model_name", model_name)
        self.model_selector_btn.setText(f" {self._short_model_label(model_name)}")
        self.model_selector_btn.setIcon(make_provider_icon(model_id, size=18))

    def _open_effort_popover(self):
        theme_mode = self.storage.get_setting("theme", "light")
        pop = EffortPopover(self.current_effort, self.fast_mode, theme_mode=theme_mode, parent=self)
        pop.effort_selected.connect(self._on_effort_selected)
        pop.fast_mode_toggled.connect(self._on_fast_mode_toggled)

        btn_pos = self.effort_selector_btn.mapToGlobal(self.effort_selector_btn.rect().topRight())
        pop_x = max(20, btn_pos.x() - 195)
        pop_y = max(20, btn_pos.y() - 295)
        pop.move(QPoint(pop_x, pop_y))
        pop.exec()

    def _on_effort_selected(self, effort: str):
        self.current_effort = effort
        self.storage.set_setting("reasoning_effort", effort)
        self.effort_selector_btn.setText(f"{effort} ⌄")

    def _on_fast_mode_toggled(self, checked: bool):
        self.fast_mode = checked
        self.storage.set_setting("fast_mode", checked)

    def _sync_perm_and_ctx_buttons(self):
        perm_names = {
            "perm_safe": "자동 안전 제어 (Auto-Safe)",
            "perm_ask": "매번 확인 (Ask Always)",
            "perm_full": "완전 자율 원격제어 (Full Auto)",
        }
        ctx_names = {
            "ctx_summary": "현재 페이지 핵심 요약",
            "ctx_remote": "원격 조작 도구 모음",
            "ctx_visual": "페이지 구조 시각화 (@visualize)",
            "ctx_draft": "공유 초안 카드 작성 (@draft-preview)",
        }
        self.perm_btn.setIcon(make_status_chip_icon(self.current_perm_key, size=22))
        self.perm_btn.setToolTip(f"원격 제어 권한: ✓ {perm_names.get(self.current_perm_key, '자동 안전 제어')}")

        self.ctx_btn.setIcon(make_status_chip_icon(self.current_ctx_key, size=22))
        self.ctx_btn.setToolTip(f"컨텍스트/스킬 모드: ✓ {ctx_names.get(self.current_ctx_key, '현재 페이지 핵심 요약')}")

    def _open_permission_menu(self):
        theme_mode = self.storage.get_setting("theme", "light")
        p = get_palette(theme_mode)
        menu = QMenu(self)
        menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: {p['popover']};
                color: {p['fg']};
                border: 1px solid {p['border_strong']};
                border-radius: 12px;
                padding: 6px;
                font-size: 13px;
                font-weight: 600;
            }}
            QMenu::item {{
                padding: 7px 14px 7px 10px;
                border-radius: 8px;
            }}
            QMenu::item:selected {{
                background-color: {p['card_hover']};
            }}
            """
        )
        options = [
            ("perm_safe", "자동 안전 제어 (Auto-Safe)"),
            ("perm_ask", "매번 확인 (Ask Always)"),
            ("perm_full", "완전 자율 원격제어 (Full Auto)"),
        ]
        for key, label in options:
            is_sel = key == self.current_perm_key
            display = f"{label}   ✓" if is_sel else label
            act = menu.addAction(make_status_chip_icon(key, size=20), display)
            act.triggered.connect(lambda checked=False, k=key: self._select_permission_mode(k))
        menu.exec(self.perm_btn.mapToGlobal(self.perm_btn.rect().topLeft() - QPoint(0, 125)))

    def _select_permission_mode(self, key: str):
        self.current_perm_key = key
        self.storage.set_setting("remote_permission_mode", key)
        self._sync_perm_and_ctx_buttons()

    def _open_context_menu(self):
        theme_mode = self.storage.get_setting("theme", "light")
        p = get_palette(theme_mode)
        menu = QMenu(self)
        menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: {p['popover']};
                color: {p['fg']};
                border: 1px solid {p['border_strong']};
                border-radius: 12px;
                padding: 6px;
                font-size: 13px;
                font-weight: 600;
            }}
            QMenu::item {{
                padding: 7px 14px 7px 10px;
                border-radius: 8px;
            }}
            QMenu::item:selected {{
                background-color: {p['card_hover']};
            }}
            """
        )
        items = [
            ("ctx_summary", "현재 페이지 핵심 요약", "현재 페이지의 핵심 내용을 요약해줘."),
            ("ctx_remote", "원격 조작 도구 모음 열기/닫기", "__toggle_remote__"),
            ("ctx_visual", "페이지 구조 시각화 (@visualize)", "@visualize 현재 페이지 구조를 차트로 보여줘."),
            ("ctx_draft", "공유 초안 카드 작성 (@draft-preview)", "@draft-preview 현재 페이지 공유 초안을 작성해줘."),
        ]
        for key, label, cmd in items:
            is_sel = key == self.current_ctx_key
            display = f"{label}   ✓" if is_sel else label
            act = menu.addAction(make_status_chip_icon(key, size=20), display)
            act.triggered.connect(lambda checked=False, k=key, c=cmd: self._select_context_mode(k, c))
        menu.exec(self.ctx_btn.mapToGlobal(self.ctx_btn.rect().topLeft() - QPoint(0, 155)))

    def _select_context_mode(self, key: str, cmd: str):
        self.current_ctx_key = key
        self.storage.set_setting("active_ctx_mode", key)
        self._sync_perm_and_ctx_buttons()
        if cmd == "__toggle_remote__":
            self.remote_toggle_btn.setChecked(not self.remote_toggle_btn.isChecked())
        else:
            self.quick_action_triggered.emit(cmd)

    def _toggle_remote_bar(self, checked: bool):
        self.remote_bar.setVisible(checked)

    def _prompt_remote_write(self):
        self.composer_input.setPlainText("현재 페이지 입력란에 '' 내용을 작성해줘")
        self.composer_input.setFocus()
        cursor = self.composer_input.textCursor()
        cursor.setPosition(12)
        self.composer_input.setTextCursor(cursor)

    def refresh_theme(self):
        theme_mode = self.storage.get_setting("theme", "light")
        p = get_palette(theme_mode)

        self.setStyleSheet(f"background-color: {p['sidebar']}; color: {p['fg']};")
        self.header_frame.setStyleSheet("QFrame#SidepanelHeader { background: transparent; border: none; }")

        self.new_chat_btn.setIcon(make_nav_icon("new_chat", p["fg"], p["accent"], 22))
        self.settings_btn.setIcon(make_nav_icon("settings", p["fg"], p["accent"], 22))
        self.attach_btn.setIcon(make_nav_icon("plus", p["fg_muted"], p["accent"], 20))
        self.send_btn.setIcon(make_nav_icon("mic", p["primary_fg"], p["accent"], 20))

        self._sync_perm_and_ctx_buttons()
        self.model_selector_btn.setIcon(make_provider_icon(self.current_model_id, size=18))

        # Composer outer white rounded card (Image 3 style)
        self.composer_card.setStyleSheet(
            f"""
            QFrame#SidepanelComposerCard {{
                background-color: {p['card']};
                border: 1px solid {p['border']};
                border-radius: 22px;
            }}
            """
        )

        # Attached Page Context Pill inside Composer (Image 3 style)
        self.page_chip_card.setStyleSheet(
            f"""
            QFrame#AttachedPageChip {{
                background-color: {p['card']};
                border: 1px solid {p['border']};
                border-radius: 14px;
            }}
            """
        )
        self.page_title_lbl.setStyleSheet(f"color: {p['fg']}; font-size: 12.5px; font-weight: 700; border: none;")
        self.page_domain_lbl.setStyleSheet(f"color: {p['fg_muted']}; font-size: 11px; border: none;")

        self.remote_toggle_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {p['bg']};
                color: {p['fg_muted']};
                border: 1px solid {p['border']};
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:checked {{
                background-color: {p['accent_soft']};
                color: {p['accent_fg']};
                border: 1px solid {p['border']};
            }}
            """
        )

        chip_style = (
            f"QPushButton {{ background-color: {p['bg']}; color: {p['fg']}; border: 1px solid {p['border']}; "
            f"border-radius: 8px; padding: 4px 7px; font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {p['card_hover']}; }}"
        )
        for b in self.remote_btns:
            b.setStyleSheet(chip_style)

        self.composer_input.setStyleSheet(
            f"""
            QPlainTextEdit#SidepanelComposerEdit {{
                background: transparent;
                color: {p['fg']};
                border: none;
                padding: 2px 0px;
                font-size: 13.5px;
            }}
            """
        )

        # Circular + button & Circular dark send/mic button (Image 3)
        self.attach_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {p['bg_elevated']};
                border: none;
                border-radius: 17px;
            }}
            QPushButton:hover {{
                background-color: {p['card_hover']};
            }}
            """
        )
        self.send_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {p['primary']};
                border: none;
                border-radius: 18px;
            }}
            QPushButton:hover {{
                background-color: {p['accent']};
            }}
            QPushButton:disabled {{
                background-color: {p['border_strong']};
            }}
            """
        )

        footer_btn_style = (
            f"""
            QPushButton {{
                background-color: transparent;
                color: {p['fg_muted']};
                border: none;
                border-radius: 9px;
                padding: 4px 7px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {p['card_hover']};
                color: {p['fg']};
            }}
            """
        )
        self.perm_btn.setStyleSheet(footer_btn_style)
        self.ctx_btn.setStyleSheet(footer_btn_style)
        self.model_selector_btn.setStyleSheet(footer_btn_style)
        self.effort_selector_btn.setStyleSheet(footer_btn_style)

    def update_active_page_context(self, title: str, url: str):
        """Updates the embedded page card inside the chat composer (Image 3 style)."""
        self.active_page_title = title or "현재 페이지"
        self.active_page_url = url or "bside://newtab"

        short_title = self.active_page_title[:22] + ("…" if len(self.active_page_title) > 22 else "")
        self.page_title_lbl.setText(short_title)

        parsed = urllib.parse.urlparse(self.active_page_url)
        domain = parsed.netloc or self.active_page_url[:28]
        self.page_domain_lbl.setText(domain)

        low_url = self.active_page_url.lower()
        if "naver.com" in low_url:
            pix = make_3d_badge_pixmap("N", "#22C55E", "#15803D", size=36, radius=10)
        elif "google.com" in low_url:
            pix = make_3d_badge_pixmap("G", "#3B82F6", "#1D4ED8", size=36, radius=10)
        elif "github.com" in low_url:
            pix = make_3d_badge_pixmap("🐙", "#4B5563", "#1F2937", size=36, radius=10)
        elif "youtube.com" in low_url:
            pix = make_3d_badge_pixmap("▶", "#EF4444", "#B91C1C", size=36, radius=10)
        elif low_url.startswith("bside://"):
            pix = get_internal_title_icon_pixmap(36)
        else:
            pix = make_3d_badge_pixmap("🌐", "#38BDF8", "#0284C7", size=36, radius=10)
        self.page_icon_lbl.setPixmap(pix)

    def reload_active_session(self):
        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        sessions = self.storage.get_sessions()
        active_sess = self.storage.get_active_session()
        active_idx = 0
        for idx, s in enumerate(sessions):
            self.session_combo.addItem(s.get("title", "새 대화"), s.get("id"))
            if s.get("id") == active_sess.get("id"):
                active_idx = idx
        self.session_combo.setCurrentIndex(active_idx)
        self.session_combo.blockSignals(False)

        self.streaming_card = None
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        theme_mode = self.storage.get_setting("theme", "light")
        for msg in active_sess.get("messages", []):
            card = MessageCardWidget(msg, theme_mode=theme_mode)
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, card)

        self._scroll_to_bottom()

    def append_message_card(self, msg: Dict[str, Any]) -> MessageCardWidget:
        theme_mode = self.storage.get_setting("theme", "light")
        card = MessageCardWidget(msg, theme_mode=theme_mode)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, card)
        self._scroll_to_bottom()
        return card

    def start_streaming_assistant_card(self):
        self.streaming_card = self.append_message_card(
            {"role": "assistant", "content": "✦ 생각 중..."}
        )

    def update_streaming_assistant_card(self, partial_text: str):
        if self.streaming_card is not None:
            self.streaming_card.update_streaming_text(partial_text)
            self._scroll_to_bottom()

    def finalize_streaming_assistant_card(self, final_msg: Dict[str, Any]):
        if self.streaming_card is not None:
            self.streaming_card.update_streaming_text(final_msg.get("content", ""))
            if final_msg.get("visual_html"):
                self.streaming_card.add_visual_html(final_msg["visual_html"])
            if final_msg.get("draft_card"):
                self.streaming_card.add_draft_card(final_msg["draft_card"])
            self.streaming_card = None
            self._scroll_to_bottom()
        else:
            self.append_message_card(final_msg)

    def set_agent_status(self, text: str, busy: bool = False):
        self.status_label.setVisible(busy)
        self.status_label.setStyleSheet("font-size: 11px; color: #4F46E5; font-weight: 600;")
        self.status_label.setText(text)
        self.send_btn.setEnabled(not busy)

    def _scroll_to_bottom(self):
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _attach_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "첨부할 파일 선택")
        if path:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    excerpt = f.read(3000)
            except Exception:
                excerpt = ""
            self.attachments.append({"name": os.path.basename(path), "path": path, "excerpt": excerpt})
            names = ", ".join(a["name"] for a in self.attachments)
            self.attachment_label.setText(f"📎 {names}")
            self.attachment_label.setStyleSheet("font-size: 11px; color: #4F46E5; font-weight: 600;")
            self.attachment_label.setVisible(True)

    def _on_session_combo_changed(self, index: int):
        if index < 0:
            return
        sess_id = self.session_combo.itemData(index)
        if sess_id:
            self.storage.data["active_session_id"] = sess_id
            self.storage.save()
            self.reload_active_session()

    def _create_new_session(self):
        self.storage.create_session("새 대화")
        self.reload_active_session()

    def _submit(self):
        text = self.composer_input.toPlainText().strip()
        if not text:
            return
        atts = list(self.attachments)
        self.composer_input.clear()
        self.attachments.clear()
        self.attachment_label.setVisible(False)
        self.prompt_submitted.emit(text, atts)
