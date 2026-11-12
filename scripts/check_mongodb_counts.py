
import os
from pymongo import MongoClient

EXPECTED = {
    "businesses": 9261,
    "reviews": 375076,
    "tips": 49876,
    "checkins": 7747,
    "users": 117497,
}


def main():
    client = MongoClient(
        os.environ["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
    )

    try:
        client.admin.command("ping")
        database = client[os.environ["MONGO_DATABASE"]]

        print("=== VERIFICATION MONGODB ===")
        print("Base :", database.name)
        print()

        all_ok = True
        total = 0

        for name, expected in EXPECTED.items():
            actual = database[name].count_documents({})
            total += actual

            status = "PASS" if actual == expected else "FAIL"

            if status == "FAIL":
                all_ok = False

            print(
                f"{name}: {actual} / {expected} "
                f"documents - {status}"
            )

        print()
        print("Total :", total)
        print("Statut :", "PASS" if all_ok else "FAIL")

        if not all_ok:
            raise SystemExit(1)

    finally:
        client.close()


if __name__ == "__main__":
    main()
