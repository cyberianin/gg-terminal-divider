# Stable PowerShell launcher. An installed command pins one release per call.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$homeDir = Join-Path $root '.gg-divider-ps'
if (Test-Path -LiteralPath (Join-Path $homeDir 'current') -PathType Leaf) {
    $version = [IO.File]::ReadAllText((Join-Path $homeDir 'current')).Trim()
    if ($version -cnotmatch '^version\.[a-zA-Z0-9]{6}$') {
        [Console]::Error.WriteLine('GG: invalid PowerShell release pointer')
        exit 1
    }
    $engine = Join-Path (Join-Path $homeDir $version) 'gg-ps.ps1'
} else {
    $engine = Join-Path $root 'gg-ps.ps1'
}
if (-not (Test-Path -LiteralPath $engine -PathType Leaf)) {
    [Console]::Error.WriteLine('GG: missing PowerShell release adapter')
    exit 1
}
$forward = @($args | ForEach-Object {
    if ($_ -is [array]) { $_ -join ',' } else { [string]$_ }
})
if ($MyInvocation.ExpectingInput) {
    $input | & $engine @forward
} else {
    & $engine @forward
}
if ($LASTEXITCODE -is [int]) { exit $LASTEXITCODE }
