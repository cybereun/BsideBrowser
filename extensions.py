# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent — Chrome Extension Manager & Popup Host
Uses PySide6 / Qt 6.10 native `QWebEngineExtensionManager` and `QWebEngineExtensionInfo`
plus direct Chrome Web Store (`.crx` / `.zip` / unpacked folder) installation & PC Chrome extension import!
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
)
from PySide6.QtCore import Qt, Signal, QUrl, QPoint, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineExtensionInfo

from theme import get_palette
from icons import make_3d_badge_pixmap, make_nav_icon


def extract_crx_or_zip_to_dir(archive_path: str, dest_dir: str) -> Tuple[bool, str]:
    """
    Extracts a `.crx` (CRX2 or CRX3) or `.zip` Chrome extension package into `dest_dir`.
    CRX files contain a binary header followed by a standard ZIP archive starting at `PK\\x03\\x04`.
    """
    try:
        with open(archive_path, "rb") as f:
            raw = f.read()

        # Locate ZIP local file header signature PK\x03\x04
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
            # Check if extracted inside a single subfolder
            subs = [os.path.join(dest_dir, d) for d in os.listdir(dest_dir) if os.path.isdir(os.path.join(dest_dir, d))]
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
                        name = mf.get("name", ext_id)
                        if str(name).startswith("__MSG_"):
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
        self.resize(380, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        self.webview = QWebEngineView(self)
        self.page_obj = QWebEnginePage(profile, self.webview)
        self.webview.setPage(self.page_obj)
        self.webview.setUrl(popup_url)
        layout.addWidget(self.webview)


class ChromeExtensionManagerDialog(QDialog):
    """
    Minimalist, practical Chrome Extension Manager Popup & Hub (`🧩 확장 프로그램`):
    - Lists all loaded/installed Chrome Extensions in `QWebEngineExtensionManager`
    - Allows toggling On/Off, opening the extension's Action Popup (`actionPopupUrl`), or removing
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

        self.setWindowTitle("🧩 크롬 확장 프로그램 (Chrome Extensions)")
        self.resize(620, 560)

        # Connect signals from QWebEngineExtensionManager
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
        s_lbl = QLabel("크롬 웹 스토어 URL, CRX/ZIP 파일, 압축 해제된 폴더 또는 PC 크롬 확장앱을 바로 설치하세요.")
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
        """
        Copies an extension folder to the fast local SSD (`%LOCALAPPDATA%\\BsideBrowser\\extensions\\...`)
        if it resides on a virtualized/cloud drive (e.g., Google Drive `z:\\`) or non-ASCII path,
        preventing Chromium's file-locks and ServiceWorker loader from hanging or crashing!
        """
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
            # Persist path in storage so it reloads on next startup
            saved = [os.path.normpath(p) for p in self.storage.get_setting("installed_extension_paths", []) if p]
            if ext_path and ext_path not in saved:
                saved.append(ext_path)
                self.storage.set_setting("installed_extension_paths", saved)
            self.status_lbl.setStyleSheet("color: #10B981; font-size: 11.5px; font-weight: 700;")
            self.status_lbl.setText(f"✓ '{ext_name}' 확장 프로그램 로드 및 활성화 완료!")

        # Defer enabling & UI rebuild by 1 event-loop tick so we never mutate QWebEngineExtensionManager
        # or delete QWidgets while Chromium is still inside its C++ loadFinished signal dispatch!
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
        exts = self.ext_mgr.extensions()

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
                "위에서 [크롬 웹 스토어 열기], [스토어에서 바로 설치], 또는 [내 PC 크롬/엣지 확장앱 가져오기]를 눌러 추가해 보세요!"
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {p['fg_muted']}; font-size: 12.5px;")
            el.addWidget(lbl)
            self.list_layout.insertWidget(0, empty_card)
            return

        for idx, ext in enumerate(exts):
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
            glyph = (ext.name() or "E")[0].upper()
            icon_lbl.setPixmap(make_3d_badge_pixmap(glyph, "#10B981" if ext.isEnabled() else "#94A3B8", "#059669" if ext.isEnabled() else "#64748B", size=34, radius=9))
            row.addWidget(icon_lbl)

            info_col = QVBoxLayout()
            info_col.setSpacing(2)
            name_lbl = QLabel(f"{ext.name() or '확장 프로그램'}  ({'활성' if ext.isEnabled() else '비활성'})")
            name_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
            desc_lbl = QLabel(ext.description() or ext.path())
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(f"color: {p['fg_muted']}; font-size: 11px;")
            info_col.addWidget(name_lbl)
            info_col.addWidget(desc_lbl)
            row.addLayout(info_col, 1)

            popup_url = ext.actionPopupUrl()
            if popup_url and not popup_url.isEmpty():
                open_pop_btn = QPushButton("창 열기")
                open_pop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                open_pop_btn.setStyleSheet(
                    f"background-color: {p['accent_soft']}; color: {p['accent_fg']}; border: none; border-radius: 8px; padding: 5px 10px; font-weight: 700; font-size: 11.5px;"
                )
                open_pop_btn.clicked.connect(
                    lambda checked=False, n=ext.name(), u=popup_url: self._open_ext_popup(n, u)
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

    def _open_ext_popup(self, name: str, url: QUrl):
        pop = ExtensionActionPopup(name, url, self.profile, self)
        pop.move(self. geometry().center() - QPoint(190, 200))
        pop.exec()

    def _toggle_ext(self, ext: QWebEngineExtensionInfo):
        self.ext_mgr.setExtensionEnabled(ext, not ext.isEnabled())
        self._refresh_list()
        self.extensions_changed.emit()

    def _remove_ext(self, ext: QWebEngineExtensionInfo):
        path = ext.path()
        saved = self.storage.get_setting("installed_extension_paths", [])
        if path in saved:
            saved.remove(path)
            self.storage.set_setting("installed_extension_paths", saved)
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
        )
        if not path:
            return
        base_name = os.path.splitext(os.path.basename(path))[0]
        dest_dir = os.path.join(self.ext_storage_dir, base_name)
        ok, res = extract_crx_or_zip_to_dir(path, dest_dir)
        if ok:
            self.ext_mgr.loadExtension(res)
        else:
            # Try QtWebEngine's native installExtension as fallback
            self.ext_mgr.installExtension(path)

    @staticmethod
    def _find_manifest_dir(folder: str) -> Optional[str]:
        """
        Finds `manifest.json` in `folder`, or one/two levels inside if the user selected
        a parent wrapper folder or Chrome extension ID folder (which contains version subfolders).
        """
        if not folder or not os.path.isdir(folder):
            return None
        if os.path.isfile(os.path.join(folder, "manifest.json")):
            return folder
        # Search 1-2 levels deep (e.g. wrapper_dir/1.0.0_0/manifest.json)
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
        v.addWidget(QLabel("가져올 확장 프로그램을 클릭하면 Bside 브라우저에 즉시 로드됩니다:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        wl = QVBoxLayout(w)
        for item in found:
            btn = QPushButton(f"🧩 {item['name']} (v{item['version']})  —  가져오기")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("text-align: left; padding: 8px 12px; font-weight: 600; border-radius: 8px;")
            p_path = item["path"]
            btn.clicked.connect(lambda checked=False, pt=p_path, d=dlg: (self.ext_mgr.loadExtension(pt), d.accept()))
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
