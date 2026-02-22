# Backup Open WebUI Data - PowerShell Script
# Tento skript zálohuje všechna data Open WebUI

param(
    [string]$OutputPath = ".\backups",
    [switch]$Compress = $true
)

Write-Host "📦 Zálohování Open WebUI dat" -ForegroundColor Cyan
Write-Host ""

# Vytvořit složku pro zálohy
if (-not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath | Out-Null
    Write-Host "✅ Vytvořena složka: $OutputPath" -ForegroundColor Green
}

# Najít data složku
$dataDirs = @(
    "backend\data",
    "$env:USERPROFILE\.open-webui",
    ".\data"
)

$foundDataDir = $null
foreach ($dir in $dataDirs) {
    if (Test-Path $dir) {
        $foundDataDir = $dir
        break
    }
}

if (-not $foundDataDir) {
    Write-Host "❌ Data složka nenalezena." -ForegroundColor Red
    Write-Host "Zkontrolujte, že Open WebUI běžel alespoň jednou." -ForegroundColor Yellow
    exit 1
}

Write-Host "📁 Nalezena data složka: $foundDataDir" -ForegroundColor Cyan

# Vytvořit název zálohy s datumem
$timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
$backupName = "open-webui-backup-$timestamp"

# Zálohovat
try {
    Write-Host "🔄 Kopíruji data..." -ForegroundColor Yellow
    
    $backupPath = Join-Path $OutputPath $backupName
    
    # Zkopírovat celou složku
    Copy-Item -Recurse -Path $foundDataDir -Destination $backupPath -Force
    
    Write-Host "✅ Data zkopírována do: $backupPath" -ForegroundColor Green
    
    # Komprimovat (volitelné)
    if ($Compress) {
        Write-Host "🗜️  Komprimuji zálohu..." -ForegroundColor Yellow
        $zipPath = "$backupPath.zip"
        Compress-Archive -Path $backupPath -DestinationPath $zipPath -Force
        
        # Smazat nekomprimovanou složku
        Remove-Item -Recurse -Force $backupPath
        
        Write-Host "✅ Záloha vytvořena: $zipPath" -ForegroundColor Green
        
        # Zobrazit velikost
        $size = (Get-Item $zipPath).Length / 1MB
        Write-Host "📊 Velikost zálohy: $([math]::Round($size, 2)) MB" -ForegroundColor Cyan
    } else {
        Write-Host "✅ Záloha vytvořena: $backupPath" -ForegroundColor Green
        
        # Zobrazit velikost
        $size = (Get-ChildItem $backupPath -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Host "📊 Velikost zálohy: $([math]::Round($size, 2)) MB" -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Host "✨ Zálohování dokončeno!" -ForegroundColor Green
    
} catch {
    Write-Host "❌ Chyba při zálohování: $_" -ForegroundColor Red
    exit 1
}

# Docker backup (pokud běží)
$dockerRunning = docker ps -a --filter "name=open-webui" --format "{{.Names}}" 2>$null
if ($dockerRunning) {
    Write-Host ""
    Write-Host "🐳 Detekován Docker kontejner. Chcete také zálohovat Docker volume? (ano/ne)" -ForegroundColor Cyan
    $dockerConfirm = Read-Host
    
    if ($dockerConfirm -eq "ano") {
        $containerId = docker ps --filter "name=open-webui" --format "{{.ID}}" | Select-Object -First 1
        
        if ($containerId) {
            Write-Host "Kopíruji data z Docker kontejneru..." -ForegroundColor Yellow
            $dockerBackupPath = Join-Path $OutputPath "docker-$backupName"
            
            docker cp "${containerId}:/app/backend/data" $dockerBackupPath 2>$null
            
            if ($Compress) {
                $dockerZipPath = "$dockerBackupPath.zip"
                Compress-Archive -Path $dockerBackupPath -DestinationPath $dockerZipPath -Force
                Remove-Item -Recurse -Force $dockerBackupPath
                Write-Host "✅ Docker záloha: $dockerZipPath" -ForegroundColor Green
            } else {
                Write-Host "✅ Docker záloha: $dockerBackupPath" -ForegroundColor Green
            }
        }
    }
}

Write-Host ""
Write-Host "💡 Tip: Zálohy najdete ve složce: $OutputPath" -ForegroundColor Cyan
