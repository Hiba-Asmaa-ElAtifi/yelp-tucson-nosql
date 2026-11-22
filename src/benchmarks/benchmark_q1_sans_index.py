
import csv
import math
import os
import statistics
import time
from pathlib import Path

from pymongo import MongoClient


# Memes parametres geographiques que Q1
LONGITUDE = -110.880452
LATITUDE = 32.223236
RADIUS_METERS = 2000
MIN_STARS = 0

# Protocole de benchmark
WARMUP_RUNS = 3
MEASURED_RUNS = 20

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://mongodb:27017/"
)

MONGO_DATABASE = os.getenv(
    "MONGO_DATABASE",
    "yelp_tucson"
)

OUTPUT_FILE = Path(
    "/app/results/week4/q1/q1_sans_index_mesures.csv"
)


def distance_meters(lon1, lat1, lon2, lat2):
    """
    Calcule la distance entre deux points
    avec la formule de Haversine.
    """

    # Rayon terrestre de reference utilise par MongoDB
    earth_radius = 6378137.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lat = lat2 - lat1
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    return 2 * earth_radius * math.asin(
        min(1.0, math.sqrt(a))
    )


def percentile_95(values):
    ordered = sorted(values)

    position = 0.95 * (len(ordered) - 1)

    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)

    fraction = position - lower

    return ordered[lower] + fraction * (
        ordered[upper] - ordered[lower]
    )


def run_search(collection):
    """
    Recherche les commerces dans un rayon de 2 km
    sans utiliser l'index geospatial.

    MongoDB lit les commerces avec l'index _id_.
    Python calcule ensuite les distances.
    """

    cursor = collection.find(
        {"stars": {"$gte": MIN_STARS}},
        {"_id": 1, "location": 1},
        hint="_id_",
    )

    matching_ids = []

    for business in cursor:
        location = business.get("location")

        if not isinstance(location, dict):
            continue

        coordinates = location.get("coordinates")

        if not isinstance(coordinates, (list, tuple)):
            continue

        if len(coordinates) < 2:
            continue

        lon, lat = coordinates[:2]

        if not isinstance(lon, (int, float)):
            continue

        if not isinstance(lat, (int, float)):
            continue

        distance = distance_meters(
            LONGITUDE,
            LATITUDE,
            lon,
            lat,
        )

        if distance <= RADIUS_METERS:
            matching_ids.append(business["_id"])

    return matching_ids


def main():
    client = MongoClient(MONGO_URI)

    try:
        db = client[MONGO_DATABASE]
        collection = db.businesses

        print("Base MongoDB :", MONGO_DATABASE)
        print("Methode : parcours sans index geospatial")
        print("Rayon terrestre : 6378137.0 m")
        print("Echauffement :", WARMUP_RUNS, "executions")
        print("Mesures :", MEASURED_RUNS, "executions")

        # Executions d'echauffement
        for _ in range(WARMUP_RUNS):
            run_search(collection)

        measurements = []
        expected_count = None

        # Executions mesurees
        for run in range(1, MEASURED_RUNS + 1):
            start = time.perf_counter()

            matching_ids = run_search(collection)

            elapsed_ms = (
                time.perf_counter() - start
            ) * 1000

            count = len(matching_ids)

            if expected_count is None:
                expected_count = count

            elif count != expected_count:
                raise RuntimeError(
                    "Nombre de resultats different "
                    "entre les executions."
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

        # Enregistrement du fichier CSV
        OUTPUT_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with OUTPUT_FILE.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
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

        # Resultats statistiques
        print("\n--- RESULTATS Q1 SANS INDEX ---")

        print(
            f"Documents retournes : {expected_count}"
        )

        print(
            f"Mediane : "
            f"{statistics.median(durations):.3f} ms"
        )

        print(
            f"P95 : "
            f"{percentile_95(durations):.3f} ms"
        )

        print(
            f"Minimum : {min(durations):.3f} ms"
        )

        print(
            f"Maximum : {max(durations):.3f} ms"
        )

        print(
            f"Fichier CSV : {OUTPUT_FILE}"
        )

    finally:
        client.close()


if __name__ == "__main__":
    main()
