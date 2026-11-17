
import os
from pymongo import MongoClient

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://mongodb:27017/"
)
DB_NAME = os.getenv("MONGO_DB", "yelp_tucson")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

try:
    db.businesses.create_index(
        [("location", "2dsphere")],
        name="idx_businesses_location_2dsphere"
    )

    db.reviews.create_index(
        [("business_id", 1), ("date", -1)],
        name="idx_reviews_business_date"
    )

    db.tips.create_index(
        [("business_id", 1), ("date", -1)],
        name="idx_tips_business_date"
    )

    db.checkins.create_index(
        [("business_id", 1)],
        name="idx_checkins_business_id"
    )

    print("Les 4 index MongoDB sont disponibles.")

finally:
    client.close()
