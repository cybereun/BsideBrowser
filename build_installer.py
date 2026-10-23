# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent — Automated PyInstaller + Inno Setup Installer Builder
Builds inside fast local `%TEMP%\\BsideBuild` so Google Drive (`z:\\`) virtual file locks
never slow down or block PyInstaller / Inno Setup, then copies the final `Bside_Setup_v1.0.0.exe`
into `z:\\내 드라이브\\AI\\App_Bulid\\BsideBrowser\\dist_installer\\`!
"""

import os
import sys
import subprocess
import shutil
import tempfile
from version import APP_VERSION

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def find_iscc():
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        shutil.which("ISCC.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def main():
    build_root = os.path.join(tempfile.gettempdir(), "BsideBrowser_BuildWork")
    dist_dir = os.path.join(build_root, "dist")
    work_dir = os.path.join(build_root, "build")
    out_installer_dir = os.path.join(BASE_DIR, "dist_installer")
    os.makedirs(out_installer_dir, exist_ok=True)

    if "--iscc-only" not in sys.argv:
        print("=== [1/3] Building Bside.exe (windowed, no-console) with PyInstaller ===")
        spec_file = os.path.join(BASE_DIR, "Bside.spec")
        cmd_pyinstaller = [
            sys.executable,
            "-m",
            "PyInstaller",
            spec_file,
            "--noconfirm",
            "--clean",
            "--distpath",
            dist_dir,
            "--workpath",
            work_dir,
        ]

        ret = subprocess.run(cmd_pyinstaller, cwd=BASE_DIR)
        if ret.returncode != 0:
            print("[ERROR] PyInstaller build failed!")
            sys.exit(ret.returncode)

    assets_src = os.path.join(BASE_DIR, "assets")
    assets_dst = os.path.join(dist_dir, "Bside", "assets")
    if os.path.exists(assets_src):
        shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)
        print(f" -> Copied assets to: {assets_dst}")

    print("\n=== [2/3] Smoke-Testing Built Bside.exe ===")
    built_exe = os.path.join(dist_dir, "Bside", "Bside.exe")
    if not os.path.exists(built_exe):
        print(f"[ERROR] Built executable not found: {built_exe}")
        sys.exit(1)

    smoke_ret = subprocess.run([built_exe, "--smoke-test"], cwd=os.path.join(dist_dir, "Bside"), timeout=45)
    print(f" -> Built Bside.exe smoke test return code: {smoke_ret.returncode}")

    print("\n=== [3/3] Compiling Bside_Setup_v1.0.0.exe with Inno Setup ===")
    iscc_path = find_iscc()
    if not iscc_path:
        print("[ERROR] Inno Setup (ISCC.exe) not found!")
        sys.exit(1)

    clean_v = APP_VERSION.lstrip("vV")
    iss_temp = os.path.join(build_root, "bside_installer_build.iss")
    with open(os.path.join(BASE_DIR, "installer", "bside_installer.iss"), "r", encoding="utf-8") as f:
        iss_content = f.read()

    # Point Inno Setup directly to the fast local dist_dir and assets_dst (100% ASCII paths!)
    local_out_dir = os.path.join(build_root, "dist_installer")
    os.makedirs(local_out_dir, exist_ok=True)
    iss_content = iss_content.replace(r'Source: "..\dist\Bside\*"', f'Source: "{os.path.join(dist_dir, "Bside")}\\*"')
    iss_content = iss_content.replace(r'Source: "..\assets\*"', f'Source: "{assets_dst}\\*"')
    iss_content = iss_content.replace(r"SetupIconFile=..\assets\app_icon.ico", f"SetupIconFile={os.path.join(assets_dst, 'app_icon.ico')}")
    iss_content = iss_content.replace(r"OutputDir=..\dist_installer", f"OutputDir={local_out_dir}")

    with open(iss_temp, "w", encoding="utf-8-sig") as f:
        f.write(iss_content)

    cmd_iscc = [iscc_path, f"/DMyAppVersion={clean_v}", iss_temp]
    ret = subprocess.run(cmd_iscc, cwd=build_root)
    if ret.returncode != 0:
        print("[ERROR] Inno Setup compilation failed!")
        sys.exit(ret.returncode)

    local_setup_exe = os.path.join(local_out_dir, f"Bside_Setup_{APP_VERSION}.exe")
    setup_exe = os.path.join(out_installer_dir, f"Bside_Setup_{APP_VERSION}.exe")
    if os.path.exists(local_setup_exe):
        shutil.copy2(local_setup_exe, setup_exe)
        size_mb = os.path.getsize(setup_exe) / (1024 * 1024)
        print(f"\n[SUCCESS] Installer generated: {setup_exe} ({size_mb:.2f} MB)")
        print(f" -> Local copy: {local_setup_exe}")
    else:
        print("[ERROR] Setup exe was not found in dist_installer!")
        sys.exit(1)


if __name__ == "__main__":
    main()
