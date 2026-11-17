
from datetime import datetime, timezone
from uuid import uuid4

from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError


MONGO_URI = "mongodb://mongodb:27017/"
DB_NAME = "yelp_tucson"
PAGE_SIZE = 5
TEST_USER_ID = "TEST_USER_WEEK3_Q7"


def afficher_tips(db):
    business_id = input("Business ID : ").strip()

    business = db.businesses.find_one(
        {"_id": business_id},
        {"name": 1}
    )

    if not business:
        print("Établissement introuvable.")
        return

    total = db.tips.count_documents({"business_id": business_id})

    print(f"\nÉtablissement : {business.get('name', 'Inconnu')}")
    print(f"Nombre de tips : {total}")

    if total == 0:
        return

    page = 0

    while True:
        tips = list(
            db.tips.find({"business_id": business_id})
            .sort([("date", DESCENDING), ("_id", 1)])
            .skip(page * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )

        print(f"\n--- Page {page + 1} ---")

        for tip in tips:
            print("-" * 45)
            print("Date :", tip.get("date"))
            print("Auteur :", tip.get("user_id"))
            print("Conseil :", tip.get("text"))
            print("Compliments :", tip.get("compliment_count", 0))

        choix = input("\ns = suivant | p = précédent | q = quitter : ").strip().lower()

        if choix == "q":
            break
        elif choix == "s":
            if (page + 1) * PAGE_SIZE < total:
                page += 1
            else:
                print("Dernière page atteinte.")
        elif choix == "p":
            if page > 0:
                page -= 1
            else:
                print("Première page atteinte.")
        else:
            print("Choix invalide.")


def ajouter_tip(db):
    business_id = input("Business ID : ").strip()

    business = db.businesses.find_one(
        {"_id": business_id},
        {"name": 1}
    )

    if not business:
        print("Établissement introuvable.")
        return

    print(f"Établissement : {business.get('name', 'Inconnu')}")

    texte = input("Votre conseil : ").strip()

    if not texte:
        print("Le conseil ne peut pas être vide.")
        return

    if len(texte) > 500:
        print("Le conseil ne doit pas dépasser 500 caractères.")
        return

    confirmation = input("Confirmer l'ajout ? (oui/non) : ").strip().lower()

    if confirmation != "oui":
        print("Ajout annulé.")
        return

    tip = {
        "_id": "TEST_TIP_WEEK3_Q7_" + str(uuid4()),
        "business_id": business_id,
        "user_id": TEST_USER_ID,
        "text": texte,
        "date": datetime.now(timezone.utc),
        "compliment_count": 0,
    }

    db.tips.insert_one(tip)

    print("\nTip ajouté avec succès.")
    print("Identifiant :", tip["_id"])


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

    try:
        db = client[DB_NAME]
        client.admin.command("ping")

        while True:
            print("\n" + "=" * 45)
            print("Q7 — GESTION DES TIPS")
            print("=" * 45)
            print("1. Consulter les tips d'un établissement")
            print("2. Ajouter un nouveau tip")
            print("3. Quitter")

            choix = input("\nVotre choix : ").strip()

            try:
                if choix == "1":
                    afficher_tips(db)
                elif choix == "2":
                    ajouter_tip(db)
                elif choix == "3":
                    print("Fin de Q7.")
                    break
                else:
                    print("Choix invalide.")
            except PyMongoError as erreur:
                print("Erreur MongoDB :", erreur)

    except PyMongoError as erreur:
        print("Connexion MongoDB impossible :", erreur)
    finally:
        client.close()


if __name__ == "__main__":
    main()
