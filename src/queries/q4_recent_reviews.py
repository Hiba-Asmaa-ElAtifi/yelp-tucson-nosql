
import os
import math
from pymongo import MongoClient

# 1. Connexion à MongoDB
client = MongoClient(os.environ["MONGO_URI"])
db = client[os.environ["MONGO_DATABASE"]]

try:
    # 2. Choix de l'établissement
    business_id = input("Entrez le Business ID : ").strip()

    # 3. Configuration de la pagination
    page_size = 5
    page = 1

    query = {"business_id": business_id}

    total = db.reviews.count_documents(query)
    total_pages = math.ceil(total / page_size)

    print(f"\nNombre total d'avis : {total}")

    if total == 0:
        print("Aucun avis trouvé.")

    else:
        while True:

            # 4. Récupération des avis de la page
            reviews = db.reviews.find(
                query,
                {
                    "_id": 1,
                    "stars": 1,
                    "date": 1,
                    "text": 1
                }
            ).sort([
                ("date", -1),
                ("_id", 1)
            ]).skip(
                (page - 1) * page_size
            ).limit(page_size)

            # 5. En-tête de la page
            first_review = (page - 1) * page_size + 1
            last_review = min(page * page_size, total)

            print("\n" + "=" * 65)
            print(f"PAGE {page}/{total_pages}")
            print(f"AVIS {first_review} À {last_review} SUR {total}")
            print("=" * 65)

            # 6. Affichage des avis
            for index, review in enumerate(reviews, start=1):

                review_number = (page - 1) * page_size + index

                print("\n" + "-" * 65)
                print(f"AVIS N° {review_number}")
                print("-" * 65)

                print(f"NOTE : {review['stars']}/5")
                print(
                    "DATE : "
                    + review["date"].strftime("%d/%m/%Y à %H:%M")
                )

                print("\nCOMMENTAIRE :\n")
                print(review.get("text") or "Aucun commentaire.")
                print("-" * 65)

            # 7. Navigation entre les pages
            print("\n" + "=" * 65)
            print(f"Page {page} sur {total_pages}")
            print("=" * 65)

            print("\nNavigation :")
            print("  s = Page suivante")
            print("  p = Page précédente")
            print("  q = Quitter")

            choice = input("\nVotre choix (s/p/q) : ").strip().lower()

            if choice == "q":
                print("Consultation terminée.")
                break

            elif choice == "s":
                if page < total_pages:
                    page += 1
                else:
                    print("Vous êtes déjà à la dernière page.")

            elif choice == "p":
                if page > 1:
                    page -= 1
                else:
                    print("Vous êtes déjà à la première page.")

            else:
                print("Choix invalide. Utilisez s, p ou q.")

finally:
    client.close()
