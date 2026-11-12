
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

BUSINESS_FILE = Path("/data/processed/businesses.jsonl")
INPUT_FILE = Path("/data/processed/checkins.jsonl")
FILTER_REPORT = Path("/app/results/filter_checkin_report.json")
REPORT_FILE = Path("/app/results/validate_checkin_report.json")

START_DATE = datetime(2012, 1, 1)
END_DATE = datetime(2022, 1, 1)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

EXPECTED_FIELDS = {
    "business_id",
    "dates",
    "checkin_count"
}


def load_business_ids():
    """Charger les identifiants Business de Tucson."""
    ids = set()

    with BUSINESS_FILE.open("r", encoding="utf-8") as source:
        for number, line in enumerate(source, start=1):
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


def validate_checkins():
    errors = Counter()
    examples = {}
    seen_businesses = set()

    total_documents = 0
    total_dates = 0

    def add_error(name, line_number=None):
        errors[name] += 1

        if line_number is not None:
            examples.setdefault(name, [])
            if len(examples[name]) < 5:
                examples[name].append(line_number)

    for path in (BUSINESS_FILE, INPUT_FILE, FILTER_REPORT):
        if not path.is_file():
            raise SystemExit(
                f"FAIL : fichier introuvable : {path}"
            )

    business_ids = load_business_ids()

    with INPUT_FILE.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):

            if not line.strip():
                add_error("empty_line", line_number)
                continue

            try:
                checkin = json.loads(line)
            except json.JSONDecodeError:
                add_error("invalid_json", line_number)
                continue

            if not isinstance(checkin, dict):
                add_error("invalid_document", line_number)
                continue

            total_documents += 1

            # 1. Vérifier les champs du document
            if set(checkin) != EXPECTED_FIELDS:
                add_error("invalid_fields", line_number)

            # 2. Vérifier le business_id
            business_id = checkin.get("business_id")

            if (
                not isinstance(business_id, str)
                or not business_id.strip()
                or business_id not in business_ids
            ):
                add_error("invalid_business_id", line_number)

            elif business_id in seen_businesses:
                add_error("duplicate_business_id", line_number)

            else:
                seen_businesses.add(business_id)

            # 3. Vérifier le tableau des dates
            dates = checkin.get("dates")

            if not isinstance(dates, list):
                add_error("invalid_dates_array", line_number)
                continue

            if len(dates) == 0:
                add_error("empty_dates_array", line_number)

            # 4. Vérifier le compteur des visites
            count = checkin.get("checkin_count")

            if (
                type(count) is not int
                or count != len(dates)
            ):
                add_error("invalid_checkin_count", line_number)

            # 5. Vérifier chaque date
            for date_text in dates:
                total_dates += 1

                if not isinstance(date_text, str):
                    add_error("invalid_date_type", line_number)
                    continue

                try:
                    date = datetime.strptime(
                        date_text, DATE_FORMAT
                    )
                except ValueError:
                    add_error("invalid_date_format", line_number)
                    continue

                # Le format doit rester exactement celui prévu
                if date.strftime(DATE_FORMAT) != date_text:
                    add_error("noncanonical_date", line_number)

                if not START_DATE <= date < END_DATE:
                    add_error("date_outside_period", line_number)

    # 6. Contrôler le rapport de filtrage
    try:
        with FILTER_REPORT.open(
            "r", encoding="utf-8"
        ) as source:
            filter_report = json.load(source)
    except (json.JSONDecodeError, OSError):
        add_error("invalid_filter_report")
        filter_report = {}

    if not isinstance(filter_report, dict):
        add_error("invalid_filter_report_structure")
        filter_report = {}

    if filter_report.get("status") != "COMPLETED":
        add_error("filter_not_completed")

    if filter_report.get("selected_documents") != total_documents:
        add_error("document_count_mismatch")

    if filter_report.get("selected_dates") != total_dates:
        add_error("date_count_mismatch")

    if filter_report.get("selected_businesses") != len(business_ids):
        add_error("business_count_mismatch")

    # 7. Vérifier les égalités des compteurs
    counter_fields = [
        "total_documents_read",
        "excluded_other_business",
        "tucson_documents_read",
        "total_tucson_dates",
        "excluded_outside_period",
        "selected_dates",
        "documents_without_selected_dates",
        "selected_documents"
    ]

    counters_valid = all(
        type(filter_report.get(field)) is int
        and filter_report[field] >= 0
        for field in counter_fields
    )

    if not counters_valid:
        add_error("invalid_filter_counters")

    else:
        if (
            filter_report["total_documents_read"]
            != filter_report["excluded_other_business"]
            + filter_report["tucson_documents_read"]
        ):
            add_error("source_accounting_mismatch")

        if (
            filter_report["total_tucson_dates"]
            != filter_report["excluded_outside_period"]
            + filter_report["selected_dates"]
        ):
            add_error("date_accounting_mismatch")

        if (
            filter_report["tucson_documents_read"]
            != filter_report["selected_documents"]
            + filter_report["documents_without_selected_dates"]
        ):
            add_error("document_accounting_mismatch")

    # 8. Produire le rapport final
    status = (
        "PASS"
        if total_documents > 0 and not errors
        else "FAIL"
    )

    report = {
        "dataset": "Yelp Tucson Check-ins",
        "total_documents": total_documents,
        "unique_business_ids": len(seen_businesses),
        "total_dates": total_dates,
        "period_start": "2012-01-01",
        "period_end_exclusive": "2022-01-01",
        "errors": dict(sorted(errors.items())),
        "error_line_examples": examples,
        "status": status
    }

    REPORT_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        ) + "\n",
        encoding="utf-8"
    )

    print("\n=== VALIDATION CHECK-INS ===")
    print("Documents analysés :", total_documents)
    print("Business uniques :", len(seen_businesses))
    print("Dates analysées :", total_dates)
    print("Erreurs :", dict(errors))
    print("Statut :", status)
    print("Rapport :", REPORT_FILE)

    if status == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    validate_checkins()
