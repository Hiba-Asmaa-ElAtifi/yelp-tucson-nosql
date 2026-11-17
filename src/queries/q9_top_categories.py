
from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGO_URI = "mongodb://mongodb:27017/"
DB_NAME = "yelp_tucson"


def top_categories(db):
    print("\nQ9 — CATÉGORIES LES MIEUX NOTÉES")

    try:
        minimum = int(
            input("Nombre minimum d'établissements par catégorie [20] : ") or "20"
        )
        limite = int(
            input("Nombre de catégories à afficher [10] : ") or "10"
        )
    except ValueError:
        print("Veuillez saisir des nombres entiers.")
        return

    if minimum < 1 or limite < 1:
        print("Les valeurs doivent être supérieures à zéro.")
        return

    pipeline = [
        {
            "$match": {
                "stars": {"$gte": 0, "$lte": 5},
                "categories": {"$type": "array"}
            }
        },
        {"$unwind": "$categories"},
        {
            "$match": {
                "categories": {"$type": "string", "$ne": ""}
            }
        },
        {
            "$group": {
                "_id": "$categories",
                "nombre_etablissements": {"$sum": 1},
                "note_moyenne": {"$avg": "$stars"}
            }
        },
        {
            "$match": {
                "nombre_etablissements": {"$gte": minimum}
            }
        },
        {
            "$sort": {
                "note_moyenne": -1,
                "nombre_etablissements": -1,
                "_id": 1
            }
        },
        {"$limit": limite}
    ]

    resultats = list(db.businesses.aggregate(pipeline))

    if not resultats:
        print("Aucune catégorie ne correspond aux critères.")
        return

    print("\nClassement des catégories")
    print(f"Minimum d'établissements : {minimum}")
    print("Note utilisée : stars (Yelp historique)")
    print("-" * 75)

    for rang, categorie in enumerate(resultats, start=1):
        print(
            f"{rang:2}. {categorie['_id']:<35} "
            f"Note : {categorie['note_moyenne']:.2f}/5 | "
            f"Établissements : {categorie['nombre_etablissements']}"
        )


def main():
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

    try:
        client.admin.command("ping")
        db = client[DB_NAME]
        top_categories(db)

    except PyMongoError as erreur:
        print("Erreur MongoDB :", erreur)

    finally:
        client.close()


if __name__ == "__main__":
    main()
