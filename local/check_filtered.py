#!/usr/bin/env python3
import json

# Načíst oba soubory
with open('d:\\Download\\models-filtered.json', 'r', encoding='utf-8') as f:
    filtered = json.load(f)

with open('d:\\Download\\models-export-1768082807484.json', 'r', encoding='utf-8') as f:
    original = json.load(f)

print(f"Puvodni modely: {len(original)}")
print(f"Filtrovane modely: {len(filtered)}")
print(f"Odstraneno: {len(original) - len(filtered)}")
print()

# Zkontrolovat is_active
print("Prvni 5 filtrovanych modelu:")
for m in filtered[:5]:
    print(f"  {m['id']} - is_active: {m.get('is_active', 'N/A')}")

print()
print("Zkontrolovat, jestli jsou modely jen promazane nebo odstranene:")
original_ids = {m['id'] for m in original}
filtered_ids = {m['id'] for m in filtered}
removed_ids = original_ids - filtered_ids

print(f"Odstraneno ID: {len(removed_ids)}")
print("Prvni 10 odstranenych:")
for id in list(removed_ids)[:10]:
    print(f"  {id}")
