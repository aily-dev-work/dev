# Unregister Windows Task Scheduler job
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\unregister_task.ps1

$ErrorActionPreference = "Stop"
$TaskName = "XAutoPoster"

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Unregistered: $TaskName"
} else {
    Write-Host "Task not found: $TaskName"
}
