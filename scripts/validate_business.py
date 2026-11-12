
import json
from pathlib import Path

# Fichier produit par filter_business.py
INPUT_FILE = Path("/data/processed/businesses.jsonl")

# Compteurs de validation
total = 0
duplicate_ids = 0
invalid_cities = 0
invalid_categories = 0
missing_coordinates = 0
invalid_coordinates = 0

business_ids = set()

with INPUT_FILE.open("r", encoding="utf-8") as file:
    for line in file:
        if not line.strip():
            continue

        business = json.loads(line)
        total += 1

        # Vérifier que business_id existe et est unique
        business_id = business.get("business_id")

        if not business_id or business_id in business_ids:
            duplicate_ids += 1
        else:
            business_ids.add(business_id)

        # Vérifier la ville et l'État
        if business.get("city") != "Tucson" or business.get("state") != "AZ":
            invalid_cities += 1

        # Vérifier que categories est un tableau
        if not isinstance(business.get("categories"), list):
            invalid_categories += 1

        # Vérifier les coordonnées GeoJSON
        location = business.get("location")

        if location is None:
            missing_coordinates += 1
            continue

        if not isinstance(location, dict):
            invalid_coordinates += 1
            continue

        coords = location.get("coordinates")

        if (
            location.get("type") != "Point"
            or not isinstance(coords, list)
            or len(coords) != 2
            or any(type(c) not in (int, float) for c in coords)
            or not (-180 <= coords[0] <= 180)
            or not (-90 <= coords[1] <= 90)
        ):
            invalid_coordinates += 1

print("\n=== VALIDATION BUSINESS ===")
print("Établissements analysés :", total)
print("Identifiants absents ou dupliqués :", duplicate_ids)
print("Villes incorrectes :", invalid_cities)
print("Catégories incorrectes :", invalid_categories)
print("Coordonnées manquantes :", missing_coordinates)
print("Coordonnées invalides :", invalid_coordinates)

errors = (
    duplicate_ids
    + invalid_cities
    + invalid_categories
    + missing_coordinates
    + invalid_coordinates
)

if total == 0 or errors > 0:
    print("Statut : FAIL")
    raise SystemExit(1)
else:
    print("Statut : PASS")
