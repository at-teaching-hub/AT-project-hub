param(
    [string]$TaskName = "CodexProjectHubPublish",
    [string]$Time = "18:10"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $PSScriptRoot "publish.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -Message `"Scheduled project sync`""
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$description = "Check the public Codex Project Hub for reviewed changes, commit, and push to GitHub."
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Description $description -Force | Out-Null
Write-Host "Scheduled task '$TaskName' installed for $Time daily." -ForegroundColor Green
