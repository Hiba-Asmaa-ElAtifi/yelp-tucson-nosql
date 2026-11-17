
import os
import math
from datetime import datetime, timezone
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# Identifiant réservé à notre utilisateur de test
TEST_USER_ID = "TEST_USER_WEEK3_Q5"

# Connexion à MongoDB
client = MongoClient(os.environ["MONGO_URI"])
db = client[os.environ["MONGO_DATABASE"]]

try:
    print("\n=== Q5 — AJOUTER UN AVIS ===")
    print("Mode test : aucun utilisateur Yelp réel ne sera utilisé.")

    # 1. Vérifier que l'utilisateur de test existe
    user = db.users.find_one({"_id": TEST_USER_ID})

    if user is None or user.get("test_data") is not True:
        print("Erreur : utilisateur de test introuvable.")

    else:
        # 2. Demander un commerce existant
        business_id = input(
            "\nEntrez le Business ID : "
        ).strip()

        business = db.businesses.find_one(
            {"_id": business_id},
            {"name": 1}
        )

        if business is None:
            print("Erreur : établissement introuvable.")

        else:
            print("Établissement :", business["name"])

            # 3. Vérifier la note (entier de 1 à 5)
            while True:
                try:
                    stars = float(
                        input("Donnez une note (1 à 5) : ")
                    )

                    if math.isfinite(stars) and stars in (1, 2, 3, 4, 5):
                        break

                    print("Erreur : saisissez une note entière de 1 à 5.")

                except ValueError:
                    print("Erreur : veuillez saisir un nombre valide.")

            # 4. Vérifier le commentaire
            while True:
                text = input("Votre commentaire : ").strip()

                if text:
                    break

                print("Erreur : le commentaire ne peut pas être vide.")

            # 5. Préparer le document MongoDB
            review = {
                "_id": str(uuid4()),
                "user_id": TEST_USER_ID,
                "business_id": business_id,
                "stars": stars,
                "useful": 0,
                "funny": 0,
                "cool": 0,
                "text": text,
                "date": datetime.now(timezone.utc),
                "test_data": True
            }

            # 6. Afficher un récapitulatif
            print("\n=== RÉCAPITULATIF ===")
            print("Établissement :", business["name"])
            print("Note :", stars, "/5")
            print("Commentaire :", text)

            confirmation = input(
                "\nConfirmer l'ajout ? (o/n) : "
            ).strip().lower()

            if confirmation == "o":

                # 7. Ajouter l'avis dans la collection reviews
                try:
                    result = db.reviews.insert_one(review)

                except DuplicateKeyError:
                    print(
                        "Erreur : cet identifiant d'avis existe déjà. "
                        "Aucun nouvel avis n'a été ajouté."
                    )

                else:
                    print("\nAvis ajouté avec succès !")
                    print("Review ID :", result.inserted_id)

                    # 8. Recalculer les statistiques de ce commerce
                    try:
                        stats = list(db.reviews.aggregate([
                            {
                                "$match": {
                                    "business_id": business_id
                                }
                            },
                            {
                                "$group": {
                                    "_id": "$business_id",
                                    "computed_review_count": {
                                        "$sum": 1
                                    },
                                    "computed_average_stars": {
                                        "$avg": "$stars"
                                    }
                                }
                            }
                        ]))

                        if not stats:
                            print(
                                "Attention : aucun avis trouvé "
                                "pour le recalcul."
                            )

                        else:
                            # 9. Enregistrer les statistiques
                            result_update = db.businesses.update_one(
                                {"_id": business_id},
                                {
                                    "$set": {
                                        "computed_review_count": (
                                            stats[0]["computed_review_count"]
                                        ),
                                        "computed_average_stars": (
                                            stats[0]["computed_average_stars"]
                                        )
                                    }
                                }
                            )

                            if result_update.matched_count == 1:
                                print(
                                    "\nStatistiques du commerce "
                                    "mises à jour !"
                                )
                                print(
                                    "Nombre d'avis :",
                                    stats[0]["computed_review_count"]
                                )
                                print(
                                    "Nouvelle moyenne :",
                                    round(
                                        stats[0]["computed_average_stars"],
                                        2
                                    ),
                                    "/5"
                                )
                            else:
                                print(
                                    "Attention : commerce introuvable "
                                    "lors de la mise à jour."
                                )

                    except Exception as error:
                        print(
                            "\nAttention : l'avis a été ajouté, "
                            "mais le recalcul a échoué."
                        )
                        print("Détail :", error)
                        print(
                            "Relancez Q6 pour synchroniser "
                            "les statistiques."
                        )

            else:
                print("Insertion annulée.")

finally:
    client.close()
