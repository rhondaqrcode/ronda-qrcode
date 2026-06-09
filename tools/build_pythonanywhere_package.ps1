param(
    [string]$OutputPath = "dist_pythonanywhere\ronda-pythonanywhere.zip"
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$absoluteOutput = Join-Path $root $OutputPath
$staging = Join-Path $root "dist_pythonanywhere\staging"

if (Test-Path $staging) {
    Remove-Item -LiteralPath $staging -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $staging | Out-Null

$excludeDirs = @(
    ".git",
    ".idea",
    ".pytest_cache",
    ".streamlit",
    ".venv",
    "__pycache__",
    "backups",
    "dart_local_cache",
    "dist_pythonanywhere",
    "mobile",
    "media",
    "node_modules",
    "venv",
    "tools\python313",
    "tools\wheels"
)

$excludeFiles = @(
    ".env",
    "*.db",
    "*.log",
    "*.pyc",
    "*.pyo",
    "*.pid",
    "*.job",
    "manual_fortguard.pdf",
    "MANUAL_USO_SISTEMA_RONDA_QRCODE.pdf",
    "tools\get-pip.py",
    "tools\pip-25.3-py3-none-any.whl",
    "tools\python-3.13.0-embed-amd64.zip"
)

function Test-IsExcludedDir {
    param([string]$RelativePath)
    foreach ($dir in $excludeDirs) {
        if ($RelativePath -eq $dir -or $RelativePath.StartsWith("$dir\")) {
            return $true
        }
    }
    return $false
}

function Test-IsExcludedFile {
    param([string]$RelativePath)
    foreach ($pattern in $excludeFiles) {
        if ($RelativePath -like $pattern) {
            return $true
        }
    }
    if ($RelativePath.StartsWith("uploads\") -and $RelativePath -ne "uploads\.gitkeep") {
        return $true
    }
    if ($RelativePath.StartsWith("reports\") -and $RelativePath -ne "reports\.gitkeep") {
        return $true
    }
    return $false
}

Get-ChildItem -Path $root -Recurse -File | ForEach-Object {
    $relative = $_.FullName.Substring($root.Path.Length + 1)
    if (Test-IsExcludedDir $relative) {
        return
    }
    if (Test-IsExcludedFile $relative) {
        return
    }

    $destination = Join-Path $staging $relative
    $destinationDir = Split-Path $destination -Parent
    New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
}

New-Item -ItemType Directory -Force -Path (Split-Path $absoluteOutput -Parent) | Out-Null
if (Test-Path $absoluteOutput) {
    Remove-Item -LiteralPath $absoluteOutput -Force
}
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $absoluteOutput -Force
Remove-Item -LiteralPath $staging -Recurse -Force

Write-Host "Pacote criado em: $absoluteOutput"
