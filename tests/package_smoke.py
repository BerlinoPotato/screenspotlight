"""Launch the packaged app hidden and verify startup plus graceful WM_CLOSE."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import time


def main():
    exe = Path(__file__).resolve().parents[1] / "dist" / "ScreenSpotlight" / "ScreenSpotlight.exe"
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen([str(exe)], startupinfo=startup)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    windows = []
    duplicate_windows = []
    duplicate = None

    @callback_type
    def inspect(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process.pid:
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title, len(title))
            if title.value == "Screen Spotlight":
                windows.append(hwnd)
        elif duplicate is not None and pid.value == duplicate.pid:
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title, len(title))
            if title.value == "Screen Spotlight already running":
                duplicate_windows.append(hwnd)
        return True

    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not windows:
            assert process.poll() is None, f"App exited early: {process.returncode}"
            user32.EnumWindows(inspect, 0)
            time.sleep(0.1)
        assert windows, "Packaged control panel not found"
        print("PASS: Packaged application created its control panel")
        duplicate = subprocess.Popen([str(exe)], startupinfo=startup)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not duplicate_windows:
            assert duplicate.poll() is None, "Duplicate exited before reporting its instance lock"
            user32.EnumWindows(inspect, 0)
            time.sleep(0.1)
        assert duplicate_windows, "Duplicate instance was not blocked"
        user32.PostMessageW(duplicate_windows[0], 0x0010, 0, 0)
        assert duplicate.wait(timeout=10) == 0
        print("PASS: A second packaged instance is blocked before creating overlays or hotkeys")
        user32.PostMessageW(windows[0], 0x0010, 0, 0)
        assert process.wait(timeout=10) == 0, "App exited with an error"
        print("PASS: Closing the packaged control panel exits cleanly")
    finally:
        if duplicate is not None and duplicate.poll() is None:
            duplicate.terminate()
            duplicate.wait(timeout=10)
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
