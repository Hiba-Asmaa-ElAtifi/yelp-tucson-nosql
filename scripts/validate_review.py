
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

BUSINESS_FILE = Path("/data/processed/businesses.jsonl")
INPUT_FILE = Path("/data/processed/reviews.jsonl")
REPORT_FILE = Path("/app/results/validate_review_report.json")

START_DATE = datetime(2012, 1, 1)
END_DATE = datetime(2022, 1, 1)

errors = Counter()
examples = {}
review_ids = set()
total = 0


def add_error(name, line_number):
    errors[name] += 1

    # Mémoriser quelques numéros de lignes,
    # sans enregistrer le texte des avis.
    if name not in examples:
        examples[name] = []

    if len(examples[name]) < 5:
        examples[name].append(line_number)


def load_business_ids():
    ids = set()

    with BUSINESS_FILE.open("r", encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                raise ValueError("Ligne Business vide")

            business = json.loads(line)

            if not isinstance(business, dict):
                raise ValueError("Document Business invalide")

            business_id = business.get("business_id")

            if not isinstance(business_id, str) or not business_id:
                raise ValueError("Identifiant Business invalide")

            if business_id in ids:
                raise ValueError("Identifiant Business dupliqué")

            ids.add(business_id)

    if not ids:
        raise ValueError("Aucun Business disponible")

    return ids


def validate_review(review, line_number, business_ids):
    # Identifiant unique de l'avis
    review_id = review.get("review_id")

    if not isinstance(review_id, str) or not review_id.strip():
        add_error("invalid_review_id", line_number)
    elif review_id in review_ids:
        add_error("duplicate_review_id", line_number)
    else:
        review_ids.add(review_id)

    # Référence vers un établissement conservé
    business_id = review.get("business_id")

    if business_id not in business_ids:
        add_error("orphan_business_id", line_number)

    # Référence vers l'auteur de l'avis
    user_id = review.get("user_id")

    if not isinstance(user_id, str) or not user_id.strip():
        add_error("invalid_user_id", line_number)

    # Note de 1 à 5
    stars = review.get("stars")

    if (
        type(stars) not in (int, float)
        or not 1 <= stars <= 5
    ):
        add_error("invalid_stars", line_number)

    # Date valide et comprise dans notre période
    try:
        date = datetime.strptime(
            review.get("date"),
            "%Y-%m-%d %H:%M:%S"
        )

        if not START_DATE <= date < END_DATE:
            add_error("date_outside_period", line_number)

    except (ValueError, TypeError):
        add_error("invalid_date", line_number)

    # Le texte doit rester du texte
    if not isinstance(review.get("text"), str):
        add_error("invalid_text", line_number)

    # Votes : des nombres entiers non négatifs
    for field in ("useful", "funny", "cool"):
        value = review.get(field)

        if type(value) is not int or value < 0:
            add_error(f"invalid_{field}", line_number)


def main():
    global total

    if not BUSINESS_FILE.is_file():
        raise SystemExit("FAIL : fichier Business introuvable")

    if not INPUT_FILE.is_file():
        raise SystemExit("FAIL : fichier Reviews introuvable")

    business_ids = load_business_ids()

    with INPUT_FILE.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                add_error("empty_line", line_number)
                continue

            try:
                review = json.loads(line)
            except json.JSONDecodeError:
                add_error("invalid_json", line_number)
                continue

            if not isinstance(review, dict):
                add_error("invalid_document_type", line_number)
                continue

            total += 1
            validate_review(
                review, line_number, business_ids
            )

    status = "PASS" if total > 0 and not errors else "FAIL"

    report = {
        "dataset": "Yelp Tucson Reviews",
        "total_reviews": total,
        "unique_review_ids": len(review_ids),
        "selected_businesses": len(business_ids),
        "period": "2012-01-01 to 2021-12-31",
        "errors": dict(sorted(errors.items())),
        "error_line_examples": examples,
        "status": status
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    REPORT_FILE.write_text(
        json.dumps(
            report, ensure_ascii=False, indent=2
        ) + "\n",
        encoding="utf-8"
    )

    print("\n=== VALIDATION REVIEWS ===")
    print("Avis analysés :", total)
    print("Identifiants uniques :", len(review_ids))
    print("Erreurs :", dict(errors))
    print("Statut :", status)
    print("Rapport :", REPORT_FILE)

    if status == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
