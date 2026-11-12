
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

# 1. Chemins des fichiers dans Docker
USER_FILE = Path("/data/processed/users.jsonl")
REVIEW_FILE = Path("/data/processed/reviews.jsonl")
TIP_FILE = Path("/data/processed/tips.jsonl")

FILTER_REPORT = Path("/app/results/filter_user_report.json")
REPORT_FILE = Path("/app/results/validate_user_report.json")

# 2. Compteurs des erreurs
errors = Counter()
examples = {}


def add_error(name, line_number=None):
    """Enregistrer une erreur et quelques lignes concernées."""
    errors[name] += 1

    if line_number is not None:
        examples.setdefault(name, [])

        if len(examples[name]) < 5:
            examples[name].append(line_number)


def read_jsonl(path):
    """Lire un fichier JSONL ligne par ligne."""
    with path.open("r", encoding="utf-8") as source:
        for number, line in enumerate(source, start=1):

            if not line.strip():
                raise ValueError(
                    f"Ligne vide dans {path.name}: {number}"
                )

            try:
                document = json.loads(line)

            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSON invalide dans {path.name}: {number}"
                ) from exc

            if not isinstance(document, dict):
                raise ValueError(
                    f"Document incorrect dans {path.name}: {number}"
                )

            yield number, document


def load_referenced_users(path):
    """Récupérer les user_id des Reviews ou des Tips."""
    ids = set()
    count = 0

    for number, document in read_jsonl(path):
        user_id = document.get("user_id")

        if (
            not isinstance(user_id, str)
            or not user_id.strip()
        ):
            raise ValueError(
                f"user_id invalide dans {path.name}: {number}"
            )

        ids.add(user_id)
        count += 1

    if count == 0:
        raise ValueError(
            f"Fichier vide: {path.name}"
        )

    return ids, count


def valid_nonnegative_integer(value):
    """Vérifier qu'une valeur est un entier positif ou nul."""
    return type(value) is int and value >= 0


def validate_user(user, number):
    """Valider les champs importants d'un utilisateur Yelp."""

    # 3. Vérifier le nom
    if not isinstance(user.get("name"), str):
        add_error("invalid_name", number)

    # 4. Vérifier la date d'inscription
    # Attention : on ne filtre PAS sur 2012-2021.
    joined = user.get("yelping_since")

    if not isinstance(joined, str):
        add_error("invalid_yelping_since", number)

    else:
        try:
            datetime.strptime(
                joined,
                "%Y-%m-%d %H:%M:%S"
            )

        except ValueError:
            add_error("invalid_yelping_since", number)

    # 5. Vérifier les statistiques Yelp
    integer_fields = (
        "review_count",
        "useful",
        "funny",
        "cool",
        "fans",
    )

    for field in integer_fields:
        if not valid_nonnegative_integer(user.get(field)):
            add_error(f"invalid_{field}", number)

    # 6. Vérifier la moyenne des notes
    average = user.get("average_stars")

    if (
        type(average) not in (int, float)
        or not math.isfinite(average)
        or not 0 <= average <= 5
    ):
        add_error("invalid_average_stars", number)

    # 7. Vérifier le statut Elite
    if not isinstance(user.get("elite"), str):
        add_error("invalid_elite", number)

    # 8. Vérifier tous les compteurs de compliments
    compliment_fields = (
        "compliment_hot",
        "compliment_more",
        "compliment_profile",
        "compliment_cute",
        "compliment_list",
        "compliment_note",
        "compliment_plain",
        "compliment_cool",
        "compliment_funny",
        "compliment_writer",
        "compliment_photos",
    )

    for field in compliment_fields:
        if not valid_nonnegative_integer(user.get(field)):
            add_error(f"invalid_{field}", number)

    # 9. Vérifier que le champ friends a été exclu
    if "friends" in user:
        add_error("friends_not_removed", number)


def validate_users():

    # 10. Vérifier la présence des fichiers nécessaires
    for path in (
        USER_FILE,
        REVIEW_FILE,
        TIP_FILE,
        FILTER_REPORT
    ):
        if not path.is_file():
            raise SystemExit(
                f"FAIL : fichier introuvable : {path}"
            )

    # 11. Récupérer les auteurs des Reviews et Tips
    review_ids, review_documents = load_referenced_users(
        REVIEW_FILE
    )

    tip_ids, tip_documents = load_referenced_users(
        TIP_FILE
    )

    # Ensemble des utilisateurs nécessaires
    required_ids = review_ids | tip_ids

    seen_ids = set()
    total_users = 0

    # 12. Parcourir les utilisateurs filtrés
    for number, user in read_jsonl(USER_FILE):
        total_users += 1

        user_id = user.get("user_id")

        # Vérifier l'identifiant
        if (
            not isinstance(user_id, str)
            or not user_id.strip()
        ):
            add_error("invalid_user_id", number)

        elif user_id in seen_ids:
            add_error("duplicate_user_id", number)

        else:
            seen_ids.add(user_id)

        # Vérifier que l'utilisateur est référencé
        if (
            isinstance(user_id, str)
            and user_id not in required_ids
        ):
            add_error("unreferenced_user", number)

        # Vérifier les autres champs
        validate_user(user, number)

    # 13. Vérifier les relations avec Reviews et Tips
    missing_ids = required_ids - seen_ids

    if missing_ids:
        errors["missing_referenced_users"] += len(missing_ids)

    # 14. Lire le rapport du filtre
    with FILTER_REPORT.open(
        "r", encoding="utf-8"
    ) as source:
        filter_report = json.load(source)

    if not isinstance(filter_report, dict):
        raise ValueError("Rapport de filtrage incorrect")

    if filter_report.get("status") != "COMPLETED":
        add_error("filter_not_completed")

    # 15. Comparer les compteurs calculés au rapport
    expected_values = {
        "review_documents": review_documents,
        "tip_documents": tip_documents,
        "unique_review_authors": len(review_ids),
        "unique_tip_authors": len(tip_ids),
        "required_unique_users": len(required_ids),
        "selected_users": total_users,
        "missing_referenced_users": len(missing_ids),
    }

    for field, actual_value in expected_values.items():

        if (
            type(filter_report.get(field)) is not int
            or filter_report[field] != actual_value
        ):
            add_error(f"report_mismatch_{field}")

    # 16. Vérifier les compteurs du fichier original
    source_total = filter_report.get("total_users_read")
    excluded = filter_report.get("excluded_not_referenced")

    if (
        not valid_nonnegative_integer(source_total)
        or not valid_nonnegative_integer(excluded)
        or source_total != excluded + total_users
    ):
        add_error("source_accounting_mismatch")

    # 17. Vérifier la règle d'exclusion de friends
    if filter_report.get("excluded_fields") != ["friends"]:
        add_error("excluded_fields_mismatch")

    # 18. Déterminer le statut final
    status = (
        "PASS"
        if total_users > 0 and not errors
        else "FAIL"
    )

    # 19. Préparer le rapport de validation
    report = {
        "dataset": "Yelp Tucson Users",
        "review_documents": review_documents,
        "tip_documents": tip_documents,
        "unique_review_authors": len(review_ids),
        "unique_tip_authors": len(tip_ids),
        "required_unique_users": len(required_ids),
        "total_users": total_users,
        "unique_user_ids": len(seen_ids),
        "missing_referenced_users": len(missing_ids),
        "errors": dict(sorted(errors.items())),
        "error_line_examples": examples,
        "status": status,
    }

    # 20. Enregistrer le rapport sur le Mac
    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        ) + "\n",
        encoding="utf-8"
    )

    # 21. Afficher les résultats
    print("\n=== VALIDATION USERS ===")
    print("Utilisateurs analysés :", total_users)
    print("Identifiants uniques :", len(seen_ids))
    print("Utilisateurs référencés requis :", len(required_ids))
    print("Utilisateurs manquants :", len(missing_ids))
    print("Erreurs :", dict(errors))
    print("Statut :", status)
    print("Rapport :", REPORT_FILE)

    if status == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    validate_users()
