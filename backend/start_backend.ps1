# start_backend.ps1
# Loads backend/.env (or backend/.env.example) into environment variables and starts the backend.

$envFile = Join-Path $PSScriptRoot '.\backend\.env'
if (-not (Test-Path $envFile)) {
    $envFile = Join-Path $PSScriptRoot '.\backend\.env.example'
    Write-Host "Using .env example: $envFile" -ForegroundColor Yellow
}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and $line -notmatch '^[\s#]') {
        $parts = $line -split '=', 2
        if ($parts.Length -eq 2) {
            $k = $parts[0].Trim()
            $v = $parts[1].Trim()
            if ($v -ne '') { Set-Item -Path Env:$k -Value $v }
        }
    }
}

Write-Host "Starting backend on $($env:HOST):$($env:PORT)"
python .\backend\main.py