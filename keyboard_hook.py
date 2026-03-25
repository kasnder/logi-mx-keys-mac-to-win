"""Low-level keyboard hook to swap Win <-> Alt keys."""

import ctypes
import ctypes.wintypes as wintypes
from ctypes import CFUNCTYPE, c_int

# Virtual key codes
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_LMENU = 0xA4  # Left Alt
VK_RMENU = 0xA5  # Right Alt

# Scan codes
SC_LWIN = 0x5B
SC_RWIN = 0x5C
SC_LALT = 0x38
SC_RALT = 0x38

# Hook constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

# Flags
LLKHF_INJECTED = 0x00000010
LLKHF_EXTENDED = 0x00000001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

# Win32 API
user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

HOOKPROC = CFUNCTYPE(ctypes.c_long, c_int, wintypes.WPARAM, wintypes.LPARAM)

ULONG_PTR = ctypes.c_uint64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_uint32


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('vkCode', wintypes.DWORD),
        ('scanCode', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ULONG_PTR),
    ]


# --- INPUT structures (all union members needed for correct sizeof) ---

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', ctypes.c_long),
        ('dy', ctypes.c_long),
        ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wintypes.WORD),
        ('wScan', wintypes.WORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ('uMsg', wintypes.DWORD),
        ('wParamL', wintypes.WORD),
        ('wParamH', wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ('mi', MOUSEINPUT),
        ('ki', KEYBDINPUT),
        ('hi', HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ('type', wintypes.DWORD),
        ('union', INPUT_UNION),
    ]


# Configure API signatures
user32.SetWindowsHookExW.argtypes = [c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = ctypes.c_void_p

user32.CallNextHookEx.argtypes = [ctypes.c_void_p, c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_long

user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL

user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL

user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), c_int]
user32.SendInput.restype = wintypes.UINT


def send_key(vk, scan, is_up, extended=False):
    """Send a synthetic key event."""
    inp = INPUT()
    inp.type = 1  # INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = scan
    inp.union.ki.dwFlags = 0
    if is_up:
        inp.union.ki.dwFlags |= KEYEVENTF_KEYUP
    if extended:
        inp.union.ki.dwFlags |= KEYEVENTF_EXTENDEDKEY
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = 0
    result = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    return result


class KeyboardHook:
    """Installs a low-level keyboard hook that swaps Win and Alt keys."""

    def __init__(self):
        self._hook = None
        self._thread_id = None
        self._enabled = False
        self._callback = HOOKPROC(self._hook_proc)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    def _hook_proc(self, nCode, wParam, lParam):
        """Low-level keyboard hook callback."""
        if nCode >= 0 and self._enabled:
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            vk = kb.vkCode
            flags = kb.flags

            # Skip injected events (from SendInput) to avoid infinite loop
            if flags & LLKHF_INJECTED:
                return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

            is_up = wParam in (WM_KEYUP, WM_SYSKEYUP)
            is_extended = bool(flags & LLKHF_EXTENDED)

            # Left Win -> Left Alt
            if vk == VK_LWIN:
                send_key(VK_LMENU, SC_LALT, is_up, extended=False)
                return 1

            # Left Alt -> Left Win
            if vk == VK_LMENU and not is_extended:
                send_key(VK_LWIN, SC_LWIN, is_up, extended=True)
                return 1

            # Right Win -> Right Alt
            if vk == VK_RWIN:
                send_key(VK_RMENU, SC_RALT, is_up, extended=True)
                return 1

            # Right Alt -> Right Win
            if vk == VK_RMENU:
                send_key(VK_RWIN, SC_RWIN, is_up, extended=True)
                return 1

        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def install(self):
        """Install the keyboard hook. Must be called from the hook thread."""
        h_mod = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._callback, h_mod, 0)
        if not self._hook:
            raise ctypes.WinError(ctypes.get_last_error())

    def uninstall(self):
        """Remove the keyboard hook."""
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None

    def run_message_loop(self):
        """Run the Windows message loop (required for hooks to work)."""
        self._thread_id = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0012:  # WM_QUIT
                break

    def stop_message_loop(self):
        """Stop the message loop from another thread."""
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
