
import csv
import os
import statistics
import time
from pathlib import Path

from pymongo import MongoClient


# Commerce ayant 2 223 avis
BUSINESS_ID = "UCMSWPqzXjd7QHq7v8PJjQ"

# Parametres identiques a la requete Q4
PAGE_SIZE = 5
PAGES = [1, 10, 100, 400]

# Protocole de mesure
WARMUP_RUNS = 3
MEASURED_RUNS = 20

# Index existants dans MongoDB
INDEXES = {
    "ancien_index": "idx_reviews_business_date",
    "nouvel_index": "idx_reviews_business_date_id_week4",
}

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://mongodb:27017/"
)

MONGO_DATABASE = os.getenv(
    "MONGO_DATABASE",
    "yelp_tucson"
)

OUTPUT_DIR = Path("/app/results/week4/q4")


def percentile_95(values):
    """Calcule le percentile 95 avec interpolation lineaire."""
    ordered = sorted(values)
    position = 0.95 * (len(ordered) - 1)

    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower

    return ordered[lower] + fraction * (
        ordered[upper] - ordered[lower]
    )


def run_query(collection, page, index_name):
    """
    Reproduit la requete Q4 avec un index impose.

    Le hint permet de comparer les deux index
    sans supprimer ni modifier les index existants.
    """
    query = {"business_id": BUSINESS_ID}

    projection = {
        "_id": 1,
        "stars": 1,
        "date": 1,
        "text": 1,
    }

    reviews = list(
        collection.find(query, projection)
        .sort([("date", -1), ("_id", 1)])
        .skip((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .hint(index_name)
    )

    return reviews


def main():
    client = MongoClient(MONGO_URI)

    try:
        collection = client[MONGO_DATABASE].reviews
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        print("=== BENCHMARK Q4 : PAGINATION DES AVIS ===")
        print("Base :", MONGO_DATABASE)
        print("Business ID :", BUSINESS_ID)
        print("Pages testees :", PAGES)
        print("Taille de page :", PAGE_SIZE)
        print("Echauffements :", WARMUP_RUNS)
        print("Mesures :", MEASURED_RUNS)

        all_measurements = []
        summaries = []

        for page in PAGES:
            print(f"\n=== PAGE {page} ===")

            reference_ids = None

            for label, index_name in INDEXES.items():
                print(f"\nIndex : {label}")
                print("Nom :", index_name)

                # Echauffement
                for _ in range(WARMUP_RUNS):
                    run_query(collection, page, index_name)

                durations = []
                result_ids = None

                # Mesures repetees
                for execution in range(1, MEASURED_RUNS + 1):
                    start = time.perf_counter()

                    reviews = run_query(
                        collection,
                        page,
                        index_name,
                    )

                    duration_ms = (
                        time.perf_counter() - start
                    ) * 1000

                    ids = [review["_id"] for review in reviews]

                    if result_ids is None:
                        result_ids = ids
                    elif ids != result_ids:
                        raise RuntimeError(
                            "Resultats differents entre executions."
                        )

                    durations.append(duration_ms)

                    all_measurements.append({
                        "page": page,
                        "index": label,
                        "execution": execution,
                        "duration_ms": round(duration_ms, 3),
                        "n_returned": len(reviews),
                    })

                # Verification de l'equivalence fonctionnelle
                if reference_ids is None:
                    reference_ids = result_ids
                elif result_ids != reference_ids:
                    raise RuntimeError(
                        f"Resultats differents entre index "
                        f"pour la page {page}."
                    )

                median_ms = statistics.median(durations)
                p95_ms = percentile_95(durations)

                summaries.append({
                    "page": page,
                    "index": label,
                    "median_ms": round(median_ms, 3),
                    "p95_ms": round(p95_ms, 3),
                    "n_returned": len(result_ids),
                    "identical_results": True,
                })

                print("Avis retournes :", len(result_ids))
                print(f"Mediane : {median_ms:.3f} ms")
                print(f"P95 : {p95_ms:.3f} ms")

            print(
                f"Equivalence des resultats page {page} : OK"
            )

        # CSV des 160 mesures individuelles
        measurements_file = (
            OUTPUT_DIR / "q4_mesures.csv"
        )

        with measurements_file.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "page",
                    "index",
                    "execution",
                    "duration_ms",
                    "n_returned",
                ],
            )
            writer.writeheader()
            writer.writerows(all_measurements)

        # CSV des medianes et p95
        summary_file = (
            OUTPUT_DIR / "q4_resume.csv"
        )

        with summary_file.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "page",
                    "index",
                    "median_ms",
                    "p95_ms",
                    "n_returned",
                    "identical_results",
                ],
            )
            writer.writeheader()
            writer.writerows(summaries)

        print("\n=== BENCHMARK Q4 TERMINE ===")
        print("Mesures enregistrees :", len(all_measurements))
        print("Fichier :", measurements_file)
        print("Resume :", summary_file)
        print("Equivalence fonctionnelle : OK")

    finally:
        client.close()


if __name__ == "__main__":
    main()
