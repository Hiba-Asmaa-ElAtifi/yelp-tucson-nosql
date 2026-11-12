
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

BUSINESS_FILE = Path("/data/processed/businesses.jsonl")
INPUT_FILE = Path("/data/processed/tips.jsonl")
FILTER_REPORT = Path("/app/results/filter_tip_report.json")
REPORT_FILE = Path("/app/results/validate_tip_report.json")

START_DATE = datetime(2012, 1, 1)
END_DATE = datetime(2022, 1, 1)

EXPECTED_FIELDS = {
    "business_id",
    "user_id",
    "text",
    "date",
    "compliment_count",
}

errors = Counter()
examples = {}
seen_keys = set()
total = 0


def add_error(error_name, line_number):
    errors[error_name] += 1
    examples.setdefault(error_name, [])

    if len(examples[error_name]) < 5:
        examples[error_name].append(line_number)


def load_business_ids():
    """Charger et contrôler les identifiants Business."""
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
                    f"Document Business invalide : {number}"
                )

            business_id = business.get("business_id")

            if (
                not isinstance(business_id, str)
                or not business_id.strip()
            ):
                raise ValueError(
                    f"business_id invalide : {number}"
                )

            if business_id in ids:
                raise ValueError(
                    f"business_id dupliqué : {number}"
                )

            ids.add(business_id)

    if not ids:
        raise ValueError("Aucun Business disponible")

    return ids


def make_tip_key(tip):
    """Même méthode de déduplication que filter_tip.py."""
    canonical = json.dumps(
        tip,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def validate_tip(tip, line_number, business_ids):
    # 1. Vérifier les champs attendus
    missing = EXPECTED_FIELDS - set(tip)
    extra = set(tip) - EXPECTED_FIELDS

    if missing:
        add_error("missing_fields", line_number)

    if extra:
        add_error("unexpected_fields", line_number)

    # 2. Vérifier la relation avec Business
    business_id = tip.get("business_id")

    if (
        not isinstance(business_id, str)
        or business_id not in business_ids
    ):
        add_error("invalid_business_id", line_number)

    # 3. Vérifier l'identifiant de l'auteur
    user_id = tip.get("user_id")

    if (
        not isinstance(user_id, str)
        or not user_id.strip()
    ):
        add_error("invalid_user_id", line_number)

    # 4. Vérifier le texte
    if not isinstance(tip.get("text"), str):
        add_error("invalid_text", line_number)

    # 5. Vérifier la date
    try:
        date = datetime.strptime(
            tip.get("date"),
            "%Y-%m-%d %H:%M:%S",
        )

        if not START_DATE <= date < END_DATE:
            add_error("date_outside_period", line_number)

    except (ValueError, TypeError):
        add_error("invalid_date", line_number)

    # 6. Vérifier le nombre de compliments
    count = tip.get("compliment_count")

    if type(count) is not int or count < 0:
        add_error("invalid_compliment_count", line_number)

    # 7. Détecter les doublons exacts
    key = make_tip_key(tip)

    if key in seen_keys:
        add_error("duplicate_tip", line_number)
    else:
        seen_keys.add(key)


def main():
    global total

    for path in (BUSINESS_FILE, INPUT_FILE, FILTER_REPORT):
        if not path.is_file():
            raise SystemExit(
                f"FAIL : fichier introuvable : {path}"
            )

    business_ids = load_business_ids()

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):

            if not line.strip():
                add_error("empty_line", line_number)
                continue

            try:
                tip = json.loads(line)
            except json.JSONDecodeError:
                add_error("invalid_json", line_number)
                continue

            if not isinstance(tip, dict):
                add_error("invalid_document", line_number)
                continue

            total += 1
            validate_tip(
                tip, line_number, business_ids
            )

    # 8. Comparer avec le rapport de filtrage
    with FILTER_REPORT.open("r", encoding="utf-8") as file:
        filter_report = json.load(file)

    if filter_report.get("status") != "COMPLETED":
        errors["filter_not_completed"] += 1

    if filter_report.get("selected") != total:
        errors["filter_count_mismatch"] += 1

    if filter_report.get("selected_businesses") != len(
        business_ids
    ):
        errors["business_count_mismatch"] += 1

    count_fields = (
        "excluded_other_business",
        "excluded_outside_period",
        "excluded_exact_duplicates",
        "selected",
    )

    if any(
        type(filter_report.get(field)) is not int
        or filter_report[field] < 0
        for field in count_fields
    ):
        errors["invalid_filter_counters"] += 1
    elif filter_report.get("total_read") != sum(
        filter_report[field] for field in count_fields
    ):
        errors["filter_accounting_mismatch"] += 1

    status = (
        "PASS" if total > 0 and not errors else "FAIL"
    )

    report = {
        "dataset": "Yelp Tucson Tips",
        "total_tips": total,
        "unique_tip_keys": len(seen_keys),
        "selected_businesses": len(business_ids),
        "period_start": "2012-01-01",
        "period_end_exclusive": "2022-01-01",
        "errors": dict(sorted(errors.items())),
        "error_line_examples": examples,
        "status": status,
    }

    REPORT_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    REPORT_FILE.write_text(
        json.dumps(
            report, indent=2, ensure_ascii=False
        ) + "\n",
        encoding="utf-8",
    )

    print("\n=== VALIDATION TIPS ===")
    print("Tips analysés :", total)
    print("Clés uniques :", len(seen_keys))
    print("Erreurs :", dict(errors))
    print("Statut :", status)
    print("Rapport :", REPORT_FILE)

    if status == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
