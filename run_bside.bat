@echo off
chcp 65001 > nul
cd /d "%~dp0"
set "PYSIDE_DIR=%APPDATA%\Python\Python314\site-packages\PySide6"
set "SHIBOKEN_DIR=%APPDATA%\Python\Python314\site-packages\shiboken6"
set "PATH=%PYSIDE_DIR%;%SHIBOKEN_DIR%;%PATH%"
set "QTWEBENGINE_DISABLE_SANDBOX=1"
set "QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu"
set "BSIDE_QT_PATH_BOOTSTRAPPED=1"
start "" pythonw main.py
