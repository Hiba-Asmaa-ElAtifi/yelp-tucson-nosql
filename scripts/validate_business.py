
import json
import math
from pathlib import Path
from collections import Counter

INPUT_FILE = Path("/data/processed/businesses.jsonl")
REPORT_FILE = Path("/app/results/validate_business_report.json")

DAYS = {
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
}

errors = Counter()
warnings = Counter()
total = 0
business_ids = set()


def is_number(value):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
    )


def validate_business(business):
    business_id = business.get("business_id")

    # 1. Identifiant présent et unique
    if not isinstance(business_id, str) or not business_id.strip():
        errors["missing_business_id"] += 1
    elif business_id in business_ids:
        errors["duplicate_business_id"] += 1
    else:
        business_ids.add(business_id)

    # 2. Ville et État
    if business.get("city") != "Tucson" or business.get("state") != "AZ":
        errors["invalid_city"] += 1

    # 3. Nom de l'établissement
    if not isinstance(business.get("name"), str) or not business["name"].strip():
        errors["invalid_name"] += 1

    # 4. Catégories
    categories = business.get("categories")

    if (
        not isinstance(categories, list)
        or any(not isinstance(c, str) or not c.strip() for c in categories)
    ):
        errors["invalid_categories"] += 1

    # 5. Localisation GeoJSON
    location = business.get("location")

    if not isinstance(location, dict):
        errors["missing_or_invalid_location"] += 1
    else:
        coords = location.get("coordinates")

        if (
            location.get("type") != "Point"
            or not isinstance(coords, list)
            or len(coords) != 2
            or not all(is_number(c) for c in coords)
            or not (-180 <= coords[0] <= 180)
            or not (-90 <= coords[1] <= 90)
        ):
            errors["invalid_coordinates"] += 1
        else:
            longitude = business.get("longitude")
            latitude = business.get("latitude")

            if (
                not is_number(longitude)
                or not is_number(latitude)
                or not math.isclose(coords[0], longitude, abs_tol=1e-9)
                or not math.isclose(coords[1], latitude, abs_tol=1e-9)
            ):
                errors["coordinate_mismatch"] += 1

    # 6. Horaires : source originale obligatoire
    if "source_hours" not in business:
        errors["missing_source_hours"] += 1

    hours = business.get("hours")
    source_hours = business.get("source_hours")

    if source_hours is None:
        warnings["missing_hours"] += 1

        if hours is not None:
            errors["unexpected_hours"] += 1

    elif not isinstance(source_hours, dict):
        errors["invalid_source_hours"] += 1

    elif not isinstance(hours, dict):
        errors["invalid_hours"] += 1

    else:
        if set(hours) != set(source_hours):
            errors["hours_days_mismatch"] += 1

        for day, interval in hours.items():
            if day not in DAYS:
                errors["unknown_day"] += 1

            if not isinstance(interval, dict):
                errors["unnormalized_hours"] += 1
                continue

            opening = interval.get("open_minutes")
            closing = interval.get("close_minutes")

            if (
                type(opening) is not int
                or type(closing) is not int
                or not 0 <= opening <= 1440
                or not 0 <= closing <= 1440
            ):
                errors["invalid_hour_minutes"] += 1

    # 7. Attributs
    if "source_attributes" not in business:
        errors["missing_source_attributes"] += 1

    attributes = business.get("attributes")
    source_attributes = business.get("source_attributes")

    if source_attributes is None:
        warnings["missing_attributes"] += 1

        if attributes is not None:
            errors["unexpected_attributes"] += 1

    elif not isinstance(source_attributes, dict):
        errors["invalid_source_attributes"] += 1

    elif not isinstance(attributes, dict):
        errors["invalid_attributes"] += 1

    elif set(attributes) != set(source_attributes):
        errors["attributes_keys_mismatch"] += 1

    # 8. Notes et compteurs Yelp
    stars = business.get("stars")
    review_count = business.get("review_count")

    if not is_number(stars) or not 1 <= stars <= 5:
        errors["invalid_stars"] += 1

    if type(review_count) is not int or review_count < 0:
        errors["invalid_review_count"] += 1

    if business.get("source_stars") != stars:
        errors["source_stars_mismatch"] += 1

    if business.get("source_review_count") != review_count:
        errors["source_review_count_mismatch"] += 1

    if business.get("is_open") not in (0, 1):
        errors["invalid_is_open"] += 1


def main():
    global total

    if not INPUT_FILE.is_file():
        print("FAIL : fichier introuvable :", INPUT_FILE)
        raise SystemExit(1)

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                errors["empty_lines"] += 1
                continue

            try:
                business = json.loads(line)
            except json.JSONDecodeError:
                errors["invalid_json"] += 1
                continue

            if not isinstance(business, dict):
                errors["invalid_document_type"] += 1
                continue

            total += 1
            validate_business(business)

    if total != 9261:
        # Contrôle de référence pour notre version Yelp.
        # À rendre configurable pour d'autres versions du dataset.
        warnings["unexpected_total"] += 1

    status = "PASS" if total > 0 and not errors else "FAIL"

    report = {
        "dataset": "Yelp Tucson Business",
        "total_businesses": total,
        "unique_business_ids": len(business_ids),
        "errors": dict(sorted(errors.items())),
        "warnings": dict(sorted(warnings.items())),
        "status": status
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\n=== VALIDATION BUSINESS ===")
    print("Établissements analysés :", total)
    print("Identifiants uniques :", len(business_ids))
    print("Erreurs :", dict(errors))
    print("Avertissements :", dict(warnings))
    print("Statut :", status)
    print("Rapport :", REPORT_FILE)

    if status == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
