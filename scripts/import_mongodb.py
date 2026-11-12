
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from bson import BSON
from pymongo import MongoClient

# Configuration Docker
DATA_DIR = Path("/data/processed")
MONGO_URI = os.environ["MONGO_URI"]
DATABASE_NAME = os.environ["MONGO_DATABASE"]

BATCH_SIZE = 500
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

COLLECTIONS = {
    "businesses": "businesses.jsonl",
    "reviews": "reviews.jsonl",
    "tips": "tips.jsonl",
    "checkins": "checkins.jsonl",
    "users": "users.jsonl",
}


def convert_date(value):
    """Convertit une date Yelp en datetime pour BSON."""
    parsed = datetime.strptime(value, DATE_FORMAT)

    # Convention technique : UTC.
    # Le dataset ne précise pas explicitement le fuseau.
    return parsed.replace(tzinfo=timezone.utc)


def create_tip_id(document):
    """Crée un identifiant stable à partir du Tip original."""
    canonical = json.dumps(
        document,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()

    return "tip_" + digest


def transform_document(collection_name, document):
    """Adapte un document JSONL au modèle MongoDB."""
    document = document.copy()

    if collection_name == "businesses":
        document["_id"] = document["business_id"]

    elif collection_name == "reviews":
        document["_id"] = document["review_id"]
        document["date"] = convert_date(document["date"])

    elif collection_name == "tips":
        document["_id"] = create_tip_id(document)
        document["date"] = convert_date(document["date"])

    elif collection_name == "checkins":
        document["_id"] = document["business_id"]

        document["dates"] = [
            convert_date(value)
            for value in document["dates"]
        ]

        if document["checkin_count"] != len(document["dates"]):
            raise ValueError(
                "checkin_count différent du nombre de dates"
            )

    elif collection_name == "users":
        document["_id"] = document["user_id"]
        document["yelping_since"] = convert_date(
            document["yelping_since"]
        )

    return document


def import_collection(database, collection_name, file_name):
    """Importe un fichier JSONL progressivement."""
    source = DATA_DIR / file_name

    if not source.is_file():
        raise FileNotFoundError(source)

    collection = database[collection_name]
    batch = []
    total = 0

    with source.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                raise ValueError(
                    f"{file_name}, ligne {line_number} : ligne vide"
                )

            try:
                original = json.loads(line)
                document = transform_document(
                    collection_name, original
                )

                # Contrôle de la limite BSON MongoDB
                if len(BSON.encode(document)) > 16 * 1024 * 1024:
                    raise ValueError(
                        "Document supérieur à 16 Mio"
                    )

            except Exception as error:
                raise ValueError(
                    f"{file_name}, ligne {line_number} : {error}"
                ) from error

            batch.append(document)

            if len(batch) >= BATCH_SIZE:
                collection.insert_many(batch, ordered=True)
                total += len(batch)
                batch.clear()

        if batch:
            collection.insert_many(batch, ordered=True)
            total += len(batch)

    print(f"{collection_name}: {total} documents importés")
    return total


def main():
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
    )

    try:
        client.admin.command("ping")
        database = client[DATABASE_NAME]

        # Vérification des fichiers avant toute insertion
        for file_name in COLLECTIONS.values():
            source = DATA_DIR / file_name
            if not source.is_file():
                raise FileNotFoundError(source)

        # Sécurité : ne pas charger sur des collections
        # déjà remplies.
        occupied = [
            name
            for name in COLLECTIONS
            if database[name].estimated_document_count() > 0
        ]

        if occupied:
            raise RuntimeError(
                "Importation annulée : collections non vides : "
                + ", ".join(occupied)
            )

        print("Connexion MongoDB : PASS")
        print("Base :", DATABASE_NAME)
        print("Début de l'importation")

        totals = {}

        for collection_name, file_name in COLLECTIONS.items():
            totals[collection_name] = import_collection(
                database,
                collection_name,
                file_name,
            )

        print("\nImportation terminée.")
        print("Total :", sum(totals.values()))

    finally:
        client.close()


if __name__ == "__main__":
    main()
