#!/bin/bash
# Backup Open WebUI Data - Bash Script
# Tento skript zálohuje všechna data Open WebUI

OUTPUT_PATH="${1:-./backups}"
COMPRESS="${2:-true}"

echo "📦 Zálohování Open WebUI dat"
echo ""

# Vytvořit složku pro zálohy
mkdir -p "$OUTPUT_PATH"
echo "✅ Složka pro zálohy: $OUTPUT_PATH"

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
    echo "❌ Data složka nenalezena."
    echo "Zkontrolujte, že Open WebUI běžel alespoň jednou."
    exit 1
fi

echo "📁 Nalezena data složka: $FOUND_DIR"

# Vytvořit název zálohy s datumem
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
BACKUP_NAME="open-webui-backup-$TIMESTAMP"
BACKUP_PATH="$OUTPUT_PATH/$BACKUP_NAME"

# Zálohovat
echo "🔄 Kopíruji data..."
cp -r "$FOUND_DIR" "$BACKUP_PATH"

if [ $? -eq 0 ]; then
    echo "✅ Data zkopírována do: $BACKUP_PATH"
    
    # Komprimovat (volitelné)
    if [ "$COMPRESS" = "true" ]; then
        echo "🗜️  Komprimuji zálohu..."
        ZIP_PATH="$BACKUP_PATH.tar.gz"
        tar -czf "$ZIP_PATH" -C "$OUTPUT_PATH" "$BACKUP_NAME"
        
        # Smazat nekomprimovanou složku
        rm -rf "$BACKUP_PATH"
        
        echo "✅ Záloha vytvořena: $ZIP_PATH"
        
        # Zobrazit velikost
        SIZE=$(du -h "$ZIP_PATH" | cut -f1)
        echo "📊 Velikost zálohy: $SIZE"
    else
        echo "✅ Záloha vytvořena: $BACKUP_PATH"
        
        # Zobrazit velikost
        SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)
        echo "📊 Velikost zálohy: $SIZE"
    fi
    
    echo ""
    echo "✨ Zálohování dokončeno!"
else
    echo "❌ Chyba při zálohování."
    exit 1
fi

# Docker backup (pokud běží)
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "open-webui"; then
    echo ""
    echo "🐳 Detekován Docker kontejner. Chcete také zálohovat Docker volume? (ano/ne)"
    read docker_confirm
    
    if [ "$docker_confirm" = "ano" ]; then
        CONTAINER_ID=$(docker ps --filter "name=open-webui" --format "{{.ID}}" | head -n 1)
        
        if [ -n "$CONTAINER_ID" ]; then
            echo "Kopíruji data z Docker kontejneru..."
            DOCKER_BACKUP_PATH="$OUTPUT_PATH/docker-$BACKUP_NAME"
            
            docker cp "${CONTAINER_ID}:/app/backend/data" "$DOCKER_BACKUP_PATH" 2>/dev/null
            
            if [ "$COMPRESS" = "true" ]; then
                DOCKER_ZIP_PATH="$DOCKER_BACKUP_PATH.tar.gz"
                tar -czf "$DOCKER_ZIP_PATH" -C "$OUTPUT_PATH" "docker-$BACKUP_NAME"
                rm -rf "$DOCKER_BACKUP_PATH"
                echo "✅ Docker záloha: $DOCKER_ZIP_PATH"
            else
                echo "✅ Docker záloha: $DOCKER_BACKUP_PATH"
            fi
        fi
    fi
fi

echo ""
echo "💡 Tip: Zálohy najdete ve složce: $OUTPUT_PATH"
