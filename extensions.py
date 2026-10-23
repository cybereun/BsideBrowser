# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent — Chrome Extension Manager, Toolbar Popover & Popup Host
Uses PySide6 / Qt 6.10 native `QWebEngineExtensionManager` and `QWebEngineExtensionInfo`
plus:
- Real Extension Icon loading from `manifest.json` (like Chrome/Edge Image 1 & Image 3)
- Chrome-style Extensions Popover (`ExtensionToolbarPopover`, Image 1) with Pushpin (`📌`) toggle
  and 3-dot (`⋮`) menu + `⚙️ 확장 프로그램 관리` button
- Direct Chrome Web Store (`.crx` / `.zip` / unpacked folder) installation & PC Chrome extension import!
"""

import os
import json
import shutil
import zipfile
import tempfile
import urllib.request
from typing import List, Dict, Any, Optional, Tuple

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QWidget,
    QLineEdit,
    QApplication,
    QMenu,
)
from PySide6.QtCore import Qt, Signal, QUrl, QPoint, QTimer, QSize
from PySide6.QtGui import QIcon, QPixmap, QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineExtensionInfo

from theme import get_palette
from icons import (
    make_3d_badge_pixmap,
    make_nav_icon,
    make_pushpin_icon,
    make_more_dots_icon,
)


def is_internal_builtin_extension(ext: QWebEngineExtensionInfo) -> bool:
    """
    Returns True if `ext` is one of Chromium/QtWebEngine's internal component extensions
    (`chromium-pdf`, `Google Hangouts` inside `PySide6/resources/...`) so they don't clutter
    the user's Chrome extension list or toolbar pins.
    """
    try:
        path = (ext.path() or "").replace("\\", "/").lower()
        name = (ext.name() or "").strip().lower()
        if "pyside6/resources" in path or "qtwebengine" in path:
            return True
        if name in ("chromium-pdf", "google hangouts", "hangout_services"):
            return True
    except Exception:
        pass
    return False


def _resolve_manifest_message(ext_dir: str, raw_val: str) -> str:
    """Resolves `__MSG_xxx__` i18n placeholders from `_locales/<lang>/messages.json` if present."""
    if not raw_val or not str(raw_val).startswith("__MSG_"):
        return str(raw_val or "")
    key = str(raw_val)[6:].rstrip("_")
    locales_dir = os.path.join(ext_dir, "_locales")
    if not os.path.isdir(locales_dir):
        return str(raw_val)
    # Prefer ko, en, en_US, then any folder
    langs = ["ko", "ko_KR", "en", "en_US"] + os.listdir(locales_dir)
    seen = set()
    for lang in langs:
        if lang in seen:
            continue
        seen.add(lang)
        msg_file = os.path.join(locales_dir, lang, "messages.json")
        if os.path.isfile(msg_file):
            try:
                with open(msg_file, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                for k, v in data.items():
                    if k.lower() == key.lower() and isinstance(v, dict) and "message" in v:
                        return str(v["message"])
            except Exception:
                pass
    return str(raw_val)


def get_extension_meta_and_icon(ext: QWebEngineExtensionInfo, icon_size: int = 22) -> Dict[str, Any]:
    """
    Reads `manifest.json` from `ext.path()` and extracts:
    - `display_name`: Resolved human-readable extension name
    - `pixmap` & `icon`: Real extension icon from `icons` or `action.default_icon` (or fallback badge)
    - `access_category`: `"full"` (`전체 액세스`), `"requested"` (`액세스가 요청됨`), or `"none"` (`필요한 액세스 권한 없음`)
    - `fallback_popup_url`: QUrl to local popup/options HTML if `ext.actionPopupUrl()` is empty
    - `content_scripts`: list of JS/CSS files from `manifest.json` so clicking a content-script extension
      on the toolbar can actively execute/toggle it on the current page!
    """
    ext_dir = ext.path() or ""
    raw_name = ext.name() or "확장 프로그램"
    display_name = raw_name
    manifest: Dict[str, Any] = {}

    manifest_file = os.path.join(ext_dir, "manifest.json") if ext_dir else ""
    if manifest_file and os.path.isfile(manifest_file):
        try:
            with open(manifest_file, "r", encoding="utf-8", errors="ignore") as f:
                manifest = json.load(f)
            mf_name = manifest.get("name") or manifest.get("short_name") or raw_name
            resolved = _resolve_manifest_message(ext_dir, str(mf_name))
            if resolved and not resolved.startswith("__MSG_"):
                display_name = resolved
        except Exception:
            pass

    # 1. Resolve Real Extension Icon file path
    icon_candidates: List[str] = []

    # Check action / browser_action / page_action default_icon first or manifest icons
    for act_key in ("action", "browser_action", "page_action"):
        act_obj = manifest.get(act_key)
        if isinstance(act_obj, dict):
            def_ic = act_obj.get("default_icon")
            if isinstance(def_ic, str):
                icon_candidates.append(def_ic)
            elif isinstance(def_ic, dict):
                for sz in ("128", "64", "48", "38", "32", "24", "19", "16"):
                    if sz in def_ic:
                        icon_candidates.append(str(def_ic[sz]))
                icon_candidates.extend(str(v) for v in def_ic.values())

    mf_icons = manifest.get("icons")
    if isinstance(mf_icons, dict):
        for sz in ("128", "64", "48", "32", "24", "16"):
            if sz in mf_icons:
                icon_candidates.append(str(mf_icons[sz]))
        icon_candidates.extend(str(v) for v in mf_icons.values())

    loaded_pix: Optional[QPixmap] = None
    for rel_path in icon_candidates:
        if not rel_path:
            continue
        clean_rel = rel_path.lstrip("/\\")
        full_ic = os.path.join(ext_dir, clean_rel)
        if os.path.isfile(full_ic):
            p = QPixmap(full_ic)
            if not p.isNull():
                loaded_pix = p.scaled(
                    icon_size,
                    icon_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                break

    # Also search common icon filenames inside ext_dir if manifest lookup didn't find one
    if loaded_pix is None and ext_dir and os.path.isdir(ext_dir):
        for fname in ("icon128.png", "icon48.png", "icon32.png", "icon16.png", "icon.png", "logo.png"):
            cand = os.path.join(ext_dir, fname)
            if os.path.isfile(cand):
                p = QPixmap(cand)
                if not p.isNull():
                    loaded_pix = p.scaled(
                        icon_size,
                        icon_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    break

    if loaded_pix is None:
        glyph = (display_name or "E")[0].upper()
        loaded_pix = make_3d_badge_pixmap(
            glyph,
            "#6366F1" if ext.isEnabled() else "#94A3B8",
            "#4338CA" if ext.isEnabled() else "#64748B",
            size=icon_size,
            radius=max(5, int(icon_size * 0.28)),
        )

    # 2. Determine Access Category matching Image 1:
    # - "full": 전체 액세스 (이 사이트의 정보를 확인하고 변경할 수 있는 확장 프로그램입니다)
    # - "requested": 액세스가 요청됨 (사이트 액세스를 허용하려면 확장 프로그램을 클릭하세요.)
    # - "none": 필요한 액세스 권한 없음 (이 사이트의 정보를 확인하고 변경할 필요가 없는 확장 프로그램입니다.)
    perms = [str(x) for x in manifest.get("permissions", []) if x]
    host_perms = [str(x) for x in manifest.get("host_permissions", []) if x]
    content_scripts = manifest.get("content_scripts", [])
    all_perms_str = " ".join(perms + host_perms).lower()

    if (
        "<all_urls>" in all_perms_str
        or "*://*/*" in all_perms_str
        or "http://*/*" in all_perms_str
        or "https://*/*" in all_perms_str
        or "scripting" in perms
        or "declarativeNetRequest" in perms
        or "webRequest" in perms
        or bool(content_scripts)
    ):
        access_cat = "full"
    elif "activeTab" in perms or "tabs" in perms or bool(host_perms):
        access_cat = "requested"
    else:
        access_cat = "none"

    # 3. Resolve Fallback Popup / Options HTML URL
    fallback_popup_url: Optional[QUrl] = None
    popup_rel = None
    for act_key in ("action", "browser_action", "page_action"):
        act_obj = manifest.get(act_key)
        if isinstance(act_obj, dict) and act_obj.get("default_popup"):
            popup_rel = str(act_obj["default_popup"]).lstrip("/\\")
            break
    if not popup_rel:
        if isinstance(manifest.get("options_ui"), dict) and manifest["options_ui"].get("page"):
            popup_rel = str(manifest["options_ui"]["page"]).lstrip("/\\")
        elif manifest.get("options_page"):
            popup_rel = str(manifest["options_page"]).lstrip("/\\")
        elif isinstance(manifest.get("side_panel"), dict) and manifest["side_panel"].get("default_path"):
            popup_rel = str(manifest["side_panel"]["default_path"]).lstrip("/\\")

    if popup_rel and ext_dir:
        full_pop = os.path.join(ext_dir, popup_rel)
        if os.path.isfile(full_pop):
            fallback_popup_url = QUrl.fromLocalFile(full_pop)

    return {
        "display_name": display_name,
        "pixmap": loaded_pix,
        "icon": QIcon(loaded_pix),
        "access_category": access_cat,
        "fallback_popup_url": fallback_popup_url,
        "content_scripts": content_scripts if isinstance(content_scripts, list) else [],
        "manifest": manifest,
        "path": os.path.normpath(ext_dir) if ext_dir else "",
    }


def extract_crx_or_zip_to_dir(archive_path: str, dest_dir: str) -> Tuple[bool, str]:
    """
    Extracts a `.crx` (CRX2 or CRX3) or `.zip` Chrome extension package into `dest_dir`.
    CRX files contain a binary header followed by a standard ZIP archive starting at `PK\\x03\\x04`.
    """
    try:
        with open(archive_path, "rb") as f:
            raw = f.read()

        pk_idx = raw.find(b"PK\x03\x04")
        if pk_idx == -1:
            return False, "유효한 크롬 확장 프로그램(.crx / .zip) 포맷이 아닙니다."

        zip_bytes = raw[pk_idx:]
        tmp_zip = os.path.join(tempfile.gettempdir(), "bside_ext_temp.zip")
        with open(tmp_zip, "wb") as zf:
            zf.write(zip_bytes)

        os.makedirs(dest_dir, exist_ok=True)
        with zipfile.ZipFile(tmp_zip, "r") as z:
            z.extractall(dest_dir)

        manifest_path = os.path.join(dest_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            subs = [
                os.path.join(dest_dir, d)
                for d in os.listdir(dest_dir)
                if os.path.isdir(os.path.join(dest_dir, d))
            ]
            if len(subs) == 1 and os.path.exists(os.path.join(subs[0], "manifest.json")):
                return True, subs[0]
            return False, "압축 파일 내에 manifest.json이 없습니다."
        return True, dest_dir
    except Exception as e:
        return False, f"확장 프로그램 압축 해제 오류: {e}"


def download_crx_from_webstore_id(ext_id_or_url: str, save_root_dir: str) -> Tuple[bool, str]:
    """
    Downloads a Chrome extension `.crx` directly from Google's CRX update endpoint
    given a Chrome Web Store URL or 32-char extension ID, and extracts it.
    """
    import re
    m = re.search(r"([a-p]{32})", ext_id_or_url.lower())
    if not m:
        return False, "유효한 크롬 웹 스토어 URL 또는 32자리 확장 프로그램 ID를 입력해 주세요."
    ext_id = m.group(1)

    crx_url = (
        f"https://clients2.google.com/service/update2/crx?"
        f"response=redirect&prodversion=130.0.0.0&acceptformat=crx2,crx3&x=id%3D{ext_id}%26uc"
    )
    try:
        req = urllib.request.Request(
            crx_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            },
        )
        tmp_crx = os.path.join(tempfile.gettempdir(), f"{ext_id}.crx")
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = resp.read()
            if not data or len(data) < 100:
                return False, "크롬 웹 스토어에서 CRX 패키지를 내려받지 못했습니다."
            with open(tmp_crx, "wb") as f:
                f.write(data)

        dest_dir = os.path.join(save_root_dir, ext_id)
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)
        return extract_crx_or_zip_to_dir(tmp_crx, dest_dir)
    except Exception as e:
        return False, f"웹 스토어 다운로드 실패: {e}"


def scan_local_chrome_extensions() -> List[Dict[str, str]]:
    """
    Scans the user's installed Google Chrome / Edge extensions on Windows so they can be
    imported into Bside with 1 click!
    """
    results: List[Dict[str, str]] = []
    local_app = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local_app, "Google", "Chrome", "User Data", "Default", "Extensions"),
        os.path.join(local_app, "Microsoft", "Edge", "User Data", "Default", "Extensions"),
    ]
    seen_ids = set()
    for base in candidates:
        if not os.path.isdir(base):
            continue
        for ext_id in os.listdir(base):
            if ext_id in seen_ids:
                continue
            ext_dir = os.path.join(base, ext_id)
            if not os.path.isdir(ext_dir):
                continue
            versions = sorted(os.listdir(ext_dir), reverse=True)
            for ver in versions:
                ver_dir = os.path.join(ext_dir, ver)
                manifest_file = os.path.join(ver_dir, "manifest.json")
                if os.path.isfile(manifest_file):
                    try:
                        with open(manifest_file, "r", encoding="utf-8", errors="ignore") as f:
                            mf = json.load(f)
                        raw_name = str(mf.get("name", ext_id))
                        name = _resolve_manifest_message(ver_dir, raw_name)
                        if name.startswith("__MSG_"):
                            name = mf.get("short_name") or f"Chrome 확장앱 ({ext_id[:8]})"
                        results.append(
                            {
                                "id": ext_id,
                                "name": str(name),
                                "version": str(mf.get("version", ver)),
                                "path": ver_dir,
                            }
                        )
                        seen_ids.add(ext_id)
                        break
                    except Exception:
                        pass
    return results


class ExtensionActionPopup(QDialog):
    """Floating popup window that renders an extension's `actionPopupUrl()` HTML page when clicked."""

    def __init__(self, ext_title: str, popup_url: QUrl, profile: QWebEngineProfile, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle(ext_title)
        self.resize(390, 500)
        self.setStyleSheet(
            "QDialog { background-color: #FFFFFF; border: 1px solid #D4D4D8; border-radius: 12px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        # Compact header bar with extension title and close button
        hdr = QFrame()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet("background-color: #F4F4F5; border-bottom: 1px solid #E4E4E7;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 2, 6, 2)
        t_lbl = QLabel(f"🧩 {ext_title}")
        t_lbl.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #18181B;")
        hl.addWidget(t_lbl, 1)
        c_btn = QPushButton("×")
        c_btn.setFixedSize(22, 22)
        c_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        c_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #52525B; font-size: 15px; font-weight: 700; }"
            "QPushButton:hover { background-color: #E4E4E7; border-radius: 5px; }"
        )
        c_btn.clicked.connect(self.close)
        hl.addWidget(c_btn)
        layout.addWidget(hdr)

        self.webview = QWebEngineView(self)
        self.page_obj = QWebEnginePage(profile, self.webview)
        self.webview.setPage(self.page_obj)
        self.webview.setUrl(popup_url)
        layout.addWidget(self.webview, 1)


class ExtensionToolbarPopover(QDialog):
    """
    Chrome-style Extensions Dropdown Popover (Image 1) that opens when clicking the Puzzle Icon (`🧩` Image 2):
    - Top header: `확장 프로그램` + `×` close button
    - Categorized sections matching Image 1:
      1. `전체 액세스` ("이 사이트의 정보를 확인하고 변경할 수 있는 확장 프로그램입니다")
      2. `액세스가 요청됨` ("사이트 액세스를 허용하려면 확장 프로그램을 클릭하세요.")
      3. `필요한 액세스 권한 없음` ("이 사이트의 정보를 확인하고 변경할 필요가 없는 확장 프로그램입니다.")
    - Each row: `[Real Extension Icon]` + `[Extension Name]` + `[📌 압핀 Pin/Unpin Toggle]` + `[⋮ More Menu]`
    - Clicking the Pushpin (`📌`) immediately shows/hides that extension's real icon on the browser toolbar (Image 3)!
    - Bottom footer: `⚙️ 확장 프로그램 관리` -> opens the full `ChromeExtensionManagerDialog`.
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.main_window = main_window
        self.storage = main_window.storage
        self.ext_mgr = main_window.ext_mgr
        self.setFixedWidth(340)

        self._build_ui()
        self._populate_extensions()

    def _build_ui(self):
        theme_mode = self.storage.get_setting("theme", "light")
        p = get_palette(theme_mode)

        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {p['popover']};
                color: {p['fg']};
                border: 1px solid {p['border_strong']};
                border-radius: 12px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 10, 0, 8)
        self.root_layout.setSpacing(4)

        # Header: "확장 프로그램" + Close '×'
        hdr = QHBoxLayout()
        hdr.setContentsMargins(18, 4, 14, 6)
        title_lbl = QLabel("확장 프로그램")
        title_lbl.setStyleSheet(f"color: {p['fg']}; font-size: 15px; font-weight: 700;")
        hdr.addWidget(title_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("닫기")
        close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {p['fg_muted']};
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {p['card_hover']};
                color: {p['fg']};
            }}
            """
        )
        close_btn.clicked.connect(self.close)
        hdr.addWidget(close_btn)
        self.root_layout.addLayout(hdr)

        # Scrollable list area for extension categories
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.body_widget = QWidget()
        self.body_widget.setStyleSheet("background: transparent;")
        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(18, 4, 14, 8)
        self.body_layout.setSpacing(10)
        self.scroll.setWidget(self.body_widget)
        self.root_layout.addWidget(self.scroll, 1)

        # Bottom Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background-color: {p['border']}; border: none;")
        self.root_layout.addWidget(div)

        # Footer: "⚙️ 확장 프로그램 관리" button matching Image 1
        footer_wrap = QHBoxLayout()
        footer_wrap.setContentsMargins(8, 4, 8, 2)
        manage_btn = QPushButton("  확장 프로그램 관리")
        manage_btn.setIcon(make_nav_icon("settings", p["fg_muted"], p["accent"], 18))
        manage_btn.setIconSize(QSize(18, 18))
        manage_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        manage_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {p['fg']};
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 500;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {p['card_hover']};
            }}
            """
        )
        manage_btn.clicked.connect(self._open_full_manager)
        footer_wrap.addWidget(manage_btn)
        self.root_layout.addLayout(footer_wrap)

    def _populate_extensions(self):
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        p = get_palette(self.storage.get_setting("theme", "light"))
        all_exts = [
            e for e in self.ext_mgr.extensions() if not is_internal_builtin_extension(e)
        ]

        if not all_exts:
            empty_lbl = QLabel(
                "설치된 크롬 확장 프로그램이 없습니다.\n\n"
                "아래 [⚙ 확장 프로그램 관리]를 눌러 크롬 웹 스토어나 폴더에서 확장앱을 추가해 보세요."
            )
            empty_lbl.setWordWrap(True)
            empty_lbl.setStyleSheet(f"color: {p['fg_muted']}; font-size: 12.5px; padding: 12px 0px;")
            self.body_layout.addWidget(empty_lbl)
            self.setFixedHeight(220)
            return

        pinned_paths = [
            os.path.normpath(x) for x in self.storage.get_setting("pinned_extension_paths", []) if x
        ]

        groups: Dict[str, List[Tuple[QWebEngineExtensionInfo, Dict[str, Any]]]] = {
            "full": [],
            "requested": [],
            "none": [],
        }

        for ext in all_exts:
            meta = get_extension_meta_and_icon(ext, icon_size=22)
            cat = meta["access_category"]
            groups.get(cat, groups["full"]).append((ext, meta))

        section_defs = [
            (
                "full",
                "전체 액세스",
                "이 사이트의 정보를 확인하고 변경할 수 있는 확장 프로그램입니다",
            ),
            (
                "requested",
                "액세스가 요청됨",
                "사이트 액세스를 허용하려면 확장 프로그램을 클릭하세요.",
            ),
            (
                "none",
                "필요한 액세스 권한 없음",
                "이 사이트의 정보를 확인하고 변경할 필요가 없는 확장 프로그램입니다.",
            ),
        ]

        total_rows = 0
        for cat_key, sec_title, sec_desc in section_defs:
            items = groups[cat_key]
            if not items:
                continue

            sec_box = QVBoxLayout()
            sec_box.setContentsMargins(0, 2, 0, 4)
            sec_box.setSpacing(4)

            h_lbl = QLabel(sec_title)
            h_lbl.setStyleSheet(f"color: {p['fg']}; font-size: 12.5px; font-weight: 700;")
            sec_box.addWidget(h_lbl)

            d_lbl = QLabel(sec_desc)
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet(f"color: {p['fg_muted']}; font-size: 11.5px; margin-bottom: 4px;")
            sec_box.addWidget(d_lbl)

            for ext, meta in items:
                total_rows += 1
                row_widget = QFrame()
                row_widget.setStyleSheet(
                    f"""
                    QFrame {{
                        background: transparent;
                        border-radius: 8px;
                    }}
                    QFrame:hover {{
                        background-color: {p['card_hover']};
                    }}
                    """
                )
                rl = QHBoxLayout(row_widget)
                rl.setContentsMargins(6, 5, 4, 5)
                rl.setSpacing(8)

                # Extension Icon + Name Button (clicking runs/opens the extension!)
                run_btn = QPushButton()
                run_btn.setIcon(meta["icon"])
                run_btn.setIconSize(QSize(20, 20))
                disp_name = meta["display_name"]
                short_name = disp_name[:22] + ("..." if len(disp_name) > 22 else "")
                if not ext.isEnabled():
                    short_name += " (꺼짐)"
                run_btn.setText(f"  {short_name}")
                run_btn.setToolTip(f"{disp_name} — 클릭하여 실행")
                run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                run_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: transparent;
                        color: {p['fg'] if ext.isEnabled() else p['fg_muted']};
                        border: none;
                        font-size: 13px;
                        font-weight: 500;
                        text-align: left;
                        padding: 2px 4px;
                    }}
                    """
                )
                run_btn.clicked.connect(
                    lambda checked=False, e=ext: self._on_click_extension(e)
                )
                rl.addWidget(run_btn, 1)

                # Pushpin (압핀) Button matching Image 1 -> pins/unpins icon on Image 3 toolbar!
                norm_path = meta["path"]
                is_pinned = norm_path in pinned_paths
                pin_btn = QPushButton()
                pin_btn.setFixedSize(28, 28)
                pin_btn.setIconSize(QSize(18, 18))
                pin_btn.setIcon(make_pushpin_icon(pinned=is_pinned, size=18))
                pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                pin_btn.setToolTip(
                    "툴바에서 고정 해제 (아이콘 숨기기)"
                    if is_pinned
                    else "툴바에 고정 (상단 바에 확장앱 아이콘 표시)"
                )
                pin_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: {'rgba(37, 99, 235, 0.10)' if is_pinned else 'transparent'};
                        border: none;
                        border-radius: 14px;
                    }}
                    QPushButton:hover {{
                        background-color: {p['border']};
                    }}
                    """
                )
                pin_btn.clicked.connect(
                    lambda checked=False, pt=norm_path: self._toggle_pin(pt)
                )
                rl.addWidget(pin_btn)

                # 3-dots (`⋮`) More Options Button matching Image 1
                more_btn = QPushButton()
                more_btn.setFixedSize(28, 28)
                more_btn.setIconSize(QSize(18, 18))
                more_btn.setIcon(make_more_dots_icon(p["fg_muted"], size=18))
                more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                more_btn.setToolTip("옵션 더보기")
                more_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        border-radius: 14px;
                    }}
                    QPushButton:hover {{
                        background-color: {p['border']};
                    }}
                    """
                )
                more_btn.clicked.connect(
                    lambda checked=False, e=ext, m=meta, b=more_btn: self._show_more_menu(e, m, b)
                )
                rl.addWidget(more_btn)

                sec_box.addWidget(row_widget)

            self.body_layout.addLayout(sec_box)

        self.body_layout.addStretch(1)
        target_h = min(520, max(240, 150 + total_rows * 52 + len([g for g in groups.values() if g]) * 54))
        self.setFixedHeight(target_h)

    def _toggle_pin(self, norm_path: str):
        if not norm_path:
            return
        pinned = [
            os.path.normpath(x) for x in self.storage.get_setting("pinned_extension_paths", []) if x
        ]
        if norm_path in pinned:
            pinned.remove(norm_path)
        else:
            pinned.append(norm_path)
        self.storage.set_setting("pinned_extension_paths", pinned)
        self.main_window.refresh_extension_pins()
        self._populate_extensions()

    def _on_click_extension(self, ext: QWebEngineExtensionInfo):
        self.close()
        self.main_window.trigger_extension_from_toolbar(ext, self.main_window.extensions_btn)

    def _show_more_menu(self, ext: QWebEngineExtensionInfo, meta: Dict[str, Any], btn: QPushButton):
        menu = QMenu(self)
        p = get_palette(self.storage.get_setting("theme", "light"))
        menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: {p['popover']};
                color: {p['fg']};
                border: 1px solid {p['border_strong']};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 14px;
                border-radius: 5px;
                font-size: 12.5px;
            }}
            QMenu::item:selected {{
                background-color: {p['card_hover']};
            }}
            """
        )

        act_run = QAction(f"▶ {meta['display_name']} 실행 / 열기", self)
        act_run.triggered.connect(lambda: self._on_click_extension(ext))
        menu.addAction(act_run)

        norm_path = meta["path"]
        pinned = [
            os.path.normpath(x) for x in self.storage.get_setting("pinned_extension_paths", []) if x
        ]
        is_pinned = norm_path in pinned
        act_pin = QAction("📌 툴바에서 고정 해제" if is_pinned else "📌 툴바에 고정", self)
        act_pin.triggered.connect(lambda: self._toggle_pin(norm_path))
        menu.addAction(act_pin)

        act_toggle = QAction(
            "⏸ 확장 프로그램 비활성화 (끄기)" if ext.isEnabled() else "✓ 확장 프로그램 활성화 (켜기)",
            self,
        )
        def _do_toggle():
            self.ext_mgr.setExtensionEnabled(ext, not ext.isEnabled())
            self.main_window.refresh_extension_pins()
            self._populate_extensions()
        act_toggle.triggered.connect(_do_toggle)
        menu.addAction(act_toggle)

        menu.addSeparator()

        act_remove = QAction("🗑 브라우저에서 제거", self)
        def _do_remove():
            path = os.path.normpath(ext.path()) if ext.path() else ""
            saved = [os.path.normpath(x) for x in self.storage.get_setting("installed_extension_paths", []) if x]
            if path in saved:
                saved.remove(path)
                self.storage.set_setting("installed_extension_paths", saved)
            if path in pinned:
                pinned.remove(path)
                self.storage.set_setting("pinned_extension_paths", pinned)
            if ext.isInstalled():
                self.ext_mgr.uninstallExtension(ext)
            else:
                self.ext_mgr.unloadExtension(ext)
            self.main_window.refresh_extension_pins()
            self._populate_extensions()
        act_remove.triggered.connect(_do_remove)
        menu.addAction(act_remove)

        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _open_full_manager(self):
        self.close()
        self.main_window.open_extensions_manager_dialog()


class ChromeExtensionManagerDialog(QDialog):
    """
    Full Chrome Extension Manager & Installer Hub (`⚙️ 확장 프로그램 관리`):
    - Lists all loaded/installed user Chrome Extensions with their real icons and Pin toggles
    - Allows 1-click install from:
      1. Chrome Web Store URL / ID (auto-downloads & loads CRX!)
      2. `.crx` or `.zip` file (`installExtension`)
      3. Unpacked Extension Folder (`loadExtension`)
      4. Importing already-installed extensions from PC's Chrome / Edge
      5. Opening Chrome Web Store directly in a browser tab
    """
    open_url_requested = Signal(str)
    extensions_changed = Signal()

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.storage = main_window.storage
        self.profile = main_window.web_profile
        self.ext_mgr = main_window.ext_mgr

        local_appdata = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        self.ext_storage_dir = os.path.join(local_appdata, "BsideBrowser", "extensions")
        os.makedirs(self.ext_storage_dir, exist_ok=True)

        self.setWindowTitle("🧩 크롬 확장 프로그램 관리 (Chrome Extensions)")
        self.resize(650, 560)

        self.ext_mgr.loadFinished.connect(self._on_ext_event)
        self.ext_mgr.installFinished.connect(self._on_ext_event)
        self.ext_mgr.uninstallFinished.connect(self._on_ext_event)

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        theme_mode = self.storage.get_setting("theme", "light")
        p = get_palette(theme_mode)
        self.setStyleSheet(f"background-color: {p['bg']}; color: {p['fg']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        badge = QLabel()
        badge.setFixedSize(36, 36)
        badge.setPixmap(make_3d_badge_pixmap("🧩", "#6366F1", "#4338CA", size=36, radius=10))
        hdr.addWidget(badge)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t_lbl = QLabel("크롬 확장 프로그램 관리 & 설치")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: 800;")
        s_lbl = QLabel("확장앱을 설치하고 압핀(📌)을 누르면 브라우저 상단 바에 확장앱 아이콘이 고정됩니다.")
        s_lbl.setStyleSheet(f"color: {p['fg_muted']}; font-size: 11.5px;")
        title_col.addWidget(t_lbl)
        title_col.addWidget(s_lbl)
        hdr.addLayout(title_col, 1)

        store_btn = QPushButton("🌐 크롬 웹 스토어 열기")
        store_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        store_btn.setStyleSheet(
            f"background-color: {p['accent']}; color: #fff; border: none; border-radius: 10px; padding: 7px 14px; font-weight: 700; font-size: 12px;"
        )
        store_btn.clicked.connect(self._open_webstore)
        hdr.addWidget(store_btn)
        root.addLayout(hdr)

        # Direct Web Store URL / ID Instant Installer Bar
        url_card = QFrame()
        url_card.setObjectName("WebStoreUrlBar")
        url_card.setStyleSheet(
            f"QFrame#WebStoreUrlBar {{ background-color: {p['card']}; border: 1px solid {p['border']}; border-radius: 12px; }}"
        )
        url_row = QHBoxLayout(url_card)
        url_row.setContentsMargins(10, 8, 10, 8)
        url_row.setSpacing(8)

        self.webstore_input = QLineEdit()
        self.webstore_input.setPlaceholderText(
            "크롬 웹 스토어 확장앱 주소(URL) 또는 32자리 ID 붙여넣기 후 [바로 설치] 클릭..."
        )
        self.webstore_input.setStyleSheet("border: none; background: transparent;")
        url_row.addWidget(self.webstore_input, 1)

        dl_btn = QPushButton("⬇ 스토어에서 바로 설치")
        dl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dl_btn.setStyleSheet(
            f"background-color: {p['primary']}; color: {p['primary_fg']}; border: none; border-radius: 8px; padding: 6px 12px; font-weight: 700; font-size: 12px;"
        )
        dl_btn.clicked.connect(self._install_from_webstore_url)
        url_row.addWidget(dl_btn)
        root.addWidget(url_card)

        # Local Install Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_style = (
            f"QPushButton {{ background-color: {p['card']}; color: {p['fg']}; border: 1px solid {p['border']}; "
            f"border-radius: 10px; padding: 7px 12px; font-weight: 600; font-size: 12px; }}"
            f"QPushButton:hover {{ background-color: {p['card_hover']}; }}"
        )

        crx_btn = QPushButton("📦 .CRX / .ZIP 파일 설치")
        crx_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        crx_btn.setStyleSheet(btn_style)
        crx_btn.clicked.connect(self._install_from_file)
        btn_row.addWidget(crx_btn)

        folder_btn = QPushButton("📂 압축 해제된 확장앱 폴더 로드")
        folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        folder_btn.setStyleSheet(btn_style)
        folder_btn.clicked.connect(self._load_from_folder)
        btn_row.addWidget(folder_btn)

        import_btn = QPushButton("🔄 내 PC 크롬/엣지 확장앱 가져오기")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.setStyleSheet(btn_style)
        import_btn.clicked.connect(self._import_from_pc_chrome)
        btn_row.addWidget(import_btn)

        root.addLayout(btn_row)

        # Installed Extensions List
        list_hdr = QLabel("설치된 확장 프로그램")
        list_hdr.setStyleSheet("font-size: 13px; font-weight: 700; margin-top: 4px;")
        root.addWidget(list_hdr)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)

        self.scroll.setWidget(self.list_container)
        root.addWidget(self.scroll, 1)

        # Footer
        footer = QHBoxLayout()
        self.status_lbl = QLabel("● Chromium Native Extension Engine 활성")
        self.status_lbl.setStyleSheet("color: #10B981; font-size: 11.5px; font-weight: 600;")
        footer.addWidget(self.status_lbl)
        footer.addStretch()

        close_btn = QPushButton("닫기")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(btn_style)
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        root.addLayout(footer)

    def _stage_to_local_disk(self, src_dir: str) -> str:
        norm_src = os.path.abspath(src_dir)
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in os.path.basename(norm_src))
        if not safe_name or safe_name.strip("_") == "":
            safe_name = "unpacked_ext"
        local_dest = os.path.join(self.ext_storage_dir, safe_name)
        try:
            if os.path.abspath(local_dest).lower() != norm_src.lower():
                if os.path.exists(local_dest):
                    shutil.rmtree(local_dest, ignore_errors=True)
                shutil.copytree(norm_src, local_dest)
            return local_dest
        except Exception:
            return norm_src

    def _on_ext_event(self, ext_info: QWebEngineExtensionInfo):
        err = (ext_info.error() or "").strip()
        ext_name = ext_info.name() or "확장 프로그램"
        ext_path = os.path.normpath(ext_info.path()) if ext_info.path() else ""

        if err:
            self.status_lbl.setStyleSheet("color: #EF4444; font-size: 11.5px; font-weight: 700;")
            self.status_lbl.setText(f"⚠️ 확장앱 알림: {err[:80]}")
        else:
            if ext_path and not is_internal_builtin_extension(ext_info):
                saved = [os.path.normpath(p) for p in self.storage.get_setting("installed_extension_paths", []) if p]
                if ext_path not in saved:
                    saved.append(ext_path)
                    self.storage.set_setting("installed_extension_paths", saved)
                # Auto-pin newly installed user extensions so their icon immediately shows on the toolbar!
                pinned = [os.path.normpath(p) for p in self.storage.get_setting("pinned_extension_paths", []) if p]
                if ext_path not in pinned:
                    pinned.append(ext_path)
                    self.storage.set_setting("pinned_extension_paths", pinned)

            self.status_lbl.setStyleSheet("color: #10B981; font-size: 11.5px; font-weight: 700;")
            self.status_lbl.setText(f"✓ '{ext_name}' 확장 프로그램 로드 및 상단 툴바 고정 완료!")

        def _deferred_enable_and_refresh():
            try:
                for e in self.ext_mgr.extensions():
                    if os.path.normpath(e.path()) == ext_path and not e.isEnabled():
                        self.ext_mgr.setExtensionEnabled(e, True)
            except Exception:
                pass
            self._refresh_list()
            self.extensions_changed.emit()

        QTimer.singleShot(50, _deferred_enable_and_refresh)

    def _refresh_list(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        p = get_palette(self.storage.get_setting("theme", "light"))
        exts = [e for e in self.ext_mgr.extensions() if not is_internal_builtin_extension(e)]
        pinned_paths = [
            os.path.normpath(x) for x in self.storage.get_setting("pinned_extension_paths", []) if x
        ]

        if not exts:
            empty_card = QFrame()
            empty_card.setObjectName("EmptyExtCard")
            empty_card.setStyleSheet(
                f"QFrame#EmptyExtCard {{ background-color: {p['card']}; border: 1px solid {p['border']}; border-radius: 12px; }}"
            )
            el = QVBoxLayout(empty_card)
            el.setContentsMargins(16, 18, 16, 18)
            lbl = QLabel(
                "아직 로드된 확장 프로그램이 없습니다.\n"
                "위에서 [크롬 웹 스토어 열기], [스토어에서 바로 설치], [압축 해제된 확장앱 폴더 로드], 또는 [내 PC 크롬/엣지 확장앱 가져오기]를 눌러 추가해 보세요!"
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {p['fg_muted']}; font-size: 12.5px;")
            el.addWidget(lbl)
            self.list_layout.insertWidget(0, empty_card)
            return

        for idx, ext in enumerate(exts):
            meta = get_extension_meta_and_icon(ext, icon_size=32)
            norm_path = meta["path"]
            is_pinned = norm_path in pinned_paths

            card = QFrame()
            card_id = f"ExtCard_{idx}"
            card.setObjectName(card_id)
            card.setStyleSheet(
                f"QFrame#{card_id} {{ background-color: {p['card']}; border: 1px solid {p['border']}; border-radius: 12px; }}"
            )
            row = QHBoxLayout(card)
            row.setContentsMargins(12, 10, 12, 10)
            row.setSpacing(10)

            icon_lbl = QLabel()
            icon_lbl.setFixedSize(34, 34)
            icon_lbl.setPixmap(meta["pixmap"])
            row.addWidget(icon_lbl)

            info_col = QVBoxLayout()
            info_col.setSpacing(2)
            name_lbl = QLabel(
                f"{meta['display_name']}  ({'활성' if ext.isEnabled() else '비활성'})"
            )
            name_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
            desc_lbl = QLabel(ext.description() or ext.path())
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(f"color: {p['fg_muted']}; font-size: 11px;")
            info_col.addWidget(name_lbl)
            info_col.addWidget(desc_lbl)
            row.addLayout(info_col, 1)

            # Pin/Unpin button
            pin_btn = QPushButton("📌 고정됨" if is_pinned else "📌 툴바 고정")
            pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            pin_btn.setToolTip("브라우저 상단 바에 확장 프로그램 아이콘 표시/숨기기")
            pin_btn.setStyleSheet(
                f"background-color: {p['accent_soft'] if is_pinned else p['bg_elevated']}; "
                f"color: {p['accent_fg'] if is_pinned else p['fg']}; "
                f"border: 1px solid {p['border']}; border-radius: 8px; padding: 5px 10px; font-weight: 700; font-size: 11.5px;"
            )
            pin_btn.clicked.connect(lambda checked=False, pt=norm_path: self._toggle_pin(pt))
            row.addWidget(pin_btn)

            open_pop_btn = QPushButton("▶ 실행")
            open_pop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_pop_btn.setStyleSheet(
                f"background-color: {p['bg_elevated']}; color: {p['fg']}; border: 1px solid {p['border']}; border-radius: 8px; padding: 5px 10px; font-weight: 700; font-size: 11.5px;"
            )
            open_pop_btn.clicked.connect(
                lambda checked=False, e=ext: self.main_window.trigger_extension_from_toolbar(e, open_pop_btn)
            )
            row.addWidget(open_pop_btn)

            toggle_btn = QPushButton("끄기" if ext.isEnabled() else "켜기")
            toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            toggle_btn.setStyleSheet(
                f"background-color: {p['bg_elevated']}; color: {p['fg']}; border: 1px solid {p['border']}; border-radius: 8px; padding: 5px 10px; font-weight: 600; font-size: 11.5px;"
            )
            toggle_btn.clicked.connect(lambda checked=False, e=ext: self._toggle_ext(e))
            row.addWidget(toggle_btn)

            del_btn = QPushButton("제거")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet(
                "background-color: transparent; color: #EF4444; border: 1px solid #FCA5A5; border-radius: 8px; padding: 5px 10px; font-weight: 600; font-size: 11.5px;"
            )
            del_btn.clicked.connect(lambda checked=False, e=ext: self._remove_ext(e))
            row.addWidget(del_btn)

            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

    def _toggle_pin(self, norm_path: str):
        if not norm_path:
            return
        pinned = [
            os.path.normpath(x) for x in self.storage.get_setting("pinned_extension_paths", []) if x
        ]
        if norm_path in pinned:
            pinned.remove(norm_path)
        else:
            pinned.append(norm_path)
        self.storage.set_setting("pinned_extension_paths", pinned)
        self._refresh_list()
        self.extensions_changed.emit()

    def _toggle_ext(self, ext: QWebEngineExtensionInfo):
        self.ext_mgr.setExtensionEnabled(ext, not ext.isEnabled())
        self._refresh_list()
        self.extensions_changed.emit()

    def _remove_ext(self, ext: QWebEngineExtensionInfo):
        path = os.path.normpath(ext.path()) if ext.path() else ""
        saved = [os.path.normpath(x) for x in self.storage.get_setting("installed_extension_paths", []) if x]
        if path in saved:
            saved.remove(path)
            self.storage.set_setting("installed_extension_paths", saved)
        pinned = [os.path.normpath(x) for x in self.storage.get_setting("pinned_extension_paths", []) if x]
        if path in pinned:
            pinned.remove(path)
            self.storage.set_setting("pinned_extension_paths", pinned)
        if ext.isInstalled():
            self.ext_mgr.uninstallExtension(ext)
        else:
            self.ext_mgr.unloadExtension(ext)
        self._refresh_list()
        self.extensions_changed.emit()

    def _open_webstore(self):
        self.open_url_requested.emit("https://chromewebstore.google.com")
        self.accept()

    def _install_from_webstore_url(self):
        val = self.webstore_input.text().strip()
        if not val:
            cur = self.main_window.current_tab()
            if cur and "chromewebstore.google.com/detail/" in cur.logical_url:
                val = cur.logical_url
        if not val:
            QMessageBox.information(
                self,
                "크롬 웹 스토어 URL 안내",
                "크롬 웹 스토어의 확장 프로그램 주소(URL)나 32자리 ID를 입력란에 붙여넣어 주세요.",
            )
            return

        self.status_lbl.setText("⏳ 크롬 웹 스토어에서 확장 프로그램을 다운로드 및 압축 해제 중...")
        ok, res = download_crx_from_webstore_id(val, self.ext_storage_dir)
        if ok:
            self.webstore_input.clear()
            self.ext_mgr.loadExtension(res)
        else:
            self.status_lbl.setText(f"⚠️ {res}")
            QMessageBox.warning(self, "설치 실패", res)

    def _install_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "크롬 확장 프로그램 패키지 선택 (.crx / .zip)",
            "",
            "Chrome Extensions (*.crx *.zip);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not path:
            return
        base_name = os.path.splitext(os.path.basename(path))[0]
        dest_dir = os.path.join(self.ext_storage_dir, base_name)
        ok, res = extract_crx_or_zip_to_dir(path, dest_dir)
        if ok:
            self.ext_mgr.loadExtension(res)
        else:
            self.ext_mgr.installExtension(path)

    @staticmethod
    def _find_manifest_dir(folder: str) -> Optional[str]:
        if not folder or not os.path.isdir(folder):
            return None
        if os.path.isfile(os.path.join(folder, "manifest.json")):
            return folder
        for entry in sorted(os.listdir(folder), reverse=True):
            sub = os.path.join(folder, entry)
            if os.path.isdir(sub):
                if os.path.isfile(os.path.join(sub, "manifest.json")):
                    return sub
                for sub2_name in sorted(os.listdir(sub), reverse=True):
                    sub2 = os.path.join(sub, sub2_name)
                    if os.path.isdir(sub2) and os.path.isfile(os.path.join(sub2, "manifest.json")):
                        return sub2
        return None

    def _load_from_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "압축 해제된 크롬 확장 프로그램 폴더 선택 (manifest.json 포함)",
            "",
            QFileDialog.Option.DontUseNativeDialog,
        )
        if not folder:
            return
        target_dir = self._find_manifest_dir(folder)
        if not target_dir:
            QMessageBox.warning(
                self,
                "폴더 확인",
                "선택한 폴더(또는 하위 폴더)에서 manifest.json 파일을 찾지 못했습니다.\n확장 프로그램 압축이 풀린 폴더가 맞는지 확인해 주세요.",
            )
            return
        self.status_lbl.setStyleSheet("color: #4F46E5; font-size: 11.5px; font-weight: 700;")
        self.status_lbl.setText(f"⏳ 확장 프로그램 로컬 스테이징 및 로드 중: {os.path.basename(target_dir)}...")
        QApplication.processEvents()
        staged_dir = self._stage_to_local_disk(target_dir)
        QTimer.singleShot(20, lambda: self.ext_mgr.loadExtension(staged_dir))

    def _import_from_pc_chrome(self):
        found = scan_local_chrome_extensions()
        if not found:
            QMessageBox.information(self, "확장 프로그램 검색", "PC의 기본 Chrome / Edge 프로필에서 설치된 확장 프로그램을 찾지 못했습니다.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("내 PC 크롬/엣지 확장 프로그램 가져오기")
        dlg.resize(500, 400)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("가져올 확장 프로그램을 클릭하면 Bside 브라우저에 즉시 로드 및 상단 고정됩니다:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        wl = QVBoxLayout(w)
        for item in found:
            btn = QPushButton(f"🧩 {item['name']} (v{item['version']})  —  가져오기")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("text-align: left; padding: 8px 12px; font-weight: 600; border-radius: 8px;")
            p_path = item["path"]
            def _import_one(pt=p_path, d=dlg):
                staged = self._stage_to_local_disk(pt)
                self.ext_mgr.loadExtension(staged)
                d.accept()
            btn.clicked.connect(lambda checked=False, fn=_import_one: fn())
            wl.addWidget(btn)
        wl.addStretch(1)
        scroll.setWidget(w)
        v.addWidget(scroll, 1)
        dlg.exec()

    def closeEvent(self, event):
        try:
            self.ext_mgr.loadFinished.disconnect(self._on_ext_event)
            self.ext_mgr.installFinished.disconnect(self._on_ext_event)
            self.ext_mgr.uninstallFinished.disconnect(self._on_ext_event)
        except Exception:
            pass
        super().closeEvent(event)

    def done(self, result: int):
        try:
            self.ext_mgr.loadFinished.disconnect(self._on_ext_event)
            self.ext_mgr.installFinished.disconnect(self._on_ext_event)
            self.ext_mgr.uninstallFinished.disconnect(self._on_ext_event)
        except Exception:
            pass
        super().done(result)
