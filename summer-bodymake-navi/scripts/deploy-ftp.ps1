# Deploys the site to the configured FTP server.
# Usage:
#   1. Copy .deploy.env.example to .deploy.env and fill in the FTP settings, or
#   2. Set FTP_HOST / FTP_USER / FTP_PASS / FTP_REMOTE_DIR as environment variables.
#   3. Run: powershell -ExecutionPolicy Bypass -File scripts/deploy-ftp.ps1

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$EnvFile = Join-Path $Root ".deploy.env"
$ConfigKeys = @("FTP_HOST", "FTP_USER", "FTP_PASS", "FTP_REMOTE_DIR")

function Set-ConfigValue {
    param(
        [string]$Name,
        [string]$Value
    )
    if ($null -ne $Value -and $Value -ne "") {
        Set-Variable -Name $Name -Value $Value -Scope Script
    }
}

if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            Set-ConfigValue -Name $matches[1].Trim() -Value $matches[2].Trim()
        }
    }
}

foreach ($key in $ConfigKeys) {
    Set-ConfigValue -Name $key -Value ([System.Environment]::GetEnvironmentVariable($key))
}

foreach ($key in $ConfigKeys) {
    $var = Get-Variable -Name $key -ErrorAction SilentlyContinue
    if (-not $var -or -not $var.Value) {
        $sourceHint = if (Test-Path $EnvFile) { ".deploy.env" } else { "GitHub Actions secrets or .deploy.env" }
        Write-Error "$key is not set in $sourceHint."
    }
}

$UseSsl = $false
$ftpUseSsl = [System.Environment]::GetEnvironmentVariable("FTP_USE_SSL")
if ($ftpUseSsl) {
    $UseSsl = @("1", "true", "yes", "on") -contains $ftpUseSsl.ToString().ToLowerInvariant()
}

$ExcludeDirs = @(".git", ".github", "scripts", "_partials", ".cursor")
$ExcludeFiles = @(
    ".deploy.env",
    ".deploy.env.example",
    ".gitkeep",
    ".gitignore",
    "deploy-site.zip",
    "DEPLOYMENT.md",
    "README.md",
    "Untitled"
)

function Test-IsDeployablePath {
    param([string]$RelativePath)

    if (-not $RelativePath) {
        return $false
    }

    $normalized = $RelativePath -replace "\\", "/"
    $parts = $normalized -split "/"
    foreach ($part in $parts) {
        if ($ExcludeDirs -contains $part) {
            return $false
        }
    }

    $name = [System.IO.Path]::GetFileName($normalized)
    if ($ExcludeFiles -contains $name) {
        return $false
    }
    if ($name.StartsWith(".") -and $name -ne ".htaccess") {
        return $false
    }

    $localPath = Join-Path $Root ($normalized -replace "/", [System.IO.Path]::DirectorySeparatorChar)
    return (Test-Path $localPath -PathType Leaf)
}

function Ensure-FtpDirectory {
    param([string]$RemoteDir)

    $uri = "ftp://$FTP_HOST$RemoteDir"
    $request = [System.Net.FtpWebRequest]::Create($uri)
    $request.Method = [System.Net.WebRequestMethods+Ftp]::MakeDirectory
    $request.Credentials = New-Object System.Net.NetworkCredential($FTP_USER, $FTP_PASS)
    $request.UsePassive = $true
    $request.EnableSsl = $UseSsl

    try {
        $response = $request.GetResponse()
        $response.Close()
    }
    catch {
        # Directory may already exist.
    }
}

function Upload-RelativeFile {
    param([string]$RelativePath)

    $normalized = $RelativePath -replace "\\", "/"
    $localPath = Join-Path $Root ($normalized -replace "/", [System.IO.Path]::DirectorySeparatorChar)
    $remotePath = ($FTP_REMOTE_DIR.TrimEnd("/") + "/" + $normalized).Replace("//", "/")
    $remoteDir = [System.IO.Path]::GetDirectoryName($remotePath).Replace("\", "/")

    if ($remoteDir) {
        Ensure-FtpDirectory $remoteDir
    }

    Write-Host "UP $remotePath"
    Upload-FtpFileWithRetry $localPath $remotePath
}

function Get-ChangedDeployFiles {
    $eventPath = [System.Environment]::GetEnvironmentVariable("GITHUB_EVENT_PATH")
    if (-not $eventPath -or -not (Test-Path $eventPath)) {
        return @()
    }

    try {
        $event = Get-Content -Raw -Path $eventPath | ConvertFrom-Json
    }
    catch {
        return @()
    }

    if (-not $event.before -or -not $event.after) {
        return @()
    }
    if ($event.before -match '^0+$') {
        return @()
    }

    $changed = git -C $Root diff --name-only --diff-filter=ACMRT $event.before $event.after
    if ($LASTEXITCODE -ne 0) {
        return @()
    }

    return @($changed | Where-Object { Test-IsDeployablePath $_ })
}

function Upload-FtpFile {
    param(
        [string]$LocalPath,
        [string]$RemotePath
    )

    $uri = "ftp://$FTP_HOST$RemotePath"
    $request = [System.Net.FtpWebRequest]::Create($uri)
    $request.Method = [System.Net.WebRequestMethods+Ftp]::UploadFile
    $request.Credentials = New-Object System.Net.NetworkCredential($FTP_USER, $FTP_PASS)
    $request.UseBinary = $true
    $request.UsePassive = $true
    $request.EnableSsl = $UseSsl

    $bytes = [System.IO.File]::ReadAllBytes($LocalPath)
    $request.ContentLength = $bytes.Length

    $stream = $request.GetRequestStream()
    $stream.Write($bytes, 0, $bytes.Length)
    $stream.Close()

    $response = $request.GetResponse()
    $response.Close()
}

function Upload-FtpFileWithRetry {
    param(
        [string]$LocalPath,
        [string]$RemotePath
    )

    $maxAttempts = 3
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        try {
            Upload-FtpFile -LocalPath $LocalPath -RemotePath $RemotePath
            return
        }
        catch {
            Write-Warning "Upload failed ($attempt/$maxAttempts): $RemotePath"
            Write-Warning $_.Exception.Message
            if ($attempt -eq $maxAttempts) {
                throw
            }
            Start-Sleep -Seconds (2 * $attempt)
        }
    }
}

function Walk-RemoteDirs {
    param([string]$RelativeDir)

    $localDir = Join-Path $Root $RelativeDir
    if (-not (Test-Path $localDir)) {
        return
    }

    $remoteDir = ($FTP_REMOTE_DIR.TrimEnd("/") + "/" + ($RelativeDir -replace "\\", "/")).Replace("//", "/")
    Ensure-FtpDirectory $remoteDir

    Get-ChildItem $localDir -File | ForEach-Object {
        if ($ExcludeFiles -contains $_.Name) {
            return
        }
        if ($_.Name.StartsWith(".") -and $_.Name -ne ".htaccess") {
            return
        }

        $remotePath = $remoteDir.TrimEnd("/") + "/" + $_.Name
        Write-Host "UP $remotePath"
        Upload-FtpFileWithRetry $_.FullName $remotePath
    }

    Get-ChildItem $localDir -Directory | ForEach-Object {
        if ($ExcludeDirs -contains $_.Name) {
            return
        }

        $child = if ($RelativeDir) { Join-Path $RelativeDir $_.Name } else { $_.Name }
        Walk-RemoteDirs $child
    }
}

Write-Host "Deploy to ftp://$FTP_HOST$FTP_REMOTE_DIR"
$eventPath = [System.Environment]::GetEnvironmentVariable("GITHUB_EVENT_PATH")
$changedFiles = Get-ChangedDeployFiles
if ($changedFiles.Count -gt 0) {
    Write-Host "Deploy changed files only: $($changedFiles.Count)"
    foreach ($file in $changedFiles) {
        Upload-RelativeFile $file
    }
}
elseif ($eventPath -and (Test-Path $eventPath)) {
    Write-Host "No deployable changed files detected. Skipping FTP upload."
}
else {
    Write-Host "No deployable changed files detected. Running full deploy."
    Walk-RemoteDirs ""
}
Write-Host "Done."
