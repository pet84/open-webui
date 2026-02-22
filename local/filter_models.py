#!/usr/bin/env python3
"""
Skript pro filtrování modelů - nechá jen nejnovější verze a PRO/mini/nano/codex varianty.
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

def extract_model_family(model_id):
    """Extrahuje rodinu modelu (např. 'gpt-4o', 'claude-3', atd.)"""
    # Odstraní datum a verze
    base = re.sub(r'-\d{4}-\d{2}-\d{2}', '', model_id)
    base = re.sub(r'-\d{4}-\d{2}', '', base)
    base = re.sub(r'-preview$', '', base)
    base = re.sub(r'-latest$', '', base)
    
    # Najde základní název (před první číslicí nebo variantou)
    match = re.match(r'^([a-z]+(?:-[a-z]+)*)', base.lower())
    if match:
        family = match.group(1)
        # Odstraní varianty pro porovnání
        family = re.sub(r'-(pro|mini|nano|codex|audio|realtime|search|transcribe|image)$', '', family)
        return family
    return base.lower()

def extract_variant(model_id):
    """Extrahuje variantu modelu (pro, mini, nano, codex, atd.)"""
    variants = ['pro', 'mini', 'nano', 'codex', 'audio', 'realtime', 'search', 'transcribe', 'image']
    model_lower = model_id.lower()
    for variant in variants:
        if f'-{variant}' in model_lower:
            return variant
    return 'base'

def extract_version(model_id):
    """Extrahuje číselnou verzi modelu (např. 4.1, 5.2, atd.)"""
    # Hledá pattern typu "gpt-4.1", "gpt-5.2", atd.
    match = re.search(r'(\d+)\.(\d+)', model_id)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2))
        return (major, minor)
    
    # Hledá pattern typu "gpt-4o", "gpt-4", atd.
    match = re.search(r'(\d+)([a-z]*)', model_id)
    if match:
        major = int(match.group(1))
        letter = match.group(2)
        # Konvertuje písmeno na číslo (a=1, b=2, atd.)
        minor = ord(letter) - ord('a') + 1 if letter else 0
        return (major, minor)
    
    return (0, 0)

def extract_date(model_id):
    """Extrahuje datum z model_id (pokud existuje)"""
    # Hledá pattern YYYY-MM-DD nebo YYYY-MM
    date_match = re.search(r'(\d{4})-(\d{2})(?:-(\d{2}))?', model_id)
    if date_match:
        year = int(date_match.group(1))
        month = int(date_match.group(2))
        day = int(date_match.group(3)) if date_match.group(3) else 1
        try:
            return datetime(year, month, day)
        except:
            return None
    return None

def should_keep_model(model, family_models):
    """Rozhodne, jestli má být model zachován"""
    model_id = model['id'].lower()
    variant = extract_variant(model_id)
    version = extract_version(model_id)
    date = extract_date(model_id)
    
    # Vždy zachovat PRO, mini, nano, codex varianty
    if variant in ['pro', 'mini', 'nano', 'codex']:
        return True
    
    # Vždy zachovat specializované varianty (audio, realtime, search, transcribe, image)
    if variant in ['audio', 'realtime', 'search', 'transcribe', 'image']:
        return True
    
    # Pro základní modely - najít nejnovější verzi
    base_models = [m for m in family_models if extract_variant(m['id'].lower()) == 'base']
    
    if not base_models:
        return True
    
    # Seřadit podle verze (nejnovější první), pak podle data
    base_models_sorted = sorted(
        base_models,
        key=lambda m: (
            extract_version(m['id'].lower()),
            extract_date(m['id'].lower()) or datetime.max,  # Modely bez data mají prioritu
            m['id'].lower()
        ),
        reverse=True
    )
    
    # Najít nejnovější verzi
    latest_model = base_models_sorted[0]
    latest_version = extract_version(latest_model['id'].lower())
    latest_date = extract_date(latest_model['id'].lower())
    current_version = extract_version(model_id)
    current_date = extract_date(model_id)
    
    # Pokud je to nejnovější verze
    if current_version > latest_version:
        return True
    
    if current_version == latest_version:
        # Pokud má stejnou verzi jako nejnovější
        # Preferovat modely bez data (latest) před modely s datem
        if current_date is None and latest_date is not None:
            return True  # Tento model je "latest" verze
        elif current_date is not None and latest_date is None:
            return False  # Nejnovější je "latest" bez data
        elif current_date is None and latest_date is None:
            # Oba jsou "latest" - zachovat oba nebo ten s kratším názvem
            return model_id == latest_model['id'].lower() or 'latest' in model_id
        else:
            # Oba mají datum - zachovat ten s nejnovějším datem
            if current_date >= latest_date:
                # Pokud je to stejné nebo novější datum, zachovat
                same_date_models = [m for m in base_models 
                                  if extract_version(m['id'].lower()) == current_version 
                                  and extract_date(m['id'].lower()) == current_date]
                if len(same_date_models) > 1:
                    # Pokud je více modelů se stejným datem, zachovat ten s kratším názvem (bez suffixů)
                    same_date_models_sorted = sorted(same_date_models, key=lambda m: len(m['id']))
                    return model_id == same_date_models_sorted[0]['id'].lower()
                return True
            return False
    
    return False

def filter_models(input_file, output_file):
    """Filtruje modely a vytvoří nový JSON soubor"""
    print(f"Načítám modely z {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        models = json.load(f)
    
    print(f"Celkem modelů: {len(models)}")
    
    # Seskupit modely podle rodiny
    families = defaultdict(list)
    for model in models:
        family = extract_model_family(model['id'])
        families[family].append(model)
    
    print(f"Nalezeno {len(families)} rodin modelů")
    
    # Filtrovat modely - nastavit is_active: false místo mazání
    all_models = []
    active_count = 0
    inactive_count = 0
    
    for family, family_models in families.items():
        print(f"\nRodina: {family} ({len(family_models)} modelů)")
        
        for model in family_models:
            if should_keep_model(model, family_models):
                # Zachovat model jako aktivní
                model['is_active'] = True
                all_models.append(model)
                active_count += 1
                print(f"  [+] Aktivni: {model['id']}")
            else:
                # Nastavit jako neaktivní, ale zachovat v souboru
                model['is_active'] = False
                all_models.append(model)
                inactive_count += 1
                print(f"  [-] Neaktivni: {model['id']}")
    
    print(f"\n\nVýsledek:")
    print(f"  Aktivních: {active_count} modelů")
    print(f"  Neaktivních: {inactive_count} modelů")
    print(f"  Celkem: {len(all_models)} modelů (všechny zachovány)")
    
    # Uložit všechny modely (s is_active nastaveným)
    print(f"\nUkládám do {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_models, f, indent=2, ensure_ascii=False)
    
    print("Hotovo!")

if __name__ == '__main__':
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'd:\\Download\\models-export-1768082807484.json'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'd:\\Download\\models-filtered.json'
    
    filter_models(input_file, output_file)
