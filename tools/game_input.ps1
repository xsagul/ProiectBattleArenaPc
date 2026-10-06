# Real input to the 13.3 test client (the user allowed it on 2026-10-05): right clicks and keys, sent ONLY while the
# game's own window is the foreground window (checked before every action; otherwise the action is skipped and
# logged), so nothing lands in another application.
#
#   game_input.ps1 "<plan>" [log file]
#   plan: steps "seconds:action" separated by ';', seconds counted from when the game window first appears:
#     rclick:x,y      right click at x,y of the game's 1920x1080 frame (scaled to the window's client area)
#     click:x,y       left click there
#     key:w           a key (q w e r d f b y p esc space ctrl), key:ctrl+w for a combination
#     move:x,y        the cursor to x,y (no click; spells aim at the cursor)
#   e.g. "14:rclick:1080,470;17:key:w"
param([string]$plan, [string]$log = "")
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class GI {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr extra; }
    [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT { public int dx; public int dy; public uint data; public uint dwFlags; public uint time; public IntPtr extra; }
    // INPUT = { DWORD type; union { MOUSEINPUT, KEYBDINPUT, HARDWAREINPUT } }: the union sits at offset 8 on 64-bit
    // (4 on 32-bit) and the whole struct is 40 bytes (28); SendInput refuses (returns 0) a wrong size
    [StructLayout(LayoutKind.Explicit)] public struct UNION { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; }
    [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public UNION u; }
    [DllImport("user32.dll")] public static extern uint SendInput(uint n, INPUT[] inputs, int size);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, IntPtr extra);
    public static void Key(ushort scan, bool up) {
        INPUT[] i = new INPUT[1];
        i[0].type = 1; i[0].u.ki.wScan = scan; i[0].u.ki.dwFlags = 0x0008u | (up ? 0x0002u : 0u);
        Last = SendInput(1, i, Marshal.SizeOf(typeof(INPUT)));
    }
    public static uint Last;
    public static void Mouse(uint flags) {
        INPUT[] i = new INPUT[1];
        i[0].type = 0; i[0].u.mi.dwFlags = flags;
        Last = SendInput(1, i, Marshal.SizeOf(typeof(INPUT)));
    }
}
"@
$scan = @{ 'q' = 0x10; 'w' = 0x11; 'e' = 0x12; 'r' = 0x13; 'd' = 0x20; 'f' = 0x21; 'b' = 0x30; 'ctrl' = 0x1d; 'y' = 0x15; 'space' = 0x39; 'esc' = 0x01; 'p' = 0x19 }
function Say($m) { $line = ("{0:N2}s {1}" -f ((Get-Date) - $script:t0).TotalSeconds, $m); Write-Output $line; if ($log) { Add-Content $log $line } }
$script:t0 = Get-Date
$proc = $null
while (-not $proc -or $proc.MainWindowHandle -eq 0) {
    Start-Sleep -Milliseconds 200
    $proc = Get-Process -Name "League of Legends.unpacked" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (((Get-Date) - $script:t0).TotalSeconds -gt 60) { Say "no game window"; exit 1 }
}
$h = $proc.MainWindowHandle
$script:t0 = Get-Date
$path = try { $proc.Path } catch { "?" }
Say ("game window {0} (pid {1}, path readable: {2})" -f $h, $proc.Id, [bool]$path)
function Front {
    if ([GI]::GetForegroundWindow() -eq $h) { return $true }
    [GI]::keybd_event(0x12, 0, 0, [IntPtr]::Zero); [GI]::keybd_event(0x12, 0, 2, [IntPtr]::Zero)   # Alt lets SetForegroundWindow through
    [GI]::ShowWindow($h, 5) | Out-Null
    [GI]::SetForegroundWindow($h) | Out-Null
    Start-Sleep -Milliseconds 150
    return ([GI]::GetForegroundWindow() -eq $h)
}
foreach ($step in $plan.Split(';')) {
    $at, $kind, $arg = $step.Split(':', 3)
    while (((Get-Date) - $script:t0).TotalSeconds -lt [double]$at) { Start-Sleep -Milliseconds 30 }
    if (-not (Front)) { Say "SKIPPED $kind $arg (the game is not the foreground window)"; continue }
    if ($kind -eq 'rclick' -or $kind -eq 'click') {
        $x, $y = $arg.Split(',')
        $r = New-Object GI+RECT; [GI]::GetClientRect($h, [ref]$r) | Out-Null
        $p = New-Object GI+POINT
        $p.X = [int]([double]$x * ($r.R - $r.L) / 1920); $p.Y = [int]([double]$y * ($r.B - $r.T) / 1080)
        [GI]::ClientToScreen($h, [ref]$p) | Out-Null
        [GI]::SetCursorPos($p.X, $p.Y) | Out-Null
        Start-Sleep -Milliseconds 60
        if ([GI]::GetForegroundWindow() -ne $h) { Say "SKIPPED click (focus lost)"; continue }
        if ($kind -eq 'click') { [GI]::Mouse(0x0002); Start-Sleep -Milliseconds 50; [GI]::Mouse(0x0004) }
        else { [GI]::Mouse(0x0008); Start-Sleep -Milliseconds 50; [GI]::Mouse(0x0010) }
        Say ("$kind at {0},{1} (screen {2},{3}, client {4}x{5}), SendInput {6}" -f $x, $y, $p.X, $p.Y, ($r.R - $r.L), ($r.B - $r.T), [GI]::Last)
    } elseif ($kind -eq 'move') {
        $x, $y = $arg.Split(',')
        $r = New-Object GI+RECT; [GI]::GetClientRect($h, [ref]$r) | Out-Null
        $p = New-Object GI+POINT
        $p.X = [int]([double]$x * ($r.R - $r.L) / 1920); $p.Y = [int]([double]$y * ($r.B - $r.T) / 1080)
        [GI]::ClientToScreen($h, [ref]$p) | Out-Null
        [GI]::SetCursorPos($p.X, $p.Y) | Out-Null
        Say ("cursor at {0},{1}" -f $x, $y)
    } elseif ($kind -eq 'key') {
        $keys = $arg.Split('+')
        foreach ($k in $keys) { [GI]::Key($scan[$k], $false); Start-Sleep -Milliseconds 30 }
        Start-Sleep -Milliseconds 60
        [array]::Reverse($keys)
        foreach ($k in $keys) { [GI]::Key($scan[$k], $true); Start-Sleep -Milliseconds 30 }
        Say "key $arg, SendInput $([GI]::Last)"
    }
}
