
import csv
import math
import os
import statistics
import time
from pathlib import Path

from pymongo import MongoClient


# Commerce utilise pour Q4 : 2 223 avis
BUSINESS_ID = "UCMSWPqzXjd7QHq7v8PJjQ"

# Nouvelle note simulee (aucun avis n'est insere)
NEW_STARS = 5.0

# Protocole de mesure
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

OUTPUT_DIR = Path(
    "/app/results/week4/q5_q6"
)


def percentile_95(values):
    """Calcule le percentile 95 par interpolation lineaire."""
    ordered = sorted(values)

    position = 0.95 * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)

    fraction = position - lower

    return ordered[lower] + fraction * (
        ordered[upper] - ordered[lower]
    )


def get_initial_stats(collection):
    """
    Lit les statistiques initiales depuis les avis.

    Cette operation est effectuee hors des mesures
    pour initialiser les deux strategies.
    """
    result = list(collection.aggregate([
        {
            "$match": {
                "business_id": BUSINESS_ID
            }
        },
        {
            "$group": {
                "_id": "$business_id",
                "count": {"$sum": 1},
                "average": {"$avg": "$stars"},
            }
        },
    ]))

    if not result:
        raise RuntimeError(
            "Aucun avis pour le commerce selectionne."
        )

    return result[0]["count"], result[0]["average"]


def full_recompute(collection):
    """
    Strategie A : recalcul complet de la moyenne.

    Reproduit l'agregation utilisee dans Q5.
    Simule ensuite l'ajout d'une note dans le
    resultat, sans insertion dans MongoDB.
    """
    result = list(collection.aggregate([
        {
            "$match": {
                "business_id": BUSINESS_ID
            }
        },
        {
            "$group": {
                "_id": "$business_id",
                "count": {"$sum": 1},
                "total_stars": {"$sum": "$stars"},
            }
        },
    ]))

    if not result:
        raise RuntimeError("Aucun avis trouve.")

    count = result[0]["count"]
    total_stars = result[0]["total_stars"]

    new_count = count + 1
    new_average = (
        total_stars + NEW_STARS
    ) / new_count

    return new_count, new_average


def incremental_update(initial_count, initial_average):
    """
    Strategie B : mise a jour incrementale.

    Aucun parcours de la collection reviews.
    Aucun document MongoDB n'est modifie.
    """
    new_count = initial_count + 1

    new_average = (
        initial_count * initial_average + NEW_STARS
    ) / new_count

    return new_count, new_average


def run_benchmark(label, operation):
    """Effectue les echauffements et les mesures."""

    for _ in range(WARMUP_RUNS):
        operation()

    durations = []
    expected_result = None
    measurements = []

    for execution in range(1, MEASURED_RUNS + 1):
        start = time.perf_counter()

        result = operation()

        elapsed_ms = (
            time.perf_counter() - start
        ) * 1000

        if expected_result is None:
            expected_result = result

        elif (
            result[0] != expected_result[0]
            or not math.isclose(
                result[1],
                expected_result[1],
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        ):
            raise RuntimeError(
                "Resultats differents entre executions."
            )

        durations.append(elapsed_ms)

        measurements.append({
            "strategie": label,
            "execution": execution,
            "duration_ms": round(elapsed_ms, 6),
            "new_count": result[0],
            "new_average": round(result[1], 12),
        })

    return expected_result, durations, measurements


def main():
    client = MongoClient(MONGO_URI)

    try:
        collection = client[MONGO_DATABASE].reviews

        initial_count, initial_average = (
            get_initial_stats(collection)
        )

        print("=== BENCHMARK Q5/Q6 ===")
        print("Base :", MONGO_DATABASE)
        print("Business ID :", BUSINESS_ID)
        print("Avis existants :", initial_count)
        print("Moyenne initiale :", initial_average)
        print("Nouvelle note simulee :", NEW_STARS)
        print("Echauffements :", WARMUP_RUNS)
        print("Mesures :", MEASURED_RUNS)

        strategies = {
            "recalcul_complet": lambda: full_recompute(
                collection
            ),
            "incremental": lambda: incremental_update(
                initial_count,
                initial_average,
            ),
        }

        all_measurements = []
        summaries = []
        reference_result = None

        for label, operation in strategies.items():
            print(f"\n=== {label} ===")

            result, durations, measurements = (
                run_benchmark(label, operation)
            )

            if reference_result is None:
                reference_result = result

            elif (
                result[0] != reference_result[0]
                or not math.isclose(
                    result[1],
                    reference_result[1],
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            ):
                raise RuntimeError(
                    "Les deux strategies ne donnent pas "
                    "les memes statistiques."
                )

            median_ms = statistics.median(durations)
            p95_ms = percentile_95(durations)

            print("Nouveau nombre d'avis :", result[0])
            print(f"Nouvelle moyenne : {result[1]:.6f}")
            print(f"Mediane : {median_ms:.6f} ms")
            print(f"P95 : {p95_ms:.6f} ms")

            summaries.append({
                "strategie": label,
                "median_ms": round(median_ms, 6),
                "p95_ms": round(p95_ms, 6),
                "new_count": result[0],
                "new_average": round(result[1], 12),
                "identical_results": True,
            })

            all_measurements.extend(measurements)

        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        measurements_file = (
            OUTPUT_DIR / "q5_q6_mesures.csv"
        )

        with measurements_file.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "strategie",
                    "execution",
                    "duration_ms",
                    "new_count",
                    "new_average",
                ],
            )
            writer.writeheader()
            writer.writerows(all_measurements)

        summary_file = (
            OUTPUT_DIR / "q5_q6_resume.csv"
        )

        with summary_file.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "strategie",
                    "median_ms",
                    "p95_ms",
                    "new_count",
                    "new_average",
                    "identical_results",
                ],
            )
            writer.writeheader()
            writer.writerows(summaries)

        print("\n=== BENCHMARK TERMINE ===")
        print("Mesures :", len(all_measurements))
        print("Equivalence des resultats : OK")
        print("Fichier :", measurements_file)
        print("Resume :", summary_file)

    finally:
        client.close()


if __name__ == "__main__":
    main()
