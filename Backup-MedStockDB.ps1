#requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

# 1. Проверка пароля суперпользователя
if ([string]::IsNullOrWhiteSpace($env:PGSUPERUSER_PASSWORD)) {
    Write-Error "ERROR: Missing environment variable PGSUPERUSER_PASSWORD"
    exit 1
}

Write-Host "[INFO] Starting backup of medstock_db..." -ForegroundColor Cyan

# 2. Поиск pg_dump.exe
$pgDumpPath = Get-ChildItem -Path "C:\Program Files\PostgreSQL" -Filter "pg_dump.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (-not $pgDumpPath) {
    Write-Error "pg_dump.exe not found. Please check PostgreSQL installation."
    exit 1
}

# 3. Подготовка директории для бэкапов
$backupDir = "C:\MedStock\backups"
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}

# Имя файла с текущей датой и временем
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "$backupDir\medstock_db_$timestamp.backup"

# 4. Выполнение бэкапа
$env:PGPASSWORD = $env:PGSUPERUSER_PASSWORD
try {
    $process = Start-Process -FilePath $pgDumpPath `
        -ArgumentList "-U", "postgres", "-d", "medstock_db", "-Fc", "-f", $backupFile `
        -NoNewWindow -Wait -PassThru

    if ($process.ExitCode -ne 0) {
        throw "pg_dump failed with exit code: $($process.ExitCode)"
    }

    Write-Host "`n[SUCCESS] Backup created successfully!" -ForegroundColor Green
    Write-Host "File: $backupFile"
    Write-Host "Size: $([math]::Round((Get-Item $backupFile).Length / 1KB, 2)) KB"
} finally {
    $env:PGPASSWORD = $null
}