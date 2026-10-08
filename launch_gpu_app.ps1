param([switch]$Rebenchmark, [switch]$SetupOnly)
& (Join-Path $PSScriptRoot 'launch_app.ps1') -Rebenchmark:$Rebenchmark -SetupOnly:$SetupOnly
