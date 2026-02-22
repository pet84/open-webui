#!/bin/bash
# Reset Open WebUI Data - Bash Script
# Tento skript smaže všechna data Open WebUI pro lokální vývoj

echo "⚠️  VAROVÁNÍ: Tento skript smaže všechna data Open WebUI!"
echo "Smaže se: databáze, konfigurace, chaty, uživatelé, soubory"
echo ""

read -p "Opravdu chcete pokračovat? (ano/ne): " confirm

if [ "$confirm" != "ano" ]; then
    echo "Zrušeno."
    exit 0
fi

# Najít data složku
DATA_DIRS=(
    "backend/data"
    "$HOME/.open-webui"
    "./data"
)

FOUND_DIR=""
for dir in "${DATA_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        FOUND_DIR="$dir"
        break
    fi
done

if [ -z "$FOUND_DIR" ]; then
    echo "❌ Data složka nenalezena. Zkontrolujte, že Open WebUI běžel alespoň jednou."
    exit 1
fi

echo "📁 Nalezena data složka: $FOUND_DIR"

# Zobrazit, co bude smazáno
echo ""
echo "Obsah složky:"
ls -la "$FOUND_DIR" 2>/dev/null | tail -n +2 | awk '{print "  - " $9}'
echo ""

# Smazat obsah
echo "🗑️  Mažu data..."
rm -rf "$FOUND_DIR"/* 2>/dev/null
rm -rf "$FOUND_DIR"/.* 2>/dev/null  # Skryté soubory (kromě . a ..)

if [ $? -eq 0 ]; then
    echo "✅ Data byla úspěšně smazána!"
    echo ""
    echo "Nyní můžete restartovat Open WebUI a začít od nuly."
else
    echo "❌ Chyba při mazání dat."
    exit 1
fi

# Docker reset (pokud běží)
if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "open-webui"; then
    echo ""
    echo "🐳 Detekován Docker kontejner. Chcete také resetovat Docker volume? (ano/ne)"
    read docker_confirm
    
    if [ "$docker_confirm" = "ano" ]; then
        echo "Zastavuji Docker kontejnery..."
        docker-compose down 2>/dev/null
        
        echo "Mažu Docker volume..."
        docker volume rm open-webui_open-webui 2>/dev/null
        
        echo "✅ Docker volume smazán!"
        echo "Spusťte znovu: docker-compose up -d"
    fi
fi

echo ""
echo "✨ Hotovo! Open WebUI je připraveno k resetu."
