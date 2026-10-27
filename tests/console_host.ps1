param([string]$Launcher, [string]$Result)
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class GGConsoleProbe {
    [StructLayout(LayoutKind.Sequential)] public struct Coord { public short X, Y; }
    [StructLayout(LayoutKind.Sequential)] public struct Rect { public short Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] public struct Info {
        public Coord Size, Cursor;
        public short Attributes;
        public Rect Window;
        public Coord Maximum;
    }
    [DllImport("kernel32.dll")] public static extern IntPtr GetStdHandle(int n);
    [DllImport("kernel32.dll")] public static extern bool GetConsoleMode(IntPtr h, out uint m);
    [DllImport("kernel32.dll")] public static extern bool SetConsoleMode(IntPtr h, uint m);
    [DllImport("kernel32.dll")] public static extern bool GetConsoleScreenBufferInfo(IntPtr h, out Info i);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)]
    public static extern bool ReadConsoleOutputCharacterW(IntPtr h, StringBuilder b,
        uint n, Coord p, out uint read);
    [DllImport("kernel32.dll")]
    public static extern bool ReadConsoleOutputAttribute(IntPtr h, ushort[] attributes,
        uint n, Coord p, out uint read);
}
'@
$handle = [GGConsoleProbe]::GetStdHandle(-11)
$mode = [uint32]0
if (-not [GGConsoleProbe]::GetConsoleMode($handle, [ref]$mode)) { throw 'no console stdout' }
$withoutVt = $mode -band (-bnot 4)
if (-not [GGConsoleProbe]::SetConsoleMode($handle, $withoutVt)) { throw 'cannot clear VT mode' }
$previousNoColor = $env:NO_COLOR
$previousGGColor = $env:GG_COLOR
$previousForeground = [Console]::ForegroundColor
$previousBackground = [Console]::BackgroundColor
try {
    $env:NO_COLOR = $null
    $env:GG_COLOR = $null
    [Console]::BackgroundColor = 'DarkBlue'
    [Console]::ForegroundColor = 'Gray'
    [Console]::Clear()
    & $Launcher --width 12 cat
    $attributes = New-Object UInt16[] 1
    $read = [uint32]0
    $borderPosition = New-Object GGConsoleProbe+Coord
    $borderPosition.Y = 1
    if (-not [GGConsoleProbe]::ReadConsoleOutputAttribute($handle, $attributes, 1,
        $borderPosition, [ref]$read)) { throw 'cannot read divider color' }
    $defaultDividerForeground = ($attributes[0] -band 15) -eq 7
    [Console]::Clear()
    & $Launcher --box --width 12 BOX
    $borderPosition.Y = 0
    if (-not [GGConsoleProbe]::ReadConsoleOutputAttribute($handle, $attributes, 1,
        $borderPosition, [ref]$read)) { throw 'cannot read frame color' }
    $defaultBoxForeground = ($attributes[0] -band 15) -eq 7
    $env:NO_COLOR = $previousNoColor
    $env:GG_COLOR = $previousGGColor
    [Console]::Clear()
    & $Launcher --width 12 --force-color TEST
    & $Launcher --box --width 12 --force-color BOX
    $after = [uint32]0
    [void][GGConsoleProbe]::GetConsoleMode($handle, [ref]$after)
    $info = New-Object GGConsoleProbe+Info
    [void][GGConsoleProbe]::GetConsoleScreenBufferInfo($handle, [ref]$info)
    $count = [uint32]($info.Size.X * ($info.Cursor.Y + 1))
    $buffer = New-Object System.Text.StringBuilder -ArgumentList ([int]$count)
    $read = [uint32]0
    $origin = New-Object GGConsoleProbe+Coord
    if (-not [GGConsoleProbe]::ReadConsoleOutputCharacterW($handle, $buffer, $count,
        $origin, [ref]$read)) { throw 'cannot read console screen' }
    $file = [IO.File]::OpenWrite($Result + '.out')
    try {
        $fileMode = [uint32]0
        $fileHasConsoleMode = [GGConsoleProbe]::GetConsoleMode(
            $file.SafeFileHandle.DangerousGetHandle(), [ref]$fileMode)
    } finally { $file.Dispose() }
    $report = [ordered]@{
        initial = $withoutVt
        after = $after
        divider = $buffer.ToString().Contains([string][char]0x2550)
        box = $buffer.ToString().Contains([string][char]0x2554)
        rawEscape = $buffer.ToString().Contains([string][char]27)
        fileHasConsoleMode = $fileHasConsoleMode
        defaultDividerForeground = $defaultDividerForeground
        defaultBoxForeground = $defaultBoxForeground
    }
    [IO.File]::WriteAllText($Result, ($report | ConvertTo-Json -Compress), [Text.UTF8Encoding]::new($false))
} finally {
    $env:NO_COLOR = $previousNoColor
    $env:GG_COLOR = $previousGGColor
    [Console]::ForegroundColor = $previousForeground
    [Console]::BackgroundColor = $previousBackground
    [void][GGConsoleProbe]::SetConsoleMode($handle, $mode)
}
