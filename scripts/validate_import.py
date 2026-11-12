
import hashlib
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient

EXPECTED = {
    "businesses": 9261,
    "reviews": 375076,
    "tips": 49876,
    "checkins": 7747,
    "users": 117497,
}

EXPECTED_CHECKIN_DATES = 695828
REPORT_PATH = Path("/app/results/validate_import_report.json")

START = datetime(2012, 1, 1)
END = datetime(2022, 1, 1)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def main():
    errors = Counter()
    examples = []
    actual_counts = {}
    checked_dates = 0

    def error(message):
        errors[message] += 1
        if len(examples) < 20:
            examples.append(message)

    client = MongoClient(
        os.environ["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
    )

    try:
        client.admin.command("ping")
        db = client[os.environ["MONGO_DATABASE"]]

        print("=== VALIDATION IMPORT MONGODB ===")

        # 1. Volumes réels
        for name, expected in EXPECTED.items():
            actual = db[name].count_documents({})
            actual_counts[name] = actual

            if actual != expected:
                error(f"{name}: {actual} au lieu de {expected}")

            print(f"{name}: {actual} / {expected}")

        # 2. Identifiants des établissements
        business_ids = set()

        for doc in db.businesses.find(
            {}, {"_id": 1, "business_id": 1, "location": 1,
                 "categories": 1, "hours": 1, "attributes": 1}
        ):
            business_ids.add(doc["_id"])

            if doc["_id"] != doc.get("business_id"):
                error("Business: _id différent de business_id")

            location = doc.get("location")
            if (
                not isinstance(location, dict)
                or location.get("type") != "Point"
                or not isinstance(location.get("coordinates"), list)
                or len(location["coordinates"]) != 2
            ):
                error("Business: GeoJSON incorrect")

            if not isinstance(doc.get("categories"), list):
                error("Business: categories non tableau")

            for field in ("hours", "attributes"):
                value = doc.get(field)
                if value is not None and not isinstance(value, dict):
                    error(f"Business: {field} incorrect")

        # 3. Identifiants des utilisateurs
        user_ids = set()

        for doc in db.users.find(
            {}, {"_id": 1, "user_id": 1, "yelping_since": 1}
        ):
            user_ids.add(doc["_id"])

            if doc["_id"] != doc.get("user_id"):
                error("User: _id différent de user_id")

            if not isinstance(doc.get("yelping_since"), datetime):
                error("User: yelping_since non BSON Date")

        # 4. Reviews
        for doc in db.reviews.find(
            {}, {"_id": 1, "review_id": 1, "business_id": 1,
                 "user_id": 1, "date": 1}
        ):
            if doc["_id"] != doc.get("review_id"):
                error("Review: _id incorrect")

            if doc.get("business_id") not in business_ids:
                error("Review: établissement manquant")

            if doc.get("user_id") not in user_ids:
                error("Review: utilisateur manquant")

            date = doc.get("date")
            if not isinstance(date, datetime):
                error("Review: date non BSON Date")
            elif not START <= date < END:
                error("Review: date hors période")

        # 5. Tips
        for doc in db.tips.find({}):
            if doc.get("business_id") not in business_ids:
                error("Tip: établissement manquant")

            if doc.get("user_id") not in user_ids:
                error("Tip: utilisateur manquant")

            date = doc.get("date")
            if not isinstance(date, datetime):
                error("Tip: date non BSON Date")
                continue

            if not START <= date < END:
                error("Tip: date hors période")

            # Reconstituer le JSONL initial pour vérifier
            # que le hash SHA-256 correspond.
            original = {
                key: value
                for key, value in doc.items()
                if key != "_id"
            }
            original["date"] = date.strftime(DATE_FORMAT)

            canonical = json.dumps(
                original,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            expected_id = "tip_" + hashlib.sha256(
                canonical.encode("utf-8")
            ).hexdigest()

            if doc["_id"] != expected_id:
                error("Tip: _id SHA-256 incorrect")

        # 6. Check-ins
        for doc in db.checkins.find({}):
            if doc["_id"] != doc.get("business_id"):
                error("Checkin: _id incorrect")

            if doc.get("business_id") not in business_ids:
                error("Checkin: établissement manquant")

            dates = doc.get("dates")

            if not isinstance(dates, list):
                error("Checkin: dates non tableau")
                continue

            checked_dates += len(dates)

            if doc.get("checkin_count") != len(dates):
                error("Checkin: compteur incorrect")

            for date in dates:
                if not isinstance(date, datetime):
                    error("Checkin: élément non BSON Date")
                elif not START <= date < END:
                    error("Checkin: date hors période")

        if checked_dates != EXPECTED_CHECKIN_DATES:
            error(
                f"Total dates Check-ins: {checked_dates} "
                f"au lieu de {EXPECTED_CHECKIN_DATES}"
            )

        status = "PASS" if not errors else "FAIL"

        report = {
            "database": db.name,
            "status": status,
            "expected_counts": EXPECTED,
            "actual_counts": actual_counts,
            "expected_checkin_dates": EXPECTED_CHECKIN_DATES,
            "actual_checkin_dates": checked_dates,
            "errors": dict(errors),
            "error_examples": examples,
        }

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        print()
        print("Dates Check-ins :", checked_dates)
        print("Erreurs :", dict(errors))
        print("Statut :", status)
        print("Rapport :", REPORT_PATH)

        if errors:
            raise SystemExit(1)

    finally:
        client.close()


if __name__ == "__main__":
    main()
