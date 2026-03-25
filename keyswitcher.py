"""KeySwitcher - Windows tray app to swap Win <-> Alt keys for Mac keyboards."""

import threading
import sys
import os

from PIL import Image, ImageDraw, ImageFont
import pystray

from keyboard_hook import KeyboardHook


def create_icon_image(active: bool) -> Image.Image:
    """Create a simple tray icon indicating active/inactive state."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    bg_color = (76, 175, 80, 255) if active else (158, 158, 158, 255)  # Green or gray
    draw.ellipse([2, 2, size - 2, size - 2], fill=bg_color)

    # Draw "KS" text
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


class KeySwitcherApp:
    def __init__(self):
        self.hook = KeyboardHook()
        self.hook_thread = None
        self.tray_icon = None
        self._active = False

    def _start_hook_thread(self):
        """Start the keyboard hook in a dedicated thread."""
        def run():
            self.hook.install()
            self.hook.run_message_loop()
            self.hook.uninstall()

        self.hook_thread = threading.Thread(target=run, daemon=True)
        self.hook_thread.start()

    def toggle(self, icon=None, item=None):
        """Toggle the key swap on/off."""
        self._active = not self._active
        self.hook.enabled = self._active

        if self.tray_icon:
            self.tray_icon.icon = create_icon_image(self._active)
            self.tray_icon.title = f"KeySwitcher - {'ON' if self._active else 'OFF'}"

    def quit_app(self, icon=None, item=None):
        """Shut down the application."""
        self.hook.enabled = False
        self.hook.stop_message_loop()
        if self.tray_icon:
            self.tray_icon.stop()

    def run(self):
        """Start the tray app."""
        self._start_hook_thread()

        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: f"Swap Keys: {'ON' if self._active else 'OFF'}",
                self.toggle,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit_app),
        )

        self.tray_icon = pystray.Icon(
            name="KeySwitcher",
            icon=create_icon_image(False),
            title="KeySwitcher - OFF",
            menu=menu,
        )

        self.tray_icon.run()


def main():
    app = KeySwitcherApp()
    app.run()


if __name__ == "__main__":
    main()
