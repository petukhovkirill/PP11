#requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

# 1. Проверка пароля
if ([string]::IsNullOrWhiteSpace($env:PGSUPERUSER_PASSWORD)) {
    Write-Error "ERROR: Missing environment variable PGSUPERUSER_PASSWORD"
    exit 1
}

# 2. Автоматический поиск последнего файла бэкапа
$backupDir = "C:\MedStock\backups"
if (-not (Test-Path $backupDir)) {
    Write-Error "Backup directory not found: $backupDir"
    exit 1
}

$latestBackup = Get-ChildItem -Path $backupDir -Filter "*.backup" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $latestBackup) {
    Write-Error "No .backup files found in $backupDir"
    exit 1
}

$backupFile = $latestBackup.FullName
Write-Host "[INFO] Found latest backup: $backupFile" -ForegroundColor Cyan

# 3. Поиск утилит psql и pg_restore
$psqlPath = Get-ChildItem -Path "C:\Program Files\PostgreSQL" -Filter "psql.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
$pgRestorePath = Get-ChildItem -Path "C:\Program Files\PostgreSQL" -Filter "pg_restore.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName

if (-not $psqlPath -or -not $pgRestorePath) {
    Write-Error "PostgreSQL utilities not found."
    exit 1
}

$env:PGPASSWORD = $env:PGSUPERUSER_PASSWORD
try {
    # Шаг А: Принудительное отключение всех активных сессий от базы
    Write-Host "[INFO] Terminating active connections to medstock_db..." -ForegroundColor Yellow
    $terminateSql = "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'medstock_db' AND pid <> pg_backend_pid();"
    Start-Process -FilePath $psqlPath -ArgumentList "-U", "postgres", "-c", $terminateSql -NoNewWindow -Wait | Out-Null

    # Шаг Б: Восстановление базы
    Write-Host "[INFO] Restoring database..." -ForegroundColor Yellow
    $process = Start-Process -FilePath $pgRestorePath `
        -ArgumentList "-U", "postgres", "-d", "medstock_db", "--clean", "--if-exists", $backupFile `
        -NoNewWindow -Wait -PassThru

    if ($process.ExitCode -ne 0) {
        throw "pg_restore failed with exit code: $($process.ExitCode)"
    }

    Write-Host "`n[SUCCESS] Database restored successfully!" -ForegroundColor Green
} finally {
    $env:PGPASSWORD = $null
}