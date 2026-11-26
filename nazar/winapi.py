"""The few Windows calls Nazar needs: mouse-wheel input, global hotkeys, DPI, click-through windows."""
import ctypes
import sys
import threading

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    INPUT_MOUSE = 0
    MOUSEEVENTF_WHEEL = 0x0800

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)


def scroll(delta):
    """Send a mouse-wheel movement to the window under the cursor. Positive = up."""
    if not IS_WINDOWS or not delta:
        return
    mi = MOUSEINPUT(0, 0, int(delta) & 0xFFFFFFFF, MOUSEEVENTF_WHEEL, 0, 0)
    inp = INPUT(INPUT_MOUSE, _INPUTUNION(mi=mi))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def make_dpi_aware():
    """So screen sizes are real pixels on scaled (125%, 150%) displays."""
    if not IS_WINDOWS:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def make_click_through(tk_window):
    """Mouse clicks pass straight through this window (for the gaze rail)."""
    if not IS_WINDOWS:
        return
    GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = -20, 0x80000, 0x20, 0x80, 0x08000000
    hwnd = user32.GetParent(tk_window.winfo_id())
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)


MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x1, 0x2, 0x4000


def register_hotkeys(bindings):
    """bindings: list of (modifiers, key letter, callback). Callbacks run on a background thread.
    Returns a list of the hotkeys that could not be registered (already used by another app)."""
    failed = []
    if not IS_WINDOWS:
        return failed
    ready = threading.Event()

    def run():
        for i, (mods, key, _) in enumerate(bindings, start=1):
            if not user32.RegisterHotKey(None, i, mods | MOD_NOREPEAT, ord(key.upper())):
                failed.append(key)
        ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                idx = int(msg.wParam) - 1
                if 0 <= idx < len(bindings):
                    try:
                        bindings[idx][2]()
                    except Exception as e:
                        print("hotkey error:", e)

    threading.Thread(target=run, daemon=True, name="hotkeys").start()
    ready.wait(2)
    return failed
