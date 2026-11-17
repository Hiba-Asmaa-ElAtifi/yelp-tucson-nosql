
from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGO_URI = "mongodb://mongodb:27017/"
DB_NAME = "yelp_tucson"


def etablissements_actifs(db):
    print("\nQ12 — ÉTABLISSEMENTS LES PLUS ACTIFS")

    try:
        limite = int(
            input("Nombre d'établissements à afficher [10] : ") or "10"
        )
    except ValueError:
        print("Veuillez saisir un nombre entier.")
        return

    if limite < 1:
        print("La limite doit être supérieure à zéro.")
        return

    pipeline = [
        {
            "$project": {
                "name": 1,
                "review_count": {"$ifNull": ["$review_count", 0]},
                "stars": 1
            }
        },
        {
            "$lookup": {
                "from": "checkins",
                "localField": "_id",
                "foreignField": "business_id",
                "as": "visites"
            }
        },
        {
            "$addFields": {
                "nombre_checkins": {
                    "$ifNull": [
                        {"$arrayElemAt": ["$visites.checkin_count", 0]},
                        0
                    ]
                }
            }
        },
        {
            "$lookup": {
                "from": "tips",
                "let": {"id_commerce": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$eq": ["$business_id", "$$id_commerce"]
                            }
                        }
                    },
                    {"$count": "total"}
                ],
                "as": "conseils"
            }
        },
        {
            "$addFields": {
                "nombre_tips": {
                    "$ifNull": [
                        {"$arrayElemAt": ["$conseils.total", 0]},
                        0
                    ]
                }
            }
        },
        {
            "$addFields": {
                "score_activite": {
                    "$add": [
                        "$review_count",
                        "$nombre_checkins",
                        "$nombre_tips"
                    ]
                }
            }
        },
        {
            "$sort": {
                "score_activite": -1,
                "review_count": -1,
                "_id": 1
            }
        },
        {"$limit": limite},
        {
            "$project": {
                "name": 1,
                "stars": 1,
                "review_count": 1,
                "nombre_checkins": 1,
                "nombre_tips": 1,
                "score_activite": 1
            }
        }
    ]

    resultats = list(
        db.businesses.aggregate(
            pipeline,
            allowDiskUse=True
        )
    )

    if not resultats:
        print("Aucun établissement trouvé.")
        return

    print("\nClassement des établissements")
    print("Score = avis + check-ins + tips")
    print("=" * 70)

    for rang, commerce in enumerate(resultats, start=1):
        print(f"\n{rang}. {commerce.get('name', 'Inconnu')}")
        print(f"   Business ID : {commerce['_id']}")
        print(f"   Note Yelp : {commerce.get('stars', 'N/A')}")
        print(f"   Avis : {commerce['review_count']}")
        print(f"   Check-ins : {commerce['nombre_checkins']}")
        print(f"   Tips : {commerce['nombre_tips']}")
        print(f"   Score d'activité : {commerce['score_activite']}")


def main():
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

    try:
        client.admin.command("ping")
        db = client[DB_NAME]
        etablissements_actifs(db)

    except PyMongoError as erreur:
        print("Erreur MongoDB :", erreur)

    finally:
        client.close()


if __name__ == "__main__":
    main()
