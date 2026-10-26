# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent — Automatic Update Checker, Silent Installer & Auto-Relauncher
Checks `https://api.github.com/repos/cybereun/BsideBrowser/releases/latest`:
- When a newer version is detected, automatically downloads `Bside_Setup_v*.exe` in the background
  (or via UpdateDialog when triggered manually), runs Inno Setup silently (`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS`),
  and automatically restarts the updated Bside Browser!
"""

import os
import sys
import json
import re
import tempfile
import subprocess
import urllib.request
import urllib.error

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QMessageBox,
    QFrame,
    QApplication,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QIcon, QPixmap

from version import APP_NAME, APP_VERSION, GITHUB_API_LATEST


def parse_version(v_str: str):
    """'v1.0.1' -> (1, 0, 1) tuple"""
    clean = re.sub(r"^[vV]", "", (v_str or "").strip())
    parts = []
    for p in clean.split("."):
        digits = re.match(r"\d+", p)
        parts.append(int(digits.group(0)) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer_version(remote_v: str, local_v: str) -> bool:
    try:
        return parse_version(remote_v) > parse_version(local_v)
    except Exception:
        return False


class CheckUpdateThread(QThread):
    update_found = Signal(dict)
    no_update = Signal(str)
    check_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            req = urllib.request.Request(
                GITHUB_API_LATEST,
                headers={"User-Agent": f"{APP_NAME}-Updater/{APP_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status != 200:
                    self.check_error.emit(f"HTTP {response.status}")
                    return
                data = json.loads(response.read().decode("utf-8"))

            tag_name = data.get("tag_name", "")
            if not tag_name:
                self.no_update.emit(APP_VERSION)
                return

            if is_newer_version(tag_name, APP_VERSION):
                assets = data.get("assets", [])
                download_url = None
                asset_name = ""
                asset_size = 0

                for a in assets:
                    name = a.get("name", "")
                    if name.lower().endswith(".exe") and "setup" in name.lower():
                        download_url = a.get("browser_download_url")
                        asset_name = name
                        asset_size = a.get("size", 0)
                        break

                if not download_url:
                    for a in assets:
                        name = a.get("name", "")
                        if name.lower().endswith(".exe"):
                            download_url = a.get("browser_download_url")
                            asset_name = name
                            asset_size = a.get("size", 0)
                            break

                info = {
                    "tag_name": tag_name,
                    "title": data.get("name", tag_name),
                    "body": data.get("body", "새로운 버전이 출시되었습니다."),
                    "download_url": download_url,
                    "asset_name": asset_name,
                    "asset_size": asset_size,
                    "html_url": data.get("html_url", ""),
                }
                self.update_found.emit(info)
            else:
                self.no_update.emit(APP_VERSION)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.no_update.emit(APP_VERSION)
            else:
                self.check_error.emit(f"서버 응답 오류 (HTTP {e.code})")
        except Exception as e:
            self.check_error.emit(str(e))


class DownloadUpdateThread(QThread):
    """
    Downloads the installer with automatic retry + resume (HTTP Range). A connection that is reset mid-way
    (flaky network, proxy or security software closing the socket) continues from the bytes already saved.
    """
    progress = Signal(int, int, int)  # percent, downloaded, total
    retrying = Signal(str)            # human readable retry notice
    finished = Signal(str)            # local file path
    failed = Signal(str)

    MAX_ATTEMPTS = 8

    def __init__(self, url: str, asset_name: str, parent=None, expected_size: int = 0):
        super().__init__(parent)
        self.url = url
        self.asset_name = asset_name
        self.expected_size = int(expected_size or 0)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def _discard(self, *paths):
        for pth in paths:
            try:
                if os.path.exists(pth):
                    os.remove(pth)
            except OSError:
                pass

    def run(self):
        filename = self.asset_name if self.asset_name else "Bside_Setup_Update.exe"
        target_path = os.path.join(tempfile.gettempdir(), filename)
        part_path = target_path + ".part"
        self._discard(part_path)  # never resume a leftover from an older run
        last_err = ""

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            if self._is_cancelled:
                break
            have = os.path.getsize(part_path) if os.path.exists(part_path) else 0
            if self.expected_size and have >= self.expected_size:
                break
            try:
                headers = {"User-Agent": f"{APP_NAME}-Updater/{APP_VERSION}"}
                if have:
                    headers["Range"] = f"bytes={have}-"
                req = urllib.request.Request(self.url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resumed = bool(have) and resp.status == 206
                    if have and not resumed:
                        have = 0  # server ignored Range: start over
                    length = int(resp.headers.get("Content-Length", 0))
                    total = self.expected_size or (length + have)
                    downloaded = have
                    with open(part_path, "ab" if resumed else "wb") as out_file:
                        while not self._is_cancelled:
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            out_file.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                self.progress.emit(int(downloaded / total * 100), downloaded, total)
                if self._is_cancelled:
                    break
                size_now = os.path.getsize(part_path)
                if not self.expected_size or size_now >= self.expected_size:
                    break  # complete
                last_err = f"전송이 중간에 끊겼습니다 ({size_now}/{self.expected_size} bytes)"
            except urllib.error.HTTPError as e:
                if e.code == 416:  # range past the end: the file is already complete
                    break
                last_err = f"HTTP {e.code}"
            except Exception as e:  # reset / timeout / DNS: retry and resume
                last_err = str(e)

            if attempt < self.MAX_ATTEMPTS and not self._is_cancelled:
                self.retrying.emit(f"연결이 끊겨 이어받는 중... ({attempt}/{self.MAX_ATTEMPTS - 1}회 재시도) — {last_err[:60]}")
                self.msleep(min(2000 * attempt, 8000))

        if self._is_cancelled:
            self._discard(part_path)
            self.failed.emit("다운로드가 취소되었습니다.")
            return

        size_now = os.path.getsize(part_path) if os.path.exists(part_path) else 0
        if size_now == 0 or (self.expected_size and size_now < self.expected_size):
            self._discard(part_path)
            self.failed.emit(f"다운로드 실패: {last_err or '연결할 수 없습니다'}")
            return

        try:
            os.replace(part_path, target_path)
        except OSError as e:
            self.failed.emit(f"다운로드 파일 저장 실패: {e}")
            return
        self.finished.emit(target_path)


def launch_silent_installer_and_restart(installer_path: str):
    """
    Runs the downloaded Inno Setup installer silently in the background, waits for it to finish
    updating `{autopf}\\Bside\\Bside.exe`, and automatically relaunches the new Bside.exe
    with zero visible console/terminal windows!
    """
    installed_exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Bside\Bside.exe")
    if getattr(sys, "frozen", False):
        relaunch_cmd = f'"{sys.executable}"'
    else:
        relaunch_cmd = f'if exist "{installed_exe}" (start "" "{installed_exe}") else (start "" pythonw "{os.path.abspath(sys.argv[0])}")'

    bat_path = os.path.join(tempfile.gettempdir(), "bside_auto_update_restart.bat")
    with open(bat_path, "w", encoding="utf-8") as bf:
        bf.write(
            "@echo off\n"
            "timeout /t 1 /nobreak >nul\n"
            f'"{installer_path}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS\n'
            "timeout /t 1 /nobreak >nul\n"
            f'if exist "{installed_exe}" (\n'
            f'    start "" "{installed_exe}"\n'
            ") else (\n"
            f"    {relaunch_cmd}\n"
            ")\n"
        )

    no_win = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=no_win)
    QApplication.quit()
    sys.exit(0)


class UpdateDialog(QDialog):
    """
    Shows update progress and automatically starts downloading & installing the new version
    within 1.5 seconds (or immediately when clicked), then restarts Bside Browser automatically!
    """

    def __init__(self, update_info: dict, auto_install: bool = True, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.auto_install = auto_install
        self.download_thread = None

        self.setWindowTitle(f"{APP_NAME} 자동 업데이트 ({update_info.get('tag_name', '')})")
        self.setFixedSize(500, 400)

        asset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        icon_path = os.path.join(asset_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._init_ui()
        if self.auto_install and self.update_info.get("download_url"):
            QTimer.singleShot(800, self._start_download)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)

        asset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        png_icon = os.path.join(asset_dir, "app_icon.png")
        icon_lbl = QLabel()
        if os.path.exists(png_icon):
            icon_lbl.setPixmap(
                QPixmap(png_icon).scaled(
                    56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
            )
        icon_lbl.setFixedSize(56, 56)
        header_layout.addWidget(icon_lbl)

        v_layout = QVBoxLayout()
        v_layout.setSpacing(4)
        title_lbl = QLabel(f"<b>새로운 {APP_NAME} 버전이 감지되어 자동 업데이트합니다!</b>")
        title_lbl.setStyleSheet("font-size: 14.5px; color: #1E293B; font-weight: bold;")
        v_layout.addWidget(title_lbl)

        cur_v = APP_VERSION
        new_v = self.update_info.get("tag_name", "")
        ver_lbl = QLabel(
            f"현재 버전: <span style='color:#64748B;'>{cur_v}</span>  ➔  최신 버전: <b style='color:#4F46E5;'>{new_v}</b>"
        )
        ver_lbl.setStyleSheet("font-size: 12px;")
        v_layout.addWidget(ver_lbl)

        header_layout.addLayout(v_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(line)

        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setPlainText(self.update_info.get("body", "새로운 업데이트가 출시되었습니다."))
        self.notes_text.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 10px; font-size: 11.5px; color: #334155;"
        )
        layout.addWidget(self.notes_text, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                text-align: center;
                height: 20px;
                font-size: 11px;
                font-weight: bold;
                color: #1E293B;
                background-color: #F1F5F9;
            }
            QProgressBar::chunk {
                background-color: #4F46E5;
                border-radius: 5px;
            }
            """
        )
        layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("최신 설치 파일을 자동으로 다운로드하고 재실행합니다...")
        self.status_lbl.setStyleSheet("font-size: 11.5px; color: #4F46E5; font-weight: 600;")
        layout.addWidget(self.status_lbl)

        btn_layout = QHBoxLayout()
        self.btn_row = btn_layout
        btn_layout.addStretch()

        self.btn_later = QPushButton("취소 / 나중에")
        self.btn_later.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_later.clicked.connect(self._cancel_and_close)
        btn_layout.addWidget(self.btn_later)

        self.btn_update = QPushButton("지금 바로 설치 및 재시작")
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.setStyleSheet(
            "background-color: #4F46E5; color: #FFFFFF; border: none; border-radius: 8px; padding: 7px 16px; font-weight: 700;"
        )
        self.btn_update.clicked.connect(self._start_download)
        btn_layout.addWidget(self.btn_update)
        layout.addLayout(btn_layout)

    def _cancel_and_close(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
        self.reject()

    def _start_download(self):
        if self.download_thread and self.download_thread.isRunning():
            return
        download_url = self.update_info.get("download_url")
        if not download_url:
            html_url = self.update_info.get("html_url")
            if html_url:
                import webbrowser
                webbrowser.open(html_url)
            self.accept()
            return

        self.btn_update.setEnabled(False)
        self.btn_update.setText("자동 설치 진행 중...")
        self.status_lbl.setText("업데이트 설치 파일 다운로드 중...")

        asset_name = self.update_info.get("asset_name", "Bside_Setup_Update.exe")
        self.download_thread = DownloadUpdateThread(
            download_url, asset_name, self, expected_size=int(self.update_info.get("asset_size") or 0)
        )
        self.download_thread.progress.connect(self._on_progress)
        self.download_thread.retrying.connect(self.status_lbl.setText)
        self.download_thread.finished.connect(self._on_finished)
        self.download_thread.failed.connect(self._on_failed)
        self.download_thread.start()

    def _on_progress(self, pct, downloaded, total):
        self.progress_bar.setValue(pct)
        mb_down = downloaded / (1024 * 1024)
        if total > 0:
            mb_tot = total / (1024 * 1024)
            self.status_lbl.setText(f"다운로드 중: {mb_down:.1f} MB / {mb_tot:.1f} MB ({pct}%)")
        else:
            self.status_lbl.setText(f"다운로드 중: {mb_down:.1f} MB")

    def _on_finished(self, target_path):
        self.progress_bar.setValue(100)
        self.status_lbl.setText("다운로드 완료! 자동 설치 후 Bside를 다시 시작합니다...")
        QTimer.singleShot(300, lambda: launch_silent_installer_and_restart(target_path))

    def _on_failed(self, err_msg):
        self.btn_update.setEnabled(True)
        self.btn_update.setText("재시도")
        self.status_lbl.setText(
            f"오류: {err_msg}\n보안 프로그램이나 네트워크가 다운로드를 막고 있다면 '브라우저로 직접 받기'를 이용하세요."
        )
        self.status_lbl.setWordWrap(True)
        if not getattr(self, "btn_browser", None):
            self.btn_browser = QPushButton("브라우저로 직접 받기")
            self.btn_browser.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_browser.clicked.connect(self._open_release_page)
            self.btn_row.insertWidget(1, self.btn_browser)

    def _open_release_page(self):
        import webbrowser
        webbrowser.open(self.update_info.get("html_url") or self.update_info.get("download_url") or "")


class AutoUpdater:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.check_thread = None

    def check(self, silent=True):
        self.silent = silent
        self.check_thread = CheckUpdateThread(self.parent)
        self.check_thread.update_found.connect(self._on_update_found)
        self.check_thread.no_update.connect(self._on_no_update)
        self.check_thread.check_error.connect(self._on_check_error)
        self.check_thread.start()

    def _on_update_found(self, info):
        dialog = UpdateDialog(info, auto_install=True, parent=self.parent)
        dialog.exec()

    def _on_no_update(self, cur_ver):
        if not self.silent:
            QMessageBox.information(
                self.parent,
                "업데이트 확인",
                f"현재 최신 버전({cur_ver})을 사용 중입니다.\n새 버전이 출시되면 자동으로 설치 후 재실행됩니다.",
            )

    def _on_check_error(self, err):
        if not self.silent:
            QMessageBox.warning(
                self.parent,
                "업데이트 확인 실패",
                f"GitHub 릴리즈 서버 확인 중 오류가 발생했습니다:\n{err}",
            )
