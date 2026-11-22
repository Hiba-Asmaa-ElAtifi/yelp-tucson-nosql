
import csv
import os
import statistics
import time
from pathlib import Path

from pymongo import MongoClient


# Parametres de Q1
LONGITUDE = -110.880452
LATITUDE = 32.223236
RADIUS_METERS = 2000
MIN_STARS = 0

# Protocole : echauffement puis repetitions
WARMUP_RUNS = 3
MEASURED_RUNS = 20

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "yelp_tucson")

OUTPUT_FILE = Path("/app/results/week4/q1/q1_avec_index_mesures.csv")


def percentile_95(values):
    ordered = sorted(values)
    position = 0.95 * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def main():
    client = MongoClient(MONGO_URI)

    try:
        db = client[MONGO_DATABASE]

        query = {
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [LONGITUDE, LATITUDE],
                    },
                    "$maxDistance": RADIUS_METERS,
                }
            },
            "stars": {"$gte": MIN_STARS},
        }

        index_names = [
            index["name"]
            for index in db.businesses.list_indexes()
        ]

        required_index = "idx_businesses_location_2dsphere"

        if required_index not in index_names:
            raise RuntimeError(
                "Index geospatial absent : " + required_index
            )

        print("Base MongoDB :", MONGO_DATABASE)
        print("Index verifie :", required_index)
        print("Echauffement :", WARMUP_RUNS, "executions")
        print("Mesures :", MEASURED_RUNS, "executions")

        # Echauffement non comptabilise
        for _ in range(WARMUP_RUNS):
            list(db.businesses.find(query, {"_id": 1}))

        measurements = []
        expected_count = None

        for run in range(1, MEASURED_RUNS + 1):
            start = time.perf_counter()

            documents = list(
                db.businesses.find(query, {"_id": 1})
            )

            elapsed_ms = (time.perf_counter() - start) * 1000
            count = len(documents)

            if expected_count is None:
                expected_count = count
            elif count != expected_count:
                raise RuntimeError(
                    "Nombre de resultats different entre les executions."
                )

            measurements.append({
                "execution": run,
                "duration_ms": round(elapsed_ms, 3),
                "n_returned": count,
            })

            print(
                f"Execution {run:02d} : "
                f"{elapsed_ms:.3f} ms, "
                f"{count} documents"
            )

        durations = [
            item["duration_ms"]
            for item in measurements
        ]

        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "execution",
                    "duration_ms",
                    "n_returned",
                ],
            )
            writer.writeheader()
            writer.writerows(measurements)

        print("\n--- RESULTATS Q1 AVEC INDEX ---")
        print(f"Documents retournes : {expected_count}")
        print(f"Mediane : {statistics.median(durations):.3f} ms")
        print(f"P95 : {percentile_95(durations):.3f} ms")
        print(f"Minimum : {min(durations):.3f} ms")
        print(f"Maximum : {max(durations):.3f} ms")
        print(f"Fichier CSV : {OUTPUT_FILE}")

    finally:
        client.close()


if __name__ == "__main__":
    main()
