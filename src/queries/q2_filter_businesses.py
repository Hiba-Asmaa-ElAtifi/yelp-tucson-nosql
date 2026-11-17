
import os
import math
from pymongo import MongoClient

# Connexion à MongoDB
client = MongoClient(os.environ["MONGO_URI"])
db = client[os.environ["MONGO_DATABASE"]]

try:
    # 1. Critères saisis par l'utilisateur
    while True:
        category = input("Entrez une catégorie : ").strip()

        if category:
            break

        print("Erreur : la catégorie ne peut pas être vide.")

    while True:
        try:
            min_stars = float(input("Entrez la note minimale (0 à 5) : "))

            if math.isfinite(min_stars) and 0 <= min_stars <= 5:
                break

            print("Erreur : la note doit être comprise entre 0 et 5.")

        except ValueError:
            print("Erreur : veuillez saisir un nombre valide.")

    # 2. Filtre MongoDB
    query = {
        "categories": category,
        "stars": {"$gte": min_stars}
    }

    # 3. Pagination
    page_size = 10
    page = 1

    total = db.businesses.count_documents(query)
    total_pages = math.ceil(total / page_size)

    print(f"\nNombre total d'établissements : {total}")

    if total == 0:
        print("Aucun établissement trouvé.")

    else:
        while True:
            # 4. Recherche des établissements de la page
            businesses = db.businesses.find(
                query,
                {
                    "_id": 1,
                    "name": 1,
                    "stars": 1,
                    "categories": 1
                }
            ).sort([
                ("stars", -1),
                ("_id", 1)
            ]).skip(
                (page - 1) * page_size
            ).limit(page_size)

            # 5. Affichage des résultats
            print("\n" + "=" * 65)
            print(f"RÉSULTATS — PAGE {page}/{total_pages}")
            print("=" * 65)

            for index, business in enumerate(businesses, start=1):
                business_number = (page - 1) * page_size + index

                print("\n" + "-" * 65)
                print(f"ÉTABLISSEMENT N° {business_number}")
                print("-" * 65)

                print(f"Nom        : {business.get('name', 'Inconnu')}")
                print(f"Note       : {business.get('stars', 'N/A')}/5")
                print(
                    "Catégories : "
                    + ", ".join(business.get("categories") or [])
                )
                print(f"Business ID: {business['_id']}")

            print("\n" + "=" * 65)
            print(f"Page {page} sur {total_pages} | Total : {total} établissements")
            print("=" * 65)

            # 6. Navigation entre les pages
            print("\nNavigation :")
            print("  s = Page suivante")
            print("  p = Page précédente")
            print("  q = Quitter")

            choice = input("\nVotre choix (s/p/q) : ").strip().lower()

            if choice == "q":
                print("Recherche terminée.")
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
