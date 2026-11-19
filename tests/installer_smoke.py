"""Exercise the real installer, shortcuts, installed application, and uninstaller."""
import ctypes
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import winreg

from package_smoke import check_package

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "installer"))
from build_installer import app_version

UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{791218E2-B216-4A44-AAD4-75214B8924CC}_is1"
REG_ACCESS = winreg.KEY_READ | winreg.KEY_WOW64_64KEY


def installed_info():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, REG_ACCESS) as key:
            return {name: winreg.QueryValueEx(key, name)[0] for name in
                    ("DisplayName", "DisplayVersion", "InstallLocation", "UninstallString")}
    except FileNotFoundError:
        return None


def shell_folder(identifier):
    buffer = ctypes.create_unicode_buffer(260)
    result = ctypes.windll.shell32.SHGetFolderPathW(None, identifier, None, 0, buffer)
    if result != 0:
        raise OSError(f"Cannot resolve shell folder {identifier}: {result:#x}")
    return Path(buffer.value)


def shortcut_target(shortcut):
    environment = dict(os.environ, SCREEN_SPOTLIGHT_TEST_LINK=str(shortcut))
    return Path(subprocess.check_output([
        "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
        "[Console]::Write((New-Object -ComObject WScript.Shell).CreateShortcut($env:SCREEN_SPOTLIGHT_TEST_LINK).TargetPath)",
    ], env=environment, text=True, creationflags=subprocess.CREATE_NO_WINDOW))


def run_setup(executable, arguments):
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    result = subprocess.run([str(executable), "/VERYSILENT", "/SUPPRESSMSGBOXES",
                             "/NORESTART", *arguments], startupinfo=startup, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"{executable.name} failed: {result.returncode}; see build installer logs")


def main():
    version = app_version()
    installer = ROOT / "dist" / f"ScreenSpotlight-Setup-{version}.exe"
    assert installer.is_file(), f"Build the installer first: {installer}"
    assert installed_info() is None, "An installation exists; refusing to replace it during testing"
    menu_folder = shell_folder(2) / "Screen Spotlight"
    assert not menu_folder.exists(), "A Start menu folder exists; refusing to replace its shortcuts"
    desktop_shortcut = shell_folder(0x10) / "Screen Spotlight.lnk"
    desktop_existed = desktop_shortcut.exists()
    (ROOT / "build").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="installer-smoke-", dir=ROOT / "build") as temporary:
        install_dir = (Path(temporary) / "Screen Spotlight").resolve()
        assert install_dir.is_relative_to((ROOT / "build").resolve())
        installed_exe = install_dir / "ScreenSpotlight.exe"
        common_args = ["/SP-", f"/DIR={install_dir}"]
        uninstaller = None
        try:
            run_setup(installer, [*common_args, "/MERGETASKS=!desktopicon",
                                 f"/LOG={ROOT / 'build/installer-install.log'}"])
            uninstaller = install_dir / "unins000.exe"
            assert installed_exe.is_file() and uninstaller.is_file()
            assert hashlib.sha256(installed_exe.read_bytes()).digest() == hashlib.sha256(
                (ROOT / "dist/ScreenSpotlight.exe").read_bytes()).digest()
            info = installed_info()
            assert info and info["DisplayName"] == "Screen Spotlight"
            assert info["DisplayVersion"] == version
            assert Path(info["InstallLocation"]).resolve() == install_dir
            shortcut = menu_folder / "Screen Spotlight.lnk"
            assert shortcut.is_file() and shortcut_target(shortcut).resolve() == installed_exe
            assert desktop_shortcut.exists() == desktop_existed, "Desktop shortcut should be opt-in"
            print("PASS: Per-user installation, exact application payload, version, and Start menu shortcut", flush=True)
            check_package(installed_exe)
            print("PASS: Installed application starts, blocks duplicate instances, and closes", flush=True)
            user_file = install_dir / "user-file.keep"
            user_file.write_text("Keep unowned files during uninstall", encoding="utf-8")
            task = "/MERGETASKS=!desktopicon" if desktop_existed else "/MERGETASKS=desktopicon"
            run_setup(installer, [*common_args, task, f"/LOG={ROOT / 'build/installer-reinstall.log'}"])
            assert installed_info()["DisplayVersion"] == version
            assert list(install_dir.glob("unins*.exe")) == [uninstaller]
            assert user_file.read_text(encoding="utf-8") == "Keep unowned files during uninstall"
            if not desktop_existed:
                assert desktop_shortcut.is_file() and shortcut_target(desktop_shortcut).resolve() == installed_exe
            print("PASS: Reinstallation reuses the installation; optional desktop shortcut works", flush=True)
            run_setup(uninstaller, [f"/LOG={ROOT / 'build/installer-uninstall.log'}"])
            deadline = time.monotonic() + 15
            while uninstaller.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            assert not installed_exe.exists() and not uninstaller.exists()
            assert installed_info() is None and not shortcut.exists()
            assert desktop_shortcut.exists() == desktop_existed
            assert user_file.exists(), "Uninstaller removed an unowned file"
            print("PASS: Uninstall removes application, registry entry, and shortcuts; unowned files remain", flush=True)
        finally:
            # Cleanup is limited to this test's own installation, never a prior one.
            if installed_info() and (install_dir / "unins000.exe").exists():
                assert Path(installed_info()["InstallLocation"]).resolve() == install_dir
                run_setup(install_dir / "unins000.exe", [])


if __name__ == "__main__":
    main()
