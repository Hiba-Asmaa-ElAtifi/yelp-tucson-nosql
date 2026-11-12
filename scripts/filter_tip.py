
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

BUSINESS_FILE = Path("/data/processed/businesses.jsonl")
RAW_FILE = Path("/data/raw/yelp_academic_dataset_tip.json")
OUTPUT_FILE = Path("/data/processed/tips.jsonl")
REPORT_FILE = Path("/app/results/filter_tip_report.json")

START_DATE = datetime(2012, 1, 1)
END_DATE = datetime(2022, 1, 1)

EXPECTED_FIELDS = {
    "business_id",
    "user_id",
    "text",
    "date",
    "compliment_count"
}


def load_business_ids():
    """Charger les établissements sélectionnés à Tucson."""
    ids = set()

    with BUSINESS_FILE.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                raise ValueError(
                    f"Business vide à la ligne {line_number}"
                )

            business = json.loads(line)

            if not isinstance(business, dict):
                raise ValueError("Document Business incorrect")

            business_id = business.get("business_id")

            if not isinstance(business_id, str) or not business_id.strip():
                raise ValueError("business_id absent ou incorrect")

            if business_id in ids:
                raise ValueError("business_id dupliqué")

            ids.add(business_id)

    if not ids:
        raise ValueError("Aucun établissement sélectionné")

    return ids


def parse_date(value):
    """Lire la date Yelp sans changer son contenu."""
    if not isinstance(value, str):
        raise ValueError("Date absente ou incorrecte")

    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def make_tip_key(tip):
    """Créer une clé stable à partir du contenu original du tip."""
    canonical = json.dumps(
        tip,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":")
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def filter_tips():
    business_ids = load_business_ids()
    counters = Counter()
    seen_tips = set()

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
                    counters["total_read"] += 1

                    if not line.strip():
                        raise ValueError(
                            f"Ligne Tip vide : {line_number}"
                        )

                    try:
                        tip = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise ValueError(
                            f"JSON invalide, ligne {line_number}"
                        ) from error

                    if not isinstance(tip, dict):
                        raise ValueError(
                            f"Document Tip incorrect, ligne {line_number}"
                        )

                    # Ne pas ignorer silencieusement
                    # des champs inattendus.
                    unknown = set(tip) - EXPECTED_FIELDS

                    if unknown:
                        raise ValueError(
                            f"Champs inattendus ligne {line_number}: "
                            f"{sorted(unknown)}"
                        )

                    # 1. Établissement appartenant à Tucson
                    if tip.get("business_id") not in business_ids:
                        counters["excluded_other_business"] += 1
                        continue

                    # 2. Période 2012–2021
                    try:
                        date = parse_date(tip.get("date"))
                    except ValueError as error:
                        raise ValueError(
                            f"Date invalide, ligne {line_number}"
                        ) from error

                    if not START_DATE <= date < END_DATE:
                        counters["excluded_outside_period"] += 1
                        continue

                    # 3. Déduplication exacte
                    key = make_tip_key(tip)

                    if key in seen_tips:
                        counters["excluded_exact_duplicates"] += 1
                        continue

                    seen_tips.add(key)

                    # 4. Conserver tous les champs originaux
                    output.write(
                        json.dumps(
                            tip, ensure_ascii=False
                        ) + "\n"
                    )

                    counters["selected"] += 1

        temporary_file.replace(OUTPUT_FILE)

    except Exception:
        temporary_file.unlink(missing_ok=True)
        raise

    report = {
        "dataset": "Yelp Tucson Tips",
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
        "excluded_exact_duplicates": counters[
            "excluded_exact_duplicates"
        ],
        "selected": counters["selected"],
        "status": "COMPLETED"
    }

    REPORT_FILE.write_text(
        json.dumps(
            report, indent=2, ensure_ascii=False
        ) + "\n",
        encoding="utf-8"
    )

    print("\n=== FILTER TIPS ===")
    for key, value in report.items():
        print(f"{key} : {value}")


if __name__ == "__main__":
    filter_tips()
