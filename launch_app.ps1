param([switch]$Rebenchmark, [switch]$CpuOnly, [switch]$SetupOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$bootstrapPython = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $ErrorActionPreference = 'Continue'
    foreach ($version in @('-3.13', '-3.12', '-3.11')) {
        $candidate = & py $version -c "import sys,struct; assert struct.calcsize('P')==8; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) { $bootstrapPython = $candidate.Trim(); break }
    }
    $ErrorActionPreference = 'Stop'
}
if (-not $bootstrapPython -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $ErrorActionPreference = 'Continue'
    $candidate = & python -c "import sys,struct; assert (3,11)<=sys.version_info[:2]<(3,14) and struct.calcsize('P')==8; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $candidate) { $bootstrapPython = $candidate.Trim() }
}
$ErrorActionPreference = 'Stop'
if (-not $bootstrapPython) {
    Write-Host 'Installing Python 3.13 for this user...'
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Install Python 3.13 (64-bit), then launch again. Windows App Installer/winget is unavailable.' }
    & winget install --id Python.Python.3.13 --exact --scope user --architecture x64 --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw 'Automatic Python installation failed.' }
    $bootstrapPython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
    if (-not (Test-Path -LiteralPath $bootstrapPython)) { throw 'Restart PowerShell after Python installation, then launch again.' }
}
$setupArgs = @((Join-Path $PSScriptRoot 'app_bootstrap.py'))
if ($Rebenchmark) { $setupArgs += '--rebenchmark' }
if ($CpuOnly) { $setupArgs += '--cpu-only' }
if ($SetupOnly) { $setupArgs += '--no-launch' }
& $bootstrapPython @setupArgs
if ($LASTEXITCODE -ne 0) { throw 'Setup did not complete. See the message above and .runtime logs.' }
