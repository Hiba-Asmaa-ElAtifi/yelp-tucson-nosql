
import os
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from pymongo import MongoClient

# ============================================================
# Q1 — COMMERCES OUVERTS DANS UN RAYON DE 2 KM
# ============================================================

TUCSON_TZ = ZoneInfo("America/Phoenix")

DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]


def is_open_at(hours, local_time):
    """
    Vérifie si un commerce est ouvert selon les horaires Yelp.
    Gère les horaires normaux et ceux qui dépassent minuit.
    """

    if not isinstance(hours, dict):
        return False

    today = DAYS[local_time.weekday()]
    yesterday = DAYS[(local_time.weekday() - 1) % 7]

    current_minutes = local_time.hour * 60 + local_time.minute

    # Vérification des horaires du jour
    today_hours = hours.get(today)

    if isinstance(today_hours, dict):
        opening = today_hours.get("open_minutes")
        closing = today_hours.get("close_minutes")

        if type(opening) is int and type(closing) is int:

            # Horaires normaux : 11h00 -> 22h00
            if opening < closing:
                if opening <= current_minutes < closing:
                    return True

            # Horaires nocturnes : 18h00 -> 02h00
            elif opening > closing:
                if current_minutes >= opening:
                    return True

    # Vérification des horaires débordant de la veille
    yesterday_hours = hours.get(yesterday)

    if isinstance(yesterday_hours, dict):
        opening = yesterday_hours.get("open_minutes")
        closing = yesterday_hours.get("close_minutes")

        if type(opening) is int and type(closing) is int:
            if opening > closing and current_minutes < closing:
                return True

    # Horaires manquants ou 00h00-00h00 : non confirmés
    return False


# ============================================================
# CONNEXION À MONGODB
# ============================================================

client = MongoClient(os.environ["MONGO_URI"])
db = client[os.environ["MONGO_DATABASE"]]

try:
    # ========================================================
    # 1. CONFIGURATION DE LA RECHERCHE
    # ========================================================

    # Centre de référence : Target, Tucson (Arizona)
    longitude = -110.880452
    latitude = 32.223236

    # Rayon imposé dans l'énoncé : 2 km
    radius = 2000
    radius_km = radius / 1000

    print("\n" + "=" * 65)
    print("Q1 — RECHERCHE DE COMMERCES OUVERTS")
    print("=" * 65)

    print(f"Rayon de recherche : {radius_km:g} km")
    print("Centre de recherche : Target, Tucson (Arizona)")
    print(f"Coordonnées : {latitude}, {longitude}")
    print("Classement : note décroissante")
    print("Affichage : 5 établissements par page")

    # ========================================================
    # 2. CRITÈRES UTILISATEUR
    # ========================================================

    category = input(
        "\nCatégorie (Entrée = toutes) : "
    ).strip()

    while True:
        try:
            min_stars = float(
                input("Note minimale (0 à 5) : ")
            )

            if math.isfinite(min_stars) and 0 <= min_stars <= 5:
                break

            print("Erreur : la note doit être entre 0 et 5.")

        except ValueError:
            print("Erreur : veuillez saisir un nombre valide.")

    # ========================================================
    # 3. DATE ET HEURE LOCALE DE TUCSON
    # ========================================================

    while True:
        date_input = input(
            "Date de test AAAA-MM-JJ HH:MM "
            "(Entrée = maintenant à Tucson) : "
        ).strip()

        if not date_input:
            local_time = datetime.now(TUCSON_TZ)
            break

        try:
            local_time = datetime.strptime(
                date_input,
                "%Y-%m-%d %H:%M"
            ).replace(tzinfo=TUCSON_TZ)

            break

        except ValueError:
            print("Erreur : utilisez le format AAAA-MM-JJ HH:MM.")

    print(
        "\nHeure utilisée (Tucson) :",
        local_time.strftime("%A %d/%m/%Y %H:%M")
    )

    # ========================================================
    # 4. REQUÊTE MONGODB GÉOSPATIALE
    # ========================================================

    query = {
        "location": {
            "$near": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [longitude, latitude]
                },
                "$maxDistance": radius
            }
        },
        "stars": {
            "$gte": min_stars
        }
    }

    if category:
        query["categories"] = category

    cursor = db.businesses.find(
        query,
        {
            "_id": 1,
            "name": 1,
            "address": 1,
            "stars": 1,
            "categories": 1,
            "hours": 1
        }
    )

    # ========================================================
    # 5. FILTRAGE DES COMMERCES OUVERTS
    # ========================================================

    open_businesses = []

    for business in cursor:
        if is_open_at(business.get("hours"), local_time):
            open_businesses.append(business)

    # ========================================================
    # 6. TRI PAR NOTE DÉCROISSANTE
    # ========================================================

    open_businesses.sort(
        key=lambda business: (
            -business.get("stars", 0),
            business["_id"]
        )
    )

    # ========================================================
    # 7. PAGINATION — 5 ÉTABLISSEMENTS PAR PAGE
    # ========================================================

    page_size = 5
    page = 1

    total = len(open_businesses)
    total_pages = math.ceil(total / page_size)

    print("\n" + "=" * 65)
    print(f"RÉSULTATS DANS UN RAYON DE {radius_km:g} KM")
    print("=" * 65)

    print(f"Catégorie : {category or 'Toutes'}")
    print(f"Note minimale : {min_stars}/5")
    print(f"Établissements ouverts trouvés : {total}")

    if total == 0:
        print("\nAucun établissement ouvert trouvé.")

    else:
        while True:

            start = (page - 1) * page_size
            end = min(start + page_size, total)

            page_businesses = open_businesses[start:end]

            print("\n" + "=" * 65)
            print(f"RÉSULTATS — PAGE {page}/{total_pages}")
            print(f"ÉTABLISSEMENTS {start + 1} À {end} SUR {total}")
            print("=" * 65)

            # Afficher les cinq établissements de la page
            for index, business in enumerate(
                page_businesses,
                start=start + 1
            ):

                print("\n" + "-" * 65)
                print(f"ÉTABLISSEMENT N° {index}")
                print("-" * 65)

                print(f"Nom        : {business.get('name')}")
                print(f"Adresse    : {business.get('address')}")
                print(f"Note       : {business.get('stars')}/5")
                print(f"Business ID: {business['_id']}")
                print(
                    "Statut     : OUVERT "
                    "selon les horaires enregistrés"
                )

            # =================================================
            # 8. NAVIGATION ENTRE LES PAGES
            # =================================================

            print("\n" + "=" * 65)
            print(
                f"Page {page} sur {total_pages} "
                f"| Total : {total} établissements"
            )
            print("=" * 65)

            print("\nNavigation :")
            print("  s = Page suivante")
            print("  p = Page précédente")
            print("  q = Quitter")

            choice = input(
                "\nVotre choix (s/p/q) : "
            ).strip().lower()

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
