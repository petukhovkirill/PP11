#requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$WarningPreference = 'Continue'

# 1. Проверка переменных окружения
$requiredVars = @('STOCK_ADMIN_PASSWORD', 'STOCK_APP_PASSWORD', 'PGSUPERUSER_PASSWORD')
$missingVars = $requiredVars | Where-Object { [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($_)) }

if ($missingVars.Count -gt 0) {
    Write-Error "ERROR: Missing environment variables: $($missingVars -join ', ')"
    Write-Host "Example setup in PowerShell:"
    Write-Host "`$env:PGSUPERUSER_PASSWORD = '1234'"
    Write-Host "`$env:STOCK_ADMIN_PASSWORD = 'AdminPass456!'"
    Write-Host "`$env:STOCK_APP_PASSWORD = 'AppPass789!'"
    exit 1
}

Write-Host "[INFO] Environment variables verified. Starting deployment..." -ForegroundColor Cyan

# 2. Установка PostgreSQL (unattended mode)
try {
    Write-Host "[INFO] Installing PostgreSQL via winget (unattended)..." -ForegroundColor Yellow
    $wingetResult = winget install --id PostgreSQL.PostgreSQL --silent --accept-package-agreements --accept-source-agreements 2>&1
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1000) { 
        Write-Warning "winget returned code $LASTEXITCODE. If PostgreSQL is not installed, run the script after manual installation."
    }
} catch {
    Write-Warning "winget is unavailable. Assuming PostgreSQL is already installed manually."
}

# 3. Ожидание запуска службы
Write-Host "[INFO] Waiting for PostgreSQL service initialization..." -ForegroundColor Yellow
$maxWait = 60
$waited = 0
do {
    $pgService = Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue
    if ($pgService -and $pgService.Status -eq 'Running') { break }
    Start-Sleep -Seconds 2
    $waited += 2
} while ($waited -lt $maxWait)

if (-not $pgService -or $pgService.Status -ne 'Running') {
    Write-Error "PostgreSQL service did not start within $maxWait seconds. Please check the installation."
    exit 1
}

# 4. Поиск psql.exe
$psqlPath = Get-ChildItem -Path "C:\Program Files\PostgreSQL" -Filter "psql.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (-not $psqlPath) {
    Write-Error "psql.exe not found. Please check the PostgreSQL installation path."
    exit 1
}
Write-Host "[INFO] psql.exe found at: $psqlPath" -ForegroundColor Green

# 5. Формирование SQL-скрипта
$sqlFile = [System.IO.Path]::GetTempFileName()
try {
    $sqlContent = @'
CREATE USER stock_admin WITH PASSWORD '__ADMIN_PASS__' CREATEDB;
CREATE DATABASE medstock_db OWNER stock_admin;
CREATE USER stock_app WITH PASSWORD '__APP_PASS__';
\c medstock_db
GRANT CONNECT ON DATABASE medstock_db TO stock_app;
GRANT USAGE ON SCHEMA public TO stock_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO stock_app;
ALTER DEFAULT PRIVILEGES FOR ROLE stock_admin IN SCHEMA public
GRANT SELECT, INSERT, UPDATE ON TABLES TO stock_app;
'@
    
    $sqlContent = $sqlContent.Replace('__ADMIN_PASS__', $env:STOCK_ADMIN_PASSWORD)
    $sqlContent = $sqlContent.Replace('__APP_PASS__', $env:STOCK_APP_PASSWORD)

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($sqlFile, $sqlContent, $utf8NoBom)

    # 6. Выполнение инициализации
    $env:PGPASSWORD = $env:PGSUPERUSER_PASSWORD
    Write-Host "[INFO] Initializing database and users..." -ForegroundColor Yellow

    $process = Start-Process -FilePath $psqlPath `
        -ArgumentList "-U", "postgres", "-v", "ON_ERROR_STOP=1", "-f", $sqlFile `
        -NoNewWindow -Wait -PassThru

    if ($process.ExitCode -ne 0) {
        throw "psql returned error code: $($process.ExitCode)"
    }

    Write-Host "`n[SUCCESS] MedStock DB installation and configuration completed!" -ForegroundColor Green
    Write-Host "Database: medstock_db"
    Write-Host "Admin: stock_admin (full owner rights)"
    Write-Host "App: stock_app (SELECT, INSERT, UPDATE only)"
    
} finally {
    if (Test-Path $sqlFile) {
        Remove-Item -Path $sqlFile -Force -ErrorAction SilentlyContinue
        Write-Host "[INFO] Temporary SQL file securely deleted." -ForegroundColor Gray
    }
    $env:PGPASSWORD = $null
}