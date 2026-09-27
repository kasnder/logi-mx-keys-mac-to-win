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

## Start with Windows

Toggle "Start with Windows" from the tray menu. This creates a small VBScript launcher in your Windows Startup folder — no registry changes needed. To remove manually:

```
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KeySwitcher.vbs"
```

## License

MIT
