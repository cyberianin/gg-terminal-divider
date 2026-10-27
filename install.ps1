<#
PowerShell 5.1+ installer. Run with: & ./install.ps1 -Command gg
No profile is modified. Installed scripts pin one release before opening files.
#>
param(
    [ValidateSet('gg','vv','xx','bn','bb','cv')][string]$Command = 'gg',
    [switch]$CheckNames,
    [switch]$Uninstall
)
$ErrorActionPreference = 'Stop'
$source = $PSScriptRoot
$bin = if ($env:GG_BIN_DIR) { [IO.Path]::GetFullPath($env:GG_BIN_DIR) } else {
    Join-Path $HOME '.local\bin'
}
$homeDir = Join-Path $bin '.gg-divider-ps'
$target = Join-Path $bin "$Command.ps1"
$marker = Join-Path $homeDir 'owner'
$launcherHash = Join-Path $homeDir 'launcher.sha256'
$ownerText = 'gg-terminal-divider-powershell-v1'
$utf8 = New-Object System.Text.UTF8Encoding -ArgumentList $false
function Get-GGHash([string]$path) {
    $stream = [IO.File]::OpenRead($path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '') }
    finally { $sha.Dispose(); $stream.Dispose() }
}

function Test-OwnCommand([string]$path) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
    if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) { return $false }
    if ([IO.File]::ReadAllText($marker).Trim() -cne $ownerText) { return $false }
    if ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) { return $false }
    if (Test-Path -LiteralPath $launcherHash -PathType Leaf) {
        return (Get-GGHash $path) -ceq
            [IO.File]::ReadAllText($launcherHash).Trim()
    }
    return [IO.File]::ReadAllText($path) -ceq [IO.File]::ReadAllText((Join-Path $source 'gg.ps1'))
}
function Get-Conflict([string]$name) {
    $public = Join-Path $bin "$name.ps1"
    $owned = Test-OwnCommand $public
    if ((Test-Path -LiteralPath $public) -and -not $owned) {
        return "foreign destination: $public"
    }
    foreach ($entry in @(Get-Command -Name $name -All -ErrorAction SilentlyContinue)) {
        if ($entry.CommandType -eq 'ExternalScript' -and
            [IO.Path]::GetFullPath($entry.Source) -ceq [IO.Path]::GetFullPath($public) -and
            $owned) { continue }
        if ($entry.CommandType -eq 'Alias' -and $owned -and
            [IO.Path]::GetFullPath($entry.Definition) -ieq [IO.Path]::GetFullPath($public)) {
            continue
        }
        return "$($entry.CommandType): $($entry.Source)"
    }
    return ''
}
if ($CheckNames) {
    foreach ($name in @('gg','vv','xx','bn','bb','cv')) {
        $reason = Get-Conflict $name
        if ($reason) { Write-Output "$name CONFLICT: $reason" }
        else { Write-Output "$name AVAILABLE" }
    }
    return
}
if ($Uninstall) {
    if (-not (Test-OwnCommand $target)) {
        [Console]::Error.WriteLine("GG: refusing to remove a foreign command: $target")
        exit 1
    }
    Remove-Item -LiteralPath $target
    Write-Output "Removed $Command"
    return
}
$reason = Get-Conflict $Command
if ($reason) {
    [Console]::Error.WriteLine("GG: $Command CONFLICT: $reason")
    exit 1
}
if (-not (Test-Path -LiteralPath $bin -PathType Container)) {
    [void][IO.Directory]::CreateDirectory($bin)
}
if (Test-Path -LiteralPath $homeDir) {
    if (-not (Test-Path -LiteralPath $marker -PathType Leaf) -or
        [IO.File]::ReadAllText($marker).Trim() -cne $ownerText -or
        ((Get-Item -LiteralPath $homeDir).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        [Console]::Error.WriteLine("GG: foreign private directory: $homeDir")
        exit 1
    }
} else {
    [void][IO.Directory]::CreateDirectory($homeDir)
    [IO.File]::WriteAllText($marker, "$ownerText`n", $utf8)
}
$currentFile = Join-Path $homeDir 'current'
$current = ''
if (Test-Path -LiteralPath $currentFile -PathType Leaf) {
    $current = [IO.File]::ReadAllText($currentFile).Trim()
    if ($current -cnotmatch '^version\.[a-zA-Z0-9]{6}$' -or
        -not (Test-Path -LiteralPath (Join-Path $homeDir $current) -PathType Container)) {
        [Console]::Error.WriteLine('GG: invalid installed release pointer')
        exit 1
    }
}
$files = @('gg-ps.ps1', 'gg-format.exe')
$same = [bool]$current
if ($same) {
    foreach ($file in $files) {
        $oldFile = Join-Path (Join-Path $homeDir $current) $file
        $newFile = if ($file -eq 'gg-format.exe') {
            Join-Path $source 'dist/windows-x64/gg-format.exe'
        } else { Join-Path $source $file }
        if (-not (Test-Path -LiteralPath $oldFile -PathType Leaf) -or
            (Get-GGHash $oldFile) -cne
            (Get-GGHash $newFile)) {
            $same = $false
            break
        }
    }
}
if (-not $same) {
    do {
        $release = 'version.' + [Guid]::NewGuid().ToString('N').Substring(0,6)
        $releasePath = Join-Path $homeDir $release
    } while (Test-Path -LiteralPath $releasePath)
    [void][IO.Directory]::CreateDirectory($releasePath)
    foreach ($file in $files) {
        $origin = if ($file -eq 'gg-format.exe') {
            Join-Path $source 'dist/windows-x64/gg-format.exe'
        } else { Join-Path $source $file }
        [IO.File]::Copy($origin, (Join-Path $releasePath $file))
    }
    $next = Join-Path $homeDir ('.current.' + [Guid]::NewGuid().ToString('N'))
    [IO.File]::WriteAllText($next, "$release`n", $utf8)
    if (Test-Path -LiteralPath $currentFile -PathType Leaf) {
        $backup = Join-Path $homeDir ('.previous.' + [Guid]::NewGuid().ToString('N'))
        [IO.File]::Replace($next, $currentFile, $backup)
        [IO.File]::Delete($backup)
    } else {
        [IO.File]::Move($next, $currentFile)
    }
}
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
    [IO.File]::Copy((Join-Path $source 'gg.ps1'), $target)
}
if (-not (Test-Path -LiteralPath $launcherHash -PathType Leaf)) {
    [IO.File]::WriteAllText($launcherHash, ((Get-GGHash $target) + "`n"), $utf8)
}
$activate = Join-Path $homeDir 'activate.ps1'
if (-not (Test-Path -LiteralPath $activate -PathType Leaf)) {
    [IO.File]::Copy((Join-Path $source 'gg-activate.ps1'), $activate)
}
Write-Output "Installed $Command -> $target"
Write-Output "Add $bin to PATH, or dot-source $activate -Name $Command in the current session."
