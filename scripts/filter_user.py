
import json
from collections import Counter
from pathlib import Path

REVIEW_FILE = Path("/data/processed/reviews.jsonl")
TIP_FILE = Path("/data/processed/tips.jsonl")
RAW_FILE = Path("/data/raw/yelp_academic_dataset_user.json")
OUTPUT_FILE = Path("/data/processed/users.jsonl")
REPORT_FILE = Path("/app/results/filter_user_report.json")


def load_referenced_user_ids(path):
    """Récupérer les auteurs d'un fichier JSONL validé."""
    if not path.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    ids = set()
    documents = 0

    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):

            if not line.strip():
                raise ValueError(
                    f"Ligne vide dans {path.name} : {line_number}"
                )

            try:
                document = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"JSON invalide dans {path.name}, "
                    f"ligne {line_number}"
                ) from error

            if not isinstance(document, dict):
                raise ValueError(
                    f"Document invalide dans {path.name}, "
                    f"ligne {line_number}"
                )

            user_id = document.get("user_id")

            if (
                not isinstance(user_id, str)
                or not user_id.strip()
            ):
                raise ValueError(
                    f"user_id invalide dans {path.name}, "
                    f"ligne {line_number}"
                )

            ids.add(user_id)
            documents += 1

    if documents == 0:
        raise ValueError(f"Fichier vide : {path.name}")

    return ids, documents


def filter_users():
    if not RAW_FILE.is_file():
        raise FileNotFoundError(
            f"Fichier Yelp Users introuvable : {RAW_FILE}"
        )

    review_ids, review_count = load_referenced_user_ids(
        REVIEW_FILE
    )
    tip_ids, tip_count = load_referenced_user_ids(
        TIP_FILE
    )

    required_ids = review_ids | tip_ids

    print("Auteurs uniques des Reviews :", len(review_ids))
    print("Auteurs uniques des Tips :", len(tip_ids))
    print("Utilisateurs uniques recherchés :", len(required_ids))

    counters = Counter()
    found_ids = set()

    OUTPUT_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )
    REPORT_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    temporary_file = OUTPUT_FILE.with_name(
        OUTPUT_FILE.name + ".tmp"
    )

    try:
        with RAW_FILE.open("r", encoding="utf-8") as source:
            with temporary_file.open(
                "w", encoding="utf-8"
            ) as output:

                for line_number, line in enumerate(
                    source, start=1
                ):
                    counters["total_users_read"] += 1

                    if not line.strip():
                        raise ValueError(
                            f"Ligne Users vide : {line_number}"
                        )

                    try:
                        user = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise ValueError(
                            f"JSON Users invalide, "
                            f"ligne {line_number}"
                        ) from error

                    if not isinstance(user, dict):
                        raise ValueError(
                            f"Document Users invalide, "
                            f"ligne {line_number}"
                        )

                    user_id = user.get("user_id")

                    if (
                        not isinstance(user_id, str)
                        or not user_id.strip()
                    ):
                        raise ValueError(
                            f"user_id invalide, ligne {line_number}"
                        )

                    # Garder uniquement les utilisateurs
                    # référencés par Reviews ou Tips.
                    if user_id not in required_ids:
                        counters["excluded_not_referenced"] += 1
                        continue

                    if user_id in found_ids:
                        raise ValueError(
                            "user_id dupliqué dans le fichier "
                            f"source, ligne {line_number}"
                        )

                    found_ids.add(user_id)

                    # Nous conservons les champs utiles
                    # et excluons le réseau social friends.
                    filtered_user = {
                        key: value
                        for key, value in user.items()
                        if key != "friends"
                    }

                    output.write(
                        json.dumps(
                            filtered_user,
                            ensure_ascii=False
                        ) + "\n"
                    )

                    counters["selected_users"] += 1

        missing_ids = required_ids - found_ids

        report = {
            "dataset": "Yelp Tucson Users",
            "review_documents": review_count,
            "tip_documents": tip_count,
            "unique_review_authors": len(review_ids),
            "unique_tip_authors": len(tip_ids),
            "required_unique_users": len(required_ids),
            "total_users_read": counters[
                "total_users_read"
            ],
            "excluded_not_referenced": counters[
                "excluded_not_referenced"
            ],
            "selected_users": counters[
                "selected_users"
            ],
            "missing_referenced_users": len(missing_ids),
            "excluded_fields": ["friends"],
            "status": (
                "COMPLETED" if not missing_ids else "FAIL"
            )
        }

        REPORT_FILE.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False
            ) + "\n",
            encoding="utf-8"
        )

        # Ne pas publier un nouveau fichier incomplet
        # si des auteurs référencés sont absents.
        if missing_ids:
            raise ValueError(
                f"{len(missing_ids)} utilisateurs "
                "référencés sont absents du fichier Yelp"
            )

        temporary_file.replace(OUTPUT_FILE)

    except Exception:
        temporary_file.unlink(missing_ok=True)
        raise

    print("\n=== FILTER USERS ===")

    for key, value in report.items():
        print(f"{key} : {value}")

    print("Fichier :", OUTPUT_FILE)
    print("Rapport :", REPORT_FILE)


if __name__ == "__main__":
    filter_users()
