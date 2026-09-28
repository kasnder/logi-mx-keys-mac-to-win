param([int]$Seconds = 20)

# Shows device codes and raw HID bytes, not typed characters.
Add-Type -AssemblyName System.Windows.Forms
$source = @'
using System;
using System.Runtime.InteropServices;
using System.Windows.Forms;

public sealed class KeySwitcherRawLockProbe : Form
{
    private const int WM_INPUT = 0x00FF;
    private const uint RID_INPUT = 0x10000003;
    private const uint RIDEV_INPUTSINK = 0x00000100;
    private const uint RIDEV_PAGEONLY = 0x00000020;
    private readonly Timer timer = new Timer();

    [StructLayout(LayoutKind.Sequential)]
    private struct RawInputDevice
    {
        public ushort UsagePage;
        public ushort Usage;
        public uint Flags;
        public IntPtr Target;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct RawInputHeader
    {
        public uint Type;
        public uint Size;
        public IntPtr Device;
        public IntPtr WParam;
    }

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RegisterRawInputDevices(
        RawInputDevice[] devices, uint count, uint size);
    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint GetRawInputData(
        IntPtr input, uint command, IntPtr data, ref uint size, uint headerSize);

    private KeySwitcherRawLockProbe(int seconds)
    {
        ShowInTaskbar = false;
        FormBorderStyle = FormBorderStyle.None;
        Opacity = 0;
        Width = 1;
        Height = 1;
        Shown += (sender, args) =>
        {
            Register(0x01, 0x06, RIDEV_INPUTSINK, "keyboard");
            Register(0x0C, 0x01, RIDEV_INPUTSINK, "consumer");
            Register(0xFF00, 0x00, RIDEV_INPUTSINK | RIDEV_PAGEONLY, "Logitech vendor");
            Console.WriteLine("READY: press an ordinary key, then the top-right lock key once.");
            timer.Interval = Math.Max(1, seconds) * 1000;
            timer.Tick += (s, e) => Close();
            timer.Start();
        };
    }

    private void Register(ushort page, ushort usage, uint flags, string label)
    {
        var devices = new[] {
            new RawInputDevice { UsagePage = page, Usage = usage, Flags = flags, Target = Handle }
        };
        if (RegisterRawInputDevices(devices, 1, (uint)Marshal.SizeOf(typeof(RawInputDevice))))
            Console.WriteLine("Listening: {0} (page=0x{1:X4}, usage=0x{2:X4})", label, page, usage);
        else
            Console.WriteLine("Could not listen to {0}: Windows error {1}",
                label, Marshal.GetLastWin32Error());
    }

    protected override void WndProc(ref Message message)
    {
        if (message.Msg == WM_INPUT)
            ReadInput(message.LParam);
        base.WndProc(ref message);
    }

    private static void ReadInput(IntPtr input)
    {
        uint size = 0;
        uint headerSize = (uint)Marshal.SizeOf(typeof(RawInputHeader));
        if (GetRawInputData(input, RID_INPUT, IntPtr.Zero, ref size, headerSize) == unchecked((uint)-1))
            return;
        IntPtr data = Marshal.AllocHGlobal((int)size);
        try
        {
            if (GetRawInputData(input, RID_INPUT, data, ref size, headerSize) == unchecked((uint)-1))
                return;
            int kind = Marshal.ReadInt32(data, 0);
            IntPtr device = Marshal.ReadIntPtr(data, 8);
            int offset = (int)headerSize;
            if (kind == 1 && size >= offset + 16)
            {
                int scan = (ushort)Marshal.ReadInt16(data, offset);
                int vk = (ushort)Marshal.ReadInt16(data, offset + 6);
                int flags = (ushort)Marshal.ReadInt16(data, offset + 2);
                Console.WriteLine("KEYBOARD device={0} vk=0x{1:X2} scan=0x{2:X2} flags=0x{3:X2}",
                    device, vk, scan, flags);
            }
            else if (kind == 2 && size >= offset + 8)
            {
                int reportSize = Marshal.ReadInt32(data, offset);
                int count = Marshal.ReadInt32(data, offset + 4);
                long total = (long)reportSize * count;
                if (total > 0 && total <= 256 && size >= offset + 8 + total)
                {
                    byte[] report = new byte[(int)total];
                    Marshal.Copy(IntPtr.Add(data, offset + 8), report, 0, report.Length);
                    Console.WriteLine("HID device={0} report={1}",
                        device, BitConverter.ToString(report));
                }
            }
        }
        finally { Marshal.FreeHGlobal(data); }
    }

    public static void Run(int seconds)
    {
        Application.Run(new KeySwitcherRawLockProbe(seconds));
    }
}
'@

Add-Type -TypeDefinition $source -ReferencedAssemblies System.Windows.Forms
[KeySwitcherRawLockProbe]::Run($Seconds)
