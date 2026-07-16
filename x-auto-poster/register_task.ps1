# Register Windows Task Scheduler job (does NOT run posts by itself).
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\register_task.ps1

$ErrorActionPreference = "Stop"
$Root = "D:\dev\x-auto-poster"
$TaskName = "XAutoPoster"
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "venv python not found: $Python — run setup.ps1 first."
}

$Action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "-m app.cli run-once" `
    -WorkingDirectory $Root

$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)

$Settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "It runs every 5 minutes: $Python -m app.cli run-once"
Write-Host "Ensure DRY_RUN=false in .env only when you want live posts."
