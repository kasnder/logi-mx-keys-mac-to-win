"""KeySwitcher - Windows tray app to swap Win <-> Alt keys for Mac keyboards."""

import json
import os
import subprocess
import sys
import threading
import time

from PIL import Image, ImageDraw, ImageFont
import pystray

from keyboard_hook import KeyboardHook

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", ""), "KeySwitcher")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "bt_device_name": "MX KEYS S MAC",
    "auto_detect": True,
    "poll_interval_seconds": 5,
}


def load_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        # Merge with defaults for any missing keys
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    # First run - write defaults
    save_config(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def is_bt_device_connected(device_name: str) -> bool:
    """Check if a Bluetooth device is connected via PowerShell/PnP."""
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                f"(Get-PnpDevice -FriendlyName '{device_name}' -ErrorAction SilentlyContinue).Status",
            ],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.stdout.strip() == "OK"
    except Exception:
        return False


def create_icon_image(active: bool, auto: bool = False) -> Image.Image:
    """Create a tray icon. Green=ON, Gray=OFF, Blue=AUTO."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if active:
        bg_color = (76, 175, 80, 255)    # Green
    elif auto:
        bg_color = (33, 150, 243, 255)   # Blue (auto mode, waiting)
    else:
        bg_color = (158, 158, 158, 255)  # Gray
    draw.ellipse([2, 2, size - 2, size - 2], fill=bg_color)

    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except (OSError, IOError):
        font = ImageFont.load_default()

    text = "KS"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2
    y = (size - th) // 2 - 2
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    return img


# --- Startup management ---

def _get_startup_folder():
    return os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def _get_vbs_path():
    return os.path.join(_get_startup_folder(), "KeySwitcher.vbs")


def is_startup_enabled():
    return os.path.exists(_get_vbs_path())


def enable_startup():
    """Create a VBScript in the Startup folder that launches keyswitcher silently."""
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    vbs_content = (
        f'Set WshShell = CreateObject("WScript.Shell")\n'
        f'WshShell.Run """{python_path}"" ""{script_path}""", 0, False\n'
    )
    vbs_path = _get_vbs_path()
    with open(vbs_path, "w") as f:
        f.write(vbs_content)


def disable_startup():
    vbs_path = _get_vbs_path()
    if os.path.exists(vbs_path):
        os.remove(vbs_path)


class KeySwitcherApp:
    def __init__(self):
        self.hook = KeyboardHook()
        self.hook_thread = None
        self.tray_icon = None
        self._active = False
        self._auto_mode = True
        self._bt_poll_thread = None
        self._running = True
        self.config = load_config()

    def _start_hook_thread(self):
        def run():
            self.hook.install()
            self.hook.run_message_loop()
            self.hook.uninstall()

        self.hook_thread = threading.Thread(target=run, daemon=True)
        self.hook_thread.start()

    def _set_active(self, active: bool):
        """Set the swap state and update the tray icon."""
        self._active = active
        self.hook.enabled = active
        self._update_icon()

    def _update_icon(self):
        if self.tray_icon:
            self.tray_icon.icon = create_icon_image(self._active, self._auto_mode)
            status = "ON" if self._active else "OFF"
            mode = " (Auto)" if self._auto_mode else ""
            self.tray_icon.title = f"KeySwitcher - {status}{mode}"

    def toggle(self, icon=None, item=None):
        """Manual toggle — disables auto mode."""
        if self._auto_mode:
            self._auto_mode = False
        self._set_active(not self._active)

    def toggle_auto(self, icon=None, item=None):
        """Toggle Bluetooth auto-detection mode."""
        self._auto_mode = not self._auto_mode
        if self._auto_mode:
            # Immediately check current state
            connected = is_bt_device_connected(self.config["bt_device_name"])
            self._set_active(connected)
        self._update_icon()

    def toggle_startup(self, icon=None, item=None):
        if is_startup_enabled():
            disable_startup()
        else:
            enable_startup()

    def _bt_poll_loop(self):
        """Background thread that polls Bluetooth device status."""
        while self._running:
            if self._auto_mode:
                connected = is_bt_device_connected(self.config["bt_device_name"])
                if connected != self._active:
                    self._set_active(connected)
            time.sleep(self.config.get("poll_interval_seconds", 5))

    def quit_app(self, icon=None, item=None):
        self._running = False
        self.hook.enabled = False
        self.hook.stop_message_loop()
        if self.tray_icon:
            self.tray_icon.stop()

    def run(self):
        self._start_hook_thread()

        # Start Bluetooth polling thread
        self._bt_poll_thread = threading.Thread(target=self._bt_poll_loop, daemon=True)
        self._bt_poll_thread.start()

        # Check keyboard state immediately on startup
        connected = is_bt_device_connected(self.config["bt_device_name"])
        self._set_active(connected)

        device_name = self.config["bt_device_name"]

        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: f"Swap Keys: {'ON' if self._active else 'OFF'}",
                self.toggle,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: f"Auto ({device_name}): {'ON' if self._auto_mode else 'OFF'}",
                self.toggle_auto,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: f"Start with Windows: {'ON' if is_startup_enabled() else 'OFF'}",
                self.toggle_startup,
            ),
            pystray.MenuItem("Quit", self.quit_app),
        )

        self.tray_icon = pystray.Icon(
            name="KeySwitcher",
            icon=create_icon_image(self._active, self._auto_mode),
            title="KeySwitcher - OFF",
            menu=menu,
        )

        self.tray_icon.run()


def main():
    app = KeySwitcherApp()
    app.run()


if __name__ == "__main__":
    main()
