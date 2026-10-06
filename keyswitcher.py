"""KeySwitcher - Windows tray app to swap Win <-> Alt keys for Mac keyboards."""

import os
import sys
import threading

from PIL import Image, ImageDraw, ImageFont
import pystray

from keyboard_hook import KeyboardHook
from logitech_lock import LockKeyListener
from logitech_backlight import BacklightController

def create_icon_image(active: bool) -> Image.Image:
    """Create a tray icon. Green=ON, Gray=OFF."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if active:
        bg_color = (76, 175, 80, 255)    # Green
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
        self.lock_listener = LockKeyListener(enabled=lambda: self.hook.enabled)
        self.backlight = BacklightController(self._refresh_menu)

    def _refresh_menu(self):
        if self.tray_icon:
            self.tray_icon.update_menu()

    def _backlight_items(self):
        controller = self.backlight
        state = controller.state
        def choice(label, field, value, selected):
            def apply(icon, item):
                controller.request(field, value)
            return pystray.MenuItem(label, apply, checked=lambda item: selected,
                                    radio=True, enabled=lambda item: not controller.busy)
        if state:
            for label, value in [('Off', -1), ('Automatic', 1), ('Manual', 3)]:
                if value == -1 or state.supported & (8 if value == 1 else 32):
                    yield choice(label, 'mode', value, state.mode == value)
            if state.supported & 32 and controller.levels:
                yield pystray.MenuItem('Brightness (selecting enables manual mode)', pystray.Menu(*[
                    choice(str(n), 'level', n, state.level == n and state.mode == 3)
                    for n in range(controller.levels)]))
            for label, field in [('Hands away timeout', 'hands_away'), ('Hands nearby timeout', 'hands_near'), ('USB power timeout', 'powered')]:
                seconds = getattr(state, field) * 5
                values = sorted(set([5, 15, 30, 60, 120, 300, 600, seconds]))
                yield pystray.MenuItem(f'{label}: {seconds}s', pystray.Menu(*[
                    choice(f'{n} seconds', field, n, seconds == n) for n in values if 5 <= n <= 600]))
        else:
            yield pystray.MenuItem(controller.status, None, enabled=False)
        yield pystray.Menu.SEPARATOR
        yield pystray.MenuItem('Refresh from keyboard', lambda icon, item: controller.request(),
                               enabled=lambda item: not controller.busy)

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
            self.tray_icon.icon = create_icon_image(self._active)
            status = "ON" if self._active else "OFF"
            self.tray_icon.title = f"KeySwitcher - {status}"

    def toggle(self, icon=None, item=None):
        """Toggle swapping until the next launch."""
        self._set_active(not self._active)

    def toggle_startup(self, icon=None, item=None):
        if is_startup_enabled():
            disable_startup()
        else:
            enable_startup()

    def quit_app(self, icon=None, item=None):
        self.hook.enabled = False
        self.lock_listener.stop()
        self.hook.stop_message_loop()
        if self.tray_icon:
            self.tray_icon.stop()

    def run(self):
        self._start_hook_thread()
        self._set_active(True)
        self.lock_listener.start()

        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: f"Swap Keys: {'ON' if self._active else 'OFF'}",
                self.toggle,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Backlight', pystray.Menu(self._backlight_items)),
            pystray.MenuItem(
                lambda item: f"Start with Windows: {'ON' if is_startup_enabled() else 'OFF'}",
                self.toggle_startup,
            ),
            pystray.MenuItem("Quit", self.quit_app),
        )

        self.tray_icon = pystray.Icon(
            name="KeySwitcher",
            icon=create_icon_image(self._active),
            title=f"KeySwitcher - {'ON' if self._active else 'OFF'}",
            menu=menu,
        )

        try:
            self.backlight.request()
            self.tray_icon.run()
        finally:
            self.lock_listener.stop()


def main():
    app = KeySwitcherApp()
    app.run()


if __name__ == "__main__":
    main()
