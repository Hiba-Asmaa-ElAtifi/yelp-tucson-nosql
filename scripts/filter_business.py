
import ast
import json
import re
from pathlib import Path

RAW_FILE = Path("/data/raw/yelp_academic_dataset_business.json")
OUTPUT_FILE = Path("/data/processed/businesses.jsonl")

DAYS = (
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
)

TIME_PATTERN = re.compile(r"^(\d{1,2}):(\d{1,2})$")


def parse_time(value):
    """Convertit une heure en minutes depuis minuit."""
    match = TIME_PATTERN.fullmatch(value.strip())

    if not match:
        return None

    hour, minute = map(int, match.groups())

    if not (0 <= hour <= 24 and 0 <= minute < 60):
        return None

    if hour == 24 and minute != 0:
        return None

    return hour * 60 + minute


def normalize_hours(hours):
    """Normalise les horaires sans inventer les valeurs absentes."""
    if hours is None:
        return None

    if not isinstance(hours, dict):
        return hours

    normalized = {}

    for day, interval in hours.items():
        if day not in DAYS or not isinstance(interval, str):
            normalized[day] = interval
            continue

        parts = interval.split("-")

        if len(parts) != 2:
            normalized[day] = interval
            continue

        opening = parse_time(parts[0])
        closing = parse_time(parts[1])

        if opening is None or closing is None:
            normalized[day] = interval
            continue

        normalized[day] = {
            "open_minutes": opening,
            "close_minutes": closing
        }

    return normalized


def normalize_attribute(value):
    """Convertit les valeurs Yelp avec un parseur sûr."""
    if isinstance(value, dict):
        return {
            key: normalize_attribute(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [normalize_attribute(item) for item in value]

    if not isinstance(value, str):
        return value

    cleaned = value.strip()

    if cleaned == "True":
        return True

    if cleaned == "False":
        return False

    if cleaned in ("None", "null"):
        return None

    try:
        converted = ast.literal_eval(cleaned)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return value

    if isinstance(converted, (bool, int, float, dict, list, str)):
        return normalize_attribute(converted) if isinstance(
            converted, (dict, list)
        ) else converted

    return value


def filter_businesses():
    total = 0
    selected = 0

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with RAW_FILE.open("r", encoding="utf-8") as source:
        with OUTPUT_FILE.open("w", encoding="utf-8") as output:

            for line in source:
                total += 1
                business = json.loads(line)

                city = str(business.get("city") or "").strip().casefold()
                state = str(business.get("state") or "").strip().upper()

                if city != "tucson" or state != "AZ":
                    continue

                # Catégories
                categories = business.get("categories") or ""

                business["categories"] = [
                    category.strip()
                    for category in categories.split(",")
                    if category.strip()
                ]

                # Coordonnées GeoJSON
                latitude = business.get("latitude")
                longitude = business.get("longitude")

                if (
                    type(latitude) in (int, float)
                    and type(longitude) in (int, float)
                    and -90 <= latitude <= 90
                    and -180 <= longitude <= 180
                ):
                    business["location"] = {
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    }
                else:
                    business["location"] = None

                # Conserver les données d'origine
                business["source_hours"] = business.get("hours")
                business["source_attributes"] = business.get("attributes")
                business["source_stars"] = business.get("stars")
                business["source_review_count"] = business.get("review_count")

                # Normaliser les horaires et attributs
                business["hours"] = normalize_hours(business.get("hours"))

                attributes = business.get("attributes")

                if isinstance(attributes, dict):
                    business["attributes"] = normalize_attribute(attributes)

                # Uniformiser la localisation administrative
                business["city"] = "Tucson"
                business["state"] = "AZ"

                output.write(
                    json.dumps(business, ensure_ascii=False) + "\n"
                )

                selected += 1

    print("Total des établissements :", total)
    print("Établissements Tucson :", selected)
    print("Fichier créé :", OUTPUT_FILE)


if __name__ == "__main__":
    filter_businesses()
