
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

# Chemins Docker déjà configurés dans notre projet
BUSINESS_FILE = Path("/data/processed/businesses.jsonl")
RAW_FILE = Path("/data/raw/yelp_academic_dataset_review.json")
OUTPUT_FILE = Path("/data/processed/reviews.jsonl")
REPORT_FILE = Path("/app/results/filter_review_report.json")

START_DATE = datetime(2012, 1, 1)
END_DATE = datetime(2022, 1, 1)


def read_review_date(value):
    """Lire une date Yelp au format YYYY-MM-DD HH:MM:SS."""
    if not isinstance(value, str):
        raise ValueError("Date absente ou non textuelle")

    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def load_business_ids():
    """Charger uniquement les identifiants Business retenus."""
    if not BUSINESS_FILE.is_file():
        raise FileNotFoundError(
            f"Fichier Business introuvable : {BUSINESS_FILE}"
        )

    ids = set()

    with BUSINESS_FILE.open("r", encoding="utf-8") as file:
        for number, line in enumerate(file, start=1):
            if not line.strip():
                raise ValueError(
                    f"Ligne Business vide : {number}"
                )

            business = json.loads(line)

            if not isinstance(business, dict):
                raise ValueError(
                    f"Document Business incorrect, ligne {number}"
                )

            business_id = business.get("business_id")

            if not isinstance(business_id, str) or not business_id:
                raise ValueError(
                    f"business_id absent, ligne {number}"
                )

            if business_id in ids:
                raise ValueError(
                    f"business_id dupliqué, ligne {number}"
                )

            ids.add(business_id)

    if not ids:
        raise ValueError("Aucun établissement Business trouvé")

    return ids


def filter_reviews():
    if not RAW_FILE.is_file():
        raise FileNotFoundError(
            f"Fichier Reviews introuvable : {RAW_FILE}"
        )

    business_ids = load_business_ids()
    counters = Counter()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Écrire d'abord un fichier temporaire.
    # L'ancien résultat reste intact si le traitement échoue.
    temporary_file = OUTPUT_FILE.with_name(
        OUTPUT_FILE.name + ".tmp"
    )

    try:
        with RAW_FILE.open("r", encoding="utf-8") as source:
            with temporary_file.open(
                "w", encoding="utf-8"
            ) as output:

                for line_number, line in enumerate(
                    source, start=1
                ):
                    counters["total_read"] += 1

                    if not line.strip():
                        raise ValueError(
                            f"Ligne Reviews vide : {line_number}"
                        )

                    try:
                        review = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise ValueError(
                            f"JSON invalide à la ligne {line_number}"
                        ) from error

                    if not isinstance(review, dict):
                        raise ValueError(
                            f"Document incorrect, ligne {line_number}"
                        )

                    # Condition 1 : établissement de Tucson
                    if review.get("business_id") not in business_ids:
                        counters["excluded_other_business"] += 1
                        continue

                    # Condition 2 : date entre 2012 et 2021
                    try:
                        review_date = read_review_date(
                            review.get("date")
                        )
                    except ValueError as error:
                        raise ValueError(
                            f"Date incorrecte à la ligne {line_number}"
                        ) from error

                    if not START_DATE <= review_date < END_DATE:
                        counters["excluded_outside_period"] += 1
                        continue

                    # Conserver le document complet
                    # La validation des champs suivra.
                    output.write(
                        json.dumps(
                            review, ensure_ascii=False
                        ) + "\n"
                    )

                    counters["selected"] += 1

        # Remplacer le résultat uniquement après succès
        temporary_file.replace(OUTPUT_FILE)

    except Exception:
        temporary_file.unlink(missing_ok=True)
        raise

    report = {
        "dataset": "Yelp Tucson Reviews",
        "period_start": "2012-01-01",
        "period_end_exclusive": "2022-01-01",
        "selected_businesses": len(business_ids),
        "total_read": counters["total_read"],
        "excluded_other_business": counters[
            "excluded_other_business"
        ],
        "excluded_outside_period": counters[
            "excluded_outside_period"
        ],
        "selected": counters["selected"],
        "status": "COMPLETED"
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print("\n=== FILTER REVIEWS ===")
    print("Avis lus :", counters["total_read"])
    print(
        "Avis hors établissements :",
        counters["excluded_other_business"]
    )
    print(
        "Avis hors période :",
        counters["excluded_outside_period"]
    )
    print("Avis conservés :", counters["selected"])
    print("Fichier :", OUTPUT_FILE)
    print("Rapport :", REPORT_FILE)


if __name__ == "__main__":
    filter_reviews()
