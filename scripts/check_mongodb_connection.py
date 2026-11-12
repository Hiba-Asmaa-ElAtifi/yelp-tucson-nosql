
import os
from pymongo import MongoClient

mongo_uri = os.environ["MONGO_URI"]

client = MongoClient(
    mongo_uri,
    serverSelectionTimeoutMS=5000
)

try:
    result = client.admin.command("ping")

    if result.get("ok") == 1:
        print("Connexion Python vers MongoDB : PASS")
        print("Base prévue :", os.environ["MONGO_DATABASE"])
    else:
        raise RuntimeError("Réponse MongoDB inattendue")

finally:
    client.close()
