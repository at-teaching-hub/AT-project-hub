param(
    [string]$Message = "Sync project updates",
    [string]$Branch = "main"
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$sshRoot = 'C:\Users\alex9\Documents\Codex\2026-11-25\h\work\ssh'
$env:GIT_SSH = Join-Path $sshRoot 'ssh-github-v3.exe'
$env:GIT_SSH_VARIANT = 'ssh'
$env:CODEX_SSH_KEY = Join-Path $sshRoot 'AT-project-hub_deploy_ed25519'
git config --unset core.sshCommand 2>$null

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
