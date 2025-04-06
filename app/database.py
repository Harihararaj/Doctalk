from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "dummy_db"
COLLECTION_NAME = "dummy_table"

def create_mongo_client():
    client = AsyncIOMotorClient(MONGO_URI)
    return client