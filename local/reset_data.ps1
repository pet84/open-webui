# Reset Open WebUI Data - PowerShell Script
# Tento skript smaže všechna data Open WebUI pro lokální vývoj

Write-Host "⚠️  VAROVÁNÍ: Tento skript smaže všechna data Open WebUI!" -ForegroundColor Red
Write-Host "Smaže se: databáze, konfigurace, chaty, uživatelé, soubory" -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Opravdu chcete pokračovat? (ano/ne)"

if ($confirm -ne "ano") {
    Write-Host "Zrušeno." -ForegroundColor Green
    exit
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
    Write-Host "❌ Data složka nenalezena. Zkontrolujte, že Open WebUI běžel alespoň jednou." -ForegroundColor Red
    exit 1
}

Write-Host "📁 Nalezena data složka: $foundDataDir" -ForegroundColor Cyan

# Zobrazit, co bude smazáno
Write-Host "`nObsah složky:" -ForegroundColor Yellow
Get-ChildItem $foundDataDir -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  - $($_.Name)" -ForegroundColor Gray
}

Write-Host ""

# Smazat obsah
try {
    Write-Host "🗑️  Mažu data..." -ForegroundColor Yellow
    
    Get-ChildItem $foundDataDir -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    
    Write-Host "✅ Data byla úspěšně smazána!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Nyní můžete restartovat Open WebUI a začít od nuly." -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Chyba při mazání: $_" -ForegroundColor Red
    exit 1
}

# Docker reset (pokud běží)
$dockerRunning = docker ps -a --filter "name=open-webui" --format "{{.Names}}" 2>$null
if ($dockerRunning) {
    Write-Host "`n🐳 Detekován Docker kontejner. Chcete také resetovat Docker volume? (ano/ne)" -ForegroundColor Cyan
    $dockerConfirm = Read-Host
    
    if ($dockerConfirm -eq "ano") {
        Write-Host "Zastavuji Docker kontejnery..." -ForegroundColor Yellow
        docker-compose down 2>$null
        
        Write-Host "Mažu Docker volume..." -ForegroundColor Yellow
        docker volume rm open-webui_open-webui 2>$null
        
        Write-Host "✅ Docker volume smazán!" -ForegroundColor Green
        Write-Host "Spusťte znovu: docker-compose up -d" -ForegroundColor Cyan
    }
}

Write-Host "`n✨ Hotovo! Open WebUI je připraveno k resetu." -ForegroundColor Green
