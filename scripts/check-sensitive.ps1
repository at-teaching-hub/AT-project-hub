param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = 'Stop'
$patterns = @(
    'AKfycb[A-Za-z0-9_\-]{20,}',
    'AIza[0-9A-Za-z\-_]{30,}',
    'sk-[A-Za-z0-9]{20,}',
    'gh[pousr]_[A-Za-z0-9]{30,}',
    'RBT26-[A-Za-z0-9\-]{8,}',
    'WIFI_PASSWORD\s*=\s*"[^"<][^"]*"',
    'API_TOKEN\s*=\s*"[^"<][^"]*"',
    'api[_-]?key\s*[:=]\s*["''][^"'']{16,}',
    'token\s*[:=]\s*["''][^"'']{16,}',
    'password\s*[:=]\s*["''][^"'']{8,}'
)
$exclude = '\\.git\\|node_modules|__pycache__|assets\\style.css|assets\\app.js'
$placeholder = '(?i)CHANGE_ME|YOUR_[A-Z_]+|PLACEHOLDER|<[^>]+>|範例|例如|自行設定|你的'
$files = Get-ChildItem -LiteralPath $Root -Recurse -File |
    Where-Object { $_.FullName -notmatch $exclude -and $_.Length -lt 3MB -and $_.Extension -notin '.png','.jpg','.jpeg','.webp','.zip','.pptx','.xlsx','.docx','.pdf','.bin','.blend' }
$hits = @()
foreach ($file in $files) {
    try {
        $matches = Select-String -LiteralPath $file.FullName -Pattern $patterns -AllMatches -CaseSensitive:$false |
            Where-Object { $_.Line -notmatch $placeholder }
        if ($matches) { $hits += $matches }
    } catch { }
}
if ($hits.Count -gt 0) {
    Write-Host 'Potential sensitive values found. Review before publishing:' -ForegroundColor Yellow
    $hits | Select-Object Path, LineNumber, Line | Format-Table -Wrap
    exit 2
}
Write-Host 'OK: no obvious secret patterns found.' -ForegroundColor Green
