$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = "D:\anacanda\envs\robot-yolo\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "robot-yolo Python was not found: $Python"
}

Set-Location -LiteralPath $ProjectRoot
& $Python -m windows_ai_service.main
