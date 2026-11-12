
import json
from pathlib import Path

# 1. Définir les emplacements des fichiers
RAW_FILE = Path("/data/raw/yelp_academic_dataset_business.json")
OUTPUT_FILE = Path("/data/processed/businesses.jsonl")

# 2. Préparer les compteurs
total = 0
selected = 0

# 3. Créer le dossier de sortie si nécessaire
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# 4. Lire les établissements un par un
with RAW_FILE.open("r", encoding="utf-8") as source:
    with OUTPUT_FILE.open("w", encoding="utf-8") as output:

        for line in source:
            total += 1
            business = json.loads(line)

            # 5. Normaliser la ville et l'État
            city = str(business.get("city") or "").strip().casefold()
            state = str(business.get("state") or "").strip().upper()

            # 6. Conserver uniquement Tucson, Arizona
            if city != "tucson" or state != "AZ":
                continue

            # 7. Transformer les catégories en tableau
            categories = business.get("categories") or ""
            business["categories"] = [
                category.strip()
                for category in categories.split(",")
                if category.strip()
            ]

            # 8. Créer la localisation GeoJSON
            latitude = business.get("latitude")
            longitude = business.get("longitude")

            if latitude is not None and longitude is not None:
                if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                    business["location"] = {
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    }

            # 9. Uniformiser la ville et l'État
            business["city"] = "Tucson"
            business["state"] = "AZ"

            # 10. Enregistrer l'établissement sélectionné
            output.write(json.dumps(business, ensure_ascii=False) + "\n")
            selected += 1

# 11. Afficher le résultat
print("Total des établissements :", total)
print("Établissements Tucson :", selected)
print("Fichier créé :", OUTPUT_FILE)
