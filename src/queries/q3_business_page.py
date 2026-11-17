import os
from pymongo import MongoClient

# Connexion à MongoDB via notre environnement Docker
client = MongoClient(os.environ["MONGO_URI"])
db = client[os.environ["MONGO_DATABASE"]]

# Identifiant du commerce à rechercher
business_id = input("Entrez le Business ID : ").strip()

# Q3 : récupérer la fiche d'un établissement
business = db.businesses.find_one(
    {"_id": business_id},
    {
        "_id": 1,
        "name": 1,
        "address": 1,
        "stars": 1,
        "categories": 1,
        "hours": 1,
        "attributes": 1
    }
)

if business is None:
    print("Établissement introuvable.")
else:
    print("=== FICHE ÉTABLISSEMENT ===")
    print("Nom :", business.get("name"))
    print("Adresse :", business.get("address"))
    print("Note :", business.get("stars"))
    print("Catégories :", business.get("categories"))
    print("Horaires :", business.get("hours"))
    print("Attributs :", business.get("attributes"))

client.close()