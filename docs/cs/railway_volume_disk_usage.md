# Railway – co zabírá místo na volume

Když promazávání přes konzoli nic nezměnilo, zjistěte, které složky/soubory berou místo.

## 1. Otevřete shell v Railway

Railway Dashboard → Open WebUI service → **Settings** → **Deploy** → možnost spustit shell / **Run Command** (nebo **Console** / **Terminal** podle verze Railway).

## 2. Příkazy pro diagnostiku

### Celkové využití disku
```bash
df -h
```

### Kde je data Open WebUI
Typická cesta v Dockeru: `/app/backend/data`  
(pokud máte vlastní `DATA_DIR` v env, použijte tu)

```bash
# Celková velikost data složky
du -sh /app/backend/data

# Velikost po podadresářích (vidíte, co bere nejvíc)
du -sh /app/backend/data/* 2>/dev/null

# Detailní pohled – největší složky nahoře
du -h /app/backend/data 2>/dev/null | sort -hr | head -30
```

### Typická struktura a co zabírá místo

| Složka/soubor | Obsah |
|---------------|--------|
| `uploads/` | Nahrané soubory (obrázky, dokumenty) – často největší |
| `vector_db/` | Chroma/embeddingy pro RAG – může mít stovky MB |
| `cache/` | Cache (embeddingy, modely) |
| `webui.db` | SQLite databáze – chaty, uživatelé, nastavení |
| `audit.log` | Audit log |

### Konkrétní příkazy
```bash
# Velikost uploadů
du -sh /app/backend/data/uploads 2>/dev/null

# Velikost vector DB (RAG embeddingy)
du -sh /app/backend/data/vector_db 2>/dev/null

# Velikost cache
du -sh /app/backend/data/cache 2>/dev/null

# Velikost databáze
ls -lh /app/backend/data/webui.db 2>/dev/null
```

## 3. Co lze smazat (POZOR – ztráta dat)

- **`cache/`** – relativně bezpečné, cache se znovu vytvoří
- **`vector_db/`** – smazáním ztratíte RAG embeddingy (bude potřeba znovu načíst dokumenty)
- **`uploads/`** – smazáním ztratíte nahrané soubory
- **`webui.db`** – databáze, neodstraňovat bez zálohy

### Příklad: vyprázdnit cache
```bash
rm -rf /app/backend/data/cache/*
```

### Příklad: vyprázdnit vector DB (RAG)
```bash
rm -rf /app/backend/data/vector_db/*
```

### Příklad: zjistit největší soubory
```bash
find /app/backend/data -type f -exec du -h {} + 2>/dev/null | sort -hr | head -20
```

## 4. Pokud DATA_DIR není výchozí

Zkontrolujte env `DATA_DIR`. Pokud je nastavená, použijte její cestu místo `/app/backend/data`:

```bash
echo $DATA_DIR
du -sh $DATA_DIR/* 2>/dev/null
```

## 5. Railway volume vs. ephemeral storage

- **Volume**: data zůstávají mezi deployi. Mazání v konzoli maže data v běžícím kontejneru – pokud je volume připojený, změny zůstanou.
- **Ephemeral**: po restaru kontejneru se disk znovu vytvoří.
- Pokud po mazání vidíte stejné využití, ověřte:
  1. Zda jste mazali ve správném kontejneru/službě.
  2. Zda volume používá skutečně `/app/backend/data` (ne jinou cestu).
  3. Zda nedošlo k novému deployi nebo restartu hned po mazání.
