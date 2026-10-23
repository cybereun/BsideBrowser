# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent Sidebar — Application Entrypoint
Reconstructed from Aside.exe (v1.0.1022.1) and rebranded to Bside Browser & BsideAgentManager (v1.26.1023.5).
"""

import os
import sys
import subprocess
import ctypes


def _ensure_qt_webengine_dll_path():
    """
    Fixes 'QtWebEngineProcess.exe - Qt6WebEngineCore.dll was not found' on Windows:
    1. Resolves both `PySide6` and `shiboken6` site-packages directories (or `_internal` when frozen).
    2. Sets `QTWEBENGINE_DISABLE_SANDBOX=1` and `--no-sandbox` so the Windows AppContainer
       sandbox does not strip user-roaming DLL paths from QtWebEngineProcess.exe.
    3. Pre-populates the process PATH and re-execs once with CREATE_NO_WINDOW (`0x08000000`)
       if needed so NO console/terminal window ever flashes or stays open!
    """
    if sys.platform != "win32":
        return

    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    existing_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    if "--no-sandbox" not in existing_flags:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (existing_flags + " --no-sandbox --disable-gpu").strip()

    # When packaged as a PyInstaller frozen .exe, all DLLs are already in the exe / _internal dir
    if getattr(sys, "frozen", False):
        return

    try:
        import importlib.util

        dll_dirs = []
        for pkg_name in ("PySide6", "shiboken6"):
            spec = importlib.util.find_spec(pkg_name)
            if spec and spec.origin:
                pkg_dir = os.path.dirname(os.path.abspath(spec.origin))
                if os.path.isdir(pkg_dir):
                    dll_dirs.append(pkg_dir)

        if not dll_dirs:
            return

        current_path = os.environ.get("PATH", "")
        missing = [d for d in dll_dirs if d.lower() not in current_path.lower()]

        if missing and os.environ.get("BSIDE_QT_PATH_BOOTSTRAPPED") != "1":
            env = os.environ.copy()
            env["PATH"] = os.pathsep.join(dll_dirs) + os.pathsep + current_path
            env["BSIDE_QT_PATH_BOOTSTRAPPED"] = "1"
            env["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
            env["QTWEBENGINE_CHROMIUM_FLAGS"] = os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]
            pyside_dir = dll_dirs[0]
            proc_exe = os.path.join(pyside_dir, "QtWebEngineProcess.exe")
            if os.path.exists(proc_exe):
                env["QTWEBENGINEPROCESS_PATH"] = proc_exe

            # Prefer pythonw.exe and CREATE_NO_WINDOW so a terminal window NEVER appears!
            py_exe = sys.executable
            if py_exe.lower().endswith("python.exe") and "--smoke-test" not in sys.argv:
                pyw = py_exe[:-10] + "pythonw.exe"
                if os.path.exists(pyw):
                    py_exe = pyw

            no_win_flag = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            if "--smoke-test" in sys.argv:
                ret = subprocess.call([py_exe] + sys.argv, env=env, creationflags=no_win_flag)
                sys.exit(ret)
            else:
                subprocess.Popen([py_exe] + sys.argv, env=env, creationflags=no_win_flag)
                sys.exit(0)

        for d in dll_dirs:
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(d)
                except Exception:
                    pass
    except SystemExit:
        raise
    except Exception:
        pass


_ensure_qt_webengine_dll_path()

if sys.platform == "win32":
    try:
        # Hide any attached console window if accidentally launched via python.exe instead of pythonw.exe
        if "--smoke-test" not in sys.argv:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("StudioAt.Bside.Browser.1.0.0")
    except Exception:
        pass

from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtCore import Qt, QTimer

from theme import APP_NAME, APP_VERSION, get_app_stylesheet
from main_window import MainWindow
from icons import get_app_window_icon


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Studio At")
    app_icon = get_app_window_icon()
    app.setWindowIcon(app_icon)

    initial_url = "bside://newtab"
    smoke_test = "--smoke-test" in sys.argv
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            initial_url = arg
            break

    window = MainWindow(initial_url=initial_url)
    window.setWindowIcon(app_icon)
    app.setStyleSheet(get_app_stylesheet(window.theme_mode))
    window.show()

    if smoke_test:
        def _run_smoke():
            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview.png")
            window.grab().save(screenshot_path)
            print("SMOKE_TEST_OK:", screenshot_path)
            app.quit()

        QTimer.singleShot(2500, _run_smoke)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
