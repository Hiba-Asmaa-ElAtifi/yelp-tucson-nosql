
from datetime import datetime, timezone

from pymongo import MongoClient
from pymongo.errors import PyMongoError


MONGO_URI = "mongodb://mongodb:27017/"
DB_NAME = "yelp_tucson"


def enregistrer_checkin(db):
    business_id = input("Business ID : ").strip()

    business = db.businesses.find_one(
        {"_id": business_id},
        {"name": 1}
    )

    if not business:
        print("Établissement introuvable.")
        return

    print("Établissement :", business.get("name", "Inconnu"))

    checkin = db.checkins.find_one({"_id": business_id})

    if checkin:
        print("Check-ins actuels :", checkin.get("checkin_count", 0))
    else:
        print("Aucun check-in enregistré pour cet établissement.")

    confirmation = input("Enregistrer une nouvelle visite ? (oui/non) : ").strip().lower()

    if confirmation != "oui":
        print("Opération annulée.")
        return

    date_visite = datetime.now(timezone.utc)

    resultat = db.checkins.update_one(
        {"_id": business_id},
        {
            "$push": {"dates": date_visite},
            "$inc": {"checkin_count": 1},
            "$setOnInsert": {"business_id": business_id},
        },
        upsert=True
    )

    print("\nCheck-in enregistré avec succès.")
    print("Date :", date_visite)
    print("Identifiant :", business_id)

    nouveau = db.checkins.find_one(
        {"_id": business_id},
        {"checkin_count": 1}
    )

    print("Nouveau nombre de check-ins :", nouveau["checkin_count"])


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

    try:
        client.admin.command("ping")
        db = client[DB_NAME]

        print("=" * 45)
        print("Q8 — ENREGISTRER UN CHECK-IN")
        print("=" * 45)

        enregistrer_checkin(db)

    except PyMongoError as erreur:
        print("Erreur MongoDB :", erreur)

    finally:
        client.close()


if __name__ == "__main__":
    main()
