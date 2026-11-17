
from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGO_URI = "mongodb://mongodb:27017/"
DB_NAME = "yelp_tucson"


def top_reviewers(db):
    print("\nQ11 — REVIEWERS LES PLUS UTILES")

    try:
        minimum = int(
            input("Nombre minimum d'avis par utilisateur [5] : ") or "5"
        )
        limite = int(
            input("Nombre d'utilisateurs à afficher [10] : ") or "10"
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
                "user_id": {"$type": "string", "$ne": ""},
                "useful": {"$type": "number"}
            }
        },
        {
            "$group": {
                "_id": "$user_id",
                "nombre_avis": {"$sum": 1},
                "total_useful": {"$sum": "$useful"},
                "moyenne_useful": {"$avg": "$useful"}
            }
        },
        {
            "$match": {
                "nombre_avis": {"$gte": minimum}
            }
        },
        {
            "$sort": {
                "total_useful": -1,
                "nombre_avis": -1,
                "_id": 1
            }
        },
        {"$limit": limite}
    ]

    resultats = list(db.reviews.aggregate(pipeline))

    if not resultats:
        print("Aucun utilisateur ne correspond aux critères.")
        return

    print("\nClassement des reviewers")
    print(f"Minimum d'avis par utilisateur : {minimum}")
    print("-" * 85)

    for rang, utilisateur in enumerate(resultats, start=1):
        print(f"\n{rang}. User ID : {utilisateur['_id']}")
        print(f"   Nombre d'avis : {utilisateur['nombre_avis']}")
        print(f"   Votes utiles reçus : {utilisateur['total_useful']}")
        print(f"   Moyenne utile par avis : {utilisateur['moyenne_useful']:.2f}")


def main():
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

    try:
        client.admin.command("ping")
        db = client[DB_NAME]
        top_reviewers(db)

    except PyMongoError as erreur:
        print("Erreur MongoDB :", erreur)

    finally:
        client.close()


if __name__ == "__main__":
    main()
