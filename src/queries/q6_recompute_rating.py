
import os
from pymongo import MongoClient

# Connexion à MongoDB
client = MongoClient(os.environ["MONGO_URI"])
db = client[os.environ["MONGO_DATABASE"]]

try:
    print("\n=== Q6 — STATISTIQUES D'UN COMMERCE ===")

    # 1. Demander l'identifiant du commerce
    business_id = input("Entrez le Business ID : ").strip()

    # 2. Vérifier que le commerce existe
    business = db.businesses.find_one(
        {"_id": business_id},
        {
            "name": 1,
            "stars": 1,
            "review_count": 1,
            "computed_average_stars": 1,
            "computed_review_count": 1
        }
    )

    if business is None:
        print("Erreur : établissement introuvable.")

    else:
        print("\nÉtablissement :", business["name"])

        # 3. Calculer la répartition des notes
        results = list(db.reviews.aggregate([
            {
                "$match": {
                    "business_id": business_id
                }
            },
            {
                "$group": {
                    "_id": "$stars",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {
                    "_id": -1
                }
            }
        ]))

        # 4. Afficher les statistiques
        if not results:
            print("\nAucun avis disponible pour ce commerce.")

        else:
            total_reviews = sum(
                result["count"] for result in results
            )

            total_stars = sum(
                result["_id"] * result["count"]
                for result in results
            )

            average = total_stars / total_reviews

            print("\n=== STATISTIQUES GÉNÉRALES ===")
            print("Nombre total d'avis :", total_reviews)
            print("Note moyenne :", round(average, 2), "/5")

            # 5. Afficher la répartition des notes
            print("\n=== RÉPARTITION DES NOTES ===")

            distribution = {
                result["_id"]: result["count"]
                for result in results
            }

            for rating in range(5, 0, -1):
                count = distribution.get(rating, 0)
                percentage = (count / total_reviews) * 100

                print(
                    f"{rating} étoile(s) : "
                    f"{count} avis "
                    f"({percentage:.1f} %)"
                )

            # 6. Comparer avec les statistiques enregistrées
            print("\n=== COMPARAISON AVEC LA FICHE DU COMMERCE ===")

            print("Note Yelp historique :", business.get("stars"))
            print(
                "Nombre d'avis Yelp historique :",
                business.get("review_count")
            )

            stored_average = business.get("computed_average_stars")
            stored_count = business.get("computed_review_count")

            print(
                "Moyenne enregistrée :",
                round(stored_average, 2)
                if stored_average is not None else "Non disponible"
            )
            print(
                "Nombre d'avis enregistré :",
                stored_count
                if stored_count is not None else "Non disponible"
            )

            # 7. Vérifier si les statistiques sont synchronisées
            if (
                stored_average is not None
                and stored_count is not None
                and abs(stored_average - average) < 0.000001
                and stored_count == total_reviews
            ):
                print("\nStatistiques synchronisées.")
            else:
                print(
                    "\nAttention : les statistiques enregistrées "
                    "ne correspondent pas aux avis actuels."
                )

finally:
    client.close()
