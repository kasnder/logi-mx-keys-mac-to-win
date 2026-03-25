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
- **Auto-detects your Bluetooth keyboard** — swap activates when the MX Keys connects and deactivates when it disconnects
- **Runs silently in the system tray** with a simple toggle

## Requirements

- Windows 10/11
- Python 3.10+
- Logitech MX Keys S for Mac (or any Mac-layout keyboard — see [Configuration](#configuration))

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
| Blue circle | Auto mode, keyboard not connected (waiting) |
| Gray circle | Everything **OFF** |

**Right-click the tray icon** to access:

- **Swap Keys: ON/OFF** — manual toggle (double-click also works)
- **Auto (MX KEYS S MAC): ON/OFF** — auto-enable based on Bluetooth connection
- **Start with Windows: ON/OFF** — launch automatically on login
- **Quit**

## Key Mappings

| Physical Key (Mac Layout) | Without App | With App |
|--------------------------|-------------|----------|
| Command (⌘) | Win key | Alt |
| Option (⌥) | Alt | Win key |
| fn + Lock key | Win+Ctrl+Q (nothing) | Volume Up |
| fn + F12 | Volume Down | Volume Down (unchanged) |

## Configuration

The app auto-detects the **MX KEYS S MAC** keyboard by default. To use with a different Bluetooth keyboard:

1. Find your keyboard's name in Windows Bluetooth settings
2. Edit `%APPDATA%\KeySwitcher\config.json`:
   ```json
   {
     "bt_device_name": "YOUR KEYBOARD NAME",
     "auto_detect": true,
     "poll_interval_seconds": 5
   }
   ```

## How It Works

- Uses a **low-level keyboard hook** (`WH_KEYBOARD_LL`) to intercept and remap keys before any application sees them
- Detects Bluetooth connectivity by checking the **HID Keyboard child device** status via Windows PnP (the BLE parent device always reports "OK" even when disconnected)
- Runs with minimal overhead — the Bluetooth check polls every 5 seconds via PowerShell

## Start with Windows

Toggle "Start with Windows" from the tray menu. This creates a small VBScript launcher in your Windows Startup folder — no registry changes needed. To remove manually:

```
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KeySwitcher.vbs"
```

## License

MIT
