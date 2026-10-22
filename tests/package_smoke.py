"""Launch the packaged app hidden and verify startup plus graceful WM_CLOSE."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def main():
    built_exe = Path(__file__).resolve().parents[1] / "dist" / "ScreenSpotlight.exe"
    with tempfile.TemporaryDirectory(prefix="Screen Spotlight portable ") as folder:
        exe = Path(folder) / built_exe.name
        shutil.copy2(built_exe, exe)
        assert list(Path(folder).iterdir()) == [exe]
        check_package(exe)


def check_package(exe):
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen([str(exe)], startupinfo=startup, cwd=exe.parent)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    # One-file builds launch a child process that owns the Qt windows.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    def is_test_process(pid):
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            path = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(path))
            return bool(kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size))) and Path(path.value).resolve() == exe.resolve()
        finally:
            kernel32.CloseHandle(handle)

    windows = []
    duplicate_windows = []
    duplicate = None

    @callback_type
    def inspect(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if is_test_process(pid.value):
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title, len(title))
            if title.value == "Screen Spotlight":
                windows.append(hwnd)
            elif duplicate is not None and title.value == "Screen Spotlight already running":
                duplicate_windows.append(hwnd)
        return True

    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and not windows:
            assert process.poll() is None, f"App exited early: {process.returncode}"
            user32.EnumWindows(inspect, 0)
            time.sleep(0.1)
        assert windows, "Packaged control panel not found"
        print("PASS: Executable copied alone to another folder created its control panel")
        duplicate = subprocess.Popen([str(exe)], startupinfo=startup, cwd=exe.parent)
        deadline = time.monotonic() + 60
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
            subprocess.run(["taskkill", "/PID", str(duplicate.pid), "/T", "/F"], capture_output=True)
            duplicate.wait(timeout=10)
        if process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
