# PowerShell shell adapter. Rust is the sole implementation of --box/--table.
$ErrorActionPreference = 'Stop'
if (-not ('GGConsoleMode' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class GGConsoleMode {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern IntPtr GetStdHandle(int handle);
    [DllImport("kernel32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool GetConsoleMode(IntPtr handle, out uint mode);
    [DllImport("kernel32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool SetConsoleMode(IntPtr handle, uint mode);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool WriteConsoleW(IntPtr handle, string value, uint length, out uint written, IntPtr reserved);
}
'@
}
function Test-GGVirtualTerminal {
    if ([Console]::IsOutputRedirected) { return $false }
    $handle = [GGConsoleMode]::GetStdHandle(-11)
    $mode = [uint32]0
    if ($handle -eq [IntPtr]::Zero -or $handle -eq [IntPtr](-1) -or
        -not [GGConsoleMode]::GetConsoleMode($handle, [ref]$mode)) { return $false }
    if (($mode -band 4) -ne 0) { return $true }
    if (-not [GGConsoleMode]::SetConsoleMode($handle, ($mode -bor 4))) { return $false }
    $verified = [uint32]0
    if ([GGConsoleMode]::GetConsoleMode($handle, [ref]$verified) -and (($verified -band 4) -ne 0)) {
        $script:GGVTHandle = $handle
        $script:GGVTOriginalMode = $mode
        return $true
    }
    [void][GGConsoleMode]::SetConsoleMode($handle, $mode)
    return $false
}
function Restore-GGVirtualTerminal {
    if ($script:GGVTHandle) {
        [void][GGConsoleMode]::SetConsoleMode($script:GGVTHandle, $script:GGVTOriginalMode)
        $script:GGVTHandle = $null
    }
}
function Write-GGLine([string]$value = '') {
    if ([Console]::IsOutputRedirected) {
        $bytes = ([Text.UTF8Encoding]::new($false)).GetBytes($value + [Environment]::NewLine)
        $stream = [Console]::OpenStandardOutput()
        $stream.Write($bytes, 0, $bytes.Length)
    } else { Write-GGConsoleText ($value + [Environment]::NewLine) }
}
function Write-GGConsoleText([string]$value, [int]$standardHandle = -11) {
    $handle = [GGConsoleMode]::GetStdHandle($standardHandle)
    for ($offset = 0; $offset -lt $value.Length; $offset += 16384) {
        $line = $value.Substring($offset, [Math]::Min(16384, $value.Length - $offset))
        $written = [uint32]0
        if (-not [GGConsoleMode]::WriteConsoleW($handle, $line, [uint32]$line.Length,
            [ref]$written, [IntPtr]::Zero) -or $written -ne $line.Length) {
            throw 'gg: cannot write console output'
        }
    }
}
function ConvertTo-GGWindowsArgument([string]$value) {
    if ($value -notmatch '[\s"]' -and $value.Length -gt 0) { return $value }
    $quoted = '"'
    $slashes = 0
    foreach ($character in $value.ToCharArray()) {
        if ($character -eq '\') { $slashes++; continue }
        if ($character -eq '"') {
            $quoted += ('\' * ($slashes * 2 + 1)) + '"'
        } else {
            $quoted += ('\' * $slashes) + $character
        }
        $slashes = 0
    }
    return $quoted + ('\' * ($slashes * 2)) + '"'
}
function Invoke-GGCore([string]$core, [string[]]$arguments, [bool]$feedInput) {
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $core
    $start.Arguments = (@($arguments | ForEach-Object { ConvertTo-GGWindowsArgument $_ }) -join ' ')
    $start.UseShellExecute = $false
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $utf8 = [Text.UTF8Encoding]::new($false)
    if ($start.PSObject.Properties.Name -contains 'StandardInputEncoding') {
        $start.StandardInputEncoding = $utf8
        $process = [System.Diagnostics.Process]::Start($start)
    } else {
        # .NET Framework uses Console.InputEncoding for its internal stdin writer.
        # Set a no-BOM encoding only while that writer is constructed.
        $previousInputEncoding = [Console]::InputEncoding
        try {
            [Console]::InputEncoding = $utf8
            $process = [System.Diagnostics.Process]::Start($start)
        } finally { [Console]::InputEncoding = $previousInputEncoding }
    }
    try {
        $consoleOutput = -not [Console]::IsOutputRedirected
        $consoleBytes = if ($consoleOutput) { [IO.MemoryStream]::new() } else { $null }
        $stdoutTarget = if ($consoleOutput) { $consoleBytes } else { [Console]::OpenStandardOutput() }
        $stdout = $process.StandardOutput.BaseStream.CopyToAsync($stdoutTarget)
        $consoleError = -not [Console]::IsErrorRedirected
        $errorBytes = if ($consoleError) { [IO.MemoryStream]::new() } else { $null }
        $stderrTarget = if ($consoleError) { $errorBytes } else { [Console]::OpenStandardError() }
        $stderr = $process.StandardError.BaseStream.CopyToAsync($stderrTarget)
        $writeError = $null
        if ($feedInput) {
            $writer = $null
            try { foreach ($item in $input) {
                if ($null -eq $item) { continue }
                if ($item -isnot [string]) { throw 'gg: --box and --table accept text pipeline input only' }
                if ($null -eq $writer) {
                    $writer = [IO.StreamWriter]::new($process.StandardInput.BaseStream, [Text.UTF8Encoding]::new($false))
                }
                $value = [string]$item
                if ($value.EndsWith("`n")) { $value = $value.Substring(0, $value.Length - 1).TrimEnd("`r") }
                $writer.WriteLine($value)
            } } catch [System.IO.IOException] { $writeError = $_.Exception }
            finally {
                try {
                    if ($null -ne $writer) { $writer.Dispose() }
                    else { $process.StandardInput.Close() }
                }
                catch [System.IO.IOException] { $writeError = $_.Exception }
            }
        }
        if (-not $feedInput) { $process.StandardInput.Close() }
        [void]$stdout.GetAwaiter().GetResult()
        [void]$stderr.GetAwaiter().GetResult()
        $process.WaitForExit()
        if ($consoleOutput) {
            $decoder = [Text.UTF8Encoding]::new($false, $true)
            Write-GGConsoleText ($decoder.GetString($consoleBytes.ToArray()))
            $consoleBytes.Dispose()
        }
        if ($consoleError) {
            $decoder = [Text.UTF8Encoding]::new($false, $true)
            Write-GGConsoleText ($decoder.GetString($errorBytes.ToArray())) (-12)
            $errorBytes.Dispose()
        }
        if ($writeError -and $process.ExitCode -eq 0) { throw "gg: cannot write formatter stdin: $writeError" }
        return $process.ExitCode
    } catch {
        if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() }
        throw
    } finally { $process.Dispose() }
}
$argv = @($args | ForEach-Object {
    if ($_ -is [array]) { $_ -join ',' } else { [string]$_ }
})
if ($argv.Count -eq 1 -and $argv[0] -in @('version', '--version')) {
    $root = Split-Path -Parent $MyInvocation.MyCommand.Path
    $core = Join-Path $root 'gg-format.exe'
    if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {
        $core = Join-Path $root 'dist/windows-x64/gg-format.exe'
    }
    if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {
        [Console]::Error.WriteLine('gg: missing GG Rust formatter binary')
        exit 2
    }
    & $core --version
    exit $LASTEXITCODE
}
$mode = $false
$afterOptions = $false
foreach ($item in $argv) {
    if ($item -eq '--') { $afterOptions = $true; continue }
    if (-not $afterOptions -and $item -in @('--box', '--table')) { $mode = $true; break }
}
if ($mode) {
    $root = Split-Path -Parent $MyInvocation.MyCommand.Path
    $core = Join-Path $root 'gg-format.exe'
    if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {
        $core = Join-Path $root 'dist/windows-x64/gg-format.exe'
    }
    if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {
        [Console]::Error.WriteLine('gg: missing GG Rust formatter binary')
        exit 2
    }
    $oldColumns = $env:COLUMNS
    $oldGGTTY = $env:GG_OUTPUT_IS_TTY
    if (-not $env:COLUMNS -and -not [Console]::IsOutputRedirected) {
        try { $env:COLUMNS = [string][Console]::WindowWidth } catch { }
    }
    $env:GG_OUTPUT_IS_TTY = if (Test-GGVirtualTerminal) { '1' } else { '0' }
    if (-not [Console]::IsOutputRedirected -and $env:GG_OUTPUT_IS_TTY -eq '0') {
        $argv = @('--no-color') + @($argv)
    }
    try {
        if ($MyInvocation.ExpectingInput) {
            $status = $input | Invoke-GGCore $core $argv $true
        } else {
            $status = Invoke-GGCore $core $argv $false
        }
        exit $status
    } catch {
        [Console]::Error.WriteLine($_.Exception.Message)
        exit 2
    } finally {
        $env:COLUMNS = $oldColumns
        $env:GG_OUTPUT_IS_TTY = $oldGGTTY
        Restore-GGVirtualTerminal
    }
}

# Existing divider semantics kept in a native PowerShell fast path.
$style = if ($env:GG_STYLE) { $env:GG_STYLE } else { 'double' }
$color = if ($env:GG_COLOR) { $env:GG_COLOR } else { 'default' }
$textColor = if ($env:GG_TEXT_COLOR) { $env:GG_TEXT_COLOR } else { 'default' }
$layout = if ($env:GG_LAYOUT) { $env:GG_LAYOUT } else { 'box' }
$align = if ($env:GG_ALIGN) { $env:GG_ALIGN } else { 'center' }
$width = $env:GG_WIDTH
$title = ''
$explicit = $false
$pattern = ''
$custom = $false
$noColor = $false
$forceColor = $false
$words = New-Object System.Collections.Generic.List[string]
$optionNames = @('text', 'style', 'char', 'color', 'text-color', 'width', 'align', 'layout')
$aliases = @{ '-t'='text'; '-s'='style'; '-c'='char'; '-w'='width'; '-a'='align'; '-l'='layout' }
for ($i = 0; $i -lt $argv.Count; $i++) {
    $arg = [string]$argv[$i]
    if ($arg -eq '--') {
        for ($i++; $i -lt $argv.Count; $i++) { $words.Add([string]$argv[$i]) }
        break
    }
    if ($arg -in @('-h', '--help')) {
        @'
Usage: gg [options] [text]
  -t, --text TEXT         Divider title
  -s, --style STYLE       double | single | heavy | dashed | dotted | ascii
  -c, --char PATTERN      Custom divider pattern
      --color COLOR       Divider or border color
      --text-color COLOR  Text color
  -w, --width N           Width (8..500; automatic capped at 120)
  -a, --align ALIGN       left | center | right
  -l, --layout LAYOUT     box | inline (divider only)
      --no-color          Disable colors
      --force-color       Enable colors when redirected
      --box               Multiline text frame (shared Rust binary)
      --table             TSV table (shared Rust binary)
      --title TEXT        Frame title
      --header A,B        Table column names
      --header-first-row   First TSV row is column names
      --overflow POLICY   wrap | truncate | error
      --max-rows N        Default 10000
      --max-bytes N       Default 8388608
      --version           Show GG version (also: gg version)
'@
        exit 0
    }
    if ($arg -eq '--no-color') { $noColor = $true; continue }
    if ($arg -eq '--force-color') { $forceColor = $true; continue }
    $key = $null
    if ($arg -match '^--([^=]+)=(.*)$') {
        $key = $Matches[1]; $value = $Matches[2]
    } elseif ($arg.StartsWith('--')) {
        $key = $arg.Substring(2)
        if ($key -notin $optionNames) {
            [Console]::Error.WriteLine("gg: unknown option: $arg")
            exit 2
        }
        if ($i + 1 -ge $argv.Count) {
            [Console]::Error.WriteLine("gg: $arg requires a value")
            exit 2
        }
        $i++; $value = [string]$argv[$i]
    } elseif ($aliases.ContainsKey($arg)) {
        $key = $aliases[$arg]
        if ($i + 1 -ge $argv.Count) {
            [Console]::Error.WriteLine("gg: $arg requires a value")
            exit 2
        }
        $i++; $value = [string]$argv[$i]
    } elseif ($arg.StartsWith('-')) {
        [Console]::Error.WriteLine("gg: unknown option: $arg")
        exit 2
    } else {
        $words.Add($arg); continue
    }
    if ($key -notin $optionNames) {
        [Console]::Error.WriteLine("gg: unknown option: $arg")
        exit 2
    }
    switch ($key) {
        text { $title = $value; $explicit = $true }
        style { $style = $value }
        char { $pattern = $value; $custom = $true }
        color { $color = $value }
        'text-color' { $textColor = $value }
        width { $width = $value }
        align { $align = $value }
        layout { $layout = $value }
    }
}
if ($words.Count -gt 0) {
    if ($explicit) {
        [Console]::Error.WriteLine('gg: use either --text or positional text, not both')
        exit 2
    }
    $title = $words -join ' '
}
$glyphs = @{ double=[string][char]0x2550; single=[string][char]0x2500; heavy=[string][char]0x2501; dashed=[string][char]0x254c; dotted=[string][char]0x00b7; ascii='=' }
if (-not $glyphs.ContainsKey($style)) {
    [Console]::Error.WriteLine("gg: invalid style: $style")
    exit 2
}
$glyph = if ($custom) { $pattern } else { $glyphs[$style] }
if ($glyph.Length -lt 1 -or $glyph.Length -gt 16 -or $glyph -match '[\x00-\x1f]' -or $glyph -match '^\s+$') {
    [Console]::Error.WriteLine('gg: --char must have 1..16 printable, narrow characters')
    exit 2
}
if ($align -notin @('left', 'center', 'right')) {
    [Console]::Error.WriteLine("gg: invalid align: $align")
    exit 2
}
if ($layout -notin @('box', 'inline')) {
    [Console]::Error.WriteLine("gg: invalid layout: $layout")
    exit 2
}
if ($title -match '[\x00-\x1f]') {
    [Console]::Error.WriteLine('gg: title must be a single line without control characters')
    exit 2
}
if (-not $width) {
    if ($env:COLUMNS -match '^\d+$') { $width = [int]$env:COLUMNS }
    elseif (-not [Console]::IsOutputRedirected) {
        try { $width = [Console]::WindowWidth } catch { $width = 80 }
    } else { $width = 80 }
    if ($width -gt 2) { $width -= 2 }
    $width = [Math]::Max(8, [Math]::Min(120, $width))
}
if ([string]$width -cnotmatch '^\d{1,3}$' -or [int]$width -lt 8 -or [int]$width -gt 500) {
    [Console]::Error.WriteLine('gg: width must be an integer from 8 to 500')
    exit 2
}
$width = [int]$width
if ($title.Length + 4 -gt $width) {
    [Console]::Error.WriteLine("gg: text is too long for width $width; increase --width")
    exit 2
}
function Get-GGColor([string]$name) {
    $named = @{ black=30; red=31; green=32; yellow=33; blue=34; magenta=35; cyan=36; white=37
                gray=90; 'bright-red'=91; 'bright-green'=92; 'bright-yellow'=93
                'bright-blue'=94; 'bright-magenta'=95; 'bright-cyan'=96; 'bright-white'=97 }
    if ($name -in @('none', 'default')) { return '' }
    if ($named.ContainsKey($name)) { return "$([char]27)[$($named[$name])" + 'm' }
    if ($name -match '^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$') {
        $r = [Convert]::ToInt32($Matches[1], 16)
        $g = [Convert]::ToInt32($Matches[2], 16)
        $b = [Convert]::ToInt32($Matches[3], 16)
        return "$([char]27)[38;2;$r;$g;$b" + 'm'
    }
    if ($name -match '^\d{1,3}$' -and [int]$name -le 255) {
        return "$([char]27)[38;5;$([int]$name)" + 'm'
    }
    throw "gg: invalid color: $name"
}
try {
    $bc = Get-GGColor $color
    $tc = Get-GGColor $textColor
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
if ($noColor -or (-not $forceColor -and ([Console]::IsOutputRedirected -or $env:NO_COLOR)) -or
    (-not [Console]::IsOutputRedirected -and -not (Test-GGVirtualTerminal))) {
    $bc = ''; $tc = ''
}
$br = if ($bc) { "$([char]27)[0m" } else { '' }
$tr = if ($tc) { "$([char]27)[0m" } else { '' }
$line = $glyph
while ($line.Length -lt $width) { $line += $line }
$line = $line.Substring(0, $width)
try {
    Write-GGLine
    if (-not $title) {
        Write-GGLine "$bc$line$br"
    } elseif ($layout -eq 'inline') {
        $free = $width - $title.Length - 2
        $left = switch ($align) {
            left { 1 } center { [int][Math]::Floor($free / 2) } right { $free - 1 }
        }
        $right = $free - $left
        Write-GGLine "$bc$($line.Substring(0,$left))$br $tc$title$tr $bc$($line.Substring(0,$right))$br"
    } else {
        $free = $width - $title.Length - 4
        $left = switch ($align) {
            left { 0 } center { [int][Math]::Floor($free / 2) } right { $free }
        }
        $right = $free - $left
        Write-GGLine "$bc$line$br"
        Write-GGLine "$(' ' * ($left + 2))$tc$title$tr$(' ' * ($right + 2))"
        Write-GGLine "$bc$line$br"
    }
    Write-GGLine
} finally { Restore-GGVirtualTerminal }
