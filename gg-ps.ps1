# PowerShell shell adapter. Rust is the sole implementation of --box/--table.
$ErrorActionPreference = 'Stop'
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
function Invoke-GGCore51([string]$core, [string[]]$arguments) {
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $core
    $start.Arguments = (@($arguments | ForEach-Object { ConvertTo-GGWindowsArgument $_ }) -join ' ')
    $start.UseShellExecute = $false
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::Start($start)
    try {
        $stdout = $process.StandardOutput.BaseStream.CopyToAsync([Console]::OpenStandardOutput())
        $stderr = $process.StandardError.BaseStream.CopyToAsync([Console]::OpenStandardError())
        $writer = New-Object System.IO.StreamWriter -ArgumentList $process.StandardInput.BaseStream, (New-Object System.Text.UTF8Encoding -ArgumentList $false)
        $writeError = $null
        try {
            foreach ($item in $input) {
                if ($item -isnot [string]) { throw 'gg: --box and --table accept text pipeline input only' }
                $value = [string]$item
                if ($value.EndsWith("`n")) { $value = $value.Substring(0, $value.Length - 1).TrimEnd("`r") }
                $writer.WriteLine($value)
            }
        } catch [System.IO.IOException] { $writeError = $_.Exception }
        finally {
            try { $writer.Dispose() }
            catch [System.IO.IOException] { $writeError = $_.Exception }
        }
        [void]$stdout.GetAwaiter().GetResult()
        [void]$stderr.GetAwaiter().GetResult()
        $process.WaitForExit()
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
    $oldOutputEncoding = $OutputEncoding
    $OutputEncoding = New-Object System.Text.UTF8Encoding -ArgumentList $false
    $oldConsoleInputEncoding = [Console]::InputEncoding
    [Console]::InputEncoding = New-Object System.Text.UTF8Encoding -ArgumentList $false
    $oldColumns = $env:COLUMNS
    $oldGGTTY = $env:GG_OUTPUT_IS_TTY
    if (-not $env:COLUMNS -and -not [Console]::IsOutputRedirected) {
        try { $env:COLUMNS = [string][Console]::WindowWidth } catch { }
    }
    if (-not [Console]::IsOutputRedirected) { $env:GG_OUTPUT_IS_TTY = '1' }
    try {
        if ($MyInvocation.ExpectingInput) {
            if ($PSVersionTable.PSVersion.Major -lt 7) {
                $status = $input | Invoke-GGCore51 $core $argv
                exit $status
            } else {
                $input | ForEach-Object {
                    if ($_ -isnot [string]) {
                        throw 'gg: --box and --table accept text pipeline input only'
                    }
                    $value = [string]$_
                    if ($value.EndsWith("`n")) {
                        $value = $value.Substring(0, $value.Length - 1).TrimEnd("`r")
                    }
                    $value
                } | & $core @argv
            }
        } else {
            & $core @argv
        }
        exit $LASTEXITCODE
    } catch {
        [Console]::Error.WriteLine($_.Exception.Message)
        exit 2
    } finally {
        $OutputEncoding = $oldOutputEncoding
        [Console]::InputEncoding = $oldConsoleInputEncoding
        $env:COLUMNS = $oldColumns
        $env:GG_OUTPUT_IS_TTY = $oldGGTTY
    }
}

# Existing divider semantics kept in a native PowerShell fast path.
$style = if ($env:GG_STYLE) { $env:GG_STYLE } else { 'double' }
$color = if ($env:GG_COLOR) { $env:GG_COLOR } else { 'magenta' }
$textColor = if ($env:GG_TEXT_COLOR) { $env:GG_TEXT_COLOR } else { 'cyan' }
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
$glyphs = @{ double='═'; single='─'; heavy='━'; dashed='╌'; dotted='·'; ascii='=' }
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
if ($noColor -or (-not $forceColor -and ([Console]::IsOutputRedirected -or $env:NO_COLOR))) {
    $bc = ''; $tc = ''
}
$br = if ($bc) { "$([char]27)[0m" } else { '' }
$tr = if ($tc) { "$([char]27)[0m" } else { '' }
$line = $glyph
while ($line.Length -lt $width) { $line += $line }
$line = $line.Substring(0, $width)
[Console]::Out.WriteLine()
if (-not $title) {
    [Console]::Out.WriteLine("$bc$line$br")
} elseif ($layout -eq 'inline') {
    $free = $width - $title.Length - 2
    $left = switch ($align) {
        left { 1 } center { [int][Math]::Floor($free / 2) } right { $free - 1 }
    }
    $right = $free - $left
    [Console]::Out.WriteLine("$bc$($line.Substring(0,$left))$br $tc$title$tr $bc$($line.Substring(0,$right))$br")
} else {
    $free = $width - $title.Length - 4
    $left = switch ($align) {
        left { 0 } center { [int][Math]::Floor($free / 2) } right { $free }
    }
    $right = $free - $left
    [Console]::Out.WriteLine("$bc$line$br")
    [Console]::Out.WriteLine("$(' ' * ($left + 2))$tc$title$tr$(' ' * ($right + 2))")
    [Console]::Out.WriteLine("$bc$line$br")
}
[Console]::Out.WriteLine()
