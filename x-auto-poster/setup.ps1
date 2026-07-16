# Setup X Auto Poster on D: drive
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1

$ErrorActionPreference = "Stop"
$Root = "D:\dev\x-auto-poster"

if (-not (Test-Path -LiteralPath $Root)) {
    Write-Error "Project root not found: $Root"
}

Set-Location -LiteralPath $Root
Write-Host ("Working directory: " + (Get-Location).Path)

$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    Write-Error "python not found. Install Python 3.10+."
}

$VenvPath = Join-Path $Root ".venv"
if (-not (Test-Path -LiteralPath $VenvPath)) {
    Write-Host "Creating virtual environment..."
    python -m venv $VenvPath
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")

$dataDir = Join-Path $Root "data"
$logsDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $dataDir, $logsDir | Out-Null

$EnvFile = Join-Path $Root ".env"
$EnvExample = Join-Path $Root ".env.example"
if (-not (Test-Path -LiteralPath $EnvFile)) {
    Copy-Item -LiteralPath $EnvExample -Destination $EnvFile
    Write-Host "Created .env from .env.example"
} else {
    Write-Host ".env already exists - not overwritten"
}

$TokenPath = Join-Path $dataDir "oauth_tokens.json"
if (-not (Test-Path -LiteralPath $TokenPath)) {
    $template = @{
        access_token  = ""
        refresh_token = ""
        token_type    = "bearer"
        expires_at    = $null
        scope         = "tweet.read tweet.write users.read offline.access"
    } | ConvertTo-Json
    Set-Content -LiteralPath $TokenPath -Value $template -Encoding UTF8
    Write-Host "Created data/oauth_tokens.json template"
} else {
    Write-Host "oauth_tokens.json already exists - not overwritten"
}

& $VenvPython -m app.cli init-db
Write-Host "Setup complete."
Write-Host "Next: edit .env and data/oauth_tokens.json, then run verify-auth"
