# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent — Modal Dialogs
Replicates:
1. tabsearch.html (Quick Tab Search & Switcher Modal, Ctrl+Shift+A)
2. BsidePasswordManager (Bside Vault Modal, Ctrl+Shift+Y)
3. main.html Settings:
   - Tab 1: 🔗 구독 로그인 & CLI 연결 (Claude Code / Codex / Antigravity agy.exe OAuth 로그인 상태 확인 및 원클릭 로그인 창 실행)
   - Tab 2: 🔑 AI API 키 & 테마 (Anthropic / OpenAI / Gemini API 키 및 로컬 Ollama 설정)
   - Tab 3: 🧠 에이전트 기억 (Memories)
   - Tab 4: ⚡ 자동화 루틴 (Routines)
"""

from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QWidget,
    QFormLayout,
    QComboBox,
    QFrame,
    QMessageBox,
    QApplication,
    QCheckBox,
)
from PySide6.QtCore import Qt, Signal

from storage import StorageManager
from theme import get_palette
from agent_engine import get_subscription_auth_status, launch_subscription_login_terminal


class TabSearchDialog(QDialog):
    """Replicates BsideAgentManager/tabsearch.html (Quick Tab Search & Switcher)."""
    tab_selected = Signal(int)

    def __init__(self, tabs_info: List[Dict[str, Any]], theme_mode: str = "dark", parent=None):
        super().__init__(parent)
        self.tabs_info = tabs_info
        self.setWindowTitle("Bside 탭 검색 (tabsearch.html)")
        self.resize(520, 380)

        p = get_palette(theme_mode)
        self.setStyleSheet(f"background-color: {p['bg']}; color: {p['fg']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel("🔍 열린 탭 및 방문 기록 빠른 검색 (Ctrl+Shift+A)")
        header.setStyleSheet(f"font-weight: 700; font-size: 14px; color: {p['accent_fg']}; border: none;")
        layout.addWidget(header)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("탭 제목 또는 URL로 필터링...")
        self.search_input.textChanged.connect(self._filter_list)
        layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.itemActivated.connect(self._on_item_activated)
        self.list_widget.itemClicked.connect(self._on_item_activated)
        layout.addWidget(self.list_widget, 1)

        self._populate("")
        self.search_input.setFocus()

    def _populate(self, query: str):
        self.list_widget.clear()
        q = query.lower().strip()
        for t in self.tabs_info:
            title = t.get("title", "무제")
            url = t.get("url", "")
            idx = t.get("index", 0)
            if q and q not in title.lower() and q not in url.lower():
                continue
            item = QListWidgetItem(f"[{idx + 1}] {title}\n    {url}")
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _filter_list(self, text: str):
        self._populate(text)

    def _on_item_activated(self, item: QListWidgetItem):
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None:
            self.tab_selected.emit(int(idx))
            self.accept()


class BsideVaultDialog(QDialog):
    """
    Upgraded Bside Vault (Ctrl+Shift+Y / 🔑 Icon):
    - Tab 1: 🔑 로그인 계정 (아이디 / 비밀번호 저장, 사이트 접속 시 자동입력, 1클릭 자동입력 및 로그인 실행)
    - Tab 2: 💳 결제 카드 (카드번호 / 유효기간 / CVC / 명의자 저장 및 결제창 1클릭 자동입력)
    """
    autofill_login_requested = Signal(dict, bool)  # (vault_entry, auto_submit)
    autofill_card_requested = Signal(dict)         # (card_entry)

    def __init__(self, storage: StorageManager, current_url: str = "", parent=None):
        super().__init__(parent)
        self.storage = storage
        self.current_url = current_url or ""
        self.setWindowTitle("🔐 Bside Vault — 비밀번호 & 결제카드 자동입력 매니저 (Ctrl+Shift+Y)")
        self.resize(670, 520)

        p = get_palette(self.storage.get_setting("theme", "light"))
        self.setStyleSheet(f"background-color: {p['bg']}; color: {p['fg']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header Row + Auto-Fill Toggle
        top_row = QHBoxLayout()
        title = QLabel("🔐 Bside Vault — 자동 로그인 & 결제카드 금고")
        title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {p['fg']}; border: none;")
        top_row.addWidget(title)
        top_row.addStretch(1)

        self.auto_fill_cb = QCheckBox("사이트 접속 시 저장된 아이디/비밀번호 자동 입력")
        self.auto_fill_cb.setChecked(bool(self.storage.get_setting("vault_auto_fill", True)))
        self.auto_fill_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auto_fill_cb.setStyleSheet(f"font-size: 12.5px; font-weight: 700; color: {p['accent']};")
        self.auto_fill_cb.toggled.connect(lambda checked: self.storage.set_setting("vault_auto_fill", bool(checked)))
        top_row.addWidget(self.auto_fill_cb)
        layout.addLayout(top_row)

        sub_lbl = QLabel(
            "💡 계정이나 카드를 선택하고 [⚡ 현재 페이지에 자동입력] 또는 [🚀 자동입력 후 로그인]을 누르면 브라우저 화면에 즉시 입력됩니다."
        )
        sub_lbl.setStyleSheet(f"color: {p['fg_muted']}; font-size: 12px; border: none;")
        layout.addWidget(sub_lbl)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # =========================================================
        # Tab 1: 🔑 로그인 계정 (아이디 / 비밀번호)
        # =========================================================
        login_tab = QWidget()
        login_layout = QVBoxLayout(login_tab)
        login_layout.setContentsMargins(12, 12, 12, 12)
        login_layout.setSpacing(10)

        self.vault_list = QListWidget()
        self.vault_list.itemDoubleClicked.connect(lambda _item: self._trigger_selected_login_autofill(auto_submit=False))
        login_layout.addWidget(self.vault_list, 1)

        # Add new login credential form
        form = QHBoxLayout()
        form.setSpacing(6)
        self.site_input = QLineEdit()
        default_site = self.current_url if self.current_url.startswith("http") else ""
        self.site_input.setText(default_site)
        self.site_input.setPlaceholderText("사이트 주소 (예: https://nid.naver.com)")
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("아이디 / 이메일")
        self.pw_input = QLineEdit()
        self.pw_input.setPlaceholderText("비밀번호 (실제 자동입력용)")
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)

        add_btn = QPushButton("+ 계정 저장")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            f"background: {p['accent']}; color: #fff; border: none; border-radius: 8px; padding: 7px 14px; font-weight: 700;"
        )
        add_btn.clicked.connect(self._add_entry)

        form.addWidget(self.site_input, 2)
        form.addWidget(self.user_input, 2)
        form.addWidget(self.pw_input, 2)
        form.addWidget(add_btn)
        login_layout.addLayout(form)

        # Action buttons for selected login entry
        login_act_row = QHBoxLayout()
        login_act_row.setSpacing(8)

        fill_login_btn = QPushButton("⚡ 현재 페이지에 자동입력")
        fill_login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fill_login_btn.setStyleSheet(
            f"background: {p['accent']}; color: #ffffff; border: none; border-radius: 8px; padding: 7px 14px; font-weight: 700;"
        )
        fill_login_btn.clicked.connect(lambda: self._trigger_selected_login_autofill(auto_submit=False))
        login_act_row.addWidget(fill_login_btn)

        submit_login_btn = QPushButton("🚀 자동입력 후 로그인 클릭")
        submit_login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        submit_login_btn.setStyleSheet(
            "background: #10B981; color: #ffffff; border: none; border-radius: 8px; padding: 7px 14px; font-weight: 700;"
        )
        submit_login_btn.clicked.connect(lambda: self._trigger_selected_login_autofill(auto_submit=True))
        login_act_row.addWidget(submit_login_btn)

        copy_id_btn = QPushButton("아이디 복사")
        copy_id_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_id_btn.clicked.connect(self._copy_selected_user)
        login_act_row.addWidget(copy_id_btn)

        copy_pw_btn = QPushButton("비밀번호 복사")
        copy_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_pw_btn.clicked.connect(self._copy_selected_pw)
        login_act_row.addWidget(copy_pw_btn)

        del_login_btn = QPushButton("삭제")
        del_login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_login_btn.clicked.connect(self._delete_selected_login)
        login_act_row.addWidget(del_login_btn)

        login_act_row.addStretch(1)
        login_layout.addLayout(login_act_row)

        self.tabs.addTab(login_tab, "🔑 로그인 계정 (아이디 / 비밀번호)")

        # =========================================================
        # Tab 2: 💳 결제 카드 (카드번호 / 유효기간 / CVC)
        # =========================================================
        card_tab = QWidget()
        card_layout = QVBoxLayout(card_tab)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        self.card_list = QListWidget()
        self.card_list.itemDoubleClicked.connect(lambda _item: self._trigger_selected_card_autofill())
        card_layout.addWidget(self.card_list, 1)

        card_form = QHBoxLayout()
        card_form.setSpacing(6)
        self.card_label_input = QLineEdit()
        self.card_label_input.setPlaceholderText("카드 별칭 (예: 현대카드)")
        self.card_num_input = QLineEdit()
        self.card_num_input.setPlaceholderText("카드번호 (1234-5678-1234-5678)")
        self.card_exp_input = QLineEdit()
        self.card_exp_input.setPlaceholderText("유효기간 (MM/YY)")
        self.card_exp_input.setFixedWidth(105)
        self.card_cvc_input = QLineEdit()
        self.card_cvc_input.setPlaceholderText("CVC (3자리)")
        self.card_cvc_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.card_cvc_input.setFixedWidth(90)
        self.card_holder_input = QLineEdit()
        self.card_holder_input.setPlaceholderText("명의자 성함")
        self.card_holder_input.setFixedWidth(105)

        add_card_btn = QPushButton("+ 카드 저장")
        add_card_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_card_btn.setStyleSheet(
            f"background: {p['accent']}; color: #fff; border: none; border-radius: 8px; padding: 7px 14px; font-weight: 700;"
        )
        add_card_btn.clicked.connect(self._add_card_entry)

        card_form.addWidget(self.card_label_input, 1)
        card_form.addWidget(self.card_num_input, 2)
        card_form.addWidget(self.card_exp_input)
        card_form.addWidget(self.card_cvc_input)
        card_form.addWidget(self.card_holder_input)
        card_form.addWidget(add_card_btn)
        card_layout.addLayout(card_form)

        card_act_row = QHBoxLayout()
        card_act_row.setSpacing(8)

        fill_card_btn = QPushButton("⚡ 현재 페이지 결제창에 카드 자동입력")
        fill_card_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fill_card_btn.setStyleSheet(
            f"background: {p['accent']}; color: #ffffff; border: none; border-radius: 8px; padding: 7px 14px; font-weight: 700;"
        )
        fill_card_btn.clicked.connect(self._trigger_selected_card_autofill)
        card_act_row.addWidget(fill_card_btn)

        copy_card_btn = QPushButton("카드번호 복사")
        copy_card_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_card_btn.clicked.connect(self._copy_selected_card_number)
        card_act_row.addWidget(copy_card_btn)

        del_card_btn = QPushButton("카드 삭제")
        del_card_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_card_btn.clicked.connect(self._delete_selected_card)
        card_act_row.addWidget(del_card_btn)

        card_act_row.addStretch(1)
        card_layout.addLayout(card_act_row)

        self.tabs.addTab(card_tab, "💳 결제 카드 (카드번호 / 유효기간 / CVC)")

        # Bottom Close Row
        footer_row = QHBoxLayout()
        footer_row.addStretch(1)
        close_btn = QPushButton("닫기")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        footer_row.addWidget(close_btn)
        layout.addLayout(footer_row)

        self._reload()

    @staticmethod
    def _mask_card_number(num: str) -> str:
        digits = "".join(ch for ch in (num or "") if ch.isdigit())
        if len(digits) >= 12:
            return f"{digits[:4]}-****-****-{digits[-4:]}"
        return num or "****"

    def _reload(self):
        self.vault_list.clear()
        for v in self.storage.data.get("vault", []):
            pw_raw = v.get("password", "")
            has_real_pw = bool(pw_raw and not str(pw_raw).startswith("••"))
            pw_badge = "비밀번호 저장됨 (자동입력 준비됨)" if has_real_pw else "아이디만 저장됨"
            item = QListWidgetItem(
                f"🔑 {v.get('title') or v.get('site')}  ({v.get('site')})\n"
                f"    계정: {v.get('username')}   |   비밀번호: •••••••• ({pw_badge})"
            )
            item.setData(Qt.ItemDataRole.UserRole, v)
            self.vault_list.addItem(item)
        if self.vault_list.count() > 0:
            self.vault_list.setCurrentRow(0)

        self.card_list.clear()
        for c in self.storage.get_card_entries():
            masked = self._mask_card_number(c.get("number", ""))
            item = QListWidgetItem(
                f"💳 {c.get('label', '카드')}  —  {masked}\n"
                f"    유효기간: {c.get('expiry', 'MM/YY')}   |   CVC: •••   |   명의자: {c.get('cardholder', '-')}"
            )
            item.setData(Qt.ItemDataRole.UserRole, c)
            self.card_list.addItem(item)
        if self.card_list.count() > 0:
            self.card_list.setCurrentRow(0)

    def _add_entry(self):
        site = self.site_input.text().strip()
        user = self.user_input.text().strip()
        pw = self.pw_input.text().strip()
        if not site or not user:
            QMessageBox.warning(self, "입력 확인", "사이트 주소와 아이디(이메일)를 입력해 주세요.")
            return
        # Save the REAL password so auto-fill works on websites!
        self.storage.add_vault_entry(site=site, title=site, username=user, password=pw)
        self.user_input.clear()
        self.pw_input.clear()
        self._reload()

    def _trigger_selected_login_autofill(self, auto_submit: bool = False):
        item = self.vault_list.currentItem()
        if not item:
            return
        v = item.data(Qt.ItemDataRole.UserRole) or {}
        self.autofill_login_requested.emit(v, auto_submit)
        self.accept()

    def _copy_selected_user(self):
        item = self.vault_list.currentItem()
        if item:
            v = item.data(Qt.ItemDataRole.UserRole) or {}
            QApplication.clipboard().setText(v.get("username", ""))

    def _copy_selected_pw(self):
        item = self.vault_list.currentItem()
        if item:
            v = item.data(Qt.ItemDataRole.UserRole) or {}
            QApplication.clipboard().setText(v.get("password", ""))

    def _delete_selected_login(self):
        item = self.vault_list.currentItem()
        if item:
            v = item.data(Qt.ItemDataRole.UserRole) or {}
            if v.get("id"):
                self.storage.delete_vault_entry(v["id"])
                self._reload()

    def _add_card_entry(self):
        label = self.card_label_input.text().strip() or "내 결제카드"
        num = self.card_num_input.text().strip()
        exp = self.card_exp_input.text().strip()
        cvc = self.card_cvc_input.text().strip()
        holder = self.card_holder_input.text().strip()
        if not num:
            QMessageBox.warning(self, "카드번호 확인", "카드번호를 입력해 주세요.")
            return
        self.storage.add_card_entry(label=label, cardholder=holder, number=num, expiry=exp, cvc=cvc)
        self.card_label_input.clear()
        self.card_num_input.clear()
        self.card_exp_input.clear()
        self.card_cvc_input.clear()
        self.card_holder_input.clear()
        self._reload()

    def _trigger_selected_card_autofill(self):
        item = self.card_list.currentItem()
        if not item:
            return
        c = item.data(Qt.ItemDataRole.UserRole) or {}
        self.autofill_card_requested.emit(c)
        self.accept()

    def _copy_selected_card_number(self):
        item = self.card_list.currentItem()
        if item:
            c = item.data(Qt.ItemDataRole.UserRole) or {}
            QApplication.clipboard().setText(c.get("number", ""))

    def _delete_selected_card(self):
        item = self.card_list.currentItem()
        if item:
            c = item.data(Qt.ItemDataRole.UserRole) or {}
            if c.get("id"):
                self.storage.delete_card_entry(c["id"])
                self._reload()


class SettingsWorkspaceDialog(QDialog):
    """Replicates BsideAgentManager Settings with 1-Click Subscription Login & CLI Connection Hub."""
    settings_updated = Signal()

    def __init__(self, storage: StorageManager, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle("⚙ Bside 에이전트 구독 연결 & 브라우저 설정")
        self.resize(680, 540)

        p = get_palette(self.storage.get_setting("theme", "dark"))
        self.setStyleSheet(f"background-color: {p['bg']}; color: {p['fg']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        # --- Tab 1: Subscription OAuth & CLI Login Hub ---
        sub_tab = QWidget()
        self.sub_layout = QVBoxLayout(sub_tab)
        self.sub_layout.setContentsMargins(14, 14, 14, 14)
        self.sub_layout.setSpacing(10)

        sub_intro = QLabel(
            "💡 현재 PC에 설치된 구독형 AI CLI(Claude Code, Codex, Antigravity `agy.exe`)의 로그인 상태입니다.\n"
            "로그인되어 있으면 별도 작업 없이 바로 사용 가능하며, 계정을 변경하거나 새로 연결하려면 우측 [브라우저 로그인 창 열기] 버튼을 누르세요."
        )
        sub_intro.setWordWrap(True)
        sub_intro.setStyleSheet(f"color: {p['fg_muted']}; font-size: 12px; border: none;")
        self.sub_layout.addWidget(sub_intro)

        self.sub_cards_container = QVBoxLayout()
        self.sub_cards_container.setSpacing(8)
        self.sub_layout.addLayout(self.sub_cards_container)

        refresh_sub_btn = QPushButton("↻ 구독 로그인 상태 다시 확인")
        refresh_sub_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_sub_btn.setStyleSheet(
            f"background-color: {p['card']}; color: {p['fg']}; border: 1px solid {p['border']}; border-radius: 8px; padding: 6px 12px; font-weight: 600;"
        )
        refresh_sub_btn.clicked.connect(self._render_subscription_cards)
        self.sub_layout.addWidget(refresh_sub_btn)
        self.sub_layout.addStretch(1)

        tabs.addTab(sub_tab, "🔗 구독 연결 (Claude / Codex / Antigravity)")

        # --- Tab 2: API Keys & Theme ---
        model_tab = QWidget()
        form = QFormLayout(model_tab)
        form.setContentsMargins(14, 14, 14, 14)
        form.setSpacing(10)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self.storage.get_setting("theme", "dark"))
        form.addRow("테마 모드 (Dark / Warm Ivory Light):", self.theme_combo)

        self.anthropic_input = QLineEdit(self.storage.get_setting("anthropic_api_key", ""))
        self.anthropic_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_input.setPlaceholderText("sk-ant-... (구독 모두 소진 후 API 모드 선택 시 사용)")
        form.addRow("Anthropic API Key:", self.anthropic_input)

        self.openai_input = QLineEdit(self.storage.get_setting("openai_api_key", ""))
        self.openai_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_input.setPlaceholderText("sk-... (구독 모두 소진 후 API 모드 선택 시 사용)")
        form.addRow("OpenAI API Key:", self.openai_input)

        self.gemini_input = QLineEdit(self.storage.get_setting("gemini_api_key", ""))
        self.gemini_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_input.setPlaceholderText("AIza... (구독 모두 소진 후 API 모드 선택 시 사용)")
        form.addRow("Gemini API Key:", self.gemini_input)

        self.custom_url_input = QLineEdit(self.storage.get_setting("custom_base_url", "http://localhost:11434/v1"))
        form.addRow("로컬 Ollama / OpenAI 호환 URL:", self.custom_url_input)

        self.custom_model_input = QLineEdit(self.storage.get_setting("custom_model_name", "qwen2.5:7b"))
        form.addRow("로컬 모델 이름:", self.custom_model_input)

        tabs.addTab(model_tab, "🔑 API 키 & 테마")

        # --- Tab 3: Memories ---
        mem_tab = QWidget()
        mem_layout = QVBoxLayout(mem_tab)
        self.mem_list = QListWidget()
        mem_layout.addWidget(self.mem_list, 1)

        mem_add_row = QHBoxLayout()
        self.mem_input = QLineEdit()
        self.mem_input.setPlaceholderText("에이전트가 기억할 새로운 선호사항이나 규칙 입력...")
        mem_add_btn = QPushButton("+ 기억 추가")
        mem_add_btn.clicked.connect(self._add_memory)
        mem_add_row.addWidget(self.mem_input, 1)
        mem_add_row.addWidget(mem_add_btn)
        mem_layout.addLayout(mem_add_row)

        tabs.addTab(mem_tab, "🧠 에이전트 기억 (Memories)")

        # --- Tab 4: Routines ---
        rt_tab = QWidget()
        rt_layout = QVBoxLayout(rt_tab)
        self.rt_list = QListWidget()
        rt_layout.addWidget(self.rt_list, 1)

        rt_add_row = QHBoxLayout()
        self.rt_name_input = QLineEdit()
        self.rt_name_input.setPlaceholderText("루틴 이름")
        self.rt_prompt_input = QLineEdit()
        self.rt_prompt_input.setPlaceholderText("실행할 프롬프트 지시문...")
        rt_add_btn = QPushButton("+ 루틴 추가")
        rt_add_btn.clicked.connect(self._add_routine)
        rt_add_row.addWidget(self.rt_name_input, 1)
        rt_add_row.addWidget(self.rt_prompt_input, 2)
        rt_add_row.addWidget(rt_add_btn)
        rt_layout.addLayout(rt_add_row)

        tabs.addTab(rt_tab, "⚡ 자동화 루틴 (Routines)")

        # Footer Save/Close
        btn_row = QHBoxLayout()
        update_chk_btn = QPushButton("🔄 최신 버전 업데이트 확인 (자동 설치)")
        update_chk_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        update_chk_btn.setStyleSheet(
            f"background: {p['card']}; color: {p['accent']}; border: 1px solid {p['border']}; border-radius: 8px; padding: 7px 14px; font-weight: 700;"
        )
        update_chk_btn.clicked.connect(self._check_updates_now)
        btn_row.addWidget(update_chk_btn)
        btn_row.addStretch()
        save_btn = QPushButton("저장 및 닫기")
        save_btn.setStyleSheet(
            f"background: {p['accent']}; color: #fff; border: none; border-radius: 8px; padding: 7px 16px; font-weight: 700;"
        )
        save_btn.clicked.connect(self._save_all)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self._render_subscription_cards()
        self._reload_lists()

    def _render_subscription_cards(self):
        while self.sub_cards_container.count():
            item = self.sub_cards_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        p = get_palette(self.storage.get_setting("theme", "dark"))
        status_map = get_subscription_auth_status()

        for key in ("antigravity", "claude", "codex"):
            info = status_map.get(key, {})
            card = QFrame()
            card.setObjectName(f"SubCard_{key}")
            card.setStyleSheet(
                f"QFrame#SubCard_{key} {{ background-color: {p['card']}; border: 1px solid {p['border']}; border-radius: 10px; }}"
            )
            row = QHBoxLayout(card)
            row.setContentsMargins(14, 10, 14, 10)
            row.setSpacing(10)

            left_col = QVBoxLayout()
            left_col.setSpacing(3)

            logged = info.get("logged_in", False)
            installed = info.get("installed", False)
            badge_text = "● 로그인 연결됨 (즉시 사용 가능)" if logged else ("○ 로그인 필요" if installed else "✕ CLI 미설치")
            badge_color = "#10B981" if logged else "#F59E0B"

            title_lbl = QLabel(f"{info.get('name', key)}   —   {badge_text}")
            title_lbl.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {badge_color}; border: none;")
            left_col.addWidget(title_lbl)

            path_lbl = QLabel(
                f"실행 파일: {info.get('bin') or '없음'}\n인증 토큰: {info.get('cred_path') or '없음'}"
            )
            path_lbl.setStyleSheet(f"color: {p['fg_muted']}; font-size: 11px; border: none;")
            left_col.addWidget(path_lbl)
            row.addLayout(left_col, 1)

            login_btn = QPushButton("🔗 브라우저 로그인 창 열기" if not logged else "🔄 계정 재연결 / 로그인")
            login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            login_btn.setStyleSheet(
                f"background-color: {p['bg_elevated']}; color: {p['fg']}; border: 1px solid {p['border_strong']}; border-radius: 7px; padding: 6px 12px; font-weight: 600; font-size: 11.5px;"
            )
            login_btn.clicked.connect(lambda checked=False, prov=key: self._trigger_cli_login(prov))
            row.addWidget(login_btn)

            self.sub_cards_container.addWidget(card)

    def _trigger_cli_login(self, provider: str):
        ok, msg = launch_subscription_login_terminal(provider)
        if ok:
            QMessageBox.information(self, "구독 OAuth 로그인 실행", msg)
        else:
            QMessageBox.warning(self, "로그인 실행 실패", msg)

    def _reload_lists(self):
        self.mem_list.clear()
        for m in self.storage.data.get("memories", []):
            self.mem_list.addItem(f"• {m.get('content')} ({m.get('source')})")

        self.rt_list.clear()
        for r in self.storage.data.get("routines", []):
            self.rt_list.addItem(f"⚡ {r.get('name')} — {r.get('prompt')}")

    def _add_memory(self):
        txt = self.mem_input.text().strip()
        if txt:
            self.storage.add_memory(txt, source="User Settings")
            self.mem_input.clear()
            self._reload_lists()

    def _add_routine(self):
        name = self.rt_name_input.text().strip()
        pr = self.rt_prompt_input.text().strip()
        if name and pr:
            self.storage.add_routine(name, "수동 실행 / 온디맨드", pr)
            self.rt_name_input.clear()
            self.rt_prompt_input.clear()
            self._reload_lists()

    def _check_updates_now(self):
        from updater import AutoUpdater
        self._updater = AutoUpdater(self)
        self._updater.check(silent=False)

    def _save_all(self):
        self.storage.update_settings(
            {
                "theme": self.theme_combo.currentText(),
                "openai_api_key": self.openai_input.text().strip(),
                "gemini_api_key": self.gemini_input.text().strip(),
                "anthropic_api_key": self.anthropic_input.text().strip(),
                "custom_base_url": self.custom_url_input.text().strip(),
                "custom_model_name": self.custom_model_input.text().strip(),
            }
        )
        self.settings_updated.emit()
        self.accept()
