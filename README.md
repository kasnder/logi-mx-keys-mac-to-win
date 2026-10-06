# Logi MX Keys S MAC → Windows Key Remapper

A lightweight Windows system tray app that makes your **Logitech MX Keys S for Mac** keyboard work properly on Windows by swapping the Command and Option keys and fixing missing media key functionality.

## The Problem

When using a Mac-layout keyboard on Windows:

- The **Command key** acts as the **Windows key** — but on a Mac layout, it sits where Alt should be
- The **Option key** acts as **Alt** — but it sits where the Windows key should be
- The **fn + lock key** (volume up position) sends `Win+Ctrl+Q` instead of Volume Up

## What This App Does

- **Swaps Command ↔ Option** so the keys behave like a standard Windows layout
- **Maps fn + lock key → Volume Up** so your volume controls work correctly
- **Corrects the ^ and < key positions** on the Mac ISO keyboard with a German Windows layout
- **Locks Windows from the Mini's top-right special key** — supported on MX Keys Mini for Mac via Logi Bolt
- **Enables swapping when the app starts** — works with Bluetooth or a Logi Bolt receiver
- **Runs silently in the system tray** with a simple toggle

## Requirements

- Windows 10/11
- Python 3.10+
- Logitech MX Keys S for Mac (or another Mac-layout keyboard)

## Installation

1. **Clone this repo**
   ```
   git clone https://github.com/shirgans/logi-mx-keys-mac-to-win.git
   cd logi-mx-keys-mac-to-win
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Run**
   ```
   python keyswitcher.py
   ```

## Usage

The app runs in the **system tray** (bottom-right of your taskbar):

| Icon | Meaning |
|------|---------|
| Green circle | Swap is **ON** |
| Gray circle | Swap is **OFF** |

**Right-click the tray icon** to access:

- **Swap Keys: ON/OFF** — manual toggle (double-click also works); swapping turns on again when the app starts
- **Start with Windows: ON/OFF** — launch automatically on login
- **Quit**

### Backlight controls

The **Backlight** tray submenu controls the MX Keys Mini for Mac over Logi Bolt:

- Off, Automatic, or Manual illumination.
- Brightness levels reported by the keyboard (0–7 on the tested Mini). Selecting a level enables Manual mode.
- Separate timeouts for hands away, hands nearby, and USB power, from 5 seconds to 10 minutes.
- **Refresh from keyboard** reads current values, including changes made outside this app. Wake a sleeping keyboard before refreshing.

Settings are read when the app starts. Changes are written directly to the keyboard and read back for verification; the app does not override them at startup or periodically reapply them. Firmware determines whether they survive a power cycle. Backlight controls work independently of the key-swap toggle. Existing timeouts are preserved when changing brightness or mode.

## Key Mappings

| Physical Key (Mac Layout) | Without App | With App |
|--------------------------|-------------|----------|
| Command (⌘) | Win key | Alt |
| Option (⌥) | Alt | Win key |
| ^ key (left of 1) | < key position | ^ key position |
| < key (right of left Shift) | ^ key position | < key position |
| fn + Lock key | Win+Ctrl+Q (nothing) | Volume Up |
| fn + F12 | Volume Down | Volume Down (unchanged) |

## How It Works

- Uses a **low-level keyboard hook** (`WH_KEYBOARD_LL`) to intercept and remap keys before any application sees them
- Swaps the two ISO scan codes so Shift and the selected Windows keyboard layout still determine the typed character
- Swapping is on while the app runs, unless you turn it off with the tray icon

### MX Keys Mini for Mac lock key

The Mini's top-right Do Not Disturb/lock key is a Logitech special control that the ordinary Windows keyboard hook cannot see. Through a Logi Bolt receiver, the app enables temporary HID++ reporting for that single button and calls Windows' lock function once per press. It restores the button's previous reporting setting when you turn swapping off or quit the app. Restarting the app enables it again.

This special-button support currently targets the **MX Keys Mini for Mac over Bolt**. The regular key swaps remain independent of how the keyboard connects. After updating, run `python -m pip install -r requirements.txt` to install the HID library used for the lock button.

## Start with Windows

Toggle "Start with Windows" from the tray menu. This creates a small VBScript launcher in your Windows Startup folder — no registry changes needed. To remove manually:

```
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KeySwitcher.vbs"
```

## Acknowledgements

Thanks to [Solaar](https://github.com/pwr-Solaar/Solaar) and its contributors for documenting and implementing Logitech's HID++ protocol. Solaar's [device capability documentation](https://pwr-solaar.github.io/Solaar/capabilities/) and source code were valuable references for this project's special-key handling and BACKLIGHT2 illumination controls, including brightness modes and timeout settings.

## License

MIT
