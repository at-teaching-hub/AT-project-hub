param(
    [string]$Message = "Sync project updates",
    [string]$Branch = "main"
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& "$PSScriptRoot\check-sensitive.ps1" -Root $Root
if ($LASTEXITCODE -ne 0) { throw 'Sensitive-content check failed.' }

git add .
$changes = git status --porcelain
if (-not $changes) {
    Write-Host 'Nothing to publish.' -ForegroundColor Cyan
    exit 0
}
git commit -m $Message
git push origin $Branch
