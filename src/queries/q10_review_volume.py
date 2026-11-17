
from datetime import datetime, timezone

from pymongo import MongoClient
from pymongo.errors import PyMongoError


MONGO_URI = "mongodb://mongodb:27017/"
DB_NAME = "yelp_tucson"

DEBUT = datetime(2012, 1, 1, tzinfo=timezone.utc)
FIN = datetime(2022, 1, 1, tzinfo=timezone.utc)


def volume_avis(db):
    print("\nQ10 — VOLUME D'AVIS PAR PÉRIODE")
    print("1. Volume d'avis par année")
    print("2. Volume d'avis par mois")

    choix = input("\nVotre choix (1 ou 2) : ").strip()

    if choix == "1":
        unite = "year"
        format_date = "%Y"
        titre = "ANNÉE"
    elif choix == "2":
        unite = "month"
        format_date = "%Y-%m"
        titre = "MOIS"
    else:
        print("Choix invalide.")
        return

    pipeline = [
        {
            "$match": {
                "date": {
                    "$gte": DEBUT,
                    "$lt": FIN
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateTrunc": {
                        "date": "$date",
                        "unit": unite,
                        "timezone": "UTC"
                    }
                },
                "nombre_avis": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]

    resultats = list(db.reviews.aggregate(pipeline))

    if not resultats:
        print("Aucun avis trouvé.")
        return

    total = 0

    print(f"\n{'=' * 45}")
    print(f"{titre:<12} | NOMBRE D'AVIS")
    print("-" * 45)

    for ligne in resultats:
        periode = ligne["_id"].strftime(format_date)
        nombre = ligne["nombre_avis"]
        total += nombre

        print(f"{periode:<12} | {nombre:>10}")

    print("-" * 45)
    print(f"{'TOTAL':<12} | {total:>10}")
    print("=" * 45)


def main():
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

    try:
        client.admin.command("ping")
        db = client[DB_NAME]
        volume_avis(db)

    except PyMongoError as erreur:
        print("Erreur MongoDB :", erreur)

    finally:
        client.close()


if __name__ == "__main__":
    main()
