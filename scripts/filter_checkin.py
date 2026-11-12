
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

BUSINESS_FILE = Path("/data/processed/businesses.jsonl")
RAW_FILE = Path("/data/raw/yelp_academic_dataset_checkin.json")
OUTPUT_FILE = Path("/data/processed/checkins.jsonl")
REPORT_FILE = Path("/app/results/filter_checkin_report.json")

START_DATE = datetime(2012, 1, 1)
END_DATE = datetime(2022, 1, 1)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def load_business_ids():
    """Charger les établissements sélectionnés à Tucson."""
    ids = set()

    if not BUSINESS_FILE.is_file():
        raise FileNotFoundError(
            f"Fichier Business introuvable : {BUSINESS_FILE}"
        )

    with BUSINESS_FILE.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                raise ValueError(
                    f"Ligne Business vide : {line_number}"
                )

            business = json.loads(line)

            if not isinstance(business, dict):
                raise ValueError(
                    f"Document Business invalide : {line_number}"
                )

            business_id = business.get("business_id")

            if (
                not isinstance(business_id, str)
                or not business_id.strip()
            ):
                raise ValueError(
                    f"business_id incorrect : {line_number}"
                )

            if business_id in ids:
                raise ValueError(
                    f"business_id dupliqué : {line_number}"
                )

            ids.add(business_id)

    if not ids:
        raise ValueError("Aucun établissement Business trouvé")

    return ids


def parse_checkin_date(value):
    """Lire une date Yelp au format attendu."""
    if not isinstance(value, str):
        raise ValueError("Date non textuelle")

    return datetime.strptime(value, DATE_FORMAT)


def filter_checkins():
    if not RAW_FILE.is_file():
        raise FileNotFoundError(
            f"Fichier Check-in introuvable : {RAW_FILE}"
        )

    business_ids = load_business_ids()
    counters = Counter()
    seen_businesses = set()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

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
                    counters["total_documents_read"] += 1

                    if not line.strip():
                        raise ValueError(
                            f"Ligne vide : {line_number}"
                        )

                    try:
                        checkin = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise ValueError(
                            f"JSON invalide, ligne {line_number}"
                        ) from error

                    if not isinstance(checkin, dict):
                        raise ValueError(
                            f"Document incorrect, ligne {line_number}"
                        )

                    # Les champs attendus dans Yelp Check-in
                    if set(checkin) != {"business_id", "date"}:
                        raise ValueError(
                            f"Champs inattendus ou absents, "
                            f"ligne {line_number}"
                        )

                    business_id = checkin.get("business_id")

                    if (
                        not isinstance(business_id, str)
                        or not business_id.strip()
                    ):
                        raise ValueError(
                            f"business_id invalide : {line_number}"
                        )

                    # Sélectionner seulement les Business Tucson
                    if business_id not in business_ids:
                        counters["excluded_other_business"] += 1
                        continue

                    # Un document Check-in par Business
                    if business_id in seen_businesses:
                        raise ValueError(
                            f"business_id dupliqué dans les "
                            f"Check-ins : {business_id}"
                        )

                    seen_businesses.add(business_id)
                    counters["tucson_documents_read"] += 1

                    raw_dates = checkin.get("date")

                    if not isinstance(raw_dates, str):
                        raise ValueError(
                            f"Champ date invalide : {line_number}"
                        )

                    # Séparer toutes les visites
                    date_values = [
                        part.strip()
                        for part in raw_dates.split(",")
                    ]

                    selected_dates = []

                    for date_text in date_values:
                        if not date_text:
                            raise ValueError(
                                f"Date vide, ligne {line_number}"
                            )

                        counters["total_tucson_dates"] += 1

                        try:
                            visit_date = parse_checkin_date(
                                date_text
                            )
                        except ValueError as error:
                            raise ValueError(
                                f"Date invalide : {date_text}, "
                                f"ligne {line_number}"
                            ) from error

                        if START_DATE <= visit_date < END_DATE:
                            selected_dates.append(date_text)
                            counters["selected_dates"] += 1
                        else:
                            counters["excluded_outside_period"] += 1

                    # Aucun document vide dans le résultat
                    if not selected_dates:
                        counters["documents_without_selected_dates"] += 1
                        continue

                    result = {
                        "business_id": business_id,
                        "dates": selected_dates,
                        "checkin_count": len(selected_dates)
                    }

                    output.write(
                        json.dumps(
                            result,
                            ensure_ascii=False
                        ) + "\n"
                    )

                    counters["selected_documents"] += 1

        # Remplacer l'ancien résultat seulement si tout a réussi
        temporary_file.replace(OUTPUT_FILE)

    except Exception:
        temporary_file.unlink(missing_ok=True)
        raise

    report = {
        "dataset": "Yelp Tucson Check-ins",
        "period_start": "2012-01-01",
        "period_end_exclusive": "2022-01-01",
        "selected_businesses": len(business_ids),
        "total_documents_read": counters[
            "total_documents_read"
        ],
        "excluded_other_business": counters[
            "excluded_other_business"
        ],
        "tucson_documents_read": counters[
            "tucson_documents_read"
        ],
        "total_tucson_dates": counters[
            "total_tucson_dates"
        ],
        "excluded_outside_period": counters[
            "excluded_outside_period"
        ],
        "selected_dates": counters["selected_dates"],
        "documents_without_selected_dates": counters[
            "documents_without_selected_dates"
        ],
        "selected_documents": counters[
            "selected_documents"
        ],
        "status": "COMPLETED"
    }

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        ) + "\n",
        encoding="utf-8"
    )

    print("\n=== FILTER CHECK-INS ===")
    for key, value in report.items():
        print(f"{key} : {value}")


if __name__ == "__main__":
    filter_checkins()
