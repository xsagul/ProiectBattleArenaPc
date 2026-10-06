# Presses keys in the foreground window (the 13.3 client in a run_match.sh test) the way a real keyboard does
# (SendInput with scan codes). Moves nothing but the keyboard; the game must be the foreground window.
#
#   press_keys.ps1 "14:ctrl+q;16:q"     at 14 s after start Ctrl+Q, at 16 s Q
#   press_keys.ps1 "14:ctrl+q;16:q" <unix time>   the seconds count from that moment instead (PowerShell itself
#                                                 takes a few seconds to start, more the first time)
param([string]$plan, [double]$since = 0)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Keys {
    [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr extra; }
    [StructLayout(LayoutKind.Explicit, Size = 28)] public struct INPUT { [FieldOffset(0)] public uint type; [FieldOffset(4)] public KEYBDINPUT ki; }
    [DllImport("user32.dll")] public static extern uint SendInput(uint n, INPUT[] inputs, int size);
    public static void Scan(ushort scan, bool up) {
        INPUT[] i = new INPUT[1];
        i[0].type = 1;
        i[0].ki.wScan = scan;
        i[0].ki.dwFlags = 0x0008u | (up ? 0x0002u : 0u);
        SendInput(1, i, Marshal.SizeOf(typeof(INPUT)));
    }
}
"@
$scan = @{ 'q' = 0x10; 'w' = 0x11; 'e' = 0x12; 'r' = 0x13; 'ctrl' = 0x1d }
$t0 = Get-Date
if ($since -gt 0) { $t0 = [DateTimeOffset]::FromUnixTimeMilliseconds([long]($since * 1000)).LocalDateTime }
foreach ($step in $plan.Split(';')) {
    $at, $combo = $step.Split(':')
    while (((Get-Date) - $t0).TotalSeconds -lt [double]$at) { Start-Sleep -Milliseconds 50 }
    $keys = $combo.Split('+')
    foreach ($k in $keys) { [Keys]::Scan($scan[$k], $false); Start-Sleep -Milliseconds 30 }
    Start-Sleep -Milliseconds 60
    [array]::Reverse($keys)
    foreach ($k in $keys) { [Keys]::Scan($scan[$k], $true); Start-Sleep -Milliseconds 30 }
    Write-Output ("{0:N1}s {1}" -f ((Get-Date) - $t0).TotalSeconds, $combo)
}
