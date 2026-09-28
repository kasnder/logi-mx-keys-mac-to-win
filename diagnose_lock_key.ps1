param([int]$Seconds = 20)

# Records virtual-key and scan codes, not typed characters.
$source = @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;

public static class KeySwitcherLockKeyProbe
{
    private const int WH_KEYBOARD_LL = 13;
    private const uint PM_REMOVE = 1;
    private const uint LLKHF_INJECTED = 0x10;
    private static IntPtr hook;
    private static HookProc callback = OnKey;
    private static bool stop;

    private delegate IntPtr HookProc(int code, IntPtr message, IntPtr data);

    [StructLayout(LayoutKind.Sequential)]
    private struct KeyData
    {
        public uint VirtualKey;
        public uint ScanCode;
        public uint Flags;
        public uint Time;
        public UIntPtr ExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct Point { public int X, Y; }

    [StructLayout(LayoutKind.Sequential)]
    private struct Message
    {
        public IntPtr Window;
        public uint Id;
        public UIntPtr WParam;
        public IntPtr LParam;
        public uint Time;
        public Point Position;
        public uint Private;
    }

    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr SetWindowsHookEx(int kind, HookProc procedure, IntPtr module, uint thread);
    [DllImport("user32.dll")]
    private static extern bool UnhookWindowsHookEx(IntPtr handle);
    [DllImport("user32.dll")]
    private static extern IntPtr CallNextHookEx(IntPtr handle, int code, IntPtr message, IntPtr data);
    [DllImport("user32.dll")]
    private static extern bool PeekMessage(out Message message, IntPtr window, uint min, uint max, uint remove);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr GetModuleHandle(string module);

    private static IntPtr OnKey(int code, IntPtr message, IntPtr data)
    {
        if (code >= 0)
        {
            KeyData key = (KeyData)Marshal.PtrToStructure(data, typeof(KeyData));
            if ((key.Flags & LLKHF_INJECTED) == 0)
            {
                Console.WriteLine("message=0x{0:X4} vk=0x{1:X2} scan=0x{2:X2} flags=0x{3:X2}",
                    message.ToInt64(), key.VirtualKey, key.ScanCode, key.Flags);
                if (key.VirtualKey == 0x1B) stop = true; // Esc
            }
        }
        return CallNextHookEx(hook, code, message, data);
    }

    public static void Run(int seconds)
    {
        stop = false;
        hook = SetWindowsHookEx(WH_KEYBOARD_LL, callback, GetModuleHandle("user32.dll"), 0);
        if (hook == IntPtr.Zero)
            throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
        Console.WriteLine("Press the top-right lock key once, then Esc. Recording key codes for {0} seconds.", seconds);
        try
        {
            Stopwatch timer = Stopwatch.StartNew();
            Message message;
            while (!stop && timer.Elapsed.TotalSeconds < seconds)
            {
                while (PeekMessage(out message, IntPtr.Zero, 0, 0, PM_REMOVE)) { }
                Thread.Sleep(10);
            }
        }
        finally
        {
            UnhookWindowsHookEx(hook);
            hook = IntPtr.Zero;
        }
    }
}
'@

Add-Type -TypeDefinition $source
[KeySwitcherLockKeyProbe]::Run($Seconds)
