
import os
from pymongo import MongoClient

COLLECTIONS = [
    "businesses",
    "reviews",
    "tips",
    "checkins",
    "users",
]


def main():
    client = MongoClient(
        os.environ["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
    )

    try:
        client.admin.command("ping")

        database = client[os.environ["MONGO_DATABASE"]]

        print("=== VERIFICATION AVANT IMPORT ===")
        print("Base :", database.name)

        existing = set(database.list_collection_names())
        safe = True

        for name in COLLECTIONS:
            if name not in existing:
                print(f"{name}: absente (OK)")
                continue

            count = database[name].count_documents({})
            print(f"{name}: {count} documents")

            if count != 0:
                safe = False

        print()
        print("Statut :", "PASS" if safe else "BLOCKED")

        if not safe:
            raise RuntimeError(
                "Importation bloquee : des collections "
                "contiennent deja des documents."
            )

    finally:
        client.close()


if __name__ == "__main__":
    main()
