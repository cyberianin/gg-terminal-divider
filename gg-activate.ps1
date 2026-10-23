param([ValidateSet('gg','vv','xx','bn','bb','cv')][string]$Name = 'gg')
$bin = if ((Split-Path -Leaf $PSScriptRoot) -eq '.gg-divider-ps') {
    Split-Path -Parent $PSScriptRoot
} else { $PSScriptRoot }
$target = Join-Path $bin "$Name.ps1"
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
    throw "GG: $Name is not installed at $target"
}
foreach ($entry in @(Get-Command -Name $Name -All -ErrorAction SilentlyContinue)) {
    if ($entry.CommandType -eq 'ExternalScript' -and
        [IO.Path]::GetFullPath($entry.Source) -ceq [IO.Path]::GetFullPath($target)) { continue }
    if ($entry.CommandType -eq 'Alias' -and $entry.Definition -ceq $target) { continue }
    throw "GG: $Name conflicts with $($entry.CommandType): $($entry.Source)"
}
Set-Alias -Name $Name -Value $target -Scope Global
