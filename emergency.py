"""Independent Escape hold monitor; never accesses Qt from its worker thread."""
import ctypes
import os
import sys
import threading
import time


class EmergencyExit:
    def __init__(self, key_down=None, terminate=None):
        self.active = threading.Event()
        self.stopped = threading.Event()
        self.held_since = None
        self.thread = None
        self.terminate = terminate or (lambda: os._exit(2))
        if key_down is not None:
            self.key_down = key_down
        elif sys.platform == "win32":
            self.user32 = ctypes.WinDLL("user32", use_last_error=True)
            self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
            self.user32.GetAsyncKeyState.restype = ctypes.c_short
            self.key_down = lambda: bool(self.user32.GetAsyncKeyState(0x1B) & 0x8000)
        else:
            self.key_down = lambda: False

    def check(self, now):
        if not self.active.is_set() or not self.key_down():
            self.held_since = None
        elif self.held_since is None:
            self.held_since = now
        elif now - self.held_since >= 2.0:
            self.active.clear()
            self.terminate()

    def run(self):
        while not self.stopped.wait(0.05):
            self.check(time.monotonic())

    def start(self):
        self.thread = threading.Thread(target=self.run, name="spotlight-emergency-exit", daemon=True)
        self.thread.start()

    def stop(self):
        self.active.clear()
        self.stopped.set()
        if self.thread:
            self.thread.join(timeout=0.2)
